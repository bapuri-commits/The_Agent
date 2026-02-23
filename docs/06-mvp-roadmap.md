# 06 — MVP Roadmap (v2)

> **v2 재설계: 2026-02-15**
> Pain-point 우선 순서. 생활 관리 먼저, 학교 연동은 개강 후.
> 동국대 2026-1학기 개강: **3월 3일** (실제 일정 확인 완료)

## 목표

**개강 전까지 "매일 쓸 수 있는 생활 관리 시스템" 완성.**
학교 연동은 개강 후 학교 시스템 접근 가능할 때 추가.

---

## Phase 1: Core + Web UI (2/15 ~ 2/28, 2주)

> "브라우저 열면 바로 쓸 수 있는 기본 시스템"

### Sprint 1 (Day 1~4) — Backend Foundation

#### Step 1.1: 프로젝트 초기 세팅 (Day 1)

**작업:**
- 프로젝트 구조 생성 (backend/, frontend/, docs/)
- Docker Compose (Postgres + FastAPI)
- requirements.txt (fastapi, uvicorn, sqlalchemy, asyncpg, openai, anthropic, apscheduler, pydantic)
- SQLAlchemy 모델 정의 (models.py) — Postgres 기준
- DB 초기화 + seed 데이터
- config.py (.env 로딩)

**Done 정의:**
- `docker compose up` → Postgres + FastAPI 컨테이너 기동
- 모든 테이블 생성됨
- user_profile(id=1) + "미분류" 프로젝트 존재
- `/health` 엔드포인트 응답

#### Step 1.2: Inbox + LLM 파싱 (Day 2~3)

**작업:**
- LLM Router 구현 (Fast Lane: gpt-4o-mini, Smart Lane: Claude 3.5 Sonnet)
- inbox.py: parse_inbox() — 자연어 → TaskCreate
- schemas.py: TaskCreate, TaskResponse
- POST /inbox 엔드포인트
- 기본값 자동 채움 (est=60min, importance=3, energy=3)
- LLM 장애 시 fallback (원문 그대로 저장)

**Done 정의:**
- `POST /inbox {"text": "내일 OS과제 제출 2시간 중요"}` → task DB 저장
- 기본값 자동 채움 동작
- audit_logs에 기록
- LLM 죽어도 task 생성 가능

#### Step 1.3: Priority Engine (Day 3~4)

**작업:**
- prioritizer.py: f(), g(), h(), p(), calculate_priority()
- 불변 규칙 (24h 이내 최상단)
- GET /tasks에 priority_score 정렬

**Done 정의:**
- 순수 함수: 같은 입력 → 같은 출력
- 단위 테스트 전체 통과

---

### Sprint 2 (Day 5~8) — Web UI + Planner

#### Step 2.1: React 프론트엔드 세팅 (Day 5)

**작업:**
- Vite + React + TypeScript + Tailwind + shadcn/ui 초기화
- 기본 레이아웃 (사이드바 + 메인 영역)
- API 클라이언트 설정 (fetch/axios)
- Docker 멀티스테이지 빌드 설정

**Done 정의:**
- `docker compose up` → Frontend도 함께 기동
- 브라우저에서 기본 레이아웃 표시됨

#### Step 2.2: Chat UI (Day 5~6)

**작업:**
- ChatPage.tsx: 대화형 인터페이스
- 메시지 입력 → POST /inbox → 응답 표시
- task 생성 결과 카드 형태로 표시
- WebSocket 연결 (실시간 업데이트)

**Done 정의:**
- 채팅창에 "내일 OS과제 제출" 입력 → task 생성 카드 표시
- 실시간 반영 (새로고침 없이)

#### Step 2.3: Task Board (Day 6~7)

**작업:**
- TasksPage.tsx: 우선순위 순 task 목록
- 상태 필터 (pending/in_progress/done)
- 빠른 완료/미루기 버튼
- 마감 임박 하이라이트

**Done 정의:**
- task 목록이 우선순위 순으로 표시
- 완료/미루기 동작

#### Step 2.4: Today Planner + Calendar View (Day 7~8)

**작업:**
- planner.py: extract_free_windows(), generate_today_plan()
- CalendarPage.tsx: 시간 블록 시각화
- POST /plan/today → 블록 생성 → UI 표시
- planned_blocks DB 저장

**Done 정의:**
- "오늘 플랜" 요청 시 시간 블록 리스트 생성
- 캘린더 뷰에 블록 표시
- 고정 일정과 겹치지 않음

---

### Sprint 3 (Day 9~12) — Enforcement + Deploy

#### Step 2.5: 컨텍스트 파이프라인 기반 구축 (Day 9~10)

> **Phase 2 Step 2.0에서 앞당김 (2026-02-18 결정)**
> 이유: M1이 이미 USER_PROFILE.md를 사용 중이고, M2/M3 추가 시 프롬프트 조립이
> 중복되는 구조적 문제가 있음. 컨텍스트 시스템은 모든 모델의 판단 품질을 결정하는
> 기반 인프라이므로 Phase 1에서 잡아야 함.
> 상세 명세: `07-memory-architecture.md` § 7 참조.

