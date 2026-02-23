"""
The Agent — Pydantic 스키마
API 입출력 검증용.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Inbox ─────────────────────────────────────────────────

class InboxRequest(BaseModel):
    """사용자 자연어 입력."""
    text: str = Field(..., min_length=1, max_length=1000, description="자연어 입력 텍스트")


class InboxConfirmRequest(BaseModel):
    """Inbox 파싱 결과 확인/수정."""
    corrections: Optional[dict] = None
    user_responses: Optional[list[dict]] = None


# ─── Task ──────────────────────────────────────────────────

class TaskCreate(BaseModel):
    """LLM 파싱 결과 또는 수동 생성용."""
    title: str
    deadline_at: Optional[datetime] = None
    est_minutes: int = Field(default=60, ge=5, le=480)
    energy: int = Field(default=3, ge=1, le=5)
    importance: int = Field(default=3, ge=1, le=5)
    next_action: Optional[str] = None
    project_id: Optional[int] = None


class TaskResponse(BaseModel):
    """Task 조회/반환용."""
    id: int
    title: str
    deadline_at: Optional[datetime] = None
    est_minutes: int
    energy: int
    importance: int
    status: str
    next_action: Optional[str] = None
    project_id: Optional[int] = None
    postpone_count: int
    priority_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskCompleteRequest(BaseModel):
    """Task 완료 시 선택적 데이터."""
    actual_minutes: Optional[int] = None
    energy_actual: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None


class TaskPostponeRequest(BaseModel):
    """Task 미루기."""
    reason: Optional[str] = None


# ─── Plan ──────────────────────────────────────────────────

class PlanRequest(BaseModel):
    """오늘 플랜 생성 요청."""
    current_energy: Optional[int] = Field(default=None, ge=1, le=5)
    available_from: Optional[str] = None  # HH:MM
    available_until: Optional[str] = None  # HH:MM


class PlanBlock(BaseModel):
    """플랜 내 단일 블록."""
    start_at: str  # HH:MM
    end_at: str    # HH:MM
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    next_action: Optional[str] = None
    energy_level: Optional[int] = None
    type: str = "task"  # task / break


class PlanResponse(BaseModel):
    """오늘 플랜 결과."""
    date: str
    blocks: list[PlanBlock]
    total_focus_minutes: int
    total_blocks: int


# ─── Chat ──────────────────────────────────────────────────

class ChatMessageCreate(BaseModel):
    """채팅 메시지 저장용."""
    role: str = "user"
    content: str
    metadata: Optional[dict] = None


class ChatMessageResponse(BaseModel):
    """채팅 메시지 조회 응답."""
    id: int
    role: str
    content: str
    metadata: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageBatchCreate(BaseModel):
    """여러 메시지 일괄 저장."""
    messages: list[ChatMessageCreate]


class ChatHistoryResponse(BaseModel):
    """대화 히스토리 응답 (날짜 페이지네이션)."""
    messages: list[ChatMessageResponse]
    has_more: bool


class WsChatMessage(BaseModel):
    """WebSocket 채팅 메시지."""
    type: str = "chat"
    role: str = "user"
    content: str
    metadata: Optional[dict] = None


# ─── Health ────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """시스템 상태."""
    status: str
    db: str
    scheduler: str
    pending_tasks: int
    today_blocks: int
