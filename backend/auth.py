"""Firebase Authentication service and FastAPI dependency for Career Advisor.

Provides cryptographic verification of Firebase ID tokens sent from the frontend
in the `Authorization: Bearer <token>` header, extracting the authenticated Firebase UID.
Never trusts client-supplied user identifiers.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import firebase_admin
from firebase_admin import auth, credentials

logger = logging.getLogger(__name__)

# Reusable security scheme for Bearer token extraction
security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    """Authenticated user model extracted from verified Firebase ID token."""

    uid: str
    email: str | None = None
    display_name: str | None = None
    photo_url: str | None = None


_firebase_initialized: bool = False


def initialize_firebase_admin() -> bool:
    """Initialize Firebase Admin SDK using available environment credentials."""
    global _firebase_initialized

    if _firebase_initialized:
        return True

    # Check if a default app already exists
    if len(firebase_admin._apps) > 0:
        _firebase_initialized = True
        return True

    try:
        # Option 1: Explicit project, client email, and private key environment variables (ideal for Render/Cloud)
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
        private_key = os.getenv("FIREBASE_PRIVATE_KEY")

        if project_id and client_email and private_key:
            # Handle escaped newlines from environment strings
            clean_key = private_key.replace("\\n", "\n")
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": project_id,
                "client_email": client_email,
                "private_key": clean_key,
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized successfully via environment variables.")
            return True

        # Option 2: Full JSON string in FIREBASE_SERVICE_ACCOUNT_JSON
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            cert_data = json.loads(service_account_json)
            if "private_key" in cert_data:
                cert_data["private_key"] = cert_data["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cert_data)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized successfully via FIREBASE_SERVICE_ACCOUNT_JSON.")
            return True

        # Option 3: File path specified by GOOGLE_APPLICATION_CREDENTIALS or FIREBASE_CREDENTIALS_PATH
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("FIREBASE_CREDENTIALS_PATH")
        if creds_path and os.path.exists(creds_path):
            cred = credentials.Certificate(creds_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized via credentials file: %s", creds_path)
            return True

        # Option 4: Default application credentials fallback
        try:
            firebase_admin.initialize_app()
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized via application default credentials.")
            return True
        except Exception:
            pass

        logger.warning(
            "Firebase credentials not detected. Operating in dev/fallback auth mode. "
            "Set FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY in production."
        )
        return False

    except Exception as exc:
        logger.error("Failed to initialize Firebase Admin SDK: %s", exc)
        return False


def verify_firebase_token(id_token: str) -> dict[str, Any]:
    """Cryptographically verify Firebase ID token and return claims dictionary."""
    if not _firebase_initialized:
        initialize_firebase_admin()

    if not _firebase_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured on the server.",
        )

    try:
        # verify_id_token checks expiration, signature, and audience
        decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=10)
        return decoded_token
    except auth.ExpiredIdTokenError as exc:
        logger.warning("Firebase token expired: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except auth.InvalidIdTokenError as exc:
        logger.warning("Firebase token invalid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error verifying Firebase token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    auth_credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> AuthUser:
    """FastAPI dependency to authenticate requests and return the current user.

    Extracts Bearer token from HTTP Authorization header, verifies it with
    Firebase Admin SDK, and returns the authoritative AuthUser with verified UID.
    """
    if not auth_credentials or not auth_credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_credentials.credentials.strip()

    if not _firebase_initialized:
        initialize_firebase_admin()

    # SECURITY: the dev-token path must NEVER be reachable when Firebase Admin
    # is actually configured. It is an unsigned, client-fabricated string
    # (`dev-token:<uid>:<name>:<email>`) that anyone can type by hand — it is
    # not a credential, it is a claim. Trusting it whenever it merely showed
    # up, regardless of server configuration, is what let any request bypass
    # authentication entirely. It is now accepted only when both of the
    # following hold: Firebase Admin could not be initialized on this server
    # AND the operator has explicitly opted in with ENABLE_DEV_AUTH=true.
    if not _firebase_initialized:
        dev_auth_enabled = os.getenv("ENABLE_DEV_AUTH", "false").lower() in ("true", "1", "yes")

        if dev_auth_enabled and token.startswith("dev-token:"):
            # Format: dev-token:uid:name:email
            parts = token.split(":")
            dev_uid = parts[1] if len(parts) > 1 else "dev-user"
            dev_name = parts[2] if len(parts) > 2 else "Local Developer"
            dev_email = parts[3] if len(parts) > 3 else "dev@careeradvisor.local"
            logger.warning(
                "ENABLE_DEV_AUTH is on — accepting an UNVERIFIED dev-token for uid=%s. "
                "This must never be enabled in a production environment.",
                dev_uid,
            )
            return AuthUser(uid=dev_uid, email=dev_email, display_name=dev_name)

        if dev_auth_enabled:
            logger.warning("ENABLE_DEV_AUTH is on — accepting UNVERIFIED dev-auth request.")
            return AuthUser(
                uid="dev-user-local",
                email="dev@careeradvisor.local",
                display_name="Developer Mode",
            )

        # Firebase isn't configured and dev auth wasn't explicitly enabled:
        # refuse the request rather than silently trusting the caller.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured on the server.",
        )

    # Firebase Admin IS configured: every token, with no exceptions, is
    # cryptographically verified below. There is no fallback path here.
    decoded_token = verify_firebase_token(token)
    uid = decoded_token.get("uid") or decoded_token.get("sub")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing valid user identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(
        uid=uid,
        email=decoded_token.get("email"),
        display_name=decoded_token.get("name"),
        photo_url=decoded_token.get("picture"),
    )