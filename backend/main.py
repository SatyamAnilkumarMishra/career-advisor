"""Career Advisor — command-line interface.

Shares all retrieval/generation logic with `app.py` via `rag_service.py`.
"""

from __future__ import annotations

import logging
import sys

from backend.config import ConfigError, configure_logging, get_settings
from backend.errors import CareerAdvisorError, safe_error_message
from backend.llm_providers import ChatMessage, GeminiProvider
from backend.rag_pipeline import build_vector_store, load_existing_vector_store
from backend.rag_service import RagService
from backend.tracing import configure_langsmith

logger = logging.getLogger(__name__)


def _print_banner(has_document: bool) -> None:
    print("\n" + "=" * 50)
    print("🧭 Career Advisor is ready!")
    print("📚 Document mode: Enabled" if has_document else "💬 General mode: No document loaded")
    print("Type 'exit', 'quit', or 'q' to leave.")
    print("=" * 50 + "\n")


def main() -> None:
    try:
        settings = get_settings()
    except ConfigError as exc:
        print(f"❌ Configuration problem: {exc}")
        print("   Copy .env.example to .env, set GROQ_API_KEY or GOOGLE_API_KEY, and try again.")
        sys.exit(1)

    configure_logging(settings)
    configure_langsmith(settings)

    print(f"🧭 Initializing Career Advisor ({settings.llm_provider}: {settings.active_model})…")
    try:
        provider = create_llm_provider(settings)
    except CareerAdvisorError as exc:
        print(f"❌ Failed to initialize the AI model: {exc.user_message}")
        sys.exit(1)

    service = RagService(settings, provider)
    logger.info("RagService initialized (provider=%s, model=%s)", settings.llm_provider, settings.active_model)

    vectorstore = load_existing_vector_store(settings)
    if vectorstore is None:
        try:
            vectorstore = build_vector_store(settings.default_document_path, settings)
            print(f"✅ Indexed default document: {settings.default_document_path}")
        except CareerAdvisorError as exc:
            print(f"⚠️  {exc.user_message}")
            print("🔄 Continuing in general mode without a document.")
            vectorstore = None
    else:
        print("✅ Reused existing document index.")

    if vectorstore is not None:
        service.set_vectorstore(vectorstore)

    _print_banner(has_document=service.has_document)

    history: list[ChatMessage] = []

    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit", "q"}:
            print("👋 Goodbye!")
            break

        print("🤔 Thinking…")
        try:
            result = service.answer(query, history=history)
        except CareerAdvisorError as exc:
            print(f"❌ {exc.user_message}\n")
            continue
        except Exception as exc:
            print(f"❌ {safe_error_message(exc)}\n")
            continue

        if result.used_retrieval and result.sources:
            print(f"📖 Used {len(result.sources)} relevant document excerpt(s)")

        print(f"\nAssistant: {result.text}\n")

        history.append(ChatMessage(role="user", content=query))
        history.append(ChatMessage(role="assistant", content=result.text))


if __name__ == "__main__":
    main()
