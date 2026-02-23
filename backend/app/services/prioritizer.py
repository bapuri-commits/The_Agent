"""
The Agent — Deterministic Priority Engine
같은 입력 → 항상 같은 출력. LLM은 관여하지 않는다.
"""

import math
from datetime import datetime, timedelta, timezone

from app.models import Task, UserProfile

KST = timezone(timedelta(hours=9))

# ─── 기본 가중치 ──────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "w_deadline":   0.35,
    "w_importance": 0.25,
    "w_short":      0.10,
    "w_energy":     0.15,
    "w_postpone":   0.15,
}


# ─── 구성 함수 ────────────────────────────────────────────

def f(hours_left: float) -> float:
    """
    Deadline urgency: 0.0 ~ 1.0
    시그모이드 기반. 24h 부근에서 급격 상승.
    """
    if hours_left <= 0:
        return 1.0
    if hours_left >= 168:
        return 0.0
    midpoint = 48
    steepness = 0.08
    return 1.0 / (1.0 + math.exp(steepness * (hours_left - midpoint)))


def normalize(value: int, min_val: int = 1, max_val: int = 5) -> float:
    """1~5 → 0.0~1.0"""
    return (value - min_val) / (max_val - min_val)


def g(est_minutes: int) -> float:
    """
    Short task bonus: 0.0 ~ 1.0
    짧은 작업에 보너스. ADHD 패턴 방지.
    """
    if est_minutes <= 15:
        return 1.0
    if est_minutes >= 60:
        return 0.0
    return max(0.0, 1.0 - (est_minutes - 15) / 45)


def h(energy_required: int, current_energy: int) -> float:
    """
    Energy match: 0.0 ~ 1.0
    현재 에너지와 작업 요구 에너지의 매칭.
    """
    diff = current_energy - energy_required
    if 0 <= diff <= 1:
        return 1.0
    elif diff > 1:
        return 0.7
    else:
        return max(0.0, 1.0 + diff * 0.3)


def p(postpone_count: int) -> float:
    """
    Postpone penalty: 0.0 ~ 1.0
    미루기 횟수에 비례.
    """
    return min(1.0, postpone_count * 0.25)


# ─── 에너지 추정 ──────────────────────────────────────────

def estimate_current_energy(hour: int, profile: UserProfile) -> int:
    """
    시간표 기반 에너지 추정.
    향후 사용자 직접 입력 + 패턴 학습으로 대체 예정.
    """
    peak_hours = profile.focus_peak_hours if isinstance(profile.focus_peak_hours, list) else []
    low_hours = profile.low_energy_hours if isinstance(profile.low_energy_hours, list) else []

    if hour in peak_hours:
        return 5
    if hour in low_hours:
        return 2
    return 3


# ─── deadline 해소 ────────────────────────────────────────

def resolve_deadline(deadline_at: datetime | None, now: datetime) -> datetime:
    """deadline이 None이면 오늘 23:59 KST."""
    if deadline_at is not None:
        return deadline_at
    return now.astimezone(KST).replace(hour=23, minute=59, second=0, microsecond=0)


# ─── 불변 규칙 ────────────────────────────────────────────

def apply_invariant_rules(task: Task, now: datetime) -> float | None:
    """
    점수와 무관한 하드 규칙. 해당되면 override 점수 반환, 아니면 None.
    deadline_at이 None(= 오늘 마감)인 task에는 적용하지 않음.
    """
    if task.deadline_at is None:
        return None

    deadline = task.deadline_at
    # timezone-naive → KST로 간주
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=KST)
    now_aware = now if now.tzinfo else now.replace(tzinfo=KST)

    seconds_left = (deadline - now_aware).total_seconds()

    if seconds_left < 0:
        return 20.0

    if seconds_left < 86400:
        return 10.0

    return None


# ─── 최종 계산 ────────────────────────────────────────────

def calculate_priority(
    task: Task,
    now: datetime,
    current_energy: int,
    weights: dict | None = None,
) -> float:
    """
    결정론적 우선순위 점수 계산.
    같은 입력 → 항상 같은 출력.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    override = apply_invariant_rules(task, now)
    if override is not None:
        return override

    deadline = resolve_deadline(task.deadline_at, now)
    # timezone 방어
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=KST)
    now_aware = now if now.tzinfo else now.replace(tzinfo=KST)
    hours_left = (deadline - now_aware).total_seconds() / 3600

    score = (
        weights["w_deadline"]   * f(hours_left)
      + weights["w_importance"] * normalize(task.importance)
      + weights["w_short"]      * g(task.est_minutes)
      + weights["w_energy"]     * h(task.energy, current_energy)
      + weights["w_postpone"]   * p(task.postpone_count)
    )
    return round(score, 4)


# ─── 배치 계산 (task 리스트) ───────────────────────────────

def prioritize_tasks(
    tasks: list[Task],
    now: datetime,
    profile: UserProfile,
    weights: dict | None = None,
) -> list[tuple[Task, float]]:
    """
    전체 task 리스트에 priority_score를 계산하고 내림차순 정렬.
    Returns: [(task, score), ...] 정렬됨.
    """
    hour = now.astimezone(KST).hour
    current_energy = estimate_current_energy(hour, profile)

    scored = []
    for task in tasks:
        score = calculate_priority(task, now, current_energy, weights)
        scored.append((task, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
