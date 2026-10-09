import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teacher_auth import (  # noqa: E402
    SESSION_DURATION_SECONDS,
    create_session_token,
    get_teacher_from_token,
    hash_password,
    require_teacher,
    verify_password,
)


class TeacherPasswordTests(unittest.TestCase):
    def test_password_hash_verifies_only_matching_password(self):
        salt, password_hash = hash_password("a-long-teacher-password")

        self.assertTrue(verify_password("a-long-teacher-password", salt, password_hash))
        self.assertFalse(verify_password("incorrect-password", salt, password_hash))


class TeacherSessionTests(unittest.TestCase):
    def test_mutation_dependency_rejects_guest(self):
        request = Request({"type": "http", "headers": []})

        with self.assertRaises(HTTPException) as error:
            require_teacher(request)

        self.assertEqual(error.exception.status_code, 401)

    def test_mutation_dependency_accepts_signed_teacher_cookie(self):
        signing_key = b"test-signing-key-that-is-at-least-32-bytes"
        token = create_session_token("teacher1", signing_key)
        request = Request(
            {
                "type": "http",
                "headers": [(b"cookie", f"teacher_session={token}".encode())],
            }
        )

        with patch.dict("os.environ", {"TEACHER_AUTH_SECRET": signing_key.decode()}):
            self.assertEqual(require_teacher(request), "teacher1")

    def test_signed_session_returns_teacher_username(self):
        signing_key = b"test-signing-key-that-is-at-least-32-bytes"
        token = create_session_token("teacher1", signing_key)

        with patch.dict("os.environ", {"TEACHER_AUTH_SECRET": signing_key.decode()}):
            self.assertEqual(get_teacher_from_token(token), "teacher1")

    def test_tampered_session_is_rejected(self):
        signing_key = b"test-signing-key-that-is-at-least-32-bytes"
        token = create_session_token("teacher1", signing_key)
        tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")

        with patch.dict("os.environ", {"TEACHER_AUTH_SECRET": signing_key.decode()}):
            self.assertIsNone(get_teacher_from_token(tampered_token))

    def test_expired_session_is_rejected(self):
        signing_key = b"test-signing-key-that-is-at-least-32-bytes"
        with patch("teacher_auth.time.time", return_value=1000):
            token = create_session_token("teacher1", signing_key)

        with (
            patch.dict("os.environ", {"TEACHER_AUTH_SECRET": signing_key.decode()}),
            patch("teacher_auth.time.time", return_value=1000 + SESSION_DURATION_SECONDS),
        ):
            self.assertIsNone(get_teacher_from_token(token))


if __name__ == "__main__":
    unittest.main()
