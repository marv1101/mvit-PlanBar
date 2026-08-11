import base64
import hashlib
import hmac
import json
import logging
from collections.abc import Iterable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _base64url_decode(value: str) -> bytes:
    padding = 4 - (len(value) % 4)
    if padding and padding != 4:
        value += "=" * padding
    return base64.urlsafe_b64decode(value)


def _validate_jwt(
    token: str,
    secret: str,
    algorithms: Iterable[str],
    audience: str | None,
    issuer: str | None,
) -> dict | None:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        header = json.loads(_base64url_decode(header_b64))
        payload = json.loads(_base64url_decode(payload_b64))
        alg = header.get("alg")
        if alg not in algorithms:
            return None

        signing_input = f"{header_b64}.{payload_b64}".encode()
        signature = _base64url_decode(signature_b64)
        if alg == "HS256":
            expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        else:
            return None

        if not hmac.compare_digest(expected, signature):
            return None

        now = datetime.now(timezone.utc).timestamp()
        exp = payload.get("exp")
        if exp is not None and now > int(exp):
            return None

        if audience and payload.get("aud") != audience:
            return None

        if issuer and payload.get("iss") != issuer:
            return None

        return payload
    except (ValueError, KeyError, TypeError):
        return None


def authenticate_request(
    token: str | None,
    valid_tokens: Iterable[str],
    jwt_secret: str | None = None,
    jwt_algorithms: Iterable[str] | None = None,
    jwt_audience: str | None = None,
    jwt_issuer: str | None = None,
) -> bool:
    """Prüfe, ob ein Zugriffstoken gültig ist."""
    if not valid_tokens and not jwt_secret:
        logger.warning("No authentication configured — rejecting request (fail-closed)")
        return False
    if not token:
        return False
    if token in valid_tokens:
        return True
    if jwt_secret and jwt_algorithms is not None:
        return _validate_jwt(token, jwt_secret, jwt_algorithms, jwt_audience, jwt_issuer) is not None
    return False


def authorize_access(
    token: str | None,
    resource: str,
    token_roles: dict[str, str],
    jwt_secret: str | None = None,
    jwt_algorithms: Iterable[str] | None = None,
    jwt_audience: str | None = None,
    jwt_issuer: str | None = None,
) -> bool:
    """Prüfe, ob ein Token auf die angefragte Ressource zugreifen darf."""
    if not token_roles and not jwt_secret:
        logger.warning("No authentication configured — rejecting access (fail-closed)")
        return False
    if not token:
        return False

    role = None
    if token_roles and token in token_roles:
        role = token_roles[token]
    elif jwt_secret and jwt_algorithms is not None:
        payload = _validate_jwt(token, jwt_secret, jwt_algorithms, jwt_audience, jwt_issuer)
        if payload is None:
            return False
        role = payload.get("role")

    if role == "admin":
        return True
    if role == "worker":
        return resource in ("/workers/register", "/workers/heartbeat")
    if role == "metrics":
        return resource == "/metrics"
    if role == "jobs":
        return resource == "/jobs"

    return False
