# The Agent — 프로젝트 컨텍스트 핸드오프 문서

> **이 문서의 목적:**  
> 이 프로젝트의 전체 맥락을 한 번에 전달하기 위한 문서.  
> 새 환경(데스크탑 등)에서 작업을 이어갈 때, 이 파일과 `DECISIONS-needed.md`를 프롬프트에 넣으면 전체 상황 파악이 가능하다.

> **현재 상태:** 설계 문서 확정 단계. 아직 코드 구현은 시작하지 않았음.  
> **다음 단계:** `DECISIONS-needed.md`의 7가지 질문에 답한 후 MVP 구현 시작.

---

# Part 1: 프로젝트 개요

## 뭘 만드는가
**The Agent** — ADHD 친화적, 성능 최우선 개인 AI 비서 시스템.

## 누가 쓰는가
- 컴공 학생, ADHD가 심해서 일정/할 일 관리가 구조적으로 어려움
- 학교(수업, 과제, 시험) + 일상(개인 프로젝트, 생활) 모두 커버해야 함

## 핵심 요구
- 입력 5초 안에 끝나야 함 (1줄 텍스트)
- "조언"이 아니라 "실행"이 되어야 함
- 계획은 매일 흔들리면 안 됨 (결정론적)
- AI에 대한 의존이 아니라, 궁극적으로 습관 변화가 목표

---

# Part 2: 초기 요구사항 (사용자 원문)

아래는 사용자가 ChatGPT에게 처음 보낸 프롬프트 원문이다.

## 원래 요구
- 학교와 일상 모두를 아우르는 비서가 필요
- 해야 할 일/일정에 대한 **정보 수집 → 우선순위 설정 → 어떻게 처리할지 조언 → 실제 일처리(과제 제출, 계획 수립, 스케줄 정리 등)** 까지 이어지는 end-to-end 비서
- "그럴듯한 조언"이 아니라 **실질적인 도움 + 좋은 성능**이 최우선
- 계획을 "그냥 참고" 수준으로는 안 되고, **참고하지 않을 수 없을 만큼 실행이 강제되는 UX/흐름** 필요
- AI는 **나에 대한 이해도가 매우 높아야** 하고, 내 삶과 **매우 밀착**되어야 함
- **컨텍스트 유지가 생명**, 센스 있게(상황/패턴/습관) 행동해야 함
- 궁극적으로는 **습관이 변화**하고 삶이 개선되어야 함
- 처음에 OpenClaw(GitHub 19.5만 스타 오픈소스 AI 에이전트)를 사용하려 했음

## 성능 정의
성능 = 실행 성공률 + 일정 안정성 + 낮은 지연 + 결정론적 계획 + 컨텍스트 유지 + 실패 복구

## 핵심 원칙 (사용자가 정의)
1. LLM을 학습/파인튜닝하지 않고, **외부 메모리(SSOT) + 검색(RAG) + 컨텍스트 주입**으로 개인화
2. 계획/우선순위는 **결정론적(규칙 기반)**으로 고정, LLM은 보조(구조화/분해/설명)
3. 실행은 도구 호출로 수행하되, 권한은 최소화(allowlist), 샌드박스, 감사로그(audit)
4. 실패 모드(최소 플랜/긴급 플랜/회복 플랜) 내장 → 모델이 틀려도 시스템은 무너지지 않음

## MVP 4대 플로우 (반드시 작동해야 함)
- **A) Inbox Capture:** 1줄 입력 → 태스크로 구조화 → DB 저장
- **B) Deterministic Prioritization:** 규칙 기반 점수로 우선순위 산정 (재현 가능)
- **C) Today Plan:** 오늘 가능한 시간 창 안에 30~60분 블록으로 일정 생성
- **D) Enforcement:** 미이행 시 '다음 행동 1개'로 좁혀 재제시 + 자동 재분해/재계획

---

# Part 3: ChatGPT와의 논의 결과 요약

ChatGPT는 다음과 같은 아키텍처를 제안했다:

## ChatGPT 추천 1순위 스택
```
OpenClaw (Gateway) → FastAPI → LangGraph → Postgres → Redis → pgvector → Langfuse
```

