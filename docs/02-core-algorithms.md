# 02 — Core Algorithms

## 1. Deterministic Priority Engine

### 점수 공식

```
priority_score =
    w_deadline  * f(deadline_hours_left)
  + w_importance * normalize(importance)
  + w_short     * g(est_minutes)
  + w_energy    * h(energy_required, current_energy_level)
  + w_postpone  * p(postpone_count)
```

### 기본 가중치 (user_profile.rules_json에서 조정 가능)

```python
DEFAULT_WEIGHTS = {
    "w_deadline":   0.35,
    "w_importance": 0.25,
    "w_short":      0.10,
    "w_energy":     0.15,
    "w_postpone":   0.15,
}
```

### 구성 함수 정의

#### f(hours_left) — Deadline Urgency

마감이 가까울수록 급격히 상승. ADHD 마감 효과를 시뮬레이션.

```python
def f(hours_left: float) -> float:
    """
    Deadline urgency score: 0.0 ~ 1.0
    - 이미 지남 (<=0): 1.0 (최대 긴급)
    - 24h 이내: 0.7 ~ 1.0 (급격 상승)
    - 1주일 이상: ~0.0 (여유)
    """
    if hours_left <= 0:
        return 1.0
    if hours_left >= 168:  # 1주일 이상
        return 0.0
    # 시그모이드 기반: 24h 부근에서 급격 상승
    import math
    midpoint = 48  # 2일 기준
    steepness = 0.08
    return 1.0 / (1.0 + math.exp(steepness * (hours_left - midpoint)))
```

시각화 (대략적 값):
```
hours_left | score
-----------+------
     0     | 1.00  (지남)
     6     | 0.97
    12     | 0.95
    24     | 0.87
    48     | 0.50  (2일)
    72     | 0.13  (3일)
   120     | 0.004 (5일)
   168     | 0.00  (1주)
```

#### normalize(importance) — Importance 정규화

```python
def normalize(value: int, min_val: int = 1, max_val: int = 5) -> float:
    """1~5 스케일을 0.0~1.0으로 정규화"""
    return (value - min_val) / (max_val - min_val)
```

#### g(est_minutes) — Short Task Bonus

짧은 작업에 보너스. "2분이면 끝나는 일"을 계속 미루는 ADHD 패턴 방지.

```python
def g(est_minutes: int) -> float:
    """
    Short task bonus: 0.0 ~ 1.0
    - 15분 이하: 1.0 (최대 보너스)
    - 30분: 0.5
    - 60분 이상: 0.0
    """
    if est_minutes <= 15:
        return 1.0
    if est_minutes >= 60:
        return 0.0
    return max(0.0, 1.0 - (est_minutes - 15) / 45)
```

#### h(energy_required, current_energy) — Energy Match

현재 에너지와 작업 요구 에너지의 매칭 점수.

```python
def h(energy_required: int, current_energy: int) -> float:
    """
    Energy match score: 0.0 ~ 1.0
    - 에너지 딱 맞거나 여유: 1.0
    - 에너지 부족할수록 감소 (무리한 작업 배치 방지)
    - 에너지 크게 남으면 약간 감소 (고에너지 시간에 저에너지 작업 배치 비효율)
    
    energy_required: 1~5 (작업이 요구하는 에너지)
    current_energy: 1~5 (현재 시간대의 에너지 레벨)
    """
    diff = current_energy - energy_required
    if diff >= 0 and diff <= 1:
        return 1.0   # 딱 맞거나 약간 여유
    elif diff > 1:
        return 0.7   # 고에너지 시간에 저에너지 작업 = 약간 비효율
    else:
        # 에너지 부족: diff < 0
        return max(0.0, 1.0 + diff * 0.3)  # -1→0.7, -2→0.4, -3→0.1
```

#### p(postpone_count) — Postpone Penalty

미루기 횟수에 비례해 우선순위 상승.

```python
def p(postpone_count: int) -> float:
    """
    Postpone penalty: 0.0 ~ 1.0
    - 0회: 0.0
    - 1회: 0.25
    - 2회: 0.50
    - 3회+: 0.75~1.0
    """
    return min(1.0, postpone_count * 0.25)
```

