"""
The Agent — Tasks API
Task CRUD + 완료/미루기 + priority_score 정렬.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Task, UserProfile, AuditLog
from app.schemas import TaskResponse, TaskCompleteRequest, TaskPostponeRequest
from app.services.prioritizer import prioritize_tasks, KST

router = APIRouter()


@router.get("/tasks", response_model=dict)
async def list_tasks(
    status: str = Query(default="pending", description="pending/in_progress/done/cancelled/all"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Task 목록 조회. priority_score 내림차순 정렬."""
    query = select(Task)

    if status != "all":
        query = query.where(Task.status == status)

    result = await db.execute(query)
    tasks = list(result.scalars().all())

    # 전체 개수
    count_query = select(sqlfunc.count(Task.id))
    if status != "all":
        count_query = count_query.where(Task.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Priority score 계산 + 정렬
    now = datetime.now(KST)
    profile = await db.get(UserProfile, 1)

    if profile and status in ("pending", "in_progress"):
        scored = prioritize_tasks(tasks, now, profile)
        task_responses = [
            _to_response(task, score) for task, score in scored
        ]
    else:
        task_responses = [_to_response(t, None) for t in tasks]

    return {
        "tasks": task_responses[:limit],
        "total": total,
    }


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    request: TaskCompleteRequest = TaskCompleteRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Task 완료 처리."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task를 찾을 수 없습니다")

    task.status = "done"

    db.add(AuditLog(
        actor="user",
        event_type="task_completed",
        target_type="task",
        target_id=task.id,
        payload={
            "actual_minutes": request.actual_minutes,
            "energy_actual": request.energy_actual,
            "notes": request.notes,
        },
    ))

    return {"task_id": task.id, "status": "done"}


@router.post("/tasks/{task_id}/postpone")
async def postpone_task(
    task_id: int,
    request: TaskPostponeRequest = TaskPostponeRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Task 미루기. postpone_count 증가 + 우선순위 자동 상승."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task를 찾을 수 없습니다")

    task.postpone_count += 1

    db.add(AuditLog(
        actor="user",
        event_type="task_postponed",
        target_type="task",
        target_id=task.id,
        payload={
            "reason": request.reason,
            "postpone_count": task.postpone_count,
        },
    ))

    return {
        "task_id": task.id,
        "postpone_count": task.postpone_count,
        "message": "우선순위가 올라갔습니다. 다음 plan에 반영됩니다.",
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Task 취소. status를 cancelled로 변경."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task를 찾을 수 없습니다")

    if task.status == "cancelled":
        return {"task_id": task.id, "status": "cancelled", "message": "이미 취소된 task입니다."}

    task.status = "cancelled"

    db.add(AuditLog(
        actor="user",
        event_type="task_cancelled",
        target_type="task",
        target_id=task.id,
        payload={"previous_status": task.status},
    ))

    return {"task_id": task.id, "status": "cancelled", "message": "취소되었습니다."}


# ─── Helper ────────────────────────────────────────────────

def _to_response(task: Task, score: float | None) -> TaskResponse:
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
        priority_score=score,
        created_at=task.created_at or datetime.now(timezone.utc),
        updated_at=task.updated_at or datetime.now(timezone.utc),
    )
