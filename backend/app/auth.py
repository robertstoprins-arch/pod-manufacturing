"""
Clerk JWT authentication dependency.

Validates Bearer JWTs issued by Clerk using the JWKS endpoint.
PyJWKClient caches the signing keys so we don't hit Clerk on every request.

Required env vars:
  CLERK_JWKS_URL  e.g. https://xxxxx.clerk.accounts.dev/.well-known/jwks.json

Usage:
  @router.get("/something")
  def endpoint(claims: ClerkClaims = Depends(require_auth)):
      ...
"""
import os
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException

_jwks_client: jwt.PyJWKClient | None = None


def _client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        url = os.environ.get("CLERK_JWKS_URL", "")
        if not url:
            raise RuntimeError("CLERK_JWKS_URL is not set")
        _jwks_client = jwt.PyJWKClient(url, cache_keys=True)
    return _jwks_client


@dataclass
class ClerkClaims:
    user_id: str        # Clerk sub — "user_xxxx"
    org_id: str | None  # Clerk org_id — "org_xxxx" (None for personal sessions)
    org_role: str | None


def require_auth(authorization: str = Header(...)) -> ClerkClaims:
    """FastAPI dependency — raises 401 if the token is absent or invalid."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:]
    try:
        signing_key = _client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    return ClerkClaims(
        user_id=payload["sub"],
        org_id=payload.get("org_id"),
        org_role=payload.get("org_role"),
    )
