"""Password hashing and login sessions for Campus Customs.

Passwords are stored as  pbkdf2_sha256$<salt>$<hash>  , matching the seed database:
  - function:   PBKDF2-HMAC-SHA256
  - iterations: 120,000
  - salt:       random per user, stored as text and used as its UTF-8 bytes
  - hash:       hex-encoded 32-byte digest

Signup and login both go through hash_password() so the settings can never drift apart.
"""

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000

SESSION_COOKIE = "cc_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # one week, in seconds


def hash_password(password: str, salt: str) -> str:
    """Hash a password with the given salt and return the stored-string format."""
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS)
    return f"{ALGORITHM}${salt}${digest.hex()}"


def make_password_hash(password: str) -> str:
    """For signup: create a fresh random salt and hash the new password with it."""
    return hash_password(password, secrets.token_hex(8))


def verify_password(password: str, stored: str) -> bool:
    """For login: re-hash the typed password with the stored salt and compare.

    The stored hash is never "unhashed". We read the salt (the middle piece) out of
    the stored string, hash what the user typed with that same salt, and compare the
    two strings in constant time so the response time doesn't leak how close a guess was.
    """
    try:
        algorithm, salt, _ = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


# A real hash to check against when the email doesn't exist, so a login attempt for an
# unknown email takes as long as one for a real account (no hint about which emails exist).
DUMMY_HASH = make_password_hash(secrets.token_hex(16))


# ---- Sessions ---------------------------------------------------------------
# After login the browser gets a signed token in an HttpOnly cookie:  <user_id>.<expires>.<signature>
# JavaScript can't read the cookie, and the signature means it can't be forged or edited.


def _load_secret_key() -> bytes:
    """Signing key from SESSION_SECRET, or a random key saved next to this file."""
    from_env = os.environ.get("SESSION_SECRET")
    if from_env:
        return from_env.encode("utf-8")
    key_file = Path(__file__).resolve().parent / ".session_secret"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32), encoding="utf-8")
    return key_file.read_text(encoding="utf-8").strip().encode("utf-8")


SECRET_KEY = _load_secret_key()


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + SESSION_MAX_AGE}"
    return f"{payload}.{_sign(payload)}"


def read_session_token(token: str | None) -> int | None:
    """Return the user id if the token is genuine and not expired, else None."""
    if not token:
        return None
    try:
        user_id, expires, signature = token.split(".")
        if not hmac.compare_digest(_sign(f"{user_id}.{expires}"), signature):
            return None
        if int(expires) < time.time():
            return None
        return int(user_id)
    except ValueError:
        return None
