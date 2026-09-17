import sys
import types
import unittest
from unittest.mock import MagicMock

from backend.errors import LLMError
from backend.llm_providers import ChatMessage, GeminiProvider


class _FakeCandidate:
    def __init__(self, finish_reason=None):
        self.finish_reason = finish_reason


class _FakeResponse:
    """Mimics google.genai types.GenerateContentResponse closely enough."""

    def __init__(self, text="", candidates=None, prompt_feedback=None):
        self.text = text
        self.candidates = candidates or []
        self.prompt_feedback = prompt_feedback


class _FakeFinishReason:
    def __init__(self, name):
        self.name = name


_SAVED_MODULES = {}


def _install_fake_genai(generate_content_impl):
    """Inject a fake `google.genai` module so GeminiProvider can be exercised
    without the real package or any network call."""
    for mod in ("google", "google.genai", "google.genai.types"):
        if mod not in _SAVED_MODULES:
            _SAVED_MODULES[mod] = sys.modules.get(mod)

    fake_models = MagicMock()
    fake_models.generate_content.side_effect = generate_content_impl

    fake_client = MagicMock()
    fake_client.models = fake_models

    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = MagicMock(return_value=fake_client)

    fake_types = types.ModuleType("google.genai.types")
    fake_types.HttpOptions = MagicMock()
    fake_types.GenerateContentConfig = MagicMock()
    fake_types.AutomaticFunctionCallingConfig = MagicMock()

    fake_genai.types = fake_types

    # Preserve any existing google submodules (like auth) on fake_google
    fake_google = types.ModuleType("google")
    orig_google = _SAVED_MODULES.get("google")
    if orig_google:
        for attr in dir(orig_google):
            if not attr.startswith("__"):
                try:
                    setattr(fake_google, attr, getattr(orig_google, attr))
                except Exception:
                    pass
    fake_google.genai = fake_genai

    sys.modules["google"] = fake_google
    sys.modules["google.genai"] = fake_genai
    sys.modules["google.genai.types"] = fake_types
    return fake_models


