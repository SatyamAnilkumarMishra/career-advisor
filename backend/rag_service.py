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
            "DOMAIN & FIELD ORIENTATION (CRITICAL):\n"
            "- Tailor every response strictly and specifically to the profession, industry, discipline, or field asked about in the user's prompt (e.g., healthcare/medicine, finance/accounting, civil/mechanical/chemical engineering, marketing/sales, law, human resources, teaching/education, design, trades, etc.).\n"
            "- DO NOT DEFAULT TO SOFTWARE OR CODING: Never assume or steer towards software engineering, programming (Python, JavaScript, etc.), Git/GitHub, LeetCode, or IT paradigms unless the user explicitly asks about software development, data science, or computing careers.\n"
            "- FIELD-AUTHENTIC CREDENTIALS & SKILLS: Ensure all advice, terminology, skills, and learning resources are native to the specific field in question (e.g., clinical credentials/NCLEX for healthcare; CPA/CFA for finance; FE/PE/CAD for physical engineering; SHRM for HR; Bar exam for law; HubSpot/Google Analytics for digital marketing; PMP for general project management).\n\n"
            "RESPONSE STYLE & FORMATTING RULES:\n"
            "1. NO EMOJIS: Do NOT use emojis anywhere in responses (no decorative symbols or icons like 🎯, ✦, 📅, ✅, 🚀, etc.).\n"
            "2. DEFAULT TO PROSE: The response should primarily be well-written text — tables are used selectively for structured information.\n"
            "3. WHEN TO USE TABLES:\n"
            "   a. LEARNING RESOURCES: Whenever you suggest or recommend learning resources, courses, books, certifications, or tutorials, ALWAYS format them as a structured markdown table with columns such as Resource Name, Platform / Provider, Key Skills Covered, and Level / Type. The resources must be strictly relevant to the specific domain asked about.\n"
            "   b. COMPARISONS: Use tables when presenting comparative data across 3+ items with shared attributes (e.g., comparing salaries, job roles, or program lengths). Outside of learning resources and comparative data, explain concepts in natural prose.\n"
            "4. NEVER use a table for a single column of items, a single list of steps, or a simple sequence — use plain bullets or numbered prose instead.\n"
            "5. READABILITY: A response should read as text first, with the learning resources table or comparative table embedded seamlessly.\n"
            "6. HEADERS: Use markdown headers (##, ###) sparingly — only when the content has multiple genuinely distinct sections. Keep section headers concise.\n"
            "7. NO DECORATIVE SYMBOLS: Do not put decorative symbols or icons before headers.\n"
            "8. BULLETS: Avoid nesting bullet points more than one level deep. Use bullets only for genuinely list-like information.\n"
            "9. NATURAL STRUCTURE: Integrate next steps naturally into the text without repeating rigid bold boilerplate headers.\n"
            "10. NO CHECKLISTS: Avoid checkbox-style formatting unless the user explicitly asks for a checklist.\n"
            "11. COMPLETE SENTENCES: Write in complete sentences and flowing paragraphs by default.\n"
            "12. DEPTH & LENGTH: Match response depth to the complexity of the question. Summarize clearly first, then offer deeper guidance if useful.\n"
            "13. STRUCTURE GUIDANCE: Default to a clear intro in prose, organized advice sections, a structured table of recommended field-specific learning resources where relevant to career growth or skill acquisition, and a brief closing suggestion.",
            "THINGS TO AVOID:\n"
            "- Defaulting to software engineering or coding advice when the question is about another field\n"
            "- Recommending programming languages, GitHub, or tech stacks for non-software roles\n"
            "- Decorative symbols or icons before headers\n"
            "- Repeating the same boilerplate section labels after every subsection\n"
            "- Turning simple explanatory lists into awkward multi-column tables\n"
            "- Omitting the learning resources table when advising on skill or career development",
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
