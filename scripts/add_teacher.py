#!/usr/bin/env python3
import getpass
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from teacher_auth import DEFAULT_TEACHERS_FILE, hash_password


def main() -> None:
    credentials_path = Path(os.getenv("TEACHERS_FILE", DEFAULT_TEACHERS_FILE))
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty.")

    password = getpass.getpass("Teacher password (at least 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        with credentials_path.open(encoding="utf-8") as credentials_file:
            credentials = json.load(credentials_file)
    except FileNotFoundError:
        credentials = {}
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Could not read {credentials_path}: {error}") from error

    if not isinstance(credentials, dict):
        raise SystemExit(f"{credentials_path} must contain a JSON object.")

    salt, password_hash = hash_password(password)
    credentials[username] = {"salt": salt, "password_hash": password_hash}

    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    credentials_path.write_text(
        json.dumps(credentials, indent=2) + "\n", encoding="utf-8"
    )
    credentials_path.chmod(0o600)
    print(f"Teacher account {username!r} saved to {credentials_path}.")


if __name__ == "__main__":
    main()
