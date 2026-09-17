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
