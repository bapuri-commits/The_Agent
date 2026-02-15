# 06 — MVP Roadmap

## 목표

**개강 전까지 4대 플로우가 실제로 돌아가는 시스템 완성.**

핵심은 "완벽한 시스템"이 아니라 **"매일 쓸 수 있는 시스템"**.

---

## Phase 1: MVP (2주)

### Sprint 1 (Day 1~4) — Foundation + Inbox

#### Step 1.1: 프로젝트 초기 세팅 (Day 1)

**작업:**
- Python 프로젝트 구조 생성 (app/, tests/)
- requirements.txt 작성 (fastapi, uvicorn, sqlalchemy, python-telegram-bot, openai, apscheduler, pydantic)
- SQLAlchemy 모델 정의 (models.py)
- DB 초기화 + seed 데이터 (db.py)
- config.py (.env 로딩)
- .env.example 작성

**Done 정의:**
- [x] `python -m app.db` 실행 시 SQLite DB 파일 생성됨
- [x] 모든 테이블이 생성됨 (tasks, projects, calendar_blocks, planned_blocks, user_profile, audit_logs, task_completions)
- [x] user_profile에 기본 row(id=1) 존재
- [x] "미분류" 프로젝트 존재

**테스트:**
- DB 생성/삭제 반복 시 에러 없음
- ORM 모델로 task CRUD 가능

---

#### Step 1.2: Inbox + LLM 파싱 (Day 2~3)

**작업:**
- schemas.py: TaskCreate, TaskResponse Pydantic 모델
- services/llm.py: OpenAI 클라이언트 래퍼 (structured output)
- services/inbox.py: parse_inbox() — 1줄 텍스트 → TaskCreate
- services/audit.py: 기본 audit log 기록
- api/inbox.py: POST /inbox 엔드포인트
- main.py: FastAPI 앱 생성

**Done 정의:**
- [x] `POST /inbox {"text": "내일 OS과제 제출"}` → task가 DB에 저장됨
- [x] 반환값에 title, deadline_at, est_minutes, importance 포함
- [x] 기본값 자동 채움 동작 (빈 필드에 est=60, importance=3)
- [x] audit_logs에 "task_created" 이벤트 기록됨

**테스트:**
- "내일 OS과제 제출 2시간 중요" → deadline이 내일, est=120, importance=5
- "빨래" → deadline=null, est=60, importance=3 (전부 기본값)
- 빈 문자열 → 422 에러
- LLM 장애 시 → fallback (title=원문 그대로, 나머지 기본값)

---

#### Step 1.3: Telegram Bot 연동 (Day 3~4)

**작업:**
- bot.py: Telegram Bot 설정 + 메시지 핸들러
- 명령어 핸들러: /tasks, /done, /skip, /plan, /status
- 기본 동작: 일반 텍스트 → POST /inbox 호출
- chat_id 필터링 (본인만 허용)
- main.py에 Bot startup 추가

**Done 정의:**
- [x] Telegram에서 "내일 OS과제 제출" 전송 → task 생성 + 확인 메시지 수신
- [x] `/tasks` → pending tasks 목록 출력
- [x] `/done 42` → task 완료 처리 + 확인 메시지
- [x] 모르는 chat_id → 무응답

**테스트:**
- 실제 Telegram에서 메시지 송수신 확인
- 허용되지 않은 chat_id에서 메시지 보내도 응답 없음

---

### Sprint 2 (Day 5~8) — Priority + Planner

#### Step 2.1: Deterministic Prioritizer (Day 5)

**작업:**
- services/prioritizer.py: f(), g(), h(), p(), calculate_priority() 구현
- 가중치 상수 정의
- 불변 규칙 (24h 이내 최상단) 구현
- GET /tasks에 priority_score 정렬 적용

**Done 정의:**
- [x] calculate_priority()가 순수 함수 (같은 입력 → 같은 출력)
- [x] 마감 24h 이내 task가 항상 최상단
- [x] postpone_count 증가 시 점수 상승
- [x] 모든 f/g/h/p 함수에 대한 단위 테스트 통과

**테스트 시나리오:**
```python
# 같은 입력 → 같은 결과 (결정론 검증)
assert calculate_priority(task_a, now, energy=3) == calculate_priority(task_a, now, energy=3)

# 마감 가까울수록 높음
assert f(12) > f(48) > f(120)

# 미루기 많을수록 높음
task_a.postpone_count = 0
task_b.postpone_count = 3
assert calculate_priority(task_b, ...) > calculate_priority(task_a, ...)

# 불변 규칙: 24h 이내 무조건 최상단
assert calculate_priority(due_in_12h, ...) > calculate_priority(due_in_72h_importance_5, ...)
```

---

#### Step 2.2: Today Planner (Day 6~7)

**작업:**
- services/planner.py: extract_free_windows(), generate_today_plan()
- 에너지 레벨 시간대 매핑
- 30/60분 블록 배치 로직
- 휴식 블록 삽입
- POST /plan/today 엔드포인트
- planned_blocks DB 저장

**Done 정의:**
- [x] POST /plan/today → 오늘의 시간 블록 리스트 반환
- [x] fixed 일정(수업 등)과 겹치지 않음
- [x] 수면/식사 시간에 배치되지 않음
- [x] 고에너지 작업은 집중 시간대에 우선 배치
- [x] 연속 2블록 후 휴식 블록 존재
- [x] 같은 조건으로 재실행 시 같은 결과

