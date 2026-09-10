"""Shared conversation/retrieval logic used by both the Streamlit UI and the CLI.

The original codebase duplicated the "retrieve context, then call the LLM"
flow separately in `app.py` and `main.py`, which meant the two interfaces
could silently drift out of sync. This module is the single place that logic
lives now; both entry points call `RagService.answer()`.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from backend.config import Settings
from backend.errors import OffTopicQueryError, QueryValidationError
from backend.llm_providers import ChatMessage, LLMProvider
from backend.rag_pipeline import RetrievedChunk, retrieve_relevant_chunks
from backend.tracing import traceable

logger = logging.getLogger(__name__)

# Shown verbatim to the user when the topic guard refuses a question, so it has
# to explain the boundary and point at something useful.
OFF_TOPIC_MESSAGE = (
    "I'm a career advisor, so I can only answer career-related questions — "
    "resumes, job search, interviews, skills, salaries, and career planning. "
    "Ask me something about your career and I'll help."
)


@dataclass(frozen=True)
class AnswerResult:
    text: str
    used_retrieval: bool
    sources: list[RetrievedChunk] = field(default_factory=list)


def validate_query(query: str, settings: Settings) -> str:
    query = (query or "").strip()
    if not query:
        raise QueryValidationError("Please enter a question.")
    if len(query) > settings.max_query_length:
        raise QueryValidationError(
            f"Your question is too long ({len(query)} characters). "
            f"Please keep it under {settings.max_query_length} characters."
        )
    return query


def trim_history(history: Sequence[ChatMessage], settings: Settings) -> list[ChatMessage]:
    """Keep only the most recent `max_history_turns` user/assistant exchanges.

    A "turn" is one user message + one assistant reply, so we keep the last
    `max_history_turns * 2` messages. This bounds prompt size/cost while still
    giving the model enough context for natural follow-up questions.
    """
    max_messages = settings.max_history_turns * 2
    if max_messages <= 0:
        return []
    return list(history[-max_messages:])


class RagService:
    """Ties together retrieval decision-making, document search, and generation."""

    def __init__(self, settings: Settings, llm_provider: LLMProvider, vectorstore=None):
        self._settings = settings
        self._llm = llm_provider
        self._vectorstore = vectorstore

    @property
    def has_document(self) -> bool:
        return self._vectorstore is not None

    @property
    def llm(self) -> LLMProvider:
        """Expose the underlying LLM provider so other features (e.g. the
        career-tools UI in `app.py`) can reuse the same configured client
        instead of constructing a second one."""
        return self._llm

    def set_vectorstore(self, vectorstore) -> None:
        self._vectorstore = vectorstore

    @traceable(name="RagService.answer", run_type="chain")
    def answer(
        self,
        query: str,
        history: Sequence[ChatMessage] | None = None,
        student_profile: str = "",
    ) -> AnswerResult:
        query = validate_query(query, self._settings)
