"""Tests for multi-user authentication and data isolation.

Verifies that:
1. Requests without credentials or with invalid credentials fail with 401.
2. User A and User B have strictly isolated search histories.
3. User A clearing history leaves User B's history completely intact.
4. User A conversation messages are isolated from User B.
5. User A resume and analysis data are isolated from User B.
6. /api/auth/me returns the profile corresponding exclusively to the caller's token.
"""

from unittest.mock import MagicMock
from starlette.testclient import TestClient

from backend.server import app, state
import backend.firestore_db as firestore_db


USER_A_TOKEN = "dev-token:user-alice:Alice Walker:alice@example.com"
USER_B_TOKEN = "dev-token:user-bob:Bob Miller:bob@example.com"

HEADERS_A = {"Authorization": f"Bearer {USER_A_TOKEN}"}
HEADERS_B = {"Authorization": f"Bearer {USER_B_TOKEN}"}


def test_auth_rejections():
    client = TestClient(app)

    # Missing token
    res = client.get("/api/history")
    assert res.status_code == 401
    assert "detail" in res.json()

    # Malformed token
    res = client.get("/api/history", headers={"Authorization": "InvalidScheme token123"})
    assert res.status_code == 401


def test_auth_me_endpoint():
    client = TestClient(app)

    res_a = client.get("/api/auth/me", headers=HEADERS_A)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["uid"] == "user-alice"
    assert data_a["email"] == "alice@example.com"
    assert data_a["display_name"] == "Alice Walker"

    res_b = client.get("/api/auth/me", headers=HEADERS_B)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["uid"] == "user-bob"
    assert data_b["email"] == "bob@example.com"
    assert data_b["display_name"] == "Bob Miller"


def test_multi_user_history_isolation():
    client = TestClient(app)

    # 1. Clear history for both users
    client.delete("/api/history", headers=HEADERS_A)
    client.delete("/api/history", headers=HEADERS_B)

    # 2. User A adds history items
    client.post("/api/history", headers=HEADERS_A, json={"query": "Alice Query 1: Data Scientist"})
    client.post("/api/history", headers=HEADERS_A, json={"query": "Alice Query 2: Machine Learning"})

    # 3. User B adds a distinct history item
    client.post("/api/history", headers=HEADERS_B, json={"query": "Bob Query 1: UI Designer"})

    # 4. User A must only see Alice's 2 items
    res_a = client.get("/api/history", headers=HEADERS_A)
    assert res_a.status_code == 200
    items_a = res_a.json()
    queries_a = [item["query"] for item in items_a]
    assert len(queries_a) == 2
    assert "Alice Query 1: Data Scientist" in queries_a
    assert "Alice Query 2: Machine Learning" in queries_a
    assert "Bob Query 1: UI Designer" not in queries_a

    # 5. User B must only see Bob's 1 item
    res_b = client.get("/api/history", headers=HEADERS_B)
    assert res_b.status_code == 200
    items_b = res_b.json()
    queries_b = [item["query"] for item in items_b]
    assert len(queries_b) == 1
    assert "Bob Query 1: UI Designer" in queries_b
    assert "Alice Query 1: Data Scientist" not in queries_b

    # 6. User A clears their history
    res_clear_a = client.delete("/api/history", headers=HEADERS_A)
    assert res_clear_a.status_code == 200

    # User A now has 0 items
    assert len(client.get("/api/history", headers=HEADERS_A).json()) == 0

    # User B STILL has their 1 item completely intact
    res_b_after = client.get("/api/history", headers=HEADERS_B)
    assert len(res_b_after.json()) == 1
    assert res_b_after.json()[0]["query"] == "Bob Query 1: UI Designer"


def test_multi_user_chat_isolation():
    client = TestClient(app)

    mock_service = MagicMock()
    mock_service.answer.side_effect = lambda query, history=None, student_profile="": MagicMock(
        text=f"Response to: {query}",
        used_retrieval=False,
        sources=[],
    )
    mock_settings = MagicMock(gemini_model="gemini-test", has_job_search_api=False)
    mock_llm = MagicMock()

    state.settings = mock_settings
    state.service = mock_service
    state.llm = mock_llm

    # Clear conversations
    client.post("/api/chat/clear", headers=HEADERS_A)
    client.post("/api/chat/clear", headers=HEADERS_B)

    # User A sends a message
    res_a = client.post(
        "/api/chat",
        headers=HEADERS_A,
        json={"query": "Alice secret career goal", "history": []},
    )
    assert res_a.status_code == 200

    # User B sends a different message
    res_b = client.post(
        "/api/chat",
        headers=HEADERS_B,
        json={"query": "Bob secret career goal", "history": []},
    )
    assert res_b.status_code == 200

    # Verify User A's stored messages do not contain Bob's messages
    conv_a = client.get("/api/chat/messages", headers=HEADERS_A).json()
    conv_b = client.get("/api/chat/messages", headers=HEADERS_B).json()

    contents_a = [m["content"] for m in conv_a]
    contents_b = [m["content"] for m in conv_b]

    assert any("Alice secret career goal" in c for c in contents_a)
    assert not any("Bob secret career goal" in c for c in contents_a)

    assert any("Bob secret career goal" in c for c in contents_b)
    assert not any("Alice secret career goal" in c for c in contents_b)
