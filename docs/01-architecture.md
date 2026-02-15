# 01 — Architecture

## 기술 스택

### MVP (Phase 1) — 개강 전 목표

| 레이어 | 기술 | 선택 이유 |
|--------|------|-----------|
| 채널 (입력) | **Telegram Bot** (python-telegram-bot) | 설치 5분, 모바일 입력 최적, 푸시 알림 내장 |
| API 서버 | **FastAPI** | 비동기, 자동 문서화, Python 생태계 |
| DB (SSOT) | **SQLite + SQLAlchemy** | 로컬 파일 하나로 동작, 스키마는 Postgres 호환 설계 |
| LLM | **OpenAI API (gpt-4o-mini)** | inbox 파싱 전용, 1건당 ~$0.001, 구조화 출력 강제 가능 |
| 스케줄러 | **APScheduler** | 리마인더, enforcement 체크, 일정 주기 작업 |
| 배포 | **VPS 1대** (또는 로컬) | Docker Compose로 단일 서비스 |

### Phase 2 이후 — 확장 시

| 레이어 | 기술 | 전환 시점 |
|--------|------|-----------|
| DB | **Postgres** | SQLAlchemy 덕분에 거의 무비용 마이그레이션 |
| 벡터 검색 | **pgvector** | 강의자료/메일/노트 RAG 검색 필요 시 |
| 캐시/큐 | **Redis** | 세션 상태, 리마인더 큐, 쿨다운 관리 |
| 오케스트레이션 | **LangGraph** | 멀티스텝 승인 워크플로우 필요 시 |
| 관측 | **Langfuse** | 플랜 추적, 실패 분석, 평가 루프 |
| 멀티채널 | **채널 어댑터 레이어** | Telegram + Discord + ... |

---

## MVP 아키텍처 다이어그램

```
┌──────────────────────────────────────────────────────────────┐
│                        User (Mobile)                         │
│                     Telegram 1줄 입력                        │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│   Telegram Bot Gateway   │  python-telegram-bot
│   (Channel Adapter)      │  - 메시지 수신/발신
│                          │  - 푸시 알림
└──────────┬───────────────┘
           │ HTTP
           ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                           │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Inbox       │  │ Prioritizer  │  │ Today Planner       │ │
│  │ Service     │  │ Service      │  │ Service             │ │
│  │             │  │              │  │                     │ │
│  │ LLM 호출    │  │ 순수 함수    │  │ 순수 함수            │ │
│  │ (파싱 전용)  │  │ (결정론적)   │  │ (결정론적)           │ │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬──────────┘ │
│         │               │                      │            │
│  ┌──────┴───────────────┴──────────────────────┴──────────┐ │
│  │                    Enforcement Service                  │ │
│  │  - 미이행 감지                                          │ │
│  │  - next_action 축소                                     │ │
│  │  - 자동 재분해/재계획                                    │ │
│  └────────────────────────┬───────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────┴───────────────────────────────┐ │
│  │              Tool Executor (Allowlisted)                │ │
│  │  - Google Calendar 연동 (Phase 2)                      │ │
│  │  - 파일/문서 생성 (Phase 2)                             │ │
│  │  - Audit Log 기록                                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  SQLite (SSOT)  │
              │                 │
              │  tasks          │
              │  projects       │
              │  calendar_blocks│
              │  user_profile   │
              │  audit_logs     │
              └─────────────────┘
                       │
              ┌────────┴────────┐
              │  APScheduler    │
              │                 │
              │  - 리마인더     │
              │  - enforce 체크 │
              │  - 아침 플랜    │
              └─────────────────┘
```

---

## 모듈 구조

```
The_Agent/
├── docs/                          # 설계 문서
├── tests/                         # 테스트
│   ├── test_prioritizer.py
│   ├── test_planner.py
│   └── test_enforcement.py
├── app/
│   ├── main.py                    # FastAPI 앱 + 라이프사이클
│   ├── config.py                  # 설정 (환경변수, 상수)
│   ├── db.py                      # SQLAlchemy 엔진/세션
│   ├── models.py                  # ORM 모델
│   ├── schemas.py                 # Pydantic 스키마 (입출력)
│   ├── bot.py                     # Telegram Bot 설정 + 핸들러
│   │
│   ├── services/
│   │   ├── inbox.py               # 인박스 파싱 (LLM 호출 지점)
│   │   ├── prioritizer.py         # 우선순위 점수 (순수 함수)
│   │   ├── planner.py             # Today Plan 생성 (순수 함수)
│   │   ├── enforcement.py         # 미이행 감지 + 재계획
│   │   ├── llm.py                 # LLM 클라이언트 래퍼
│   │   ├── memory.py              # 장기 기억 (Phase 2: vector search)
│   │   ├── tools_executor.py      # 도구 실행기 (allowlist + audit)
│   │   └── audit.py               # 감사 로그
│   │
│   └── api/
│       ├── inbox.py               # POST /inbox
│       ├── tasks.py               # GET/POST /tasks
│       ├── plan.py                # POST /plan/today
│       └── enforce.py             # POST /enforce/check
│
├── alembic/                       # DB 마이그레이션 (Phase 2, Postgres 전환 시)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 데이터 흐름 (4대 플로우)

### A. Inbox Capture
```
사용자 "내일 OS과제 제출" 
  → Telegram Bot 수신 
  → POST /inbox {text: "내일 OS과제 제출"} 
  → LLM parse (gpt-4o-mini) → TaskCreate 스키마 
  → 부족 필드 기본값 채움 (est=60min, importance=3) 
  → DB 저장 
  → 사용자에게 확인 메시지 (수정 가능)
```

### B. Deterministic Prioritization
```
GET /tasks?status=pending 
  → 전체 미완료 task 로드 
  → priority_score 계산 (순수 함수, 같은 입력 = 같은 결과) 
  → 정렬 후 반환
```

### C. Today Plan
```
POST /plan/today 
  → 오늘 calendar_blocks에서 free window 추출 
  → pending tasks를 priority_score 순 정렬 
  → 에너지 매칭 + 시간 fitting → 30~60분 블록 배치 
  → 결과 반환 (+ 선택적 캘린더 등록)
```

### D. Enforcement
```
APScheduler 30분 간격 실행 (또는 수동 POST /enforce/check)
  → 현재 시간 기준 지나간 블록 확인 
  → 완료 안 된 task 감지 
  → next_action 1개로 축소 
  → 사용자에게 Telegram 알림 
  → postpone_count 증가 → 재계획 트리거
```

---

## LLM 사용 지점 (최소화)

| 호출 지점 | 모델 | 목적 | 호출 빈도 |
|-----------|------|------|-----------|
| `inbox.parse()` | gpt-4o-mini | 1줄 텍스트 → TaskCreate 구조화 | 사용자 입력 시 |
| `inbox.decompose()` | gpt-4o-mini | 큰 task → next_action 1~3개 분해 | task 생성/재분해 시 |

**LLM이 하지 않는 것:**
- 우선순위 결정 (코드)
- 일정 배치 (코드)
- 리마인더 타이밍 (코드)
- 규칙 적용 (코드)

---

## 비용 추정 (MVP)

| 항목 | 추정 | 비용 |
|------|------|------|
| gpt-4o-mini (하루 20건 파싱) | ~2K tokens/건 × 20건 | 월 ~$1 |
| VPS (최소 사양) | 1 vCPU, 1GB RAM | 월 $0~5 (Oracle Free Tier 가능) |
| Telegram Bot API | 무료 | $0 |
| **합계** | | **월 $1~6** |
