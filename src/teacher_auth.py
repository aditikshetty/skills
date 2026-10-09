import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import HTTPException, Request

PASSWORD_ITERATIONS = 600_000
SESSION_COOKIE_NAME = "teacher_session"
SESSION_DURATION_SECONDS = 8 * 60 * 60
DEFAULT_TEACHERS_FILE = Path(__file__).with_name("teachers.json")


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


DUMMY_PASSWORD_SALT = _base64url_encode(b"teacher-auth-dummy-salt")
DUMMY_PASSWORD_HASH = _base64url_encode(
    hashlib.pbkdf2_hmac(
        "sha256",
        b"not-a-real-teacher-password",
        _base64url_decode(DUMMY_PASSWORD_SALT),
        PASSWORD_ITERATIONS,
    )
)


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return _base64url_encode(salt), _base64url_encode(password_hash)


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    try:
        salt_bytes = _base64url_decode(salt)
        expected_bytes = _base64url_decode(expected_hash)
    except (ValueError, TypeError):
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_bytes, PASSWORD_ITERATIONS
    )
    return hmac.compare_digest(actual_hash, expected_bytes)


def load_teacher_credentials() -> dict[str, dict[str, str]]:
    credentials_path = Path(os.getenv("TEACHERS_FILE", DEFAULT_TEACHERS_FILE))
    try:
        with credentials_path.open(encoding="utf-8") as credentials_file:
            credentials = json.load(credentials_file)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts are not configured. Add an account with scripts/add_teacher.py.",
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=503, detail="Teacher account configuration could not be loaded."
        ) from error

    if not isinstance(credentials, dict) or not credentials:
        raise HTTPException(
            status_code=503, detail="Teacher account configuration is invalid."
        )

    for username, account in credentials.items():
        if (
            not isinstance(username, str)
            or not isinstance(account, dict)
            or not isinstance(account.get("salt"), str)
            or not isinstance(account.get("password_hash"), str)
        ):
            raise HTTPException(
                status_code=503, detail="Teacher account configuration is invalid."
            )

    return credentials


def _signing_key() -> bytes:
    secret = os.getenv("TEACHER_AUTH_SECRET")
    if not secret or len(secret.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=503,
            detail="Teacher authentication is not configured. Set TEACHER_AUTH_SECRET to a secret of at least 32 characters.",
        )
    return secret.encode("utf-8")


def create_session_token(username: str, signing_key: bytes) -> str:
    header = _base64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload = _base64url_encode(
        json.dumps(
            {
                "sub": username,
                "exp": int(time.time()) + SESSION_DURATION_SECONDS,
            },
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = _base64url_encode(
        hmac.new(signing_key, signing_input, hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{signature}"


def get_teacher_from_token(token: str | None) -> str | None:
    if not token:
        return None

    try:
        header, payload, signature = token.split(".")
        signing_input = f"{header}.{payload}".encode("ascii")
        expected_signature = _base64url_encode(
            hmac.new(_signing_key(), signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(signature, expected_signature):
            return None

        token_header = json.loads(_base64url_decode(header))
        token_payload = json.loads(_base64url_decode(payload))
        if (
            token_header.get("alg") != "HS256"
            or not isinstance(token_payload.get("sub"), str)
            or not isinstance(token_payload.get("exp"), int)
            or token_payload["exp"] <= int(time.time())
        ):
            return None
        return token_payload["sub"]
    except (HTTPException, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return None


def require_teacher(request: Request) -> str:
    username = get_teacher_from_token(request.cookies.get(SESSION_COOKIE_NAME))
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required.")
    return username
