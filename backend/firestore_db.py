"""Cloud Firestore data storage service for Career Advisor.

Provides strictly user-isolated data persistence scoped by Firebase UID:
- `users/{uid}/profile`
- `users/{uid}/history`
- `users/{uid}/conversations`
- `users/{uid}/resume`
- `users/{uid}/skill_gap`
- `users/{uid}/roadmap`

Includes seamless local fallback caching for offline development and test environments.
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.auth import initialize_firebase_admin

logger = logging.getLogger(__name__)

# Fallback in-memory user-isolated storage for local/offline testing
_lock = threading.Lock()
_local_store: dict[str, dict[str, Any]] = {}


def _get_local_user_bucket(uid: str) -> dict[str, Any]:
    with _lock:
        if uid not in _local_store:
            _local_store[uid] = {
                "profile": {},
                "history": [],
                "conversations": {},
                "resume": None,
                "skill_gap": None,
                "roadmap": None,
            }
        return _local_store[uid]


def get_firestore_client():
    """Retrieve initialized Firestore client if cloud credentials are configured."""
    try:
        if initialize_firebase_admin():
            from firebase_admin import firestore
            return firestore.client()
    except Exception as exc:
        logger.debug("Firestore client initialization deferred: %s", exc)
    return None


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

def upsert_user_profile(
    uid: str,
    email: str | None = None,
    display_name: str | None = None,
    photo_url: str | None = None,
) -> dict[str, Any]:
    """Store or update user profile under users/{uid}."""
    now_iso = datetime.now(timezone.utc).isoformat()
    profile_data = {
        "uid": uid,
        "email": email or "",
        "display_name": display_name or "",
        "photo_url": photo_url or "",
        "last_login": now_iso,
    }

    db = get_firestore_client()
    if db:
        try:
            doc_ref = db.collection("users").document(uid)
            doc_ref.set(profile_data, merge=True)
            return profile_data
        except Exception as exc:
            logger.error("Firestore upsert_user_profile error for %s: %s", uid, exc)

    # Local fallback
    bucket = _get_local_user_bucket(uid)
    bucket["profile"].update(profile_data)
    return profile_data


# ---------------------------------------------------------------------------
# Search History (User-Isolated)
# ---------------------------------------------------------------------------

def get_user_history(uid: str, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve search history items strictly belonging to uid."""
    db = get_firestore_client()
    if db:
        try:
            from firebase_admin import firestore
            docs = (
                db.collection("users")
                .document(uid)
                .collection("history")
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
            items = []
            for d in docs:
                data = d.to_dict()
                data["id"] = d.id
                items.append(data)
            return items
        except Exception as exc:
            logger.error("Firestore get_user_history error for %s: %s", uid, exc)

    # Local fallback
    bucket = _get_local_user_bucket(uid)
    return list(bucket["history"][:limit])


def add_user_history_item(uid: str, query: str) -> dict[str, Any]:
    """Add a search history entry under users/{uid}/history."""
    clean_query = query.strip()
    now_iso = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid.uuid4())
    item_data = {
        "id": item_id,
        "query": clean_query,
        "timestamp": now_iso,
    }

    db = get_firestore_client()
    if db:
        try:
            # Prevent immediate duplicate query entry for this user
            hist_col = db.collection("users").document(uid).collection("history")
            existing = hist_col.where("query", "==", clean_query).limit(1).stream()
            for doc in existing:
                return {**doc.to_dict(), "id": doc.id}

            hist_col.document(item_id).set(item_data)
            return item_data
        except Exception as exc:
            logger.error("Firestore add_user_history_item error for %s: %s", uid, exc)

    # Local fallback
    bucket = _get_local_user_bucket(uid)
    # Check duplicate in local list
    for item in bucket["history"]:
        if item.get("query", "").lower() == clean_query.lower():
            return item

    bucket["history"].insert(0, item_data)
    return item_data


def delete_user_history_item(uid: str, item_id: str) -> bool:
    """Delete a single history item belonging to uid."""
    db = get_firestore_client()
    if db:
        try:
            doc_ref = db.collection("users").document(uid).collection("history").document(item_id)
            doc_ref.delete()
            return True
        except Exception as exc:
            logger.error("Firestore delete_user_history_item error: %s", exc)

    # Local fallback
    bucket = _get_local_user_bucket(uid)
    initial_len = len(bucket["history"])
    bucket["history"] = [h for h in bucket["history"] if h.get("id") != item_id]
    return len(bucket["history"]) < initial_len


def clear_user_history(uid: str) -> bool:
    """Delete all search history items for uid without affecting any other user."""
    db = get_firestore_client()
    if db:
        try:
            hist_col = db.collection("users").document(uid).collection("history")
            docs = hist_col.stream()
            for d in docs:
                d.reference.delete()
            return True
        except Exception as exc:
            logger.error("Firestore clear_user_history error for %s: %s", uid, exc)

    # Local fallback
    bucket = _get_local_user_bucket(uid)
    bucket["history"] = []
    return True


