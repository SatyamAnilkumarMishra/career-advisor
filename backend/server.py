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

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import firestore_db
from backend.auth import AuthUser, get_current_user
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


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    history: list[ChatHistoryItem] = Field(default_factory=list)
    student_profile: str = ""


class SourceItem(BaseModel):
    content: str
    page: int | None = None
    relevance_score: float = 0.0


class ChatResponse(BaseModel):
    text: str
    used_retrieval: bool
    sources: list[SourceItem] = Field(default_factory=list)


class ResumeAnalyzeRequest(BaseModel):
    resume_text: str
    target_role: str | None = None


class ResumeAnalysisResponse(BaseModel):
    extracted_skills: list[str]
    experience_summary: str
    strengths: list[str]
    gaps_or_improvements: list[str]
    suggested_target_roles: list[str]


class SkillGapRequest(BaseModel):
    skills: list[str]
    target_role: str


class SkillGapResponse(BaseModel):
    matched_skills: list[str]
    missing_skills: list[str]
    partially_met_skills: list[str]
    overall_readiness: str
    summary: str


class RoadmapRequest(BaseModel):
    skills: list[str]
    target_role: str
    timeframe_months: int = 6


class RoadmapMilestoneItem(BaseModel):
    title: str
    duration: str
    focus_skills: list[str]
    actions: list[str]


class RoadmapResponse(BaseModel):
    target_role: str
    milestones: list[RoadmapMilestoneItem]
    summary: str


class JobSearchRequest(BaseModel):
    role: str
    skills: list[str] | None = None
    location: str | None = None
    experience_level: str | None = None
    limit: int | None = None


class JobItem(BaseModel):
    title: str
    company: str
    location: str
    url: str
    description: str
    skills: list[str]
    experience_level: str | None
    source: str


class HistoryItem(BaseModel):
    id: str
    query: str
    timestamp: str


class AddHistoryRequest(BaseModel):
    query: str


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/status")
def get_status() -> dict[str, Any]:
    return {
        "status": "online",
        "model": state.settings.active_model if state.settings else "llama-3.3-70b-versatile",
        "has_job_api": state.settings.has_job_search_api if state.settings else False,
        "document_loaded": state.document_loaded,
        "document_name": state.document_name,
    }


