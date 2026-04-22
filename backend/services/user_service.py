"""In-memory user store with bcrypt password hashing."""

import threading
import uuid

import bcrypt as _bcrypt

from models.user import User


class UserService:
    """Thread-safe in-memory user storage. Will be replaced by Postgres in Phase 2."""

    def __init__(self):
        self._users_by_id: dict[str, User] = {}
        self._users_by_email: dict[str, User] = {}
        self._lock = threading.Lock()

    def register(self, email: str, password: str, role: str = "teacher") -> User:
        """Create a new user. Raises ValueError if email already taken."""
        with self._lock:
            if email.lower() in self._users_by_email:
                raise ValueError("Email already registered")

            hashed = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
            user = User(
                id=str(uuid.uuid4()),
                email=email.lower(),
                hashed_password=hashed,
                role=role,
            )
            self._users_by_id[user.id] = user
            self._users_by_email[user.email] = user
            return user

    def authenticate(self, email: str, password: str) -> User | None:
        """Verify credentials. Returns user on success, None on failure."""
        with self._lock:
            user = self._users_by_email.get(email.lower())

        if user and _bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
            return user
        return None

    def get_by_id(self, user_id: str) -> User | None:
        with self._lock:
            return self._users_by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        with self._lock:
            return self._users_by_email.get(email.lower())
