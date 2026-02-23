# The Agent — 프로젝트 컨텍스트 핸드오프 문서 (v2)

> **이 문서의 목적:**
> 이 프로젝트의 전체 맥락을 한 번에 전달하기 위한 문서.
> 새 환경에서 작업을 이어갈 때, 이 파일과 `DECISIONS-needed.md`를 프롬프트에 넣으면 전체 상황 파악이 가능하다.

> **현재 상태:** Phase 1 Sprint 1~2 진행 중. Backend + M1 Worker 동작. 컨텍스트 시스템 설계 확정.
> **다음 단계:** Phase 1 Step 2.5 (컨텍스트 파이프라인 구축) → Sprint 3 (Enforcement + Deploy)

---

# Part 1: 프로젝트 개요

## 뭘 만드는가
**The Agent** — ADHD 환경의 컴공 4학년을 위한 **깊이 통합된 개인 AI 비서**.

## 누가 쓰는가
- 동국대 첨단융합대학 컴퓨터·AI학부 4학년
- ADHD 심각: 과제 제출 누락, 공지 안 봄, 수강신청 까먹음, 일정 정리 불가
- 기기: 데스크탑 + 노트북 + (추후) 스마트폰
- 기존 도구: 옵시디언 (The Record 볼트)

## v1 → v2 변화
- **v1**: LLM으로 입력 파싱하는 스마트 할일 앱 + Telegram
- **v2**: 학교 시스템/옵시디언과 통합된 AI 비서 + Web UI

## 핵심 요구
- 정보를 자동으로 수집해서 알맞게 제시
- 구조화해서 보여주고
- 처리할 수 있도록 시간 관리/방향성 도움
- 마무리까지 추적 (제출 확인, 후속 일정)
- 성능 최우선 (LLM 비용 제한 없음)
- 직접 대신 하는 게 아니라 "최종 클릭 직전까지 안내"

---

# Part 2: 설계 경위

## 초기 논의 (ChatGPT)
- OpenClaw + LangGraph + Postgres + Redis + pgvector + Langfuse 추천
- 핵심 원칙 정의: SSOT, 결정론적 계획, LLM 역할 제한, Enforcement

## 1차 리뷰 (Claude 시니어 아키텍트)
- OpenClaw 제거 (아키텍처 충돌: 이중 SSOT, 제어권, 보안)
- 스택 경량화: SQLite + Telegram Bot 중심 MVP 제안
- 핵심 원칙은 100% 동의, 알고리즘 구체화

## v2 재설계 (2026-02-15, 현재 세션)
**변경 사항:**
1. **SQLite → Postgres**: "나중에 마이그레이션"보다 "처음부터 최종 DB"가 현실적
2. **Telegram → Web UI**: 자체 웹 UI (React) 메인, Telegram은 보조 알림
3. **비전 확장**: 스마트 할일 앱 → 깊이 통합된 AI 비서
4. **학교 시스템 연동**: e-Class, nDRIMS, 동국대 포탈, 학과 사이트
5. **옵시디언 연동**: The Record 볼트 R/W
6. **LLM 성능 최우선**: gpt-4o-mini(파싱) + Claude 3.5 Sonnet(추론)
7. **Phase 재설계**: 생활 관리 먼저 (방학), 학교 연동은 개강 후
8. **OpenClaw 확정 제외**: 아키텍처 충돌 + MCP는 Python SDK로 직접 사용 가능

**유지 사항:**
- SSOT 원칙
- 결정론적 우선순위 엔진 (같은 입력 → 같은 출력)
- LLM 역할 제한 (보조자, 의사결정자 아님)
- Enforcement 3단계 (Narrowing → Commitment → Escalation)
- Failure Mode Design
- 핵심 알고리즘 (02-core-algorithms.md)
- 보안 설계 (04-security.md)

---

# Part 3: 확정 스택

| 레이어 | 기술 |
|--------|------|
| Frontend | React (Vite) + Tailwind + shadcn/ui |
| Backend | FastAPI + WebSocket |
| DB | Postgres + SQLAlchemy (Docker) |
| LLM (Fast) | gpt-4o-mini |
| LLM (Smart) | Claude 3.5 Sonnet |
| Scheduler | APScheduler |
| Deploy | VPS + Docker Compose + Nginx/Caddy |
| 학교 연동 (Phase 3) | Playwright |
| 알림 보조 (Phase 3) | Telegram Bot |

---

# Part 4: 사용자 컨텍스트

| 항목 | 값 |
|------|-----|
| 학교 | 동국대학교 첨단융합대학 컴퓨터·AI학부 |
| 학년 | 4학년 (2026-1학기) |
| 개강일 | **2026-03-03** |
| ADHD | 심각 |
| 프로그래밍 | Python 위주, Java 학부 수준, Frontend 경험 전무 |
| 수면 | ~09:00 기상, ~00:00~01:00 취침 (방학) |
| 집중 | 오전~이른 오후 best, 깨지면 회복 어려움 |
| 기타 프로젝트 | LLM_MCP_Agent(학습용), GitMini(JavaFX), BotTycoon(Java), xrun(C++) |
| 옵시디언 | The Record 볼트 적극 사용 중 |

## 학교 시스템

