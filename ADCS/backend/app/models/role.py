from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


# Association table user <-> role
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("institution_id", Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True),
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=True, nullable=False)

    users = relationship("User", secondary=user_roles, back_populates="roles")
