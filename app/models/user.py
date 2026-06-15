from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class User(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "users"

    email: Mapped[str] = mappped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, comment="Unique constraint on email ensures no duplicate users.")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)

    # ─── Relationships ────────────────────────────────────────────────────────────
    evaluations_requested: Mapped[list["EvaluationRequest"]] = relationship("EvaluationRequest", back_populates="requester", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email!r}>"
