"""Authentication and authorization for web API."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class User:
    username: str
    password_hash: str
    roles: list[str] = field(default_factory=list)
    api_key: str = ""
    created_at: float = 0.0
    last_login: float = 0.0
    active: bool = True


class AuthManager:
    def __init__(self, secret: str = "change-me"):
        self.secret = secret
        self.users: dict[str, User] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.api_keys: dict[str, str] = {}

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username: str, password: str, roles: list[str] | None = None) -> User:
        u = User(username=username, password_hash=self.hash_password(password), roles=roles or ["user"],
                 created_at=time.time())
        self.users[username] = u
        return u

    def authenticate(self, username: str, password: str) -> bool:
        u = self.users.get(username)
        if u is None or not u.active:
            return False
        if u.password_hash != self.hash_password(password):
            return False
        u.last_login = time.time()
        return True

    def create_session(self, username: str, ttl: int = 3600) -> str:
        token = base64.urlsafe_b64encode(hashlib.sha256(f"{username}{time.time()}".encode()).digest()).decode()
        self.sessions[token] = {"username": username, "expires": time.time() + ttl}
        return token

    def validate_session(self, token: str) -> str | None:
        s = self.sessions.get(token)
        if s is None:
            return None
        if time.time() > s["expires"]:
            del self.sessions[token]
            return None
        return s["username"]

    def revoke_session(self, token: str):
        self.sessions.pop(token, None)

    def generate_api_key(self, username: str) -> str:
        key = base64.urlsafe_b64encode(hashlib.sha256(f"{username}{time.time()}".encode()).digest()).decode()
        self.api_keys[key] = username
        u = self.users.get(username)
        if u:
            u.api_key = key
        return key

    def validate_api_key(self, key: str) -> str | None:
        return self.api_keys.get(key)

    def create_jwt(self, username: str, ttl: int = 3600) -> str:
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": username, "exp": time.time() + ttl, "iat": time.time()}).encode()).decode().rstrip("=")
        sig = hmac.new(self.secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).hexdigest()
        return f"{header}.{payload}.{sig}"

    def validate_jwt(self, token: str) -> str | None:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, sig = parts
        expected = hmac.new(self.secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        try:
            data = json.loads(base64.urlsafe_b64decode(payload + "=" * (4 - len(payload) % 4)))
        except (ValueError, KeyError):
            return None
        if time.time() > data.get("exp", 0):
            return None
        return data.get("sub")

    def has_role(self, username: str, role: str) -> bool:
        u = self.users.get(username)
        if u is None:
            return False
        return role in u.roles or "admin" in u.roles

    def require_role(self, username: str, role: str) -> bool:
        return self.has_role(username, role)

    def list_users(self) -> list[dict[str, Any]]:
        return [{"username": u.username, "roles": u.roles, "active": u.active, "last_login": u.last_login} for u in self.users.values()]

    def deactivate_user(self, username: str):
        if username in self.users:
            self.users[username].active = False

    def change_password(self, username: str, new_password: str) -> bool:
        if username in self.users:
            self.users[username].password_hash = self.hash_password(new_password)
            return True
        return False
