# 03 — DB Schema

## 설계 원칙

- SQLite로 시작하되, SQLAlchemy ORM 사용 → Postgres 전환 무비용
- 모든 timestamp는 UTC 저장, 표시 시 KST 변환
- `id`는 Integer autoincrement (MVP), UUID 전환은 Phase 2
- 외래 키 제약 활성화 (`PRAGMA foreign_keys = ON`)

---

## 테이블 정의

### tasks

MVP의 핵심 테이블. 모든 할 일/과제/일정이 여기 저장.

```sql
CREATE TABLE tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    deadline_at     TIMESTAMP,                          -- NULL 허용 (마감 없는 task)
    est_minutes     INTEGER NOT NULL DEFAULT 60,        -- 예상 소요 시간 (분)
    energy          INTEGER NOT NULL DEFAULT 3,         -- 요구 에너지 1~5
    importance      INTEGER NOT NULL DEFAULT 3,         -- 중요도 1~5
    status          TEXT NOT NULL DEFAULT 'pending',    -- pending/in_progress/done/cancelled
    next_action     TEXT,                               -- "지금 할 수 있는 구체적 행동 1개"
    project_id      INTEGER REFERENCES projects(id),    -- NULL 가능 (프로젝트 없는 단독 task)
    postpone_count  INTEGER NOT NULL DEFAULT 0,         -- 미루기 횟수
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_deadline ON tasks(deadline_at);
CREATE INDEX idx_tasks_project ON tasks(project_id);
```

**status 상태 전이:**
```
pending → in_progress → done
pending → cancelled
pending → pending (postpone: postpone_count++)
in_progress → pending (다시 미룸)
```

### projects

과목/개인 프로젝트 그룹핑.

```sql
CREATE TABLE projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,                          -- "운영체제", "알고리즘", "개인 프로젝트"
    type        TEXT NOT NULL DEFAULT 'personal',      -- course / personal
    weight      REAL,                                  -- 성적 비중 (course인 경우, 0.0~1.0)
    notes       TEXT,                                  -- 자유 메모
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### calendar_blocks

고정 일정(수업, 약속)과 자유 시간 관리.

```sql
CREATE TABLE calendar_blocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT,                                   -- "운영체제 수업", "점심"
    start_at    TIMESTAMP NOT NULL,
    end_at      TIMESTAMP NOT NULL,
    type        TEXT NOT NULL,                          -- fixed / free / blocked
    source      TEXT DEFAULT 'manual',                  -- manual / google_calendar / generated
    recurrence  TEXT,                                   -- 반복 규칙 (Phase 2: RFC 5545 RRULE)
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_calendar_date ON calendar_blocks(start_at, end_at);
```

**type 의미:**
- `fixed`: 움직일 수 없는 일정 (수업, 약속)
- `blocked`: 사용 불가 시간 (수면, 식사)
- `free`: 명시적으로 비어있는 시간 (planner가 사용)

### planned_blocks

Today Plan으로 생성된 작업 블록. calendar_blocks와 별도 관리.

```sql
CREATE TABLE planned_blocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id),
    date        DATE NOT NULL,                          -- 해당 날짜
    start_at    TIMESTAMP NOT NULL,
    end_at      TIMESTAMP NOT NULL,
    status      TEXT NOT NULL DEFAULT 'scheduled',      -- scheduled / completed / missed / skipped
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_planned_date ON planned_blocks(date);
CREATE INDEX idx_planned_task ON planned_blocks(task_id);
```

### user_profile

사용자 설정. 단일 row (id=1).

```sql
CREATE TABLE user_profile (
    id                  INTEGER PRIMARY KEY DEFAULT 1,
    timezone            TEXT NOT NULL DEFAULT 'Asia/Seoul',
    sleep_start         TEXT NOT NULL DEFAULT '00:00',      -- HH:MM (수면 시작)
    sleep_end           TEXT NOT NULL DEFAULT '08:00',      -- HH:MM (기상)
    focus_peak_hours    TEXT NOT NULL DEFAULT '[10,11,14,15,16]',  -- JSON array
    low_energy_hours    TEXT NOT NULL DEFAULT '[13,20,21]',        -- JSON array
    meal_blocks         TEXT NOT NULL DEFAULT '[{"start":"12:00","end":"13:00"},{"start":"18:00","end":"19:00"}]',
    max_blocks_per_day  INTEGER NOT NULL DEFAULT 8,
    rules_json          TEXT,                               -- 가중치 커스텀 등
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### audit_logs

모든 중요 동작 기록. 디버깅 + 신뢰성의 근간.

```sql
CREATE TABLE audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    actor           TEXT NOT NULL DEFAULT 'system',     -- system / user / llm
    event_type      TEXT NOT NULL,                      -- task_created / task_completed / plan_generated / ...
    target_type     TEXT,                               -- task / plan / calendar
    target_id       INTEGER,
    payload_json    TEXT,                               -- 상세 데이터 (JSON)
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_event ON audit_logs(event_type);
CREATE INDEX idx_audit_time ON audit_logs(created_at);
```

### task_completions (습관 추적)

완료 이력. 장기적으로 습관 변화 측정에 사용.

```sql
CREATE TABLE task_completions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         INTEGER NOT NULL REFERENCES tasks(id),
    completed_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    was_on_time     BOOLEAN NOT NULL,                   -- 마감 전 완료 여부
    actual_minutes  INTEGER,                            -- 실제 소요 시간
    energy_actual   INTEGER,                            -- 실제 에너지 (1~5, 선택)
    notes           TEXT,                               -- 회고 메모 (선택)
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## Phase 2 추가 테이블

### memories (RAG 검색용)

```sql
CREATE TABLE memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,                          -- note / preference / pattern / lecture
    text        TEXT NOT NULL,
    embedding   BLOB,                                  -- Phase 2: pgvector의 vector 타입
    tags        TEXT,                                   -- JSON array
    source      TEXT,                                   -- 출처 (manual / auto / lms)
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## ERD (텍스트)

```
projects 1──┐
             │ project_id
             ▼
          tasks ──────┐
             │        │ task_id
             │        ▼
             │   planned_blocks
             │        
             ├──→ task_completions
             │
             └──→ audit_logs (polymorphic: target_type + target_id)

user_profile (singleton, id=1)

calendar_blocks (독립)
```

---

## 초기 데이터 (Seed)

```sql
-- 기본 사용자 프로필
INSERT INTO user_profile (id) VALUES (1);

-- 기본 프로젝트 (미분류)
INSERT INTO projects (name, type) VALUES ('미분류', 'personal');

-- 기본 blocked 시간 (수면, 식사) — 매일 반복은 앱 로직에서 처리
```