### 최종 계산 함수

```python
def calculate_priority(
    task: Task,
    now: datetime,
    current_energy: int,
    weights: dict = DEFAULT_WEIGHTS,
) -> float:
    """
    결정론적 우선순위 점수 계산.
    같은 입력 → 항상 같은 출력. 단위 테스트로 고정.
    """
    hours_left = (task.deadline_at - now).total_seconds() / 3600

    score = (
        weights["w_deadline"]   * f(hours_left)
      + weights["w_importance"] * normalize(task.importance)
      + weights["w_short"]      * g(task.est_minutes)
      + weights["w_energy"]     * h(task.energy, current_energy)
      + weights["w_postpone"]   * p(task.postpone_count)
    )
    return round(score, 4)
```

### 불변 규칙 (Override)

점수와 무관하게 항상 적용되는 하드 규칙:

```python
INVARIANT_RULES = [
    # 마감 24h 이내 → 무조건 최상단 (score = 10.0)
    lambda task, now: 10.0 if (task.deadline_at - now).total_seconds() < 86400 else None,
    
    # 이미 마감 지남 → 최최상단 (score = 20.0)
    lambda task, now: 20.0 if task.deadline_at < now else None,
]
```

---

## 2. Today Plan Algorithm

### 개요

오늘 하루의 free window에 task를 30~60분 블록으로 배치하는 **Greedy 알고리즘**.

### 알고리즘 (의사코드)

```python
def generate_today_plan(
    tasks: list[Task],           # pending tasks, priority 순 정렬됨
    calendar: list[CalendarBlock], # 오늘의 fixed/blocked 이벤트
    profile: UserProfile,
) -> list[PlannedBlock]:
    
    # 1. Free windows 추출
    free_windows = extract_free_windows(
        date=today,
        fixed_events=calendar,
        sleep_window=profile.sleep_window,  # e.g., 00:00~08:00
    )
    
    # 2. 각 free window에 에너지 레벨 태깅
    for window in free_windows:
        window.energy_level = get_energy_level(
            window.start_at, 
            profile.focus_peak_hours,   # e.g., [10, 11, 14, 15, 16]
            profile.low_energy_hours,   # e.g., [13, 20, 21]
        )
    
    # 3. Greedy 배치
    planned = []
    remaining_tasks = sorted(tasks, key=lambda t: t.priority_score, reverse=True)
    
    for task in remaining_tasks:
        if task.status != "pending":
            continue
            
        # 블록 크기 결정 (30분 또는 60분, est_minutes 기준)
        block_size = determine_block_size(task.est_minutes)
        
        # 가장 적합한 window 찾기
        best_window = find_best_window(
            task=task,
            windows=free_windows,
            block_size=block_size,
        )
        
        if best_window is None:
            continue  # 오늘 배치 불가 → 내일로
        
        # 블록 할당
        block = PlannedBlock(
            task_id=task.id,
            start_at=best_window.current_start,
            end_at=best_window.current_start + block_size,
            task_title=task.title,
            next_action=task.next_action,
        )
        planned.append(block)
        
        # window에서 사용한 시간 제거
        best_window.current_start += block_size
        
        # 휴식 블록 삽입 (2블록 연속 후 10분 쉬기)
        if should_insert_break(planned):
            insert_break(planned, best_window, minutes=10)
    
    return planned
```

### 블록 크기 규칙

```python
def determine_block_size(est_minutes: int) -> timedelta:
    """
    - est <= 30분: 30분 블록
    - est 31~60분: 60분 블록
    - est > 60분: 60분 블록 (나머지는 다음 블록으로)
    """
    if est_minutes <= 30:
        return timedelta(minutes=30)
    return timedelta(minutes=60)
```

### Window 선택 기준

