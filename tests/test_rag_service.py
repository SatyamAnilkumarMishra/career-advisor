import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.errors import OffTopicQueryError, QueryValidationError
from backend.llm_providers import ChatMessage, LLMProvider, is_off_topic_verdict
from backend.rag_service import RagService, trim_history, validate_query


def _settings(**overrides):
    defaults = dict(
        max_query_length=2000,
        max_history_turns=2,
        max_context_docs=3,
        relevance_score_threshold=0.35,
        strict_career_only=True,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class FakeLLMProvider(LLMProvider):
    """Minimal in-memory stand-in for LLMProvider, used across tests instead
    of hitting a real model or even the fake-genai plumbing."""

    def __init__(self, needs_retrieval=True, response="Here is your answer.", career_related=True):
        self.needs_retrieval = needs_retrieval
        self.response = response
        self.career_related = career_related
        self.last_messages = None
        self.last_system_instruction = None

    def generate(self, messages, *, system_instruction=""):
        self.last_messages = list(messages)
        self.last_system_instruction = system_instruction
        return self.response

    def decide_needs_retrieval(self, query):
        return self.needs_retrieval

    def is_career_related(self, query):
        return self.career_related


class TestValidateQuery(unittest.TestCase):
    def test_empty_query_raises(self):
        with self.assertRaises(QueryValidationError):
            validate_query("   ", _settings())

    def test_too_long_query_raises(self):
        with self.assertRaises(QueryValidationError):
            validate_query("x" * 50, _settings(max_query_length=10))

    def test_valid_query_is_stripped(self):
        self.assertEqual(validate_query("  hello  ", _settings()), "hello")


class TestTrimHistory(unittest.TestCase):
    def test_keeps_only_last_n_turns(self):
        history = [
            ChatMessage(role="user" if i % 2 == 0 else "assistant", content=str(i))
            for i in range(10)
        ]
        trimmed = trim_history(history, _settings(max_history_turns=2))
        self.assertEqual(len(trimmed), 4)
        self.assertEqual([m.content for m in trimmed], ["6", "7", "8", "9"])

    def test_zero_turns_returns_empty(self):
        history = [ChatMessage(role="user", content="hi")]
        self.assertEqual(trim_history(history, _settings(max_history_turns=0)), [])


class TestRagServiceAnswer(unittest.TestCase):
    def test_answers_without_document(self):
        provider = FakeLLMProvider()
        service = RagService(_settings(), provider, vectorstore=None)

        result = service.answer("What skills matter for data science?")

        self.assertFalse(result.used_retrieval)
        self.assertEqual(result.sources, [])
        self.assertEqual(result.text, "Here is your answer.")

    def test_retrieves_when_document_present_and_needed(self):
        provider = FakeLLMProvider(needs_retrieval=True)
        vectorstore = MagicMock()
        vectorstore.similarity_search_with_relevance_scores.return_value = [
            (SimpleNamespace(page_content="relevant excerpt", metadata={"page": 3}), 0.8),
        ]
        service = RagService(_settings(), provider, vectorstore=vectorstore)

        result = service.answer("What does the guide say about resumes?")

        self.assertTrue(result.used_retrieval)
        self.assertEqual(len(result.sources), 1)
        self.assertIn("relevant excerpt", provider.last_system_instruction)

    def test_skips_retrieval_when_llm_decides_not_needed(self):
        provider = FakeLLMProvider(needs_retrieval=False)
        vectorstore = MagicMock()
        service = RagService(_settings(), provider, vectorstore=vectorstore)

        result = service.answer("What should I wear to an interview?")

        vectorstore.similarity_search_with_relevance_scores.assert_not_called()
        self.assertFalse(result.used_retrieval)
        self.assertEqual(result.sources, [])

    def test_history_is_passed_through_to_provider(self):
        provider = FakeLLMProvider()
        service = RagService(_settings(), provider, vectorstore=None)
        history = [ChatMessage(role="user", content="first question")]

        service.answer("follow-up question", history=history)

        contents = [m.content for m in provider.last_messages]
        self.assertIn("first question", contents)
        self.assertIn("follow-up question", contents)

    def test_invalid_query_raises_before_calling_provider(self):
        provider = FakeLLMProvider()
        service = RagService(_settings(), provider, vectorstore=None)

        with self.assertRaises(QueryValidationError):
            service.answer("   ")
        self.assertIsNone(provider.last_messages)


class TestCareerTopicGuard(unittest.TestCase):
    """The assistant is scoped to career advice: anything else is refused."""

    def test_off_topic_query_is_refused(self):
        provider = FakeLLMProvider(career_related=False)
        service = RagService(_settings(), provider, vectorstore=None)

        with self.assertRaises(OffTopicQueryError):
            service.answer("who is the prime minister of India")

    def test_refusal_happens_before_generation(self):
        """An off-topic question must not cost a generation call."""
        provider = FakeLLMProvider(career_related=False)
        service = RagService(_settings(), provider, vectorstore=None)

        with self.assertRaises(OffTopicQueryError):
            service.answer("list indian actors")

        self.assertIsNone(provider.last_messages)

    def test_refusal_happens_before_retrieval(self):
        """...nor a vector search."""
        provider = FakeLLMProvider(career_related=False, needs_retrieval=True)
        vectorstore = MagicMock()
        service = RagService(_settings(), provider, vectorstore=vectorstore)

        with self.assertRaises(OffTopicQueryError):
            service.answer("who won the cricket world cup")

        vectorstore.similarity_search_with_relevance_scores.assert_not_called()

    def test_refusal_message_explains_the_scope(self):
        provider = FakeLLMProvider(career_related=False)
        service = RagService(_settings(), provider, vectorstore=None)

        with self.assertRaises(OffTopicQueryError) as ctx:
            service.answer("what is the capital of France")

        self.assertIn("career", ctx.exception.user_message.lower())

    def test_career_query_is_answered(self):
        provider = FakeLLMProvider(career_related=True)
        service = RagService(_settings(), provider, vectorstore=None)

        result = service.answer("how do I become a machine learning engineer")

        self.assertEqual(result.text, "Here is your answer.")

    def test_guard_can_be_disabled_by_config(self):
        provider = FakeLLMProvider(career_related=False)
        service = RagService(_settings(strict_career_only=False), provider, vectorstore=None)

        result = service.answer("who is the prime minister of India")

        self.assertEqual(result.text, "Here is your answer.")

    def test_guard_defaults_to_on_when_setting_is_absent(self):
        """Settings objects predating the flag must still be guarded."""
        settings = _settings()
        del settings.strict_career_only
        provider = FakeLLMProvider(career_related=False)

        with self.assertRaises(OffTopicQueryError):
            RagService(settings, provider, vectorstore=None).answer("list indian actors")


class TestOffTopicVerdictParsing(unittest.TestCase):
    """The guard refuses only on an explicit verdict — everything else is allowed."""

    def test_explicit_refusal_is_recognised(self):
        for reply in ("OFF_TOPIC", "off_topic", "  OFF_TOPIC  ", "OFF_TOPIC.", "Off topic"):
            with self.subTest(reply=reply):
                self.assertTrue(is_off_topic_verdict(reply))

    def test_career_verdict_allows(self):
        for reply in ("CAREER", "career", "  Career  "):
            with self.subTest(reply=reply):
                self.assertFalse(is_off_topic_verdict(reply))

    def test_unrecognised_replies_fail_open(self):
        for reply in ("", "   ", "I'm not sure", "Here is your answer.", None):
            with self.subTest(reply=reply):
                self.assertFalse(is_off_topic_verdict(reply))


class TestBaseProviderTopicGuard(unittest.TestCase):
    """The default `is_career_related` routes through generate() so providers
    that don't override it still get guarded."""

    class _MinimalProvider(LLMProvider):
        def __init__(self, reply="CAREER", raises=False):
            self.reply = reply
            self.raises = raises
            self.prompts = []

        def generate(self, messages, *, system_instruction=""):
            if self.raises:
                raise RuntimeError("provider is down")
            self.prompts.append(messages[-1].content)
            return self.reply

        def decide_needs_retrieval(self, query):
            return False

    def test_off_topic_reply_refuses(self):
        provider = self._MinimalProvider(reply="OFF_TOPIC")
        self.assertFalse(provider.is_career_related("who is the prime minister of India"))

    def test_career_reply_allows(self):
        provider = self._MinimalProvider(reply="CAREER")
        self.assertTrue(provider.is_career_related("how do I write a resume"))

    def test_query_is_included_in_the_prompt(self):
        provider = self._MinimalProvider()
        provider.is_career_related("list indian actors")
        self.assertIn("list indian actors", provider.prompts[0])

    def test_provider_failure_fails_open(self):
        provider = self._MinimalProvider(raises=True)
        self.assertTrue(provider.is_career_related("how do I negotiate salary"))


if __name__ == "__main__":
    unittest.main()
