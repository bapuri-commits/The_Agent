# 04 — Security Design

## 원칙

> 보안 사고 = 시스템 신뢰 붕괴 = 사용 중단.
> ADHD 비서는 **신뢰**가 생명이므로, 보안은 성능의 일부다.

---

## 1. Tool Executor 설계

### Allowlist 기반 실행

모든 도구/외부 호출은 명시적 allowlist에 등록된 것만 실행 가능.

```python
TOOL_ALLOWLIST = {
    # MVP: 최소 도구만
    "send_telegram_message": {
        "description": "Telegram으로 메시지 전송",
        "risk_level": "low",
        "requires_approval": False,
    },
    "create_task": {
        "description": "DB에 task 생성",
        "risk_level": "low",
        "requires_approval": False,
    },
    "update_task": {
        "description": "task 상태/내용 수정",
        "risk_level": "low",
        "requires_approval": False,
    },
    
    # Phase 2: 승인 필요 도구
    "google_calendar_create": {
        "description": "Google Calendar에 일정 생성",
        "risk_level": "medium",
        "requires_approval": True,  # 사용자 확인 후 실행
    },
    "send_email": {
        "description": "이메일 발송",
        "risk_level": "high",
        "requires_approval": True,
    },
    "file_write": {
        "description": "파일 생성/수정",
        "risk_level": "medium",
        "requires_approval": True,
        "allowed_paths": ["~/Documents/TheAgent/*"],  # 경로 제한
    },
}

# 명시적 차단
TOOL_DENYLIST = [
    "shell_exec",       # 임의 쉘 명령 실행 금지
    "file_delete",      # 파일 삭제 금지
    "browser_navigate", # 임의 웹 접근 금지 (MVP)
]
```

### 실행 흐름

```
LLM이 도구 호출 요청
    ↓
Tool Executor 수신
    ↓
1. allowlist 확인 → 없으면 거부 + audit log
    ↓
2. risk_level 확인
   - low: 즉시 실행
   - medium/high: requires_approval 확인
     → True: 사용자에게 Telegram 확인 요청
     → 사용자 승인 후 실행
    ↓
3. 실행 + 결과 반환
    ↓
4. audit log 기록 (성공/실패 모두)
```

---

## 2. Audit Log

### 기록 대상

모든 의미 있는 동작을 기록:

| event_type | 설명 | actor |
|------------|------|-------|
| `task_created` | task 생성 | user/llm |
| `task_completed` | task 완료 | user |
| `task_postponed` | task 미루기 | user |
| `plan_generated` | Today Plan 생성 | system |
| `enforcement_sent` | enforcement 알림 발송 | system |
| `tool_executed` | 외부 도구 실행 | system |
| `tool_denied` | 도구 실행 거부 (allowlist 위반) | system |
| `tool_approved` | 사용자가 도구 실행 승인 | user |
| `llm_called` | LLM API 호출 | system |
| `llm_error` | LLM 호출 실패 | system |

### 로그 구조

```python
class AuditEntry:
    actor: str          # "system" | "user" | "llm"
    event_type: str     # 위 표 참조
    target_type: str    # "task" | "plan" | "tool" | "calendar"
    target_id: int      # 대상 ID
    payload: dict       # 상세 데이터
    # 예: {"tool": "google_calendar_create", "input": {...}, "output": {...}, "latency_ms": 230}
```

---

## 3. 사용자 승인 흐름 (Human-in-the-Loop)

### 2단계 승인

```
[위험 도구 호출 요청]
    ↓
Telegram 메시지:
  "📋 Google Calendar에 일정을 추가하려고 합니다:
   - 제목: OS 과제 마무리
   - 시간: 2/20 14:00~16:00
   
   ✅ 승인  |  ❌ 거부"
    ↓
사용자 응답 대기 (타임아웃: 5분)
    ↓
승인 → 실행 + audit log
거부 → 취소 + audit log
타임아웃 → 취소 + audit log + 나중에 다시 제안
```

---

## 4. LLM 관련 보안

### Prompt Injection 방지

```python
# 사용자 입력은 항상 별도 필드로 전달
# 시스템 프롬프트에 사용자 입력을 직접 삽입하지 않음

llm_message = [
    {"role": "system", "content": SYSTEM_PROMPT},  # 고정
    {"role": "user", "content": user_input},         # 분리
]

# Structured output 강제 (JSON Schema)
response = await openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=llm_message,
    response_format=TaskCreateSchema,  # Pydantic 스키마 강제
)
```

### 토큰 예산 제한

```python
LLM_LIMITS = {
    "max_input_tokens": 2000,    # 입력 토큰 제한
    "max_output_tokens": 500,    # 출력 토큰 제한
    "max_calls_per_hour": 30,    # 시간당 호출 제한
    "max_calls_per_day": 200,    # 일일 호출 제한
}
```

---

## 5. 데이터 보호

### API 키 관리

```
# .env (절대 커밋 금지)
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
# Phase 2
GOOGLE_CALENDAR_CREDENTIALS=...
```

### 접근 제어

- MVP: 단일 사용자 (user_profile id=1)
- Telegram Bot은 특정 chat_id만 응답하도록 필터링

```python
ALLOWED_CHAT_IDS = [123456789]  # 본인 Telegram ID만

async def message_handler(update, context):
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        return  # 무시
```
