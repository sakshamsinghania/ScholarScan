"""User CRUD backed by MongoDB users collection."""

import threading
import uuid
from datetime import datetime, timezone

import bcrypt as _bcrypt

from db.session import get_session, is_db_available
from models.user import User


class UserService:
    """Thread-safe user storage. DB-backed when MongoDB is available, RAM fallback otherwise."""

    def __init__(self):
        self._users_by_id: dict[str, User] = {}
        self._users_by_email: dict[str, User] = {}
        self._lock = threading.Lock()

    def register(self, email: str, password: str, role: str = "teacher") -> User:
        """Create a new user. Raises ValueError if email already taken."""
        normalized_email = email.strip().lower()
        hashed = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()

        if is_db_available():
            with get_session() as db:
                if db is None:
                    raise RuntimeError("Database session unavailable")
                if db["users"].find_one({"email": normalized_email}):
                    raise ValueError("Email already registered")
                user_id = str(uuid.uuid4())
                doc = {
                    "_id": user_id,
                    "email": normalized_email,
                    "hashed_password": hashed,
                    "role": role,
                    "created_at": datetime.now(timezone.utc),
                }
                db["users"].insert_one(doc)
                return self._to_user(doc)

        with self._lock:
            if normalized_email in self._users_by_email:
                raise ValueError("Email already registered")
            user = User(
                id=str(uuid.uuid4()),
                email=normalized_email,
                hashed_password=hashed,
                role=role,
            )
            self._users_by_id[user.id] = user
            self._users_by_email[user.email] = user
            return user

    def authenticate(self, email: str, password: str) -> User | None:
        """Verify credentials. Returns user on success, None on failure."""
        normalized_email = email.strip().lower()

        if is_db_available():
            with get_session() as db:
                if db is None:
                    return None
                doc = db["users"].find_one({"email": normalized_email})
                if doc and _bcrypt.checkpw(password.encode(), doc["hashed_password"].encode()):
                    return self._to_user(doc)
                return None

        with self._lock:
            user = self._users_by_email.get(normalized_email)
        if user and _bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
            return user
        return None

    def get_by_id(self, user_id: str) -> User | None:
        if is_db_available():
            with get_session() as db:
                if db is None:
                    return None
                doc = db["users"].find_one({"_id": user_id})
                return self._to_user(doc) if doc else None

        with self._lock:
            return self._users_by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        normalized_email = email.strip().lower()

        if is_db_available():
            with get_session() as db:
                if db is None:
                    return None
                doc = db["users"].find_one({"email": normalized_email})
                return self._to_user(doc) if doc else None

        with self._lock:
            return self._users_by_email.get(normalized_email)

    @staticmethod
    def _to_user(doc: dict) -> User:
        return User(
            id=doc["_id"],
            email=doc["email"],
            hashed_password=doc["hashed_password"],
            role=doc.get("role", "teacher"),
            created_at=doc.get("created_at"),
        )