## ChatGPT가 정의한 체크포인트
1. **SSOT** — 구조화 DB가 진짜 기억 (대화 로그 X)
2. **Deterministic Priority Engine** — 같은 입력 → 같은 출력
3. **Capture Friction ≈ 0** — 입력 5초 이내
4. **Execution Enforcement Layer** — Narrowing → Commitment → Escalation 3단계
5. **Tool Permission & Audit** — Allowlist + Sandbox + Audit log
6. **Failure Mode Design** — Minimal/Urgent/Recovery 모드

## ChatGPT 제안 우선순위 공식
```
priority_score =
  w_deadline * f(deadline_hours_left)
+ w_importance * importance
+ w_short * g(est_minutes)
+ w_energy * h(energy, current_energy)
+ w_postpone * postpone_count
```
f/g/h는 명시적으로 정의, LLM은 importance/energy 제안만, 최종 점수는 코드.

## ChatGPT 제안 DB 스키마 (최소)
- tasks, projects, calendar_blocks, user_profile, memories, audit_logs

## ChatGPT 제안 API
- POST /inbox, GET /tasks, POST /tasks/{id}/complete, POST /tasks/{id}/postpone
- POST /plan/today, POST /enforce/check, GET /health

## ChatGPT 제안 모델 전략
- Planner Model: 상급 모델
- Parser Model: 빠르고 구조화 가능한 모델
- RAG Model: 긴 문서 처리용

---

# Part 4: 시니어 아키텍트 리뷰 (Claude)

ChatGPT 논의를 검토한 결과, **방향성은 우수하나 구조적 문제 및 현실적 우려**가 있다.

## 1. OpenClaw 평가 — MVP에서 빼야 함

OpenClaw는 "채널/게이트웨이"가 아니라 **에이전트 런타임**이다.

| 문제 | 설명 |
|------|------|
| **이중 진실** | OpenClaw는 Markdown 메모리, 우리는 Postgres SSOT → 두 곳에 상태 갈림 → 불일치 보장 |
| **제어권 충돌** | OpenClaw의 agentic loop가 자기 판단으로 행동 vs 우리 결정론적 플래너 → 누가 보스? |
| **보안 모델 충돌** | OpenClaw는 exec으로 쉘 자유 실행 → allowlist/sandbox와 정면충돌 |
| **오버헤드** | Telegram 메시지를 API에 전달하는 게 목적인데 Node.js 에이전트 런타임 전체를 띄우는 건 과잉 |

**결론:** 채널 연동이 목적이면 `python-telegram-bot` 하나로 충분. OpenClaw 멀티플랫폼은 v2에서 자체 어댑터로 해결.

## 2. ChatGPT 스택은 MVP가 아니라 최종 아키텍처

- OpenClaw + LangGraph + FastAPI + Postgres + Redis + pgvector + Langfuse를 1-2주에 세팅만 1주일
- ADHD 환경에서 "세팅 지옥"은 프로젝트를 죽이는 가장 빠른 방법

## 3. 추천 MVP 스택 (Phase 1, 1-2주)

| 컴포넌트 | 선택 | 이유 |
|----------|------|------|
| 채널 | **Telegram Bot** (python-telegram-bot) | 설치 5분, 모바일 입력 최적 |
| API | **FastAPI** | 비동기, 자동 문서화 |
| DB | **SQLite + SQLAlchemy** | 로컬 파일 하나, Postgres 호환 스키마 |
| LLM | **OpenAI API (gpt-4o-mini)** | inbox 파싱 전용, 월 ~$1 |
| 스케줄러 | **APScheduler** | 리마인더/enforcement |
| 배포 | **VPS 1대** 또는 로컬 | Docker 단일 서비스 |

총 코드량: 500-800줄. 월 비용: $1~6.

## 4. 확장 스택 (Phase 2, 1-2개월 후)

| 추가/교체 | 시점 |
|-----------|------|
| Postgres | SQLAlchemy 덕분에 거의 무비용 전환 |
| pgvector | 강의자료/메일 RAG 필요 시 |
| Redis | 세션 상태, 리마인더 큐 |
| LangGraph | 멀티스텝 승인 워크플로우 |
| Langfuse | 관측/평가 |
| 멀티채널 어댑터 | Telegram + Discord + ... |