**작업:**
- `backend/app/services/context.py` 모듈 생성
  - `build_context(role, db)`: 모델별 컨텍스트 조립 함수
  - `get_working_state(db)`: Layer 3 Working Memory (DB 쿼리 → 현재 상태 텍스트)
- `inbox.py`의 하드코딩된 프롬프트 조립을 `context.py` 호출로 교체
- 프롬프트 배치 규칙 적용 (Zone A/B/C 구조, `07-memory-architecture.md` § 7.2)
- `AGENT_SOUL.md`를 프롬프트에 통합
- `USER_PROFILE.md` 포맷 검토 + LLM 소화 가능한 구조로 정리
- `inbox_logs`에 `context_tokens` 필드 추가 (토큰 사용량 추적)

**Done 정의:**
- `build_context(ModelRole.WORKER, db)` 호출로 M1 system prompt 조립됨
- `inbox.py`에 프롬프트 조립 코드가 없음 (context.py로 완전 이관)
- Working Memory가 동작: pending task 수, 오늘 완료 수 등이 프롬프트에 포함됨
- `AGENT_SOUL.md` 내용이 프롬프트 상단에 포함됨
- 매 요청마다 `inbox_logs.context_tokens`에 토큰 수 기록됨

---

#### Step 3.1: Enforcement Engine (Day 11~12)

**작업:**
- enforcement.py: check_enforcement(), auto_decompose()
- APScheduler 30분 간격 체크 등록
- WebSocket으로 알림 발송 (채팅 UI에 표시)
- "할게" / "미룰게" 인라인 버튼
- 알림 쿨다운 (과도 알림 방지)

**Done 정의:**
- 미이행 블록 → 채팅 UI에 알림 표시
- "미룰게" → postpone_count 증가 + 우선순위 상승
- 같은 task 1시간 내 중복 알림 없음

#### Step 3.2: VPS 배포 (Day 12~13)