class TestGeminiProvider(unittest.TestCase):
    def tearDown(self):
        for mod, orig in _SAVED_MODULES.items():
            if orig is None:
                sys.modules.pop(mod, None)
            else:
                sys.modules[mod] = orig

    def _provider(self, **kwargs):
        kwargs.setdefault("api_key", "fake-key")
        kwargs.setdefault("model_name", "gemini-flash-latest")
        kwargs.setdefault("max_retries", 0)
        return GeminiProvider(**kwargs)

    # --- happy path -------------------------------------------------------

    def test_generate_builds_prompt_and_returns_text(self):
        models = _install_fake_genai(lambda **k: _FakeResponse("Here's some career advice."))
        provider = self._provider()

        result = provider.generate(
            [ChatMessage(role="user", content="What skills do I need for data science?")],
            system_instruction="Be concise.",
        )
        self.assertEqual(result, "Here's some career advice.")

        # The prompt must carry both the system instruction and the user turn.
        _, kwargs = models.generate_content.call_args
        self.assertEqual(kwargs["model"], "gemini-flash-latest")
        self.assertIn("Be concise.", kwargs["contents"])
        self.assertIn("What skills do I need for data science?", kwargs["contents"])

    def test_generate_includes_prior_history_in_order(self):
        models = _install_fake_genai(lambda **k: _FakeResponse("ok"))
        provider = self._provider()
        provider.generate(
            [
                ChatMessage(role="user", content="FIRST_TURN"),
                ChatMessage(role="assistant", content="SECOND_TURN"),
                ChatMessage(role="user", content="THIRD_TURN"),
            ]
        )
        contents = models.generate_content.call_args.kwargs["contents"]
        self.assertLess(contents.index("FIRST_TURN"), contents.index("SECOND_TURN"))
        self.assertLess(contents.index("SECOND_TURN"), contents.index("THIRD_TURN"))

    # --- retrieval routing ------------------------------------------------

    def test_decide_needs_retrieval_true_on_yes(self):
        _install_fake_genai(lambda **k: _FakeResponse("YES"))
        self.assertTrue(
            self._provider().decide_needs_retrieval("What does the document say about resumes?")
        )

    def test_decide_needs_retrieval_false_on_no(self):
        _install_fake_genai(lambda **k: _FakeResponse("NO"))
        self.assertFalse(
            self._provider().decide_needs_retrieval("What should I wear to an interview?")
        )

    def test_decide_needs_retrieval_defaults_true_on_failure(self):
        def _boom(**k):
            raise RuntimeError("API is down")

        _install_fake_genai(_boom)
        self.assertTrue(self._provider().decide_needs_retrieval("anything"))

    # --- failure diagnosis ------------------------------------------------

    def test_empty_response_raises_llm_error(self):
        _install_fake_genai(lambda **k: _FakeResponse(""))
        with self.assertRaises(LLMError):
            self._provider().generate([ChatMessage(role="user", content="hello")])

    def test_safety_block_reports_safety_not_api_key(self):
        _install_fake_genai(
            lambda **k: _FakeResponse(
                "", candidates=[_FakeCandidate(_FakeFinishReason("SAFETY"))]
            )
        )
        with self.assertRaises(LLMError) as ctx:
            self._provider().generate([ChatMessage(role="user", content="hello")])
        self.assertIn("safety", ctx.exception.user_message.lower())
        self.assertNotIn("api key", ctx.exception.user_message.lower())

    def test_max_tokens_reports_truncation(self):
        _install_fake_genai(
            lambda **k: _FakeResponse(
                "", candidates=[_FakeCandidate(_FakeFinishReason("MAX_TOKENS"))]
            )
        )
        with self.assertRaises(LLMError) as ctx:
            self._provider().generate([ChatMessage(role="user", content="hello")])
        self.assertIn("cut off", ctx.exception.user_message.lower())

    def test_bad_api_key_is_reported_clearly_and_not_retried_across_models(self):
        calls = []

        def _unauthorized(**k):
            calls.append(k["model"])
            raise RuntimeError("401 UNAUTHENTICATED: API key not valid")

        _install_fake_genai(_unauthorized)
        with self.assertRaises(LLMError) as ctx:
            self._provider().generate([ChatMessage(role="user", content="hello")])

        self.assertIn("api key", ctx.exception.user_message.lower())
        # A rejected key must fail fast, not burn through every fallback model.
        self.assertEqual(len(set(calls)), 1)

    def test_missing_model_falls_back_to_next_candidate(self):
        def _first_model_missing(**k):
            if k["model"] == "does-not-exist":
                raise RuntimeError("404 model not found")
            return _FakeResponse("fallback answer")

        _install_fake_genai(_first_model_missing)
        provider = self._provider(model_name="does-not-exist")
        self.assertEqual(
            provider.generate([ChatMessage(role="user", content="hi")]), "fallback answer"
        )

    def test_blank_api_key_fails_before_any_call(self):
        _install_fake_genai(lambda **k: _FakeResponse("unused"))
        with self.assertRaises(LLMError):
            GeminiProvider(api_key="   ", model_name="gemini-flash-latest")
        with self.assertRaises(LLMError):
            GeminiProvider(api_key="your_google_api_key_here", model_name="gemini-flash-latest")

    def test_transient_error_is_retried_on_same_model(self):
        attempts = {"n": 0}

        def _flaky(**k):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise RuntimeError("503 Service Unavailable")
            return _FakeResponse("recovered")

        _install_fake_genai(_flaky)
        provider = self._provider(max_retries=3)
        self.assertEqual(
            provider.generate([ChatMessage(role="user", content="hi")]), "recovered"
        )
        self.assertEqual(attempts["n"], 3)


class TestGroqProvider(unittest.TestCase):
    def test_blank_groq_api_key_fails(self):
        from backend.llm_providers import GroqProvider

        with self.assertRaises(LLMError):
            GroqProvider(api_key="   ")
        with self.assertRaises(LLMError):
            GroqProvider(api_key="your_groq_api_key_here")

    def test_groq_generate_mock(self):
        from backend.llm_providers import GroqProvider

        fake_choice = MagicMock()
        fake_choice.message.content = "Groq advice"
        fake_completion = MagicMock()
        fake_completion.choices = [fake_choice]

        provider = GroqProvider(api_key="gsk_valid_key")
        provider._client.chat.completions.create = MagicMock(return_value=fake_completion)

        response = provider.generate([ChatMessage(role="user", content="help me")])
        self.assertEqual(response, "Groq advice")

    def test_create_llm_provider_factory(self):
        from backend.config import Settings
        from backend.llm_providers import GeminiProvider, GroqProvider, create_llm_provider

        groq_settings = Settings(
            llm_provider="groq",
            groq_api_key="gsk_123",
            google_api_key="goog_123",
        )
        p1 = create_llm_provider(groq_settings)
        self.assertIsInstance(p1, GroqProvider)

        gemini_settings = Settings(
            llm_provider="gemini",
            google_api_key="goog_123",
        )
        p2 = create_llm_provider(gemini_settings)
        self.assertIsInstance(p2, GeminiProvider)


if __name__ == "__main__":
    unittest.main()
