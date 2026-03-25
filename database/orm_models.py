from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # tags stored as JSON string e.g. '["nlp","text","process"]'


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    caller: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    units: Mapped[int] = mapped_column(Integer, nullable=False)
    request_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    __table_args__ = (UniqueConstraint("request_id", name="uq_usage_logs_request_id"),)


class UsageSummary(Base):
    __tablename__ = "usage_summary"

    target: Mapped[str] = mapped_column(String(255), primary_key=True)
    total_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
