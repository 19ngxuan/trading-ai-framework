import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt


class AuthTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    *,
    username: str,
    secret: str,
    expires_delta: timedelta,
) -> str:
    expires_at = datetime.now(UTC) + expires_delta
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": username, "exp": int(expires_at.timestamp())}
    encoded_header = _base64url_json(header)
    encoded_payload = _base64url_json(payload)
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def verify_access_token(token: str, *, secret: str, expected_username: str) -> str:
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthTokenError("Malformed token.")

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    signature = _base64url_decode(parts[2])
    if not hmac.compare_digest(signature, expected_signature):
        raise AuthTokenError("Invalid token signature.")

    payload = _base64url_json_decode(parts[1])
    username = payload.get("sub")
    expires_at = payload.get("exp")
    if username != expected_username:
        raise AuthTokenError("Token subject is not allowed.")
    if not isinstance(expires_at, int):
        raise AuthTokenError("Token expiry is missing.")
    if datetime.now(UTC).timestamp() >= expires_at:
        raise AuthTokenError("Token expired.")
    return username


def _base64url_json(payload: dict[str, Any]) -> str:
    return _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )


def _base64url_json_decode(value: str) -> dict[str, Any]:
    try:
        decoded = _base64url_decode(value)
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthTokenError("Token payload is invalid.") from exc
    if not isinstance(payload, dict):
        raise AuthTokenError("Token payload is invalid.")
    return payload


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}")
    except ValueError as exc:
        raise AuthTokenError("Token segment is invalid.") from exc