| 시스템 | URL | 용도 |
|--------|-----|------|
| e-Class | eclass.dongguk.edu | 과제, 강의자료 |
| nDRIMS | ndrims.dongguk.edu | 학적부, 수강신청 |
| 동국대 포탈 | www.dongguk.edu | 학사 정보, 공지 |
| 첨단융합대학 | ai.dongguk.edu | 학과 공지, 행사 |

---

# Part 5: Phase 로드맵

| Phase | 기간 | 목표 |
|-------|------|------|
| **1: Core + Web UI** | 2/15 ~ 2/28 | 매일 쓸 수 있는 기본 시스템 (Backend + React UI + VPS 배포) |
| **2: Obsidian + Enforce** | 3/1 ~ 3/10 | 옵시디언 R/W, Enforcement, 생활 관리 안정화 |
| **3: 학교 연동** | 개강 후 2~3주 | e-Class/nDRIMS 스크래핑, 과제 자동 수집, 학사일정 등록 |
| **4: 심화** | 학기 중 지속 | 패턴 학습, 적응형 스케줄링, 프로젝트 B 흡수 |

---

# Part 6: AI 역할

이 프로젝트의 AI 어시스턴트(너)는 **시니어 엔지니어** 역할이다.

- 설계 결정에 의견 제시, 문제점 지적
- **Frontend 코드를 직접 작성** (사용자는 Frontend 경험 전무)
- Backend 코드도 작성하되, 핵심 로직은 사용자와 함께 구현
- ADHD 특성 이해: 과도한 계획보다 빠른 실행 우선
- 코드 품질: 모듈화, 단위 테스트, 타입 안전성

---

# Part 7: 현재 설계 문서

| 파일 | 상태 | 내용 |
|------|------|------|
| `00-project-overview.md` | **v2 완료** | 비전, 원칙 8가지, 5단계 플로우, 사용자 프로필, 학교 시스템 |
| `01-architecture.md` | **v2 완료** | 스택, 아키텍처 다이어그램, 모듈 구조, LLM 전략, Web UI 설계 |
| `02-core-algorithms.md` | v1 유지 | 우선순위 함수, Today Plan, Enforcement 로직 (내용 여전히 유효) |
| `03-db-schema.md` | v1.5 (Postgres 반영) | 테이블 DDL, ERD (추후 integration 테이블 추가 필요) |
| `04-security.md` | v1 유지 | Tool allowlist, audit, HITL (추후 학교 자격증명 보안 추가 필요) |
| `05-api-spec.md` | v1 (업데이트 필요) | REST 엔드포인트 (WebSocket, 프론트엔드 API 추가 필요) |
| `06-mvp-roadmap.md` | **v2.1 (2/18 갱신)** | Step 2.5 추가 (컨텍스트 파이프라인, Phase 2에서 이관), Phase 2 Step 2.0 축소 |
| `07-memory-architecture.md` | **v1.1 (2/18 갱신)** | § 7 추가: 컨텍스트 파이프라인 구현 명세 (배치 규칙, 코드 구조, 토큰 예산) |
| `HANDOFF-context.md` | **v2.1 (2/18 갱신)** | 이 문서. 현재 상태 + 컨텍스트 시스템 결정 반영 |
| `CONVERSATION-with-gpt.md` | 참고 자료 | GPT와의 메모리/개인화 논의 기록 |
| `RESEARCH-memory-personalization.md` | 핸드오프 | 메모리 연구 별도 논의용 핸드오프 문서 |
| `SECURITY-CHECKLIST.md` | **신규 (2/18)** | API 키 보안 규칙, git push 전 체크리스트, VPS 배포 보안, 유출 대응 |
| `DECISIONS-needed.md` | **업데이트 필요** | 남은 결정 사항 |

---

# Part 8: 현재 진행 상황 (2026-02-18)

## 완료된 것
- Phase 1 Sprint 1: 프로젝트 구조, Docker Compose, DB 모델, M1 Worker 파싱
- LLM Router (OpenAI/Anthropic 자동 선택)
- Inbox API + Confidence 기반 분기 (자동저장/제안/재질문)
- `inbox_logs` 학습 데이터 수집
- `USER_PROFILE.md` 수동 작성 (M1에서 사용 중)

## 진행 중
- Phase 1 Sprint 2: Web UI (React + Chat + Task Board)

## 다음 액션 (Phase 1 Step 2.5 — 컨텍스트 파이프라인)

> **이 작업은 원래 Phase 2에 있었으나, 메모리 아키텍처 리뷰(2026-02-18)에서
> Phase 1로 앞당김.** 모든 모델의 판단 품질을 결정하는 기반 인프라이므로.
> 상세 명세: `07-memory-architecture.md` § 7

1. `backend/app/services/context.py` 생성 — 컨텍스트 조립 독립 모듈
2. `inbox.py`의 하드코딩된 프롬프트 조립을 `context.py`로 이관
3. 프롬프트 배치 규칙 적용 (Zone A: 정체성/프로필, Zone B: 동적 상태, Zone C: 출력 규칙)
4. `AGENT_SOUL.md` 프롬프트 통합
5. `get_working_state()` 구현 (Layer 3: 현재 task 상태 DB 쿼리)
6. `inbox_logs`에 `context_tokens` 필드 추가

## 목표
- **2/28까지 브라우저에서 접속 가능한 기본 시스템**
- 컨텍스트 파이프라인이 동작하여 M1이 현재 상황을 반영한 파싱을 수행
