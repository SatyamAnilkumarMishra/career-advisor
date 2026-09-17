"""Tests for FastAPI backend server."""

from unittest.mock import MagicMock, patch

from starlette.testclient import TestClient

import backend.server as server
from backend.server import app, state


AUTH_HEADERS = {"Authorization": "Bearer dev-token:test-user:Test User:test@example.com"}


def test_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "model" in data


def test_endpoints_require_authentication():
    client = TestClient(app)
    # Protected endpoints must return 401 without Bearer token
    assert client.get("/api/history").status_code == 401
    assert client.post("/api/chat", json={"query": "test"}).status_code == 401
    assert client.post("/api/jobs/search", json={"role": "Engineer"}).status_code == 401


def test_chat_endpoint():
    mock_service = MagicMock()
    mock_service.answer.return_value = MagicMock(
        text="Career advice response",
        used_retrieval=False,
        sources=[],
    )
    mock_settings = MagicMock(gemini_model="gemini-test", has_job_search_api=False)
    mock_llm = MagicMock()

    state.settings = mock_settings
    state.service = mock_service
    state.llm = mock_llm

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers=AUTH_HEADERS,
        json={"query": "How to become an ML engineer?", "history": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Career advice response"
    assert data["used_retrieval"] is False


def test_chat_endpoint_rejects_off_topic_query():
    """An out-of-scope question surfaces as a 400 carrying the refusal text,
    which is what the frontend renders as an error bubble."""
    from backend.errors import OffTopicQueryError
    from backend.rag_service import OFF_TOPIC_MESSAGE

    mock_service = MagicMock()
    mock_service.answer.side_effect = OffTopicQueryError(OFF_TOPIC_MESSAGE)

    state.settings = MagicMock(gemini_model="gemini-test", has_job_search_api=False)
    state.service = mock_service
    state.llm = MagicMock()

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        headers=AUTH_HEADERS,
        json={"query": "who is the prime minister of India", "history": []},
    )

    assert response.status_code == 400
    assert "career" in response.json()["detail"].lower()


def test_job_search_endpoint():
    mock_settings = MagicMock(has_job_search_api=False, job_search_default_limit=10)
    mock_service = MagicMock()
    mock_llm = MagicMock()

    state.settings = mock_settings
    state.service = mock_service
    state.llm = mock_llm

    client = TestClient(app)
    response = client.post(
        "/api/jobs/search",
        headers=AUTH_HEADERS,
        json={"role": "Engineer"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_history_endpoints():
    client = TestClient(app)
    # Clear initial
    client.delete("/api/history", headers=AUTH_HEADERS)

    # Add item
    res = client.post("/api/history", headers=AUTH_HEADERS, json={"query": "I want to be a nurse"})
    assert res.status_code == 200
    item = res.json()
    assert item["query"] == "I want to be a nurse"
    assert "id" in item

    # Get history
    res = client.get("/api/history", headers=AUTH_HEADERS)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["id"] == item["id"]

    # Delete specific item
    res = client.delete(f"/api/history/{item['id']}", headers=AUTH_HEADERS)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Verify empty
    res = client.get("/api/history", headers=AUTH_HEADERS)
    assert len(res.json()) == 0


def test_clear_conversation_endpoint():
    client = TestClient(app)
    res = client.post("/api/chat/clear", headers=AUTH_HEADERS)
    assert res.status_code == 200
    assert res.json()["success"] is True



# ---------------------------------------------------------------------------
# Startup: the vector store is built on first boot so retrieval works without
# anyone having to run the CLI first.
# ---------------------------------------------------------------------------


def _startup_settings(**overrides):
    settings = MagicMock(
        chroma_persist_dir="chroma_db",
        default_document_path="Career_Advisor_Guide_2025.pdf",
        auto_index_default_document=True,
        gemini_model="gemini-test",
        llm_request_timeout_seconds=30,
        llm_max_retries=3,
        google_api_key="test-key",
    )
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def _run_startup(*, existing_store, settings, doc_exists=True, build=None):
    """Boot the app through its lifespan with the RAG plumbing stubbed out."""
    state.document_loaded = False
    state.document_name = None
    build = build or MagicMock(return_value=MagicMock(name="built-store"))

    with patch.object(server, "get_settings", return_value=settings), patch.object(
        server, "configure_logging"
    ), patch.object(server, "configure_langsmith"), patch.object(
        server, "GeminiProvider"
    ), patch.object(server, "RagService"), patch.object(
        server, "load_existing_vector_store", return_value=existing_store
    ), patch.object(
        server, "build_vector_store", build
    ), patch.object(
        server.os.path, "exists", return_value=doc_exists
    ):
        with TestClient(app):
            pass
    return build


def test_startup_indexes_default_document_when_no_store_exists():
    build = _run_startup(existing_store=None, settings=_startup_settings())

    build.assert_called_once()
    assert build.call_args[0][0] == "Career_Advisor_Guide_2025.pdf"
    assert state.document_loaded is True
    assert state.document_name == "Career_Advisor_Guide_2025.pdf"


def test_startup_reuses_persisted_store_without_rebuilding():
    build = _run_startup(existing_store=MagicMock(name="persisted"), settings=_startup_settings())

    build.assert_not_called()
    assert state.document_loaded is True
    assert state.document_name == "Persisted Index"


def test_startup_skips_indexing_when_disabled():
    build = _run_startup(
        existing_store=None, settings=_startup_settings(auto_index_default_document=False)
    )

    build.assert_not_called()
    assert state.document_loaded is False


def test_startup_skips_indexing_when_document_missing():
    build = _run_startup(existing_store=None, settings=_startup_settings(), doc_exists=False)

    build.assert_not_called()
    assert state.document_loaded is False


def test_server_still_starts_when_indexing_fails():
    """A broken index must not stop the API booting — chat still works
    un-grounded."""
    build = MagicMock(side_effect=RuntimeError("embedding model unavailable"))
    _run_startup(existing_store=None, settings=_startup_settings(), build=build)

    build.assert_called_once()
    assert state.document_loaded is False
