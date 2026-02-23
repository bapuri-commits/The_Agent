# Phase 1 Sprint 2 프롬프트

> 이 문서를 새 대화창에 넣고 작업을 시작한다.
> 반드시 `docs/WORKFLOW.md`의 프로세스를 따를 것.

---

## 프로젝트 컨텍스트

- **프로젝트:** The Agent — ADHD 환경 개인 AI 비서
- **레포 경로:** `G:\CS_Study\The_Agent`
- **현재 상태:** Phase 1 Sprint 1 완료, Sprint 2 시작

---

## 이전 Sprint 완료 사항

### Sprint 1 (Backend Foundation) — ✅ 완료

| Step | 내용 | 상태 |
|------|------|------|
| 1.1 | 프로젝트 초기 세팅 (Docker Compose + Postgres + FastAPI) | ✅ 감사 완료 |
| 1.2 | Inbox + LLM 파싱 (M1 Worker gpt-4o-mini) | ✅ 감사 완료, BUG 5건 수정 |
| 1.3 | Priority Engine (결정론적 우선순위 계산) | ✅ 감사 완료, BUG 1건 수정 |

### 현재 동작하는 것

```
docker compose up → Postgres + FastAPI 기동
POST /api/v1/inbox → 자연어 → task 생성 (LLM fallback 동작 중, 크레딧 미충전)
GET /api/v1/tasks → priority_score 내림차순 정렬
POST /api/v1/tasks/{id}/complete → 완료
POST /api/v1/tasks/{id}/postpone → 미루기 + count 증가
POST /api/v1/inbox/{id}/confirm → 재질문 후 확정
GET /health → 상태 확인
Swagger UI: http://localhost:8000/docs
```

### LLM 크레딧 미충전 이슈

- OpenAI + Anthropic API 키 등록 완료
- 크레딧 미충전 → M1 Worker가 fallback 모드로 동작 중
- `docs/PENDING-TESTS.md`에 충전 후 실행할 테스트 목록 있음
- **Sprint 2 진행과 무관** (백엔드 API는 정상 동작)

---

## 이번 Sprint 목표

### Sprint 2: Web UI + Planner

> 브라우저에서 접속하여 채팅으로 task 생성, task 목록 확인, 오늘 플랜 확인이 가능한 Web UI.
> 사용자는 **Frontend 경험이 전무**하므로 AI가 직접 코드 작성.

### Step 목록

| Step | 내용 | 설계 문서 참조 |
|------|------|--------------|
| **2.1** | React 프론트엔드 세팅 (Vite + React + TS + Tailwind + shadcn/ui) | `01-architecture.md` Web UI 설계 |
| **2.2** | Chat UI (대화형 인터페이스 + POST /inbox 연동) | `01-architecture.md` |
| **2.3** | Task Board (우선순위 순 목록 + 완료/미루기) | `01-architecture.md` |
| **2.4** | Today Planner + Calendar View | `02-core-algorithms.md` § 2 |

### 각 Step의 Done 정의 (로드맵 06 참조)

- **2.1:** `docker compose up` → Frontend 컨테이너 기동, 브라우저에서 기본 레이아웃 표시
- **2.2:** 채팅창에 텍스트 입력 → task 생성 카드 표시, WebSocket 실시간 반영
- **2.3:** task 목록이 priority_score 순, 완료/미루기 버튼 동작
- **2.4:** Today Plan 시간 블록 시각화, 고정 일정과 미겹침

---

## 기술 스택 (Frontend)

| 항목 | 선택 | 비고 |
|------|------|------|
| 프레임워크 | React (Vite) + TypeScript | |
| 스타일 | Tailwind CSS | |
| 컴포넌트 | shadcn/ui | 모던 UI 컴포넌트 라이브러리 |
| 실시간 | WebSocket | 알림, 채팅 메시지 |
| API 통신 | fetch 또는 axios | |
| Docker | Nginx 기반 빌드 서빙 또는 Vite dev server | |

### Web UI 레이아웃 (01-architecture.md에서)

```
┌──────────┬─────────────────────────────────────┐
│          │                                     │
│  사이드바  │          메인 영역                   │
│          │                                     │
│ 💬 Chat  │  [Chat UI / Task Board / Calendar]  │
│ ✅ Tasks │                                     │
│ 📅 Plan  │  선택한 탭에 따라 전환                 │
│ ⚙️ 설정  │                                     │
│          │                                     │
└──────────┴─────────────────────────────────────┘
```

---

## 4-Model Architecture (참고)

| 모델 | 역할 | 현재 상태 |
|------|------|----------|
| [M1] Worker (gpt-4o-mini) | 입력 파싱/구조화 | ✅ 구현 완료 (크레딧 미충전으로 fallback) |
| [M2] Stabilizer (Claude 3.5 Sonnet) | 정리/분해/노트 | 🔲 미구현 |
| [M3] Judge (Claude Opus 4.6) | 판단/개입 | 🔲 미구현 |
| [M4] Distiller (Claude 3.5 Sonnet) | 기억 정제 | 🔲 미구현 |