**테스트 시나리오:**
```python
# 수업(10:00~12:00) 시간에 task 배치 안 됨
plan = generate_today_plan(tasks, calendar_with_class)
for block in plan.blocks:
    assert not overlaps(block, class_block)

# 수면 시간에 배치 안 됨
for block in plan.blocks:
    assert not in_sleep_window(block)

# 결정론: 같은 입력 → 같은 plan
plan1 = generate_today_plan(tasks, calendar)
plan2 = generate_today_plan(tasks, calendar)
assert plan1 == plan2
```

---

#### Step 2.3: Telegram Plan 표시 (Day 8)

**작업:**
- `/plan` 명령어에 Today Plan 포맷팅 연결
- 보기 좋은 텍스트 포맷:
  ```
  📅 오늘의 플랜 (2/16)
  
  10:00-11:00  🔴 OS과제 제출
               → 과제 파일 열어서 진행 상태 확인
  11:00-11:10  ☕ 휴식
  11:10-11:40  🟡 이메일 답장
               → 교수님 메일 확인 후 답장
  
  📊 총 집중시간: 90분 (2블록)
  ```

**Done 정의:**
- [x] Telegram에서 `/plan` → 위 형태의 포맷된 플랜 출력
- [x] 아직 plan이 없으면 자동 생성 후 출력

---

### Sprint 3 (Day 9~12) — Enforcement + Polish

#### Step 3.1: Enforcement Engine (Day 9~10)

**작업:**
- services/enforcement.py: check_enforcement(), auto_decompose()
- APScheduler에 30분 간격 enforcement 체크 등록
- Telegram 알림 발송 (narrowing/escalation/deadline_warning)
- 알림 쿨다운 로직 (과도 알림 방지)
- postpone 시 자동 재계획 트리거

**Done 정의:**
- [x] 지나간 블록의 미완료 task → Telegram 알림 수신
- [x] 알림에 "할게" / "미룰게" 선택지 포함
- [x] "미룰게" → postpone_count 증가 + 우선순위 상승
- [x] postpone 3회+ → escalation 알림 (강도 높은 메시지)
- [x] 같은 task에 1시간 내 중복 알림 안 옴

**테스트:**
```python
# 미이행 감지
block = create_past_block(task_id=42, status="scheduled")
actions = check_enforcement(now)
assert any(a.task_id == 42 for a in actions)

# 쿨다운: 1시간 내 중복 방지
send_enforcement(task_id=42)
actions = check_enforcement(now + timedelta(minutes=30))
assert not any(a.task_id == 42 for a in actions)

# postpone 3회 → escalation
task.postpone_count = 3
actions = check_enforcement(now)
assert actions[0].type == "escalation"
```

---

#### Step 3.2: 안정화 + 일상 사용 테스트 (Day 11~12)

**작업:**
- 에러 핸들링 강화 (LLM 장애, DB 에러, 네트워크 에러)
- Failure mode: LLM 죽으면 → 원문 그대로 task.title에 저장 (기본값 채움)
- 로깅 정리 (structured logging)
- 실제 하루 사용 시뮬레이션 (본인이 직접 사용)
- 버그 수정 + 엣지 케이스 처리

**Done 정의:**
- [x] LLM API 장애 시에도 task 생성 가능 (fallback)
- [x] 하루 종일 사용해도 크래시 없음
- [x] 아침에 /plan → 낮에 enforcement 알림 → 저녁에 /done으로 하루 사이클 완료

---

## Phase 1 완료 기준 (개강 전)

모든 Sprint 완료 후, 다음 시나리오가 end-to-end로 동작:

```
아침 08:30  사용자 기상
        09:00  사용자: "내일 OS과제 제출 2시간 중요"
               봇: "✅ task 생성: OS과제 제출 (마감: 내일 23:59, 2시간, 중요도 5)"
        09:01  사용자: /plan
               봇: "📅 오늘의 플랜..." (시간 블록 표시)
        
낮   10:00  스케줄된 블록 시작
        11:05  블록 종료 후 미완료 감지
               봇: "'OS과제 제출' 블록이 지났어요. 지금 딱 이것만: 과제 파일 열기"
               사용자: "할게"
               봇: "좋아요! 11:10~12:00에 배정했어요."
        
저녁 20:00  사용자: /done 42
               봇: "🎉 OS과제 제출 완료! 마감 전 완료 👍"
        
밤   23:00  봇: (알림 없음 — 수면 시간 접근)
```

---

## Phase 2 (학기 중, 점진적)

| 기능 | 설명 | 우선순위 |
|------|------|---------|
| 반복 일정 | 매주 수업 자동 등록 (recurrence) | 높음 |
| Google Calendar 연동 | 캘린더에 planned block 자동 등록 | 높음 |
| 습관 대시보드 | 주간 완료율, 평균 지연, 에너지 정확도 | 중간 |
| 작업 분해 고도화 | 큰 과제 → 자동 서브태스크 생성 | 중간 |
| RAG 메모리 | 강의자료/메일 검색 (pgvector) | 낮음 |
| 멀티채널 | Discord 추가 | 낮음 |
| 웹 대시보드 | 브라우저에서 조회/수정 | 낮음 |

---

## Phase 3 (장기)

| 기능 | 설명 |
|------|------|
| LMS 연동 | 학교 LMS에서 과제/공지 자동 파싱 |
| 이메일 연동 | 중요 메일 자동 감지 → task 생성 제안 |
| 적응형 가중치 | 완료 패턴 분석 → 가중치 자동 조정 |
| 다중 사용자 | 인증/권한 분리 |