# ---------------------------------------------------------------------------
# Conversations & Chat Session (User-Isolated)
# ---------------------------------------------------------------------------

def save_user_conversation(
    uid: str,
    messages: list[dict[str, Any]],
    conversation_id: str = "default",
    title: str = "Career Consultation",
) -> None:
    """Save chat conversation state under users/{uid}/conversations/{conversation_id}."""
    now_iso = datetime.now(timezone.utc).isoformat()
    data = {
        "conversation_id": conversation_id,
        "title": title,
        "updated_at": now_iso,
        "messages": messages,
    }

    db = get_firestore_client()
    if db:
        try:
            doc_ref = (
                db.collection("users")
                .document(uid)
                .collection("conversations")
                .document(conversation_id)
            )
            doc_ref.set(data, merge=True)
            return
        except Exception as exc:
            logger.error("Firestore save_user_conversation error for %s: %s", uid, exc)

    # Local fallback
    bucket = _get_local_user_bucket(uid)
    bucket["conversations"][conversation_id] = data


def get_user_conversation(
    uid: str,
    conversation_id: str = "default",
) -> list[dict[str, Any]]:
    """Retrieve messages for a specific conversation of uid."""
    db = get_firestore_client()
    if db:
        try:
            doc_ref = (
                db.collection("users")
                .document(uid)
                .collection("conversations")
                .document(conversation_id)
            )
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict().get("messages", [])
        except Exception as exc:
            logger.error("Firestore get_user_conversation error for %s: %s", uid, exc)

    # Local fallback
    bucket = _get_local_user_bucket(uid)
    conv = bucket["conversations"].get(conversation_id)
    return conv.get("messages", []) if conv else []


def clear_user_conversation(
    uid: str,
    conversation_id: str = "default",
) -> None:
    """Clear conversation history for uid."""
    db = get_firestore_client()
    if db:
        try:
            doc_ref = (
                db.collection("users")
                .document(uid)
                .collection("conversations")
                .document(conversation_id)
            )
            doc_ref.delete()
            return
        except Exception as exc:
            logger.error("Firestore clear_user_conversation error for %s: %s", uid, exc)

    # Local fallback
    bucket = _get_local_user_bucket(uid)
    bucket["conversations"].pop(conversation_id, None)


# ---------------------------------------------------------------------------
# Resume, Skill Gap, Roadmap Storage (User-Isolated)
# ---------------------------------------------------------------------------

def save_user_resume_data(
    uid: str,
    filename: str,
    text: str,
    analysis: dict[str, Any] | None = None,
) -> None:
    """Save latest resume parsing and analysis strictly under users/{uid}/resume/latest."""
    now_iso = datetime.now(timezone.utc).isoformat()
    data = {
        "filename": filename,
        "text": text,
        "uploaded_at": now_iso,
        "analysis": analysis or {},
    }

    db = get_firestore_client()
    if db:
        try:
            db.collection("users").document(uid).collection("resume").document("latest").set(data)
            return
        except Exception as exc:
            logger.error("Firestore save_user_resume_data error for %s: %s", uid, exc)

    bucket = _get_local_user_bucket(uid)
    bucket["resume"] = data


def get_user_resume_data(uid: str) -> dict[str, Any] | None:
    """Get latest uploaded resume data for uid."""
    db = get_firestore_client()
    if db:
        try:
            doc = db.collection("users").document(uid).collection("resume").document("latest").get()
            if doc.exists:
                return doc.to_dict()
        except Exception as exc:
            logger.error("Firestore get_user_resume_data error for %s: %s", uid, exc)

    bucket = _get_local_user_bucket(uid)
    return bucket.get("resume")


def save_user_skill_gap(uid: str, target_role: str, skills: list[str], result: dict[str, Any]) -> None:
    """Save skill gap analysis result for uid."""
    now_iso = datetime.now(timezone.utc).isoformat()
    data = {
        "target_role": target_role,
        "skills": skills,
        "result": result,
        "analyzed_at": now_iso,
    }

    db = get_firestore_client()
    if db:
        try:
            db.collection("users").document(uid).collection("skill_gap").document("latest").set(data)
            return
        except Exception as exc:
            logger.error("Firestore save_user_skill_gap error for %s: %s", uid, exc)

    bucket = _get_local_user_bucket(uid)
    bucket["skill_gap"] = data


def save_user_roadmap(uid: str, target_role: str, skills: list[str], timeframe: int, result: dict[str, Any]) -> None:
    """Save learning roadmap result for uid."""
    now_iso = datetime.now(timezone.utc).isoformat()
    data = {
        "target_role": target_role,
        "skills": skills,
        "timeframe_months": timeframe,
        "result": result,
        "generated_at": now_iso,
    }

    db = get_firestore_client()
    if db:
        try:
            db.collection("users").document(uid).collection("roadmap").document("latest").set(data)
            return
        except Exception as exc:
            logger.error("Firestore save_user_roadmap error for %s: %s", uid, exc)

    bucket = _get_local_user_bucket(uid)
    bucket["roadmap"] = data
