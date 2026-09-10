"""FastAPI backend server for Career Advisor.

Provides a unified REST API for:
- RAG document-grounded chat and Gemini AI conversation
- Resume parsing and skill analysis
- Skill-gap evaluation
- Milestone-based learning roadmap generation
- Job searching (Adzuna API + verified local directory)
- Reference document indexing into Chroma vector store
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.career_tools import (
    analyze_resume,
    analyze_skill_gap,
    generate_roadmap,
    search_jobs,
)
from backend.config import Settings, configure_logging, get_settings
from backend.errors import CareerAdvisorError, safe_error_message
from backend.llm_providers import ChatMessage, GeminiProvider, LLMProvider, create_llm_provider
from backend.rag_pipeline import build_vector_store, load_existing_vector_store
from backend.rag_service import RagService
from backend.resume_pipeline import extract_resume_text
from backend.tracing import configure_langsmith

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global State Container
# ---------------------------------------------------------------------------


class AppState:
    settings: Settings | None = None
    service: RagService | None = None
    llm: LLMProvider | None = None
    document_loaded: bool = False
    document_name: str | None = None
    search_history: list[dict[str, Any]] = []


state = AppState()
state.search_history = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize core settings and LLM immediately (instant boot)
    try:
        settings = get_settings()
        configure_logging(settings)
        configure_langsmith(settings)
        state.settings = settings

        provider = create_llm_provider(settings)
        state.llm = provider
        state.service = RagService(settings, provider)
        logger.info("Career Advisor core AI service initialized (%s: %s).", settings.llm_provider, settings.active_model)

        # Warm vector store in background without blocking API readiness
        async def _warm_vectorstore() -> None:
            try:
                existing_vs = await asyncio.to_thread(load_existing_vector_store, settings)
                document_name = "Persisted Index"

                if existing_vs is None and settings.auto_index_default_document:
                    default_doc = settings.default_document_path
                    if os.path.exists(default_doc):
                        try:
                            logger.info("Indexing default document %s in background...", default_doc)
                            existing_vs = await asyncio.to_thread(build_vector_store, default_doc, settings)
                            document_name = os.path.basename(default_doc)
                        except Exception as exc:
                            logger.error("Could not index default document: %s", exc)
                    else:
                        logger.warning("Default document %s not found; continuing in general mode.", default_doc)

                if existing_vs is not None:
                    state.service.set_vectorstore(existing_vs)
                    state.document_loaded = True
                    state.document_name = document_name
                    logger.info("Vector store ready (%s).", document_name)
            except Exception as exc:
                logger.error("Background vector store warm-up failed: %s", exc)

        asyncio.create_task(_warm_vectorstore())
    except Exception as exc:
        logger.error("Failed to initialize server state: %s", exc)

    yield

    # Shutdown
    logger.info("Shutting down Career Advisor backend.")


app = FastAPI(
    title="Career Advisor API",
    version="2.0.0",
    description="REST API for Career Advisor AI platform",
    lifespan=lifespan,
)

# Allow frontend requests from Next.js dev & prod origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_service() -> tuple[Settings, RagService, LLMProvider]:
    if state.settings is None or state.service is None or state.llm is None:
        raise HTTPException(
            status_code=503,
            detail="API response error: AI Service is not initialized. Please ensure your API key is properly configured in .env",
        )
    return state.settings, state.service, state.llm
