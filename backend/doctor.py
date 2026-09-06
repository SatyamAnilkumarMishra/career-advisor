"""Preflight check: does this install actually work with the keys you supplied?

`python run.py doctor` answers one question end to end — "if I start the app
right now, will it produce a real answer?" — by exercising each dependency in
the order a real request would hit it:

    config → Gemini API key/model → embeddings → Chroma vector store → full RAG answer

Each stage prints PASS / FAIL / SKIP with an actionable message. The exit code
is non-zero if anything required failed, so it also works in CI.

This makes real network calls to Gemini (a couple of tiny prompts, costing
effectively nothing) — that is the entire point: an offline check cannot tell
you whether your key works.
"""

from __future__ import annotations

import os
import sys

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET = "\033[0m"


class _Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def ok(self, stage: str, detail: str = "") -> None:
        print(f"  {GREEN}PASS{RESET}  {stage}" + (f" {DIM}— {detail}{RESET}" if detail else ""))

    def fail(self, stage: str, detail: str, fix: str = "") -> None:
        print(f"  {RED}FAIL{RESET}  {stage} {DIM}— {detail}{RESET}")
        if fix:
            print(f"        {YELLOW}fix:{RESET} {fix}")
        self.failures.append(stage)

    def warn(self, stage: str, detail: str) -> None:
        print(f"  {YELLOW}WARN{RESET}  {stage} {DIM}— {detail}{RESET}")
        self.warnings.append(stage)

    def skip(self, stage: str, detail: str) -> None:
        print(f"  {DIM}SKIP  {stage} — {detail}{RESET}")


def _check_config(report: _Report):
    from backend.config import ConfigError, get_settings

    try:
        settings = get_settings()
    except ConfigError as exc:
        report.fail(
            "Configuration",
            str(exc),
            "cp .env.example .env, then set GROQ_API_KEY or GOOGLE_API_KEY",
        )
        return None

    if settings.llm_provider == "groq":
        key = settings.groq_api_key or ""
        if key.startswith("your_") or not key.strip():
            report.fail(
                "Configuration",
                "GROQ_API_KEY is still the placeholder value",
                "get a key at https://console.groq.com/keys and put it in .env",
            )
            return None
        report.ok("Configuration", f"provider=groq, model={settings.groq_model}, key=***{key[-4:]}")
    else:
        key = settings.google_api_key or ""
        if key.startswith("your_") or not key.strip():
            report.fail(
                "Configuration",
                "GOOGLE_API_KEY is still the placeholder value",
                "get a key at https://aistudio.google.com/apikey and put it in .env",
            )
            return None
        report.ok("Configuration", f"provider=gemini, model={settings.gemini_model}, key=***{key[-4:]}")
    return settings


def _check_gemini(report: _Report, settings):
    """The decisive check: a real generate call with the user's real key."""
    from backend.errors import LLMError
    from backend.llm_providers import ChatMessage, create_llm_provider

    provider_label = settings.llm_provider.capitalize()
    try:
        provider = create_llm_provider(settings)
    except LLMError as exc:
        report.fail(f"{provider_label} client", exc.user_message)
        return None

    try:
        answer = provider.generate(
            [ChatMessage(role="user", content="Reply with exactly: OK")],
            system_instruction="You are a health check. Answer in one word.",
        )
    except LLMError as exc:
        report.fail(f"{provider_label} generation", exc.user_message)
        return None
    except Exception as exc:  # pragma: no cover - defensive
        report.fail(f"{provider_label} generation", f"unexpected error: {exc}")
        return None

    preview = answer.strip().replace("\n", " ")[:60]
    report.ok(f"{provider_label} generation", f'model answered: "{preview}"')
    return provider


def _check_embeddings(report: _Report):
    """Embeddings download ~90MB from HuggingFace on first run."""
    from backend.errors import VectorStoreError
    from backend.rag_pipeline import _build_embeddings

    try:
        embeddings = _build_embeddings()
        vec = embeddings.embed_query("career advice")
    except VectorStoreError as exc:
        report.fail("Embedding model", exc.user_message, "pip install -r requirements.txt")
        return None
    except Exception as exc:
        report.fail(
            "Embedding model",
            f"could not load sentence-transformers/all-MiniLM-L6-v2: {exc}",
            "this model downloads from huggingface.co on first run — check network/proxy access",
        )
        return None

    report.ok("Embedding model", f"all-MiniLM-L6-v2 loaded, {len(vec)}-dim vectors")
    return embeddings


