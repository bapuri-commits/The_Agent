# 05 — API Specification

## 개요

FastAPI 기반 REST API. Telegram Bot이 주 클라이언트이지만, 향후 웹 UI/다른 채널도 같은 API 사용.

Base URL: `http://localhost:8000/api/v1`

---

## Endpoints

### POST /inbox

1줄 텍스트를 task로 구조화하여 저장.

**Request:**
```json
{
  "text": "내일 OS과제 제출 2시간 중요"
}
```

**처리 흐름:**
1. LLM(gpt-4o-mini)이 텍스트 파싱 → TaskCreate 스키마
2. 부족한 필드는 기본값 자동 채움
3. DB 저장
4. priority_score 즉시 계산

**Response (201):**
```json
{
  "task": {
    "id": 42,
    "title": "OS과제 제출",
    "deadline_at": "2026-02-17T23:59:00+09:00",
    "est_minutes": 120,
    "energy": 4,
    "importance": 5,
    "status": "pending",
    "next_action": "OS 과제 파일 열어서 현재 진행 상태 확인",
    "project_id": null,
    "postpone_count": 0,
    "priority_score": 0.7823
  },
  "parsed_from": "내일 OS과제 제출 2시간 중요",
  "auto_filled": ["energy"]
}
```

**에러 (422):**
```json
{
  "detail": "텍스트에서 task를 파싱할 수 없습니다",
  "follow_up_question": "마감일이 언제인가요?"
}
```

---

### GET /tasks

task 목록 조회. priority_score 내림차순 기본 정렬.

**Query Parameters:**
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| status | string | "pending" | pending/in_progress/done/cancelled/all |
| project_id | int | null | 특정 프로젝트만 |
| sort | string | "priority" | priority/deadline/created |
| limit | int | 20 | 최대 반환 수 |

**Response (200):**
```json
{
  "tasks": [
    {
      "id": 42,
      "title": "OS과제 제출",
      "deadline_at": "2026-02-17T23:59:00+09:00",
      "est_minutes": 120,
      "importance": 5,
      "status": "pending",
      "next_action": "OS 과제 파일 열어서 현재 진행 상태 확인",
      "priority_score": 0.7823,
      "postpone_count": 0
    }
  ],
  "total": 1
}
```

---

### POST /tasks/{id}/complete

task 완료 처리.

**Request:**
```json
{
  "actual_minutes": 90,
  "energy_actual": 3,
  "notes": "생각보다 빨리 끝남"
}
```
모든 필드 선택사항. 보내지 않아도 완료 처리됨.

**Response (200):**
```json
{
  "task_id": 42,
  "status": "done",
  "completed_at": "2026-02-16T15:30:00+09:00",
  "was_on_time": true
}
```

---

### POST /tasks/{id}/postpone

task 미루기. postpone_count 증가 + 우선순위 자동 재계산.

**Request:**
```json
{
  "reason": "컨디션 안 좋음"
}
```
reason은 선택사항. audit log에 기록됨.

**Response (200):**
```json
{
  "task_id": 42,
  "postpone_count": 2,
  "new_priority_score": 0.8547,
  "message": "우선순위가 올라갔습니다. 다음 plan에 반영됩니다."
}
```

---

### POST /plan/today

오늘의 실행 계획 생성. 결정론적 알고리즘으로 시간 블록 배치.

**Request (선택사항):**
```json
{
  "current_energy": 3,
  "available_from": "10:00",
  "available_until": "22:00"
}
```
보내지 않으면 user_profile 기본값 사용.

**Response (200):**
```json
{
  "date": "2026-02-16",
  "blocks": [
    {
      "start_at": "10:00",
      "end_at": "11:00",
      "task_id": 42,
      "task_title": "OS과제 제출",
      "next_action": "OS 과제 파일 열어서 현재 진행 상태 확인",
      "energy_level": 5
    },
    {
      "start_at": "11:00",
      "end_at": "11:10",
      "type": "break"
    },
    {
      "start_at": "11:10",
      "end_at": "11:40",
      "task_id": 15,
      "task_title": "이메일 답장",
      "next_action": "교수님 메일 확인 후 답장",
      "energy_level": 5
    }
  ],
  "total_focus_minutes": 90,
  "total_blocks": 2,
  "unscheduled_tasks": [
    {"id": 33, "title": "빨래", "reason": "시간 부족"}
  ]
}
```

---

### POST /enforce/check

미이행 블록 감지 + enforcement 액션 생성. APScheduler가 자동 호출하거나 수동 호출.

**Response (200):**
```json
{
  "actions": [
    {
      "type": "narrowing",
      "task_id": 42,
      "task_title": "OS과제 제출",
      "message": "'OS과제 제출' 블록이 지났어요. 지금 딱 이것만: OS 과제 파일 열어서 현재 진행 상태 확인",
      "next_action": "OS 과제 파일 열어서 현재 진행 상태 확인",
      "options": ["할게", "미룰게"]
    }
  ],
  "deadline_warnings": [
    {
      "task_id": 42,
      "task_title": "OS과제 제출",
      "hours_left": 18.5,
      "message": "🔴 'OS과제 제출' 마감 18시간 전!"
    }
  ]
}
```

---

### GET /health

시스템 상태 확인.

**Response (200):**
```json
{
  "status": "ok",
  "db": "connected",
  "scheduler": "running",
  "telegram_bot": "connected",
  "last_plan_generated": "2026-02-16T08:00:00+09:00",
  "pending_tasks": 12,
  "today_blocks": 5
}
```

---

## Telegram Bot 명령어 (채널 어댑터)

| 입력 | 동작 | API 매핑 |
|------|------|----------|
| 아무 텍스트 1줄 | inbox 파싱 → task 생성 | POST /inbox |
| `/tasks` | 오늘의 pending tasks 보기 | GET /tasks |
| `/plan` | Today Plan 생성/조회 | POST /plan/today |
| `/done {id}` | task 완료 | POST /tasks/{id}/complete |
| `/skip {id}` | task 미루기 | POST /tasks/{id}/postpone |
| `/status` | 시스템 상태 | GET /health |

**기본 동작:** 명령어 없이 텍스트만 보내면 자동으로 inbox 처리. 입력 마찰 최소화.
