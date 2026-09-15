"""Smoke tests for mcp_server.py.

These don't spin up a real MCP transport — they import the module (which
requires GOOGLE_API_KEY to be set, same as every other entry point) and call
the underlying tool functions directly, verifying they're registered and
return the expected shape when the LLM layer is mocked out.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("GOOGLE_API_KEY", "test-key")

import backend.mcp_server as mcp_server  # noqa: E402


class TestMcpToolsRegistered(unittest.TestCase):
    def test_expected_tools_are_registered(self):
        # FastMCP tools are wrapped; the underlying functions keep their names.
        tool_names = {
            "job_search",
            "skill_gap_analyzer",
            "resume_analyzer",
            "career_roadmap_generator",
            "analyze_uploaded_resume",
        }
        for name in tool_names:
            self.assertTrue(hasattr(mcp_server, name), f"expected mcp_server.{name} to exist")


class TestJobSearchTool(unittest.TestCase):
    def test_job_search_returns_jobs_key(self):
        result = mcp_server.job_search("Data Analyst")
        self.assertIn("jobs", result)
        self.assertIn("count", result)

    def test_job_search_handles_empty_role(self):
        result = mcp_server.job_search("")
        self.assertIn("error", result)


class TestSkillGapTool(unittest.TestCase):
    @patch("backend.mcp_server._get_provider")
    @patch("backend.career_tools._generate_json")
    def test_skill_gap_analyzer_returns_expected_keys(self, mock_generate_json, mock_get_provider):
        mock_generate_json.return_value = {
            "matched_skills": ["Python"],
            "missing_skills": ["SQL"],
            "partially_met_skills": [],
            "overall_readiness": "medium",
            "summary": "Good start.",
        }
        mock_get_provider.return_value = MagicMock()
        result = mcp_server.skill_gap_analyzer(["Python"], "Data Analyst")
        self.assertEqual(result["matched_skills"], ["Python"])
        self.assertEqual(result["overall_readiness"], "medium")


if __name__ == "__main__":
    unittest.main()
