import os
import unittest
from types import SimpleNamespace

import backend.tracing as tracing


class TestConfigureLangsmith(unittest.TestCase):
    def setUp(self):
        self._original_environ = dict(os.environ)
        tracing._configured = False
        tracing._tracing_active = False
        for key in [
            "LANGSMITH_TRACING",
            "LANGCHAIN_TRACING_V2",
            "LANGSMITH_API_KEY",
            "LANGCHAIN_API_KEY",
            "LANGSMITH_PROJECT",
            "LANGCHAIN_PROJECT",
            "LANGSMITH_ENDPOINT",
            "LANGCHAIN_ENDPOINT",
        ]:
            os.environ.pop(key, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._original_environ)
        tracing._configured = False
        tracing._tracing_active = False

    def _settings(self, **overrides):
        defaults = dict(
            langsmith_tracing_enabled=False,
            langsmith_api_key=None,
            langsmith_project="career-advisor",
            langsmith_endpoint="https://api.smith.langchain.com",
        )
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_disabled_sets_tracing_env_to_false(self):
        result = tracing.configure_langsmith(self._settings())
        self.assertFalse(result)
        self.assertEqual(os.environ["LANGSMITH_TRACING"], "false")

    def test_enabled_sets_expected_env_vars(self):
        settings = self._settings(langsmith_tracing_enabled=True, langsmith_api_key="ls-key")
        result = tracing.configure_langsmith(settings)
        self.assertTrue(result)
        self.assertEqual(os.environ["LANGSMITH_TRACING"], "true")
        self.assertEqual(os.environ["LANGSMITH_API_KEY"], "ls-key")
        self.assertEqual(os.environ["LANGSMITH_PROJECT"], "career-advisor")

    def test_second_call_is_a_no_op(self):
        tracing.configure_langsmith(
            self._settings(langsmith_tracing_enabled=True, langsmith_api_key="ls-key")
        )
        # Second call with different settings shouldn't change anything —
        # configuration happens once per process.
        result = tracing.configure_langsmith(self._settings(langsmith_tracing_enabled=False))
        self.assertTrue(result)


class TestTraceableFallback(unittest.TestCase):
    def test_bare_decorator_returns_original_function(self):
        @tracing._identity_decorator
        def add(a, b):
            return a + b

        self.assertEqual(add(2, 3), 5)

    def test_parameterized_decorator_returns_original_function(self):
        @tracing._identity_decorator(name="add", run_type="tool")
        def add(a, b):
            return a + b

        self.assertEqual(add(2, 3), 5)


if __name__ == "__main__":
    unittest.main()
