"""
The Agent — Chat API
대화 히스토리 저장/조회. M4 Distiller 학습 데이터 수집 목적.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import ChatMessage
from app.schemas import (
    ChatMessageBatchCreate,
    ChatMessageResponse,
    ChatHistoryResponse,
)

router = APIRouter()

MESSAGES_PER_PAGE = 50


@router.post("/chat/messages", status_code=201)
async def save_messages(
    request: ChatMessageBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    """메시지 일괄 저장. 프론트엔드가 user+assistant 메시지를 한 번에 보냄."""
    saved = []
    for msg in request.messages:
        record = ChatMessage(
            role=msg.role,
            content=msg.content,
            metadata_json=msg.metadata,
        )
        db.add(record)
        await db.flush()
        saved.append(ChatMessageResponse(
            id=record.id,
            role=record.role,
            content=record.content,
            metadata=record.metadata_json,
            created_at=record.created_at or datetime.now(timezone.utc),
        ))
    return {"saved": len(saved), "messages": saved}


@router.get("/chat/messages", response_model=ChatHistoryResponse)
async def get_messages(
    before: datetime | None = Query(
        default=None,
        description="이 시각 이전의 메시지를 조회 (ISO 8601). 없으면 최신부터.",
    ),
    limit: int = Query(default=MESSAGES_PER_PAGE, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    대화 히스토리 조회. 날짜별 점진 로드를 위한 커서 페이지네이션.
    최신 메시지부터 limit+1개를 가져와서 has_more 판단.
    응답은 시간순 정렬(오래된 것 먼저)로 반환.
    """
    query = select(ChatMessage).order_by(ChatMessage.created_at.desc())

    if before is not None:
        query = query.where(ChatMessage.created_at < before)

    query = query.limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars().all())

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    rows.reverse()

    messages = [
        ChatMessageResponse(
            id=r.id,
            role=r.role,
            content=r.content,
            metadata=r.metadata_json,
            created_at=r.created_at or datetime.now(timezone.utc),
        )
        for r in rows
    ]

    return ChatHistoryResponse(messages=messages, has_more=has_more)
