"""Document ingestion and retrieval pipeline.

Changes from the original version:
- `load_existing_vector_store()` is now actually called by `rag_service.py`
  instead of sitting unused — a persisted store is reused instead of being
  rebuilt from scratch on every run.
- Retrieval applies a relevance-score threshold (`Settings.relevance_score_threshold`)
  so low-quality matches are dropped instead of always injecting `k` chunks
  regardless of how relevant they are.
- Retrieval results carry source attribution (page number + a preview) so
  callers can show users what was actually used to ground an answer.
- PDF validation checks actual file content/size, not just the `.pdf` extension.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from backend.config import Settings
from backend.errors import DocumentValidationError, VectorStoreError

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True)
class RetrievedChunk:
    """A single retrieved chunk with enough metadata to attribute it in the UI."""

    content: str
    page: int | None
    source: str | None
    relevance_score: float


def validate_pdf(file_path: str, *, max_size_bytes: int) -> None:
    """Validate that `file_path` is a real, reasonably-sized PDF.

    Checks the `%PDF-` magic header rather than trusting the file extension,
    and enforces a size ceiling before any parsing/embedding work begins.
    """
    if not os.path.exists(file_path):
        raise DocumentValidationError(f"File not found: {os.path.basename(file_path)}")

    size = os.path.getsize(file_path)
    if size == 0:
        raise DocumentValidationError("The uploaded file is empty.")
    if size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise DocumentValidationError(
            f"The uploaded file is too large ({size / (1024 * 1024):.1f} MB). "
            f"Maximum allowed size is {max_mb:.0f} MB."
        )

    with open(file_path, "rb") as f:
        header = f.read(5)
    if header != b"%PDF-":
        raise DocumentValidationError(
            "This file doesn't look like a valid PDF (missing PDF header). "
            "Please upload a genuine PDF document."
        )


def _build_embeddings():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:  # pragma: no cover
        raise VectorStoreError(
            "Required embedding dependencies are not installed. "
            "Run: pip install -r requirements.txt"
        ) from exc

    return HuggingFaceEmbeddings(
        model_name=_EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vector_store(pdf_path: str, settings: Settings):
    """Build a fresh vector store from a validated PDF and persist it to disk."""
    try:
        from langchain_chroma import Chroma
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:  # pragma: no cover
        raise VectorStoreError(
            "Required RAG dependencies are not installed. Run: pip install -r requirements.txt"
        ) from exc
