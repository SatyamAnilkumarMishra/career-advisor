"""Career Advisor MCP server.

Exposes the four career tools over the Model Context Protocol so any MCP
client (Claude Desktop, Claude Code, other agents) can call them directly,
independent of this project's own Streamlit UI / CLI.

Run standalone:
    python mcp_server.py

Or register it with an MCP client, e.g. in Claude Desktop's config:
    {
      "mcpServers": {
        "career-advisor": {
          "command": "python",
          "args": ["/absolute/path/to/mcp_server.py"]
        }
      }
    }

All four tools share the exact same logic as the Streamlit "Tools" tabs and
the LangSmith evaluation harness — they all call into `career_tools.py`, so
behavior can't drift between entry points (same principle as `rag_service.py`
being the single shared brain behind `app.py` and `main.py`).
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from backend.config import configure_logging, get_settings
from backend.errors import CareerAdvisorError
from backend.tracing import configure_langsmith

logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None

if FastMCP is not None:
    _settings = get_settings()
    configure_logging(_settings)
    configure_langsmith(_settings)
    mcp = FastMCP(_settings.mcp_server_name)
    mcp_tool = mcp.tool
else:
    _settings = get_settings()
    mcp = None
    def mcp_tool():  # pragma: no cover
        def decorator(fn):
            return fn
        return decorator

_provider = None


def _get_provider():
    """Lazily build the shared LLM provider so `python mcp_server.py --help`-style
    introspection doesn't require a live API key until a tool actually runs."""
    global _provider
    if _provider is None:
        from backend.llm_providers import create_llm_provider

        _provider = create_llm_provider(_settings)
    return _provider


@mcp_tool()
def job_search(
    role: str,
    skills: list[str] | None = None,
    location: str | None = None,
    experience_level: str | None = None,
    limit: int | None = None,
) -> dict:
    """Search for jobs by role, skills, location, and experience level.

    Args:
        role: Job title or role to search for, e.g. "Data Analyst".
        skills: Optional list of skills to match against, e.g. ["SQL", "Python"].
        location: Optional location filter, e.g. "Remote" or "Chicago, IL".
        experience_level: Optional level filter: "entry", "mid", or "senior".
        limit: Maximum number of results to return.
    """
    from backend.career_tools import search_jobs

    try:
        listings = search_jobs(
            role,
            _settings,
            skills=skills,
            location=location,
            experience_level=experience_level,
            limit=limit,
        )
        return {"jobs": [asdict(job) for job in listings], "count": len(listings)}
    except CareerAdvisorError as exc:
        return {"error": exc.user_message}


@mcp_tool()
def skill_gap_analyzer(user_skills: list[str], target_role: str) -> dict:
    """Compare a user's current skills against a target role and identify gaps.

    Args:
        user_skills: List of the user's current skills.
        target_role: The role the user is targeting, e.g. "Frontend Engineer".
    """
    from backend.career_tools import analyze_skill_gap

    try:
        result = analyze_skill_gap(user_skills, target_role, _get_provider())
        return asdict(result)
    except CareerAdvisorError as exc:
        return {"error": exc.user_message}


@mcp_tool()
def resume_analyzer(resume_text: str, target_role: str | None = None) -> dict:
    """Extract skills from resume text and identify missing or improvable areas.

    Args:
        resume_text: Plain text content of the resume (already extracted from
            the uploaded file — see `resume_pipeline.extract_resume_text`).
        target_role: Optional target role to evaluate the resume against.
    """
    from backend.career_tools import analyze_resume

    try:
        result = analyze_resume(resume_text, _get_provider(), target_role=target_role)
        return asdict(result)
    except CareerAdvisorError as exc:
        return {"error": exc.user_message}


@mcp_tool()
def career_roadmap_generator(
    current_skills: list[str], target_role: str, timeframe_months: int = 6
) -> dict:
    """Generate a structured, milestone-based learning roadmap toward a target role.

    Args:
        current_skills: List of the user's current skills.
        target_role: The role the roadmap should lead toward.
        timeframe_months: Desired total timeframe in months (1-36).
    """
    from backend.career_tools import generate_roadmap

    try:
        result = generate_roadmap(
            current_skills, target_role, _get_provider(), timeframe_months=timeframe_months
        )
        return {
            "target_role": result.target_role,
            "summary": result.summary,
            "milestones": [asdict(m) for m in result.milestones],
        }
    except CareerAdvisorError as exc:
        return {"error": exc.user_message}


@mcp_tool()
def analyze_uploaded_resume(file_path: str, target_role: str | None = None) -> dict:
    """Extract text from a resume file on disk (PDF/DOCX/TXT) and analyze it in one step.

    Args:
        file_path: Absolute path to the resume file.
        target_role: Optional target role to evaluate the resume against.
    """
    from backend.career_tools import analyze_resume
    from backend.resume_pipeline import extract_resume_text

    try:
        text = extract_resume_text(file_path, _settings)
        result = analyze_resume(text, _get_provider(), target_role=target_role)
        return asdict(result)
    except CareerAdvisorError as exc:
        return {"error": exc.user_message}


if __name__ == "__main__":
    logger.info("Starting Career Advisor MCP server (transport=%s)", _settings.mcp_transport)
    mcp.run(transport=_settings.mcp_transport)
