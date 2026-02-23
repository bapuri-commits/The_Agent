"""
The Agent — Inbox API
자연어 입력 → M1 Worker 파싱 → 재질문 또는 저장.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Task, CalendarBlock, AuditLog, InboxLog
from app.schemas import InboxRequest, InboxConfirmRequest, TaskResponse
from app.services.inbox import parse_inbox

router = APIRouter()

# Confidence 임계값 (초기: 높게 설정 → calibration으로 자동 조정)
THRESHOLD_AUTO_SAVE = 0.95
THRESHOLD_SUGGEST = 0.80


@router.post("/inbox", status_code=201)
async def create_from_inbox(
    request: InboxRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    자연어 텍스트를 M1 Worker로 구조화하여 처리.

    분기:
    - fallback: LLM 실패 → 원문 저장
    - needs_clarification: 재질문
    - saved_auto: 높은 확신 → 자동 저장
    - needs_confirmation: 중간 확신 → 확인 요청
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="빈 텍스트는 처리할 수 없습니다")

    result = await parse_inbox(text)

    confidence = result["confidence"]
    parse_status = result["parse_status"]
    parsed = result["final_parsed"]

    # ─── fallback ───
    if parse_status == "fallback":
        task = await _save_as_task(db, text, parsed)
        inbox_log = await _save_inbox_log(db, text, result, auto_saved=True)
        _log_audit(db, "system", "task_created", "task", task.id,
                   {"source": "inbox_fallback", "raw_text": text, "inbox_log_id": inbox_log.id})
        await db.flush()
        return {
            "action": "saved_fallback",
            "message": "자동 분석에 실패했어요. 기본값으로 저장했습니다. 수정이 필요하면 말씀해주세요.",
            "task": _task_to_response(task),
            "parsed_from": text,
            "auto_filled": result["auto_filled"],
            "confidence": confidence,
        }

    # ─── needs_clarification ───
    if parse_status == "needs_clarification" or confidence < THRESHOLD_SUGGEST:
        inbox_log = await _save_inbox_log(db, text, result, auto_saved=False)
        return {
            "action": "needs_clarification",
            "message": "몇 가지 확인이 필요해요.",
            "parsed_preview": parsed,
            "clarification": result["clarification"],
            "confidence": confidence,
            "inbox_log_id": inbox_log.id,
            "parsed_from": text,
        }

    # ─── saved_auto (high confidence) ───
    if confidence >= THRESHOLD_AUTO_SAVE:
        saved = await _save_parsed(db, text, parsed, result, auto_saved=True)
        return {
            "action": "saved_auto",
            "message": f"'{parsed.get('title', text)}'(으)로 저장했어요. 수정할 부분이 있나요?",
            **saved,
            "parsed_from": text,
            "auto_filled": result["auto_filled"],
            "confidence": confidence,
        }

    # ─── needs_confirmation (medium confidence) ───
    inbox_log = await _save_inbox_log(db, text, result, auto_saved=False)
    return {
        "action": "needs_confirmation",
        "message": "이렇게 이해했는데 맞나요?",
        "parsed_preview": parsed,
        "confidence": confidence,
        "inbox_log_id": inbox_log.id,
        "parsed_from": text,
        "auto_filled": result["auto_filled"],
    }


# [BUG-1 FIX] InboxConfirmRequest 스키마 적용
# [BUG-5 FIX] user_responses 저장
@router.post("/inbox/{inbox_log_id}/confirm", status_code=201)
async def confirm_inbox(
    inbox_log_id: int,
    request: InboxConfirmRequest = InboxConfirmRequest(),
    db: AsyncSession = Depends(get_db),
):
    """사용자가 파싱 결과를 확인/수정 후 저장 확정."""
    inbox_log = await db.get(InboxLog, inbox_log_id)
    if not inbox_log:
        raise HTTPException(status_code=404, detail="Inbox log를 찾을 수 없습니다")

    parsed = inbox_log.final_result.copy()

    # [BUG-5 FIX] user_responses 기록
    if request.user_responses:
        inbox_log.user_responses = request.user_responses

    # corrections 반영
    if request.corrections:
        for field, value in request.corrections.items():
            parsed[field] = value
        inbox_log.corrections = request.corrections

    # 저장
    saved = await _save_parsed_from_confirm(db, inbox_log.raw_input, parsed, inbox_log)
    return saved


# ─── 저장 헬퍼 ─────────────────────────────────────────────

async def _save_parsed(
    db: AsyncSession,
    raw_text: str,
    parsed: dict,
    result: dict,
    auto_saved: bool,
) -> dict:
    """파싱 결과를 category에 따라 task 또는 event로 저장. 응답 dict 반환."""
    category = parsed.get("category", "task")

    if category == "event":
        # [BUG-2 FIX] event_at 없으면 task로 fallback
        event_at = _parse_datetime(parsed.get("event_at"))
        if event_at is None:
            return await _save_as_task_and_respond(db, raw_text, parsed, result, auto_saved)

        # [BUG-3 FIX] est_minutes로 end_at 계산
        est = parsed.get("est_minutes", 60)
        end_at = event_at + timedelta(minutes=est)

        block = CalendarBlock(
            title=parsed.get("title", raw_text),
            start_at=event_at,
            end_at=end_at,
            type="fixed",
            source="inbox",
        )
        db.add(block)
        await db.flush()

        inbox_log = await _save_inbox_log(db, raw_text, result, auto_saved)
        _log_audit(db, "system" if auto_saved else "user", "event_created", "calendar",
                   block.id, {"source": "inbox", "raw_text": raw_text, "inbox_log_id": inbox_log.id})
        await db.flush()

        return {
            "type": "event",
            "message": f"일정 '{block.title}'이 등록됐어요.",
            "calendar_block_id": block.id,
        }

    # task (기본)
    return await _save_as_task_and_respond(db, raw_text, parsed, result, auto_saved)


async def _save_as_task_and_respond(
    db: AsyncSession,
    raw_text: str,
    parsed: dict,
    result: dict,
    auto_saved: bool,
) -> dict:
    """Task로 저장하고 응답 dict 반환."""
    task = await _save_as_task(db, raw_text, parsed)
    inbox_log = await _save_inbox_log(db, raw_text, result, auto_saved)
    _log_audit(db, "system" if auto_saved else "user", "task_created", "task",
               task.id, {"source": "inbox", "raw_text": raw_text, "inbox_log_id": inbox_log.id})
    await db.flush()
    return {"type": "task", "task": _task_to_response(task)}


async def _save_parsed_from_confirm(
    db: AsyncSession,
    raw_text: str,
    parsed: dict,
    inbox_log: InboxLog,
) -> dict:
    """confirm 엔드포인트에서 저장. inbox_log가 이미 존재."""
    category = parsed.get("category", "task")

    if category == "event":
        event_at = _parse_datetime(parsed.get("event_at"))
        if event_at is None:
            task = await _save_as_task(db, raw_text, parsed)
            _log_audit(db, "user", "task_created", "task", task.id,
                       {"source": "inbox_confirmed", "inbox_log_id": inbox_log.id})
            inbox_log.was_auto_saved = False
            await db.flush()
            return {"action": "task_created", "message": f"'{task.title}' 저장 완료!", "task": _task_to_response(task)}

        est = parsed.get("est_minutes", 60)
        end_at = event_at + timedelta(minutes=est)

        block = CalendarBlock(
            title=parsed.get("title", raw_text),
            start_at=event_at,
            end_at=end_at,
            type="fixed",
            source="inbox",
        )
        db.add(block)
        await db.flush()

        _log_audit(db, "user", "event_created", "calendar", block.id,
                   {"source": "inbox_confirmed", "inbox_log_id": inbox_log.id})
        inbox_log.was_auto_saved = False
        await db.flush()
        return {"action": "event_created", "message": f"일정 '{block.title}'이 등록됐어요.", "calendar_block_id": block.id}

    task = await _save_as_task(db, raw_text, parsed)
    _log_audit(db, "user", "task_created", "task", task.id,
               {"source": "inbox_confirmed", "inbox_log_id": inbox_log.id})
    inbox_log.was_auto_saved = False
    await db.flush()
    return {"action": "task_created", "message": f"'{task.title}' 저장 완료!", "task": _task_to_response(task)}


async def _save_as_task(db: AsyncSession, raw_text: str, parsed: dict) -> Task:
    """Task ORM 생성 + flush."""
    task = Task(
        title=parsed.get("title", raw_text),
        deadline_at=_parse_datetime(parsed.get("deadline_at")),
        est_minutes=parsed.get("est_minutes", 60),
        energy=parsed.get("energy", 3),
        importance=parsed.get("importance", 3),
        next_action=parsed.get("next_action"),
        status="pending",
    )
    db.add(task)
    await db.flush()
    return task


async def _save_inbox_log(
    db: AsyncSession,
    raw_text: str,
    result: dict,
    auto_saved: bool,
) -> InboxLog:
    """학습 데이터용 InboxLog 저장."""
    time_meta = result["time_metadata"]

    inbox_log = InboxLog(
        raw_input=raw_text,
        input_hour=time_meta["input_hour"],
        input_day_of_week=time_meta["input_day_of_week"],
        energy_estimate=None,
        parse_result=result["parse_result"],
        confidence=result["confidence"],
        parse_latency_ms=result["latency_ms"],
        clarifications=(
            result["clarification"]
            if result["parse_status"] == "needs_clarification"
            else None
        ),
        final_result=result["final_parsed"],
        was_auto_saved=auto_saved,
    )
    db.add(inbox_log)
    await db.flush()
    return inbox_log


def _log_audit(db, actor: str, event_type: str, target_type: str, target_id: int, payload: dict):
    """audit_log 추가 (flush는 호출부에서)."""
    db.add(AuditLog(
        actor=actor,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
    ))


def _parse_datetime(value) -> datetime | None:
    """문자열 또는 datetime → datetime 변환. 실패 시 None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return None


# [BUG-4 FIX] Task 전용 응답 변환. CalendarBlock이 여기 오지 않음
def _task_to_response(task: Task) -> TaskResponse:
    """Task ORM → TaskResponse 스키마."""
    return TaskResponse(
        id=task.id,
        title=task.title,
        deadline_at=task.deadline_at,
        est_minutes=task.est_minutes,
        energy=task.energy,
        importance=task.importance,
        status=task.status,
        next_action=task.next_action,
        project_id=task.project_id,
        postpone_count=task.postpone_count,
        priority_score=None,
        created_at=task.created_at or datetime.now(timezone.utc),
        updated_at=task.updated_at or datetime.now(timezone.utc),
    )