Sprint 2에서는 M2~M4를 구현하지 않음. **Web UI가 M1의 API 결과를 표시하는 것이 목표.**

---

## 코드 구조 (현재)

```
The_Agent/
├── backend/
│   ├── app/
│   │   ├── main.py              ✅ FastAPI + CORS + 라우터
│   │   ├── config.py            ✅ 설정 (4-Model 모델명 포함)
│   │   ├── db.py                ✅ SQLAlchemy async
│   │   ├── models.py            ✅ 8개 테이블 ORM
│   │   ├── schemas.py           ✅ Pydantic 스키마
│   │   ├── api/
│   │   │   ├── inbox.py         ✅ POST /inbox, /inbox/{id}/confirm
│   │   │   └── tasks.py         ✅ GET /tasks, complete, postpone
│   │   ├── services/
│   │   │   ├── llm.py           ✅ 4-Model LLM Router
│   │   │   ├── inbox.py         ✅ M1 Worker 파싱 서비스
│   │   │   └── prioritizer.py   ✅ 결정론적 우선순위
│   │   ├── context/
│   │   │   ├── AGENT_SOUL.md    ✅ AI 비서 정체성
│   │   │   ├── USER_PROFILE.md  ✅ 사용자 이해
│   │   │   └── MEMORY.md        ✅ 진행 중 맥락
│   │   └── integrations/        🔲 (Phase 2~3)
│   ├── Dockerfile               ✅
│   └── requirements.txt         ✅
├── frontend/                    🔲 ← Sprint 2에서 생성
├── docker-compose.yml           ✅ (frontend 서비스 주석 처리됨, 활성화 필요)
├── .env                         ✅ (API 키 등록됨, 크레딧 미충전)
└── docs/                        ✅ (전체 설계 문서)
```

---

## docker-compose.yml 참고

현재 frontend 서비스가 주석 처리되어 있음. Sprint 2에서 활성화 필요:

```yaml
# frontend:
#   build:
#     context: ./frontend
#     dockerfile: Dockerfile
#   restart: unless-stopped
#   ports:
#     - "5173:5173"
#   depends_on:
#     - backend
```

---

## Backend API (Frontend가 호출할 엔드포인트)

| 메서드 | 경로 | 용도 | 응답 주요 필드 |
|--------|------|------|--------------|
| POST | /api/v1/inbox | 자연어 → task 생성 | action, task, clarification, inbox_log_id |
| POST | /api/v1/inbox/{id}/confirm | 재질문 후 확정 | action, task |
| GET | /api/v1/tasks | task 목록 (priority 정렬) | tasks[], total |
| POST | /api/v1/tasks/{id}/complete | 완료 | task_id, status |
| POST | /api/v1/tasks/{id}/postpone | 미루기 | task_id, postpone_count |
| GET | /health | 시스템 상태 | status |

### inbox 응답 action 종류

| action | 의미 | Frontend 동작 |
|--------|------|--------------|
| `saved_auto` | 높은 확신으로 자동 저장됨 | task 카드 표시 + "수정할 부분 있나요?" |
| `saved_fallback` | LLM 실패, 기본값 저장 | task 카드 표시 + 경고 메시지 |
| `needs_confirmation` | 중간 확신, 확인 요청 | 파싱 프리뷰 + "맞나요?" 버튼 |
| `needs_clarification` | 재질문 필요 | 질문 표시 + 답변 입력 UI |

---

## 설계 문서 위치

| 문서 | 용도 |
|------|------|
| `docs/00-project-overview.md` | 전체 비전, 원칙, 사용자 프로필 |
| `docs/01-architecture.md` | 아키텍처, 스택, Web UI 설계, 4-Model |
| `docs/02-core-algorithms.md` | Priority Engine, Today Plan, Enforcement |
| `docs/06-mvp-roadmap.md` | Sprint 2 Step별 상세 |
| `docs/07-memory-architecture.md` | 메모리 4계층, 컨텍스트 파이프라인 (Step 2.5) |
| `docs/WORKFLOW.md` | 개발 프로세스 (반드시 따를 것) |
| `docs/PENDING-TESTS.md` | LLM 크레딧 충전 후 실행할 테스트 |

---

## 워크플로우 (필수)

`docs/WORKFLOW.md` 참조. 핵심:

1. **각 Step 시작 시 설계 논의** → 사용자가 "진행해" 할 때까지 구현 시작 금지
2. **구현 후 무조건 멈춤** → 자동 진행 금지
3. **강도 높은 감사** → 버그 발견 시 즉시 수정
4. **자동 테스트 + 수동 테스트 리스트** 반환
5. **사용자 피드백** → 없으면 다음 Step

---

## 시작 지시

Step 2.1 (React 프론트엔드 세팅)의 **설계 논의**부터 시작하세요.
Frontend 경험이 전무한 사용자를 위해, 기술 선택 이유를 설명하고 레이아웃을 확정하세요.

> **참고:** Today Planner (Step 2.4)는 `services/planner.py`가 아직 없으므로,
> Sprint 2에서 planner.py 구현도 포함해야 합니다.
> 알고리즘은 `02-core-algorithms.md` § 2에 의사코드가 있습니다.
