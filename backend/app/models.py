"""
The Agent — ORM 모델
Postgres 기준. 03-db-schema.md의 DDL을 SQLAlchemy로 표현.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ─── Helpers ───────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── Projects ─────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="personal"
    )
    weight: Mapped[Optional[float]] = mapped_column(default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationships
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")

    __table_args__ = (
        CheckConstraint("type IN ('course', 'personal')", name="ck_project_type"),
    )


# ─── Tasks ─────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    deadline_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), default=None
    )
    est_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    energy: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    importance: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    next_action: Mapped[Optional[str]] = mapped_column(Text, default=None)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"), default=None
    )
    postpone_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    planned_blocks: Mapped[list["PlannedBlock"]] = relationship(back_populates="task")
    completions: Mapped[list["TaskCompletion"]] = relationship(back_populates="task")

    __table_args__ = (
        CheckConstraint("energy BETWEEN 1 AND 5", name="ck_task_energy"),
        CheckConstraint("importance BETWEEN 1 AND 5", name="ck_task_importance"),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'done', 'cancelled')",
            name="ck_task_status",
        ),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_deadline", "deadline_at"),
        Index("idx_tasks_project", "project_id"),
    )


# ─── Calendar Blocks ──────────────────────────────────────

class CalendarBlock(Base):
    __tablename__ = "calendar_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(Text, default=None)
    start_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    end_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="manual")
    recurrence: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('fixed', 'free', 'blocked')", name="ck_calendar_type"
        ),
        Index("idx_calendar_date", "start_at", "end_at"),
    )


# ─── Planned Blocks ───────────────────────────────────────

class PlannedBlock(Base):
    __tablename__ = "planned_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id"), nullable=False
    )
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    start_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    end_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="planned_blocks")

    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'completed', 'missed', 'skipped')",
            name="ck_planned_status",
        ),
        Index("idx_planned_date", "date"),
        Index("idx_planned_task", "task_id"),
    )


# ─── User Profile ─────────────────────────────────────────

class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="Asia/Seoul")
    sleep_start: Mapped[str] = mapped_column(Text, nullable=False, default="01:00")
    sleep_end: Mapped[str] = mapped_column(Text, nullable=False, default="09:00")
    focus_peak_hours: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=[9, 10, 11, 12]
    )
    low_energy_hours: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=[14, 15, 22, 23]
    )
    meal_blocks: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=[
            {"start": "12:00", "end": "13:00"},
            {"start": "18:00", "end": "19:00"},
        ],
    )
    max_blocks_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    rules_json: Mapped[Optional[dict]] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ─── Audit Logs ────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(20), nullable=False, default="system")
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    target_id: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_audit_event", "event_type"),
        Index("idx_audit_time", "created_at"),
    )


# ─── Task Completions ─────────────────────────────────────

class TaskCompletion(Base):
    __tablename__ = "task_completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id"), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    was_on_time: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    energy_actual: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="completions")

    __table_args__ = (
        CheckConstraint(
            "energy_actual IS NULL OR energy_actual BETWEEN 1 AND 5",
            name="ck_completion_energy",
        ),
    )


# ─── Inbox Logs (학습 데이터) ──────────────────────────────

class InboxLog(Base):
    __tablename__ = "inbox_logs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 원본 입력
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    input_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    input_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    input_day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    energy_estimate: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    # M1 파싱 결과
    parse_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    parse_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    # 재질문
    clarifications: Mapped[Optional[dict]] = mapped_column(JSONB, default=None)
    user_responses: Mapped[Optional[dict]] = mapped_column(JSONB, default=None)

    # 최종 결과
    final_result: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # 학습 데이터
    corrections: Mapped[Optional[dict]] = mapped_column(JSONB, default=None)
    was_auto_saved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_inbox_logs_hour", "input_hour"),
        Index("idx_inbox_logs_confidence", "confidence"),
    )


# ─── Chat Messages (대화 히스토리) ────────────────────────

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="ck_chat_role",
        ),
        Index("idx_chat_created", "created_at"),
    )