## 5. ChatGPT 논의에서 빠진 것들

- **배포/운영 스토리 없음** — 24/7 가동 필요 (enforcement), VPS 추천
- **LLM 비용 추정 없음** — MVP는 gpt-4o-mini inbox 파싱만, 월 $1. Planner에 상급 모델 쓰면 비용 폭발
- **실제 UX 플로우 불구체적** — 기본값 자동 채움 (est=60min, importance=3) + 사용자 1줄 오버라이드 추천
- **"결정론적" 범위 모호** — "입력"의 정의를 명확히 해야 함 (tasks + calendar_blocks + user_profile.current_state)
- **습관 변화 메커니즘 없음** — task_completions 테이블 추가 제안 (완료율, 지연, 에너지 정확도 추적)

## 6. 동의하는 부분 (그대로 가져감)

- SSOT 원칙 → 100% 동의
- 결정론적 우선순위 엔진 → 100% 동의
- LLM 역할 제한 → 100% 동의
- Enforcement 3단계 → 100% 동의
- Failure Mode Design → 100% 동의
- DB 스키마 → 거의 그대로 사용 가능

## 7. 수정/보완 사항

### 우선순위 함수 구체화
- `f(deadline_hours_left)`: 시그모이드 기반, 24h 부근에서 급격 상승
- 불변 규칙: 마감 24h 이내 → 무조건 최상단 (score override)

### Calendar Block 알고리즘 추가
- Greedy: free window 추출 → priority 순 정렬 → 에너지 매칭 → 시간 fitting

### 습관 추적 구조 추가
- task_completions 테이블: completed_at, was_on_time, actual_minutes, energy_actual
- 주간 리포트 → user_profile에 피드백

---

# Part 5: 현재 설계 문서 목록

`docs/` 디렉토리에 다음 7개 문서가 이미 작성되어 있음:

| 파일 | 내용 |
|------|------|
| `00-project-overview.md` | 비전, 핵심 원칙 6가지, 성능 정의, 타임라인 |
| `01-architecture.md` | 기술 스택(MVP/확장), 아키텍처 다이어그램, 모듈 구조, 데이터 흐름, 비용 추정 |
| `02-core-algorithms.md` | 우선순위 함수 f/g/h/p 수식+Python 코드, Today Plan Greedy 알고리즘, Enforcement 3단계 로직, 알림 쿨다운 |
| `03-db-schema.md` | 7개 테이블 SQL DDL (tasks, projects, calendar_blocks, planned_blocks, user_profile, audit_logs, task_completions), ERD, seed 데이터 |
| `04-security.md` | Tool allowlist 설계, audit log 구조, HITL 승인 흐름, prompt injection 방지, 토큰 예산, 접근 제어 |
| `05-api-spec.md` | 6개 REST 엔드포인트 상세 (request/response JSON 예시), Telegram Bot 명령어 매핑 |
| `06-mvp-roadmap.md` | 3 Sprint / 12일 계획, 각 Step별 Done 정의 + 테스트 시나리오, Phase 2/3 로드맵 |

---

# Part 6: 이 프로젝트에서 AI에게 기대하는 역할

이 프로젝트의 AI 어시스턴트(너)는 **시니어 엔지니어/아키텍트** 역할이다.

- 설계 결정에 대해 의견을 제시하고, 문제점을 지적해야 함
- 구현 시에는 바로 동작하는 코드를 작성
- ADHD 특성을 이해하고, "과도한 계획보다 빠른 실행"을 우선
- 불필요한 장황한 설명 대신 바로 구현 가능한 형태로 답변
- 코드 품질: 모듈화, 단위 테스트, 타입 안전성

---

# Part 7: 즉시 필요한 다음 액션

1. **`DECISIONS-needed.md` 파일의 7가지 질문에 답변** (사용자가 해야 함)
2. 답변 확정 후 → MVP Sprint 1 시작 (프로젝트 초기 세팅 + Inbox + Telegram Bot)
3. 목표: **개강 전까지 4대 플로우가 실제로 돌아가는 시스템 완성**
