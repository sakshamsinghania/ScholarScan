"""In-memory user store with bcrypt password hashing."""

import threading
import uuid

import bcrypt as _bcrypt
from sqlalchemy import select

from db.models import UserAccount
from db.session import get_session, is_db_available
from models.user import User


class UserService:
    """Thread-safe in-memory user storage. Will be replaced by Postgres in Phase 2."""

    def __init__(self):
        self._users_by_id: dict[str, User] = {}
        self._users_by_email: dict[str, User] = {}
        self._lock = threading.Lock()

    def register(self, email: str, password: str, role: str = "teacher") -> User:
        """Create a new user. Raises ValueError if email already taken."""
        normalized_email = email.strip().lower()
        hashed = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()

        if is_db_available():
            with get_session() as session:
                if session is None:
                    raise RuntimeError("Database session unavailable")

                existing = session.execute(
                    select(UserAccount).where(UserAccount.email == normalized_email)
                ).scalar_one_or_none()
                if existing is not None:
                    raise ValueError("Email already registered")

                record = UserAccount(
                    id=str(uuid.uuid4()),
                    email=normalized_email,
                    hashed_password=hashed,
                    role=role,
                )
                session.add(record)
                session.flush()
                session.refresh(record)
                return self._to_user(record)

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
            with get_session() as session:
                if session is None:
                    return None
                user = session.execute(
                    select(UserAccount).where(UserAccount.email == normalized_email)
                ).scalar_one_or_none()
                if user and _bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
                    return self._to_user(user)
                return None

        with self._lock:
            user = self._users_by_email.get(normalized_email)

        if user and _bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
            return user
        return None

    def get_by_id(self, user_id: str) -> User | None:
        if is_db_available():
            with get_session() as session:
                if session is None:
                    return None
                user = session.get(UserAccount, user_id)
                return self._to_user(user) if user is not None else None

        with self._lock:
            return self._users_by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        normalized_email = email.strip().lower()

        if is_db_available():
            with get_session() as session:
                if session is None:
                    return None
                user = session.execute(
                    select(UserAccount).where(UserAccount.email == normalized_email)
                ).scalar_one_or_none()
                return self._to_user(user) if user is not None else None

        with self._lock:
            return self._users_by_email.get(normalized_email)

    @staticmethod
    def _to_user(record: UserAccount) -> User:
        return User(
            id=record.id,
            email=record.email,
            hashed_password=record.hashed_password,
            role=record.role,
            created_at=record.created_at,
        )