@app.get("/api/auth/me")
def get_current_user_profile(user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    """Return authenticated user profile and sync to Firestore."""
    profile = firestore_db.upsert_user_profile(
        uid=user.uid,
        email=user.email,
        display_name=user.display_name,
        photo_url=user.photo_url,
    )
    return profile


@app.get("/api/history", response_model=list[HistoryItem])
def get_history(user: AuthUser = Depends(get_current_user)) -> list[HistoryItem]:
    """Retrieve search history items strictly belonging to the authenticated user."""
    items = firestore_db.get_user_history(user.uid)
    return [HistoryItem(**item) for item in items]


@app.post("/api/history", response_model=HistoryItem)
def add_history_item(payload: AddHistoryRequest, user: AuthUser = Depends(get_current_user)) -> HistoryItem:
    """Add a search history entry isolated to the authenticated user."""
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    item = firestore_db.add_user_history_item(user.uid, query)
    return HistoryItem(**item)


@app.delete("/api/history/{item_id}")
def delete_history_item(item_id: str, user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    """Delete a history item belonging to the authenticated user."""
    success = firestore_db.delete_user_history_item(user.uid, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="History item not found.")
    return {"success": True, "deleted_id": item_id}


@app.delete("/api/history")
def clear_all_history(user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    """Clear all history for the authenticated user without affecting others."""
    firestore_db.clear_user_history(user.uid)
    return {"success": True, "message": "All history cleared."}


@app.get("/api/chat/messages")
def get_chat_messages(user: AuthUser = Depends(get_current_user)) -> list[dict[str, Any]]:
    """Retrieve current conversation messages for the authenticated user."""
    return firestore_db.get_user_conversation(user.uid)


@app.post("/api/chat/clear")
def clear_conversation(user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    """Clear conversation session for the authenticated user."""
    firestore_db.clear_user_conversation(user.uid)
    return {"success": True, "message": "Conversation session cleared."}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, user: AuthUser = Depends(get_current_user)) -> ChatResponse:
    """User-isolated RAG chat. Messages and queries are scoped exclusively to user.uid."""
    settings, service, _ = _require_service()
    try:
        trimmed_query = payload.query.strip()
        if trimmed_query:
            firestore_db.add_user_history_item(user.uid, trimmed_query)

        messages = [
            ChatMessage(role="user" if m.role == "user" else "assistant", content=m.content)
            for m in payload.history
        ]
        result = service.answer(
            payload.query,
            history=messages,
            student_profile=payload.student_profile,
        )

        # Persist conversation state for this user in Firestore
        full_conversation = [
            *[{"role": m.role, "content": m.content} for m in payload.history],
            {"role": "user", "content": payload.query},
            {"role": "assistant", "content": result.text},
        ]
        firestore_db.save_user_conversation(user.uid, full_conversation)

        sources = [
            SourceItem(
                content=s.content,
                page=s.page,
                relevance_score=float(s.relevance_score),
            )
            for s in result.sources
        ]
        return ChatResponse(
            text=result.text,
            used_retrieval=result.used_retrieval,
            sources=sources,
        )
    except CareerAdvisorError as exc:
        raise HTTPException(status_code=400, detail=exc.user_message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message(exc)) from exc


@app.post("/api/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload and extract resume text for authenticated user."""
    settings = state.settings or get_settings()
    suffix = os.path.splitext(file.filename or "")[1].lower() or ".pdf"

    try:
        content = await file.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            text = extract_resume_text(tmp_path, settings)
            firestore_db.save_user_resume_data(user.uid, file.filename or "resume.pdf", text)
            return {
                "filename": file.filename,
                "text": text,
                "size_bytes": len(content),
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except CareerAdvisorError as exc:
        raise HTTPException(status_code=400, detail=exc.user_message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message(exc)) from exc


@app.post("/api/resume/analyze", response_model=ResumeAnalysisResponse)
def analyze_resume_endpoint(
    payload: ResumeAnalyzeRequest,
    user: AuthUser = Depends(get_current_user),
) -> ResumeAnalysisResponse:
    """Analyze resume and save analysis exclusively to user.uid."""
    settings = state.settings or get_settings()
    llm = state.llm
    if llm is None:
        from backend.llm_providers import create_llm_provider
        llm = create_llm_provider(settings)

    try:
        result = analyze_resume(
            payload.resume_text,
            llm,
            target_role=payload.target_role or None,
        )
        response_data = ResumeAnalysisResponse(
            extracted_skills=result.extracted_skills,
            experience_summary=result.experience_summary,
            strengths=result.strengths,
            gaps_or_improvements=result.gaps_or_improvements,
            suggested_target_roles=result.suggested_target_roles,
        )
        firestore_db.save_user_resume_data(
            user.uid,
            filename="resume",
            text=payload.resume_text,
            analysis=response_data.model_dump(),
        )
        return response_data
    except CareerAdvisorError as exc:
        raise HTTPException(status_code=400, detail=exc.user_message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message(exc)) from exc


@app.post("/api/skill-gap", response_model=SkillGapResponse)
def skill_gap_endpoint(
    payload: SkillGapRequest,
    user: AuthUser = Depends(get_current_user),
) -> SkillGapResponse:
    """Analyze skill gap and store under user.uid."""
    _, _, llm = _require_service()
    try:
        result = analyze_skill_gap(payload.skills, payload.target_role, llm)
        response_data = SkillGapResponse(
            matched_skills=result.matched_skills,
            missing_skills=result.missing_skills,
            partially_met_skills=result.partially_met_skills,
            overall_readiness=result.overall_readiness,
            summary=result.summary,
        )
        firestore_db.save_user_skill_gap(
            user.uid,
            target_role=payload.target_role,
            skills=payload.skills,
            result=response_data.model_dump(),
        )
        return response_data
    except CareerAdvisorError as exc:
        raise HTTPException(status_code=400, detail=exc.user_message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message(exc)) from exc


@app.post("/api/roadmap", response_model=RoadmapResponse)
def roadmap_endpoint(
    payload: RoadmapRequest,
    user: AuthUser = Depends(get_current_user),
) -> RoadmapResponse:
    """Generate roadmap and store under user.uid."""
    _, _, llm = _require_service()
    try:
        result = generate_roadmap(
            payload.skills,
            payload.target_role,
            llm,
            timeframe_months=payload.timeframe_months,
        )
        response_data = RoadmapResponse(
            target_role=result.target_role,
            milestones=[
                RoadmapMilestoneItem(
                    title=m.title,
                    duration=m.duration,
                    focus_skills=m.focus_skills,
                    actions=m.actions,
                )
                for m in result.milestones
            ],
            summary=result.summary,
        )
        firestore_db.save_user_roadmap(
            user.uid,
            target_role=payload.target_role,
            skills=payload.skills,
            timeframe=payload.timeframe_months,
            result=response_data.model_dump(),
        )
        return response_data
    except CareerAdvisorError as exc:
        raise HTTPException(status_code=400, detail=exc.user_message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message(exc)) from exc


@app.post("/api/jobs/search", response_model=list[JobItem])
def search_jobs_endpoint(
    payload: JobSearchRequest,
    user: AuthUser = Depends(get_current_user),
) -> list[JobItem]:
    """Search jobs for authenticated user."""
    settings, _, _ = _require_service()
    try:
        jobs = search_jobs(
            payload.role,
            settings,
            skills=payload.skills,
            location=payload.location,
            experience_level=payload.experience_level,
            limit=payload.limit,
        )
        return [
            JobItem(
                title=j.title,
                company=j.company,
                location=j.location,
                url=j.url,
                description=j.description,
                skills=j.skills,
                experience_level=j.experience_level,
                source=j.source,
            )
            for j in jobs
        ]
    except CareerAdvisorError as exc:
        raise HTTPException(status_code=400, detail=exc.user_message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message(exc)) from exc


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload reference PDF document for knowledge base indexing."""
    settings, service, _ = _require_service()
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF reference documents are supported.")

    try:
        content = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            vectorstore = build_vector_store(tmp_path, settings)
            service.set_vectorstore(vectorstore)
            state.document_loaded = True
            state.document_name = file.filename
            return {
                "success": True,
                "filename": file.filename,
                "message": "Document indexed successfully into vector store.",
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except CareerAdvisorError as exc:
        raise HTTPException(status_code=400, detail=exc.user_message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message(exc)) from exc


@app.get("/api/user-data/latest")
def get_user_latest_data(user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    """Retrieve the latest saved resume, skill gap, and roadmap data for the user."""
    return {
        "resume": firestore_db.get_user_resume_data(user.uid),
        "skill_gap": firestore_db._get_local_user_bucket(user.uid).get("skill_gap"),
        "roadmap": firestore_db._get_local_user_bucket(user.uid).get("roadmap"),
    }


# ---------------------------------------------------------------------------
# Serve Production React Frontend (if built)
# ---------------------------------------------------------------------------
dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(dist_path):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