**작업:**
- VPS 서버 세팅 (Docker, Docker Compose)
- docker-compose.yml: Postgres + Backend + Frontend
- Nginx 리버스 프록시 (또는 Caddy)
- HTTPS 설정 (Let's Encrypt)
- .env 설정

**Done 정의:**
- 외부 브라우저에서 접속 가능
- 데스크탑/노트북 모두 같은 URL로 접속
- 24/7 가동 확인

#### Step 3.3: 안정화 (Day 13~14)

**작업:**
- 에러 핸들링 강화
- 실사용 테스트 (본인이 직접 하루 종일 사용)
- 버그 수정 + 엣지 케이스
- UI 다듬기

**Done 정의:**
- 하루 종일 사용해도 크래시 없음
- 아침 플랜 → 낮 enforcement → 저녁 완료 사이클 동작

---

## Phase 2: Obsidian + 생활 안정화 (3/1 ~ 3/10, 10일)

> "옵시디언과 연동하여 기존 생활 기록 시스템과 통합"

### Step 2.0: 컨텍스트 파일 고도화 + MEMORY.md 연동

> **기존 Step 2.0의 기반 구축(context.py, 배치 규칙, AGENT_SOUL/USER_PROFILE 통합)은
> Phase 1 Step 2.5로 이관됨.** 여기서는 그 위에 쌓는 작업만 수행.

**작업:**
- `context/MEMORY.md` 자동 갱신 구조 구현 (현재는 수동)
- M2 Stabilizer 컨텍스트 구성 + 첫 호출 연동
- 컨텍스트 품질 A/B 테스트: 동일 입력에 대해 컨텍스트 유무로 파싱 품질 비교
- Phase 1에서 축적된 `inbox_logs.context_tokens` 데이터로 토큰 예산 검증

**Done 정의:**
- MEMORY.md가 주기적으로 자동 갱신됨
- M2 호출 시 `build_context(ModelRole.STABILIZER, db)`로 적절한 컨텍스트 주입됨
- 컨텍스트 유무에 따른 파싱 품질 차이가 정량적으로 확인됨

### Step 2.1: Obsidian 읽기 연동

**작업:**
- obsidian.py: 볼트 파일 읽기 (The Record 구조 이해)
- Context Engine에 옵시디언 데이터 피드 (온톨로지 역할)
  - 데일리 노트 → 일상 기록 참조
  - 프로젝트 _index.md → 프로젝트 현황
  - 3_Areas/ → 지식/학습 체계
- 채팅에서 "오늘 뭐 했었지?" → 데일리 노트 참조해서 답변

**Done 정의:**
- The Record 볼트의 데일리 노트, 프로젝트 _index.md 읽기 가능
- 채팅에서 옵시디언 내용 참조한 답변 가능
- 온톨로지 컨텍스트가 Enforcement/Planner에도 반영 가능

### Step 2.2: Obsidian 쓰기 연동

**작업:**
- 데일리 노트에 개발 로그/공부 기록 자동 추가
- 프로젝트 _index.md 업데이트
- The Record 워크플로우 규칙 일부 반영

**Done 정의:**
- 채팅에서 "오늘 한 거 기록해줘" → 데일리 노트에 반영
- 파일 충돌 없이 안전한 쓰기

### Step 2.3: 패턴 기본 설정 + Telegram 알림

**작업:**
- user_profile 상세 설정 UI
- 수면/에너지/집중 시간대 초기값 입력
- Telegram Bot 보조 알림 설정 (선택)

---

## Phase 3: 학교 연동 (개강 후, 3/10 ~ 3/31)

> "학교 시스템에서 자동으로 정보 수집, 과제 놓치는 문제 해결"

### Step 3.1: 학교 사이트 스크래핑 기반

**작업:**
- Playwright 기반 브라우저 자동화
- e-Class 로그인 + 과제 목록 수집
- nDRIMS 학사 일정 수집
- 동국대 포탈 / 학과 공지사항 수집

**기술 접근:**
```
1. Playwright headless 브라우저로 로그인
2. 과제/공지 페이지 파싱
3. LLM으로 내용 구조화 → task/event 생성
4. APScheduler로 주기적 수집 (하루 2~3회)
```

**보안:**
- 학교 로그인 정보는 .env에 저장 (커밋 금지)
- 로컬 VPS에서만 접근

### Step 3.2: 학사 일정 자동 등록

**작업:**
- 2026-1학기 주요 일정 calendar_blocks에 자동 등록
  - 개강 (3/3), 중간시험 (4/21~27), 기말시험 (6/9~15), 종강 (6/15)
  - 수강신청 정정, 학점포기 신청 등 기한 관리
- 수업 시간표 → 매주 반복 calendar_blocks

### Step 3.3: 과제/제출 리마인더

**작업:**
- e-Class에서 수집한 과제 → task 자동 생성
- 마감 D-3, D-1, D-day 리마인더
- 제출 시: LMS 제출 페이지 링크 + 제출할 파일 안내 + 제출 확인 리마인더

---

## Phase 4: 심화 (학기 중, 지속적)

| 기능 | 설명 | 우선순위 |
|------|------|---------|
| 패턴 학습 고도화 | 에너지/집중 시간대 자동 보정 | 높음 |
| 적응형 가중치 | 완료 패턴 → 우선순위 가중치 자동 조정 | 높음 |
| 주간 리포트 | 완료율, 지연, 에너지 정확도 대시보드 | 중간 |
| 프로젝트 B 흡수 | LLM_MCP_Agent의 MCP/Tool 학습 내용 통합 | 중간 |
| 고급 옵시디언 연동 | 3_Areas 자동 정리, 학습 노트 생성 | 낮음 |
| pgvector RAG | 과거 노트/강의자료 검색 | 낮음 |
| 스마트폰 최적화 | 반응형 UI + PWA | 중간 |

---

## Phase 1 완료 기준 (2/28)

다음 시나리오가 end-to-end로 동작:

```
아침 09:00  브라우저 접속
        09:01  채팅: "내일까지 알고리즘 레포트 3페이지"
               시스템: "✅ task 생성: 알고리즘 레포트 (마감: 내일 23:59, 예상 180분, 중요도 4)"
               시스템: "📝 next_action: 레포트 주제 및 목차 정리"
        
        09:02  사이드바 → Plan 탭 클릭
               시스템: 오늘의 시간 블록 표시
               10:00~11:00  🔴 알고리즘 레포트 (→ 주제 및 목차 정리)
               11:00~11:10  ☕ 휴식
               11:10~11:40  🟡 빨래
        
낮   11:05  블록 종료 후 미완료 감지
               채팅 알림: "'알고리즘 레포트' 블록이 지났어요. 지금 딱 이것만: 주제 및 목차 정리"
               [할게] [미룰게]
               → "할게" 클릭
               시스템: "11:10~12:10에 배정했어요."
        
저녁 20:00  Task Board → "알고리즘 레포트" → [완료] 클릭
               시스템: "🎉 알고리즘 레포트 완료! 마감 전 완료 👍"
```

---

## 핵심 학사 일정 (동국대 2026-1학기)

Phase 3에서 자동 등록할 일정들:

| 날짜 | 일정 |
|------|------|
| 02/19~02/24 | 1학기 등록 |
| **03/03** | **개강** |
| 03/03~03/09 | 수강신청 확인 및 정정 |
| 03/06~03/10 | 휴학 신청(2차) |
| 03/11~03/13 | 학점포기 신청(1차) |
| 03/27 | 학기 1/4 기준일 |
| **04/21~04/27** | **중간시험** |
| 05/13~05/15 | 여름 계절학기 수강신청 |
| 06/02~06/05 | 학점포기 신청(2차) |
| **06/09~06/15** | **기말시험** |
| 06/15 | 종강 |
