"""Resume upload validation and text extraction.

Separate from `rag_pipeline.py` (which handles the *reference document* used
for RAG) because a resume isn't indexed into the vector store — it's read
once, turned into plain text, and handed to `career_tools.analyze_resume()`
for a single LLM pass. Supports PDF, DOCX, and plain text, since resumes are
commonly shared in all three.
"""

from __future__ import annotations

import logging
import os

from backend.config import Settings
from backend.errors import ResumeParsingError

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def validate_resume_file(file_path: str, *, max_size_bytes: int) -> str:
    """Validate the uploaded resume and return its lowercase extension."""
    if not os.path.exists(file_path):
        raise ResumeParsingError(f"File not found: {os.path.basename(file_path)}")

    size = os.path.getsize(file_path)
    if size == 0:
        raise ResumeParsingError("The uploaded resume is empty.")
    if size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ResumeParsingError(
            f"The uploaded resume is too large ({size / (1024 * 1024):.1f} MB). "
            f"Maximum allowed size is {max_mb:.0f} MB."
        )

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise ResumeParsingError(
            f"Unsupported resume file type '{ext}'. Please upload a PDF, DOCX, or TXT file."
        )
    return ext


def _extract_pdf_text(file_path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ResumeParsingError(
            "Required PDF dependencies are not installed. Run: pip install -r requirements.txt"
        ) from exc

    try:
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise ResumeParsingError(
            "We couldn't read this PDF resume. It may be corrupted, encrypted, or "
            "a scanned image without extractable text.",
            cause=exc,
        ) from exc
    return "\n".join(pages)
