"""
Department entity — organisational unit within an Organisation.
"""

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, OrganisationMixin


class Department(Base, TimestampMixin, OrganisationMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relations
    organisation = relationship("Organisation", back_populates="departments")
    teams = relationship("Team", back_populates="department")
    employees = relationship("Employee", back_populates="department")