```python
def find_best_window(task, windows, block_size) -> Window | None:
    """
    1순위: 에너지 매칭 (고에너지 작업 → 집중 시간대)
    2순위: 충분한 여유 시간
    3순위: 가장 이른 시간 (앞에서부터 채우기)
    """
    candidates = []
    for w in windows:
        remaining = w.end_at - w.current_start
        if remaining >= block_size:
            energy_match = h(task.energy, w.energy_level)
            candidates.append((energy_match, w.current_start, w))
    
    if not candidates:
        return None
    
    # 에너지 매칭 > 이른 시간 순
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]
```

### 제약 조건

- 수면 시간(sleep_window) 내 블록 배치 금지
- 연속 2블록(120분) 후 반드시 10분 휴식
- 하루 최대 블록 수 제한 (기본: 8블록 = 4~8시간)
- 식사 시간 보호 (12:00~13:00, 18:00~19:00 기본 blocked)

---

## 3. Enforcement Logic

### 3단계 구조

```
Stage 1: Narrowing (좁히기)
  → 지나간 블록의 미완료 task 감지
  → next_action 1개만 추출하여 제시
  → "지금 딱 이것만 하세요: [next_action]"

Stage 2: Commitment (약속)
  → 사용자가 "할게" / "미룰게" 선택
  → "할게" → 새 시간 블록 즉시 배정
  → "미룰게" → postpone_count++, 우선순위 자동 상승

Stage 3: Escalation (심화)
  → postpone_count >= 3 → 강도 높은 알림
  → 마감 24h 이내 + 미이행 → "경고: [task] 마감 X시간 남음"
  → 자동 재분해: 큰 task를 더 작은 action으로 쪼갬
```

### 감지 로직 (의사코드)

```python
def check_enforcement(now: datetime) -> list[EnforcementAction]:
    """30분 간격으로 APScheduler가 호출"""
    actions = []
    
    # 1. 지나간 블록 중 미완료 찾기
    missed_blocks = get_missed_blocks(now)
    
    for block in missed_blocks:
        task = get_task(block.task_id)
        
        if task.postpone_count >= 3:
            # Stage 3: Escalation
            actions.append(EnforcementAction(
                type="escalation",
                task_id=task.id,
                message=f"⚠️ '{task.title}' {task.postpone_count}번째 미루기. "
                        f"마감까지 {hours_until_deadline(task)}시간.",
                suggested_action=task.next_action,
                auto_decompose=True,
            ))
        else:
            # Stage 1: Narrowing
            actions.append(EnforcementAction(
                type="narrowing",
                task_id=task.id,
                message=f"'{task.title}' 블록이 지났어요. "
                        f"지금 딱 이것만: {task.next_action}",
                suggested_action=task.next_action,
            ))
    
    # 2. 마감 임박 경고 (별도)
    urgent_tasks = get_tasks_due_within(hours=24)
    for task in urgent_tasks:
        if task.status == "pending":
            actions.append(EnforcementAction(
                type="deadline_warning",
                task_id=task.id,
                message=f"🔴 '{task.title}' 마감 {hours_until_deadline(task)}시간 전!",
            ))
    
    return actions
```

### 자동 재분해

```python
async def auto_decompose(task: Task) -> list[str]:
    """
    postpone_count >= 3 또는 est_minutes > 120인 경우
    LLM을 사용해 더 작은 action으로 분해
    """
    if task.est_minutes <= 30:
        return [task.next_action]  # 이미 충분히 작음
    
    sub_actions = await llm.decompose(
        task_title=task.title,
        current_next_action=task.next_action,
        est_minutes=task.est_minutes,
        max_actions=3,
        max_minutes_per_action=30,  # 각 action은 30분 이내
    )
    
    # 첫 번째 sub_action을 task.next_action으로 업데이트
    task.next_action = sub_actions[0]
    return sub_actions
```

### 알림 빈도 제어 (과도 알림 방지)

```python
NOTIFICATION_RULES = {
    "narrowing": {
        "cooldown_minutes": 60,     # 같은 task에 대해 1시간에 1번
        "max_per_day": 5,           # 하루 최대 5번
    },
    "escalation": {
        "cooldown_minutes": 30,     # 더 자주
        "max_per_day": 8,
    },
    "deadline_warning": {
        "cooldown_minutes": 120,    # 2시간에 1번
        "max_per_day": 4,
    },
}
```
