"""LangSmith integration: tracing for observability, plus an evaluation harness.

Why this exists: once the app grew MCP tools (job search, skill-gap analysis,
resume analysis, roadmap generation) on top of the RAG chat flow, "does this
prompt still work" stopped being something we could eyeball. LangSmith gives
us two things from one integration:

1. **Tracing** — every LLM call and tool invocation is logged as a run (with
   inputs/outputs/latency) when `LANGSMITH_TRACING=true` and an API key is
   configured. This module owns turning that on exactly once, consistently,
   for every entry point (CLI, Streamlit, MCP server).

2. **Evaluation** — `evaluation.py` uses `langsmith.evaluate()` against a
   small hand-written dataset of career-advisor questions so prompt/model
   changes can be checked for regressions instead of guessed at.

Tracing is strictly additive: if LangSmith isn't configured, `traceable`
degrades to a plain pass-through decorator and the app behaves exactly as it
did before this module existed.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import TypeVar

from backend.config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable)

_configured = False
_tracing_active = False


def configure_langsmith(settings: Settings) -> bool:
    """Set the LANGCHAIN_* / LANGSMITH_* env vars LangSmith's SDK reads.

    Idempotent and safe to call from every entry point (CLI, Streamlit, MCP
    server) — only the first call has any effect. Returns True if tracing is
    active after this call.
    """
    global _configured, _tracing_active
    if _configured:
        return _tracing_active

    if settings.langsmith_tracing_enabled:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
        if settings.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
            os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        logger.info("LangSmith tracing enabled (project=%s)", settings.langsmith_project)
    else:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.info("LangSmith tracing disabled")

    _configured = True
    _tracing_active = settings.langsmith_tracing_enabled
    return _tracing_active


def _identity_decorator(*_args, **_kwargs):
    """Fallback used when the `langsmith` package can't be imported.

    Mirrors `langsmith.traceable`'s calling convention (usable bare as
    `@traceable` or parameterized as `@traceable(name=..., run_type=...)`)
    so call sites never need to know whether real tracing is active.
    """

    def decorator(func: T) -> T:
        return func

    if len(_args) == 1 and callable(_args[0]) and not _kwargs:
        return _args[0]
    return decorator


try:
    from langsmith import traceable as _langsmith_traceable

    traceable = _langsmith_traceable
except ImportError:  # pragma: no cover - langsmith is an optional dependency
    logger.warning("langsmith package not installed; tracing calls will be no-ops")
    traceable = _identity_decorator
