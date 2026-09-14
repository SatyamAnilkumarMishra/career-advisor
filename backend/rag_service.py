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

        # Topic guard runs before anything expensive: an out-of-scope question
        # costs one short classification call and never reaches retrieval or
        # generation.
        if getattr(self._settings, "strict_career_only", True):
            if not self._llm.is_career_related(query):
                raise OffTopicQueryError(OFF_TOPIC_MESSAGE)

        history = trim_history(history or [], self._settings)

        sources: list[RetrievedChunk] = []
        used_retrieval = False

        if self.has_document:
            needs_retrieval = self._llm.decide_needs_retrieval(query)
            if needs_retrieval:
                sources = retrieve_relevant_chunks(self._vectorstore, query, self._settings)
                used_retrieval = bool(sources)

        system_instruction = self._build_system_instruction(sources, student_profile)
        messages = list(history) + [ChatMessage(role="user", content=query)]
        text = self._llm.generate(messages, system_instruction=system_instruction)

        return AnswerResult(text=text, used_retrieval=used_retrieval, sources=sources)

    @staticmethod
    def _build_system_instruction(sources: list[RetrievedChunk], student_profile: str) -> str:
        parts = [
            "ROLE & TONE:\n"
            "You are a knowledgeable, professional career and research assistant.\n"
            "Your tone is clear, warm, and professional — like a knowledgeable human expert, not a corporate template generator.",
            "RESPONSE STYLE & FORMATTING RULES:\n"
            "1. NO EMOJIS: Do NOT use emojis anywhere in responses (no decorative symbols or icons like 🎯, ✦, 📅, ✅, 🚀, etc.).\n"
            "2. DEFAULT TO PROSE: The response should primarily be well-written text — tables are the exception, not the default structure.\n"
            "3. WHEN TO USE TABLES: Only convert content into a table when it is genuinely comparative data across 3+ items with 2-4 shared attributes (e.g., comparing salaries across specialties, comparing program lengths and degrees). If it can be said clearly in a sentence or a short bullet list, do NOT make it a table.\n"
            "4. NEVER use a table for a single column of items, a single list of steps, or a simple sequence — use plain bullets or numbered prose instead.\n"
            "5. READABILITY: A response should read as text first, with a table dropped in only where it genuinely aids comparison — the way a knowledgeable expert would structure an answer, not a page built entirely out of tables.\n"
            "6. HEADERS: Use markdown headers (##, ###) sparingly — only when the content has multiple genuinely distinct sections. Keep section headers concise and skip redundant ones like 'Quick-Start Checklist' unless requested.\n"
            "7. NO DECORATIVE SYMBOLS: Do not put decorative symbols or icons before headers.\n"
            "8. BULLETS: Avoid nesting bullet points more than one level deep. Use bullets only for genuinely list-like information (e.g., a sequence of steps, a set of options).\n"
            "9. NATURAL STRUCTURE: Do not use bold text as a substitute for structure (e.g., no 'Action Items' bolded headers repeated after every section) — integrate next steps naturally into the text.\n"
            "10. NO CHECKLISTS: Avoid checkbox-style or copy-paste 'checklist' formatting unless the user explicitly asks for a checklist.\n"
            "11. COMPLETE SENTENCES: Write in complete sentences and flowing paragraphs by default.\n"
            "12. DEPTH & LENGTH: Match response depth to the complexity of the question. Do not pad with exhaustive sub-tables, salary breakdowns, or timelines unless the user asks for that level of detail. Summarize first, then offer to go deeper if useful.\n"
            "13. STRUCTURE GUIDANCE: Default to a short intro, 2-4 well-organized sections in prose (with headers only if needed and a table only where comparison genuinely helps), and a brief closing note or next-step suggestion — not a rigid numbered template applied to every query type.",
            "THINGS TO AVOID:\n"
            "- Decorative symbols or icons before headers\n"
            "- Repeating the same boilerplate section labels (e.g., 'Action Items') after every subsection\n"
            "- Turning simple lists into multi-column tables\n"
            "- Building the entire response out of tables instead of text\n"
            "- Overly long, template-driven roadmaps when a direct answer would suffice",
            "CONTENT & FACTUAL GROUNDING RULES:\n"
            "- Ground all factual claims in the retrieved context; do not fabricate statistics, salary figures, or timelines not present in the source documents.\n"
            "- If specific data (e.g., salary numbers, dates, costs) isn't in the retrieved context, state that clearly instead of inventing plausible-looking numbers.\n"
            "- Cite or reference the source material naturally when relevant, without exposing raw retrieval mechanics to the user."
        ]

        if student_profile.strip():
            parts.append(f"User Background & Profile Context:\n{student_profile.strip()}")

        if sources:
            context_block = "\n\n".join(
                f"[Source, page {c.page if c.page is not None else '?'}]: {c.content}"
                for c in sources
            )
            parts.append(
                "Relevant excerpts from the user's uploaded/reference document are below. "
                "Use them where they help answer the question, and rely on your "
                "own general knowledge where they don't cover something:\n\n"
                f"{context_block}"
            )
        else:
            parts.append(
                "No document context was retrieved for this question — answer from "
                "general career and research knowledge following the above guidelines."
            )

        return "\n\n".join(parts)