def _check_vector_store(report: _Report, settings):
    from backend.rag_pipeline import build_vector_store, load_existing_vector_store

    vectorstore = load_existing_vector_store(settings)
    if vectorstore is not None:
        report.ok("Chroma vector store", f"reused persisted index at {settings.chroma_persist_dir}/")
        return vectorstore

    doc = settings.default_document_path
    if not os.path.exists(doc):
        report.warn(
            "Chroma vector store",
            f"no persisted index and no document at {doc} — chat will answer without grounding",
        )
        return None

    try:
        vectorstore = build_vector_store(doc, settings)
    except Exception as exc:
        report.fail("Chroma vector store", f"could not index {doc}: {exc}")
        return None

    report.ok("Chroma vector store", f"indexed {doc} → {settings.chroma_persist_dir}/")
    return vectorstore


def _check_rag_answer(report: _Report, settings, provider, vectorstore):
    """The full path a real user request takes."""
    from backend.errors import CareerAdvisorError
    from backend.rag_service import RagService

    service = RagService(settings, provider, vectorstore=vectorstore)
    try:
        result = service.answer("What is one concrete way to improve a resume?")
    except CareerAdvisorError as exc:
        report.fail("End-to-end RAG answer", exc.user_message)
        return
    except Exception as exc:  # pragma: no cover - defensive
        report.fail("End-to-end RAG answer", f"unexpected error: {exc}")
        return

    if not result.text.strip():
        report.fail("End-to-end RAG answer", "the service returned an empty answer")
        return

    grounding = (
        f"grounded in {len(result.sources)} document excerpt(s)"
        if result.used_retrieval
        else "answered from general knowledge (no retrieval needed for this question)"
    )
    report.ok("End-to-end RAG answer", grounding)
    print(f"\n{DIM}  ── model output ──{RESET}")
    for line in result.text.strip().splitlines()[:6]:
        print(f"{DIM}  │ {line[:96]}{RESET}")
    print()


def _check_job_search(report: _Report, settings):
    from backend.career_tools import search_jobs

    try:
        jobs = search_jobs("data analyst", settings, limit=1)
    except Exception as exc:
        report.warn("Job search", f"failed: {exc}")
        return

    if settings.has_job_search_api:
        report.ok("Job search", f"Adzuna API configured, {len(jobs)} result(s)")
    else:
        report.warn(
            "Job search",
            f"no ADZUNA_APP_ID/ADZUNA_APP_KEY — using the bundled dataset ({len(jobs)} result(s))",
        )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("\nCareer Advisor — preflight check\n")

    report = _Report()

    settings = _check_config(report)
    if settings is None:
        print(f"\n{RED}Configuration failed — nothing else can be checked.{RESET}\n")
        return 1

    provider = _check_gemini(report, settings)
    embeddings = _check_embeddings(report)

    vectorstore = None
    if embeddings is not None:
        vectorstore = _check_vector_store(report, settings)
    else:
        report.skip("Chroma vector store", "embeddings unavailable")

    if provider is not None:
        _check_rag_answer(report, settings, provider, vectorstore)
    else:
        report.skip("End-to-end RAG answer", f"{settings.llm_provider.capitalize()} unavailable")

    _check_job_search(report, settings)

    print()
    if report.failures:
        print(f"{RED}[FAIL] {len(report.failures)} check(s) failed:{RESET} {', '.join(report.failures)}")
        print("  The app will not produce answers until these are resolved.\n")
        return 1

    if report.warnings:
        print(f"{GREEN}[PASS] All required checks passed.{RESET} {YELLOW}({len(report.warnings)} warning(s)){RESET}")
        print("  The app will generate responses. Warnings are optional features.\n")
        return 0

    print(f"{GREEN}[PASS] Everything passed — the app is fully functional.{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
