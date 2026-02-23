# 07 — Memory Architecture & Personalization Research

> **이 문서의 성격:**
> 단순 설계 문서가 아니라, 프로젝트의 **핵심 연구 과제**를 정리한 문서.
> "딥러닝 없이 API 모델만으로 딥러닝급 개인화를 달성하는 방법"에 대한 연구 노트.

---

## 1. 문제 정의

### 상황
- 로컬 LLM 파인튜닝은 하드웨어 한계로 불가능
- API 모델(Claude Opus 4.6, GPT-5.2 등)은 성능은 최고지만 가중치를 수정할 수 없음
- 따라서 모든 "개인화"는 **컨텍스트 주입**으로만 달성해야 함

### 핵심 딜레마
```
개인화 깊이 ∝ 컨텍스트 양
그러나
컨텍스트 양 ↑ → 비용 ↑ + 성능 ↓ (lost in the middle) + 노이즈 ↑

즉, 무작정 컨텍스트를 늘리면 개인화가 좋아지는 게 아니라
어느 시점부터 오히려 나빠진다.
```

### 목표
> 컨텍스트가 폭발하지 않으면서,
> 딥러닝급에 준하는 성능으로
> 사용자(성향, 성격, 일상, 일정)를 깊게 이해시키는 것.

---

## 2. 인간 기억 구조에서 배우기

딥러닝은 "가중치에 기억을 새기는" 방식.
우리는 "가중치는 고정 + 외부 메모리"로 같은 효과를 내야 함.

인간의 기억 구조가 좋은 모델이 됨:

| 인간 기억 유형 | 특성 | AI 대응 | 저장 방식 | LLM 토큰 소모 |
|---|---|---|---|---|
| **절차 기억** (Procedural) | 자전거 타기 — 의식 없이 자동 실행 | 학습된 규칙/패턴 → **코드 규칙** | 코드 + config | **0 토큰** |
| **의미 기억** (Semantic) | "서울은 한국의 수도" — 사실/지식 | 사용자에 대한 확정된 이해 | 고정 크기 문서 | **~500 토큰** |
| **일화 기억** (Episodic) | "지난 화요일에 일어난 일" — 경험/사건 | 과거 행동 기록 | pgvector 임베딩 | **필요시만 검색, ~500 토큰** |
| **작업 기억** (Working) | "지금 내가 뭘 하고 있었지" — 현재 맥락 | 현재 상태 | DB 쿼리 (실시간) | **~300 토큰** |

### 핵심 통찰

> **"컨텍스트"라고 생각하는 것의 대부분은 사실 코드나 DB 쿼리로 해결 가능하다.**
> LLM 토큰으로 넣어야 하는 건 전체의 일부에 불과하다.

예시:
```
"이 사용자는 '빨래'라고 하면 보통 est=40, energy=2, 오후 배치를 원한다"

❌ 나쁜 방식: 매번 LLM 프롬프트에 이 문장을 넣음 (토큰 소모)
✅ 좋은 방식: 코드 규칙으로 변환

    LEARNED_PATTERNS = {
        "빨래": {"est_minutes": 40, "energy": 2, "preferred_time": "afternoon"}
    }
    
    → LLM 호출 전에 코드가 먼저 체크
    → 매칭되면 LLM 호출 자체가 불필요
    → 0 토큰
```

---

## 3. 4계층 메모리 아키텍처 (MLPA)

**Multi-Layer Personalization Architecture**

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│  Layer 0: Procedural Memory (절차 기억)                   │
│  ┌──────────────────────────────────────────────────┐    │
│  │  학습된 패턴 → 코드 규칙으로 변환                    │    │
│  │                                                  │    │
│  │  구현: Python dict / JSON config                 │    │
│  │  갱신: M4 Distiller가 패턴 감지 → 코드 규칙 생성    │    │
│  │  토큰: 0 (코드 실행, LLM 불필요)                   │    │
│  │  예: "빨래" → {est:40, energy:2}                  │    │
│  │  예: "과제" + 마감 24h 이내 → importance 자동 5    │    │
│  │                                                  │    │
│  │  크기: 무제한 (코드니까)                            │    │
│  │  갱신 주기: 패턴 50건 이상 축적 시 자동 생성         │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  Layer 1: Semantic Memory (의미 기억)                     │
│  ┌──────────────────────────────────────────────────┐    │
│  │  사용자에 대한 확정된 이해                           │    │
│  │                                                  │    │
│  │  구현: USER_PROFILE.md (고정 크기, 덮어쓰기)        │    │
│  │  갱신: M4 Distiller가 월 1회 전체 재작성            │    │
│  │  토큰: ~500 (항상 프롬프트에 포함)                  │    │
│  │  예: "ADHD, 오전 집중, 과제 제출 누락 패턴"         │    │
│  │                                                  │    │
│  │  크기 상한: 500 tokens (초과 시 M4가 압축)          │    │
│  │  갱신 주기: 월 1회 (또는 큰 변화 감지 시)            │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  Layer 2: Episodic Memory (일화 기억)                     │
│  ┌──────────────────────────────────────────────────┐    │
│  │  과거 경험/사건 기록                                │    │
│  │                                                  │    │
│  │  구현: pgvector 임베딩 (Phase 4)                   │    │
│  │        Phase 1~3: inbox_logs + audit_logs in DB   │    │
│  │  갱신: 매 interaction마다 자동 축적                 │    │
│  │  토큰: 0 (평소) ~ 500 (검색 결과 주입 시)           │    │
│  │  예: "지난주 화요일 OS과제 3번 미룸 → 자정 마감작업" │    │
│  │                                                  │    │
│  │  크기: 무제한 (DB 저장)                             │    │
│  │  LLM 접근: 관련된 에피소드만 검색하여 주입           │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  Layer 3: Working Memory (작업 기억)                      │
│  ┌──────────────────────────────────────────────────┐    │
│  │  현재 상태 (매 요청마다 새로 계산)                    │    │
│  │                                                  │    │
│  │  구현: DB 쿼리 (실시간)                             │    │
│  │  갱신: 매 요청 시 계산                              │    │
│  │  토큰: ~300                                       │    │
│  │  예: "현재 pending task 5개, 오늘 2블록 완료,       │    │
│  │       다음 블록 14:00, 에너지 추정 3/5"             │    │
│  │                                                  │    │
│  │  크기: 고정 (~300 tokens)                          │    │
│  │  갱신 주기: 매 LLM 호출 시                          │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 각 모델이 접근하는 메모리

| 모델 | Layer 0 | Layer 1 | Layer 2 | Layer 3 | 총 토큰 |
|------|---------|---------|---------|---------|--------|
| [M1] Worker | ✅ (코드) | ✅ | ❌ | ✅ | ~800 |
| [M2] Stabilizer | ✅ (코드) | ✅ | 필요시 | ✅ | ~800~1,300 |
| [M3] Judge | ✅ (코드) | ✅ | ✅ (검색) | ✅ | ~1,300~1,800 |
| [M4] Distiller | 생성 대상 | 생성 대상 | 입력 소스 | ❌ | 입력 많음, 출력 적음 |

**핵심: 어떤 모델도 2,000 토큰을 넘지 않는다.**

---

## 4. M4 Distiller의 역할 상세

### 4가지 출력

M4 Distiller는 raw 데이터(Level 3)를 입력받아 4가지를 생산:

```
[입력] inbox_logs + audit_logs + task_completions (최근 N일)
        ↓
[M4 Distiller]
        ↓
[출력 1] Layer 0 업데이트 제안
         → "빨래 패턴 감지: est=40, energy=2가 30건 중 28건 일치"
         → 코드 규칙으로 변환하여 저장
         
[출력 2] Layer 1 재작성 (USER_PROFILE.md)
         → 전체를 처음부터 다시 씀 (추가가 아닌 교체)
         → 500 tokens 상한 유지
         
[출력 3] Layer 2 요약 (MEMORY.md = 최근 에피소드 요약)
         → "이번 주 주요 사건" 형태
         → 1000 tokens 상한
         
[출력 4] Calibration 데이터
         → M1의 confidence 정확도 계산 결과
         → 임계값 조정 제안
```

### 갱신 주기

| 출력 | 주기 | 트리거 |
|------|------|--------|
| Layer 0 (코드 규칙) | 패턴 50건 축적 시 | 자동 |
| Layer 1 (USER_PROFILE) | 월 1회 | APScheduler 크론 |
| Layer 2 (MEMORY) | 주 1회 + 매일 경량 갱신 | APScheduler 크론 |
| Calibration | 2주 1회 | APScheduler 크론 |

---

## 5. Confidence Calibration 수학 모델

### 기본 구조

```
최근 50건 inbox_logs에서:

accuracy(c) = (confidence ≈ c인 건 중 사용자 수정 없는 비율)

calibration_ratio = accuracy(c) / c

ratio > 1.0 → 과소평가 (잘 맞추는데 자신없다고 함) → 임계값 내림
ratio < 1.0 → 과대평가 (못 맞추는데 자신있다고 함) → 임계값 올림
ratio ≈ 1.0 → 잘 보정됨 → 유지
```

### 조정 알고리즘

```python
# 초기값
THRESHOLD_CONFIRM = 0.95    # 이 이상이면 자동 저장 + 확인
THRESHOLD_SUGGEST = 0.80    # 이 이상이면 제안 + 확인 요청
# 그 미만이면 재질문

# 2주마다 실행
def recalibrate(recent_logs, current_thresholds):
    # 카테고리별 분리
    for category in ["학교", "개인", "프로젝트", "기타"]:
        category_logs = [l for l in recent_logs if category in l.tags]
        
        if len(category_logs) < 10:
            continue  # 데이터 부족, 조정 안 함
        
        # high confidence 구간 정확도
        high_conf = [l for l in category_logs if l.confidence >= current_thresholds.confirm]
        if high_conf:
            accuracy = sum(1 for l in high_conf if not l.corrections) / len(high_conf)
            ratio = accuracy / current_thresholds.confirm
            
            if ratio > 1.1 and len(high_conf) >= 15:
                # 잘 맞추고 있음 → 임계값 0.05 내림
                current_thresholds.confirm = max(0.70, current_thresholds.confirm - 0.05)
                current_thresholds.suggest = max(0.50, current_thresholds.suggest - 0.05)
            
            elif ratio < 0.85:
                # 못 맞추고 있음 → 임계값 0.05 올림
                current_thresholds.confirm = min(0.95, current_thresholds.confirm + 0.05)
                current_thresholds.suggest = min(0.90, current_thresholds.suggest + 0.05)
    
    return current_thresholds
```

### 카테고리별 독립 임계값

```
학교 관련: 패턴 반복적 → 빠르게 학습 → 2개월 후 임계값 0.75
개인 활동: 다양함 → 느리게 학습 → 6개월 후에도 임계값 0.85
프로젝트:  중간 → 3개월 후 임계값 0.80
```

---

## 6. inbox_logs 테이블 (학습 데이터)

```sql
CREATE TABLE inbox_logs (
    id              SERIAL PRIMARY KEY,
    
    -- 원본
    raw_input       TEXT NOT NULL,
    input_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    input_hour      INTEGER NOT NULL,          -- 입력 시각 (0-23)
    input_day_of_week INTEGER NOT NULL,        -- 요일 (0=월 ~ 6=일)
    energy_estimate INTEGER,                   -- 입력 시점 추정 에너지 (1-5)
    
    -- M1 파싱 결과
    parse_result    JSONB NOT NULL,
    confidence      REAL NOT NULL,
    parse_latency_ms INTEGER,
    
    -- 재질문
    clarifications  JSONB,                     -- [{question, field, asked_at}]
    user_responses  JSONB,                     -- [{response, responded_at}]
    
    -- 최종 결과
    final_result    JSONB NOT NULL,
    
    -- 학습 데이터
    corrections     JSONB,                     -- 사용자가 수정한 필드 diff
    was_auto_saved  BOOLEAN NOT NULL DEFAULT FALSE,  -- 자동 저장 vs 확인 후 저장
    
    -- 메타
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inbox_logs_hour ON inbox_logs(input_hour);
CREATE INDEX idx_inbox_logs_confidence ON inbox_logs(confidence);
```

---

## 7. 컨텍스트 파이프라인 구현 명세

> **이 섹션의 성격:**
> 위의 MLPA 설계를 **실제 코드로 구현**하기 위한 구체적 명세.
> 별도 논의(2026-02-18, 메모리 아키텍처 리뷰)에서 확정된 사항.

### 7.1 현재 상태 (2026-02-18 기준)

| 항목 | 상태 |
|------|------|
| M1 Worker | ✅ 구현 완료. `inbox.py`에서 `USER_PROFILE.md` + 현재 시각을 system prompt에 주입 |
| M2/M3/M4 | 🔲 `LLMRouter`에 정의만 있음. 호출 코드 없음 |
| `USER_PROFILE.md` | ✅ 수동 작성 완료. M1에서 사용 중 |
| `AGENT_SOUL.md` | ✅ 파일 존재. **아직 프롬프트에 미사용** |
| `MEMORY.md` | ✅ 파일 존재. **아직 프롬프트에 미사용** |
| Layer 3 (Working Memory) | 🔲 미구현. DB 쿼리로 현재 상태를 주입하는 로직 없음 |
| 컨텍스트 조립 | ⚠️ `inbox.py` 내부에 하드코딩. 독립 모듈 없음 |

**문제:**
- 프롬프트 조립 로직이 `inbox.py`에 하드코딩 → M2/M3 추가 시 중복 발생
- `AGENT_SOUL.md`, `MEMORY.md`가 사용되지 않음 → 컨텍스트 품질 낮음
- Working Memory 없음 → M1이 현재 상황을 모른 채 파싱

### 7.2 프롬프트 배치 규칙

LLM에 전달하는 system prompt의 배치 순서. **모든 모델이 이 순서를 따른다.**

```
┌──────────────────────────────────────────────┐
│  Zone A: 상단 고정 (변하지 않는 핵심)           │
│  ┌──────────────────────────────────────────┐│
│  │  [1] AGENT_SOUL: 정체성 + 판단 원칙       ││
│  │  [2] USER_PROFILE: 사용자에 대한 이해      ││
│  └──────────────────────────────────────────┘│
│                                               │
│  Zone B: 동적 컨텍스트 (매 요청마다 변함)        │
│  ┌──────────────────────────────────────────┐│
│  │  [3] WORKING_STATE: 현재 상태 (DB 쿼리)   ││
│  │  [4] EPISODIC: 관련 에피소드 (Phase 4)    ││
│  │  [5] TASK_RULES: Layer 0 규칙 결과        ││
│  │      (Phase 3, 해당시에만)                ││
│  └──────────────────────────────────────────┘│
│                                               │
│  Zone C: 하단 고정 (출력 규칙)                  │
│  ┌──────────────────────────────────────────┐│
│  │  [6] ROLE_INSTRUCTION: 모델별 역할 지시    ││
│  │  [7] OUTPUT_FORMAT: 출력 형식 + 제약       ││
│  │  [8] CURRENT_TIME: 현재 시각              ││
│  └──────────────────────────────────────────┘│
└──────────────────────────────────────────────┘
```

**배치 근거:**
- Zone A (상단): LLM은 프롬프트 앞부분을 가장 잘 기억한다. 변하지 않는 정체성/사용자 이해를 여기에 고정.
- Zone B (중간): 요청마다 달라지는 정보. lost in the middle 영향을 받을 수 있으나, 양이 적으면 문제없음.
- Zone C (하단): LLM은 끝부분도 잘 기억한다. 출력 형식을 여기 배치하여 형식 준수율을 높임.

### 7.3 모델별 컨텍스트 구성

| 블록 | M1 Worker | M2 Stabilizer | M3 Judge | M4 Distiller |
|------|-----------|---------------|----------|--------------|
| [1] AGENT_SOUL | 간소화 (역할만) | ✅ 전체 | ✅ 전체 | ❌ |
| [2] USER_PROFILE | ✅ | ✅ | ✅ | 입력 소스 |
| [3] WORKING_STATE | ✅ | ✅ | ✅ | ❌ |
| [4] EPISODIC | ❌ | 필요시 | ✅ (검색) | 입력 소스 |
| [5] TASK_RULES | ❌ (코드 처리) | ❌ (코드 처리) | 참조 | ❌ |
| [6] ROLE_INSTRUCTION | ✅ (파싱 전용) | ✅ (안정화 전용) | ✅ (판단 전용) | ✅ (증류 전용) |
| [7] OUTPUT_FORMAT | ✅ (JSON) | ✅ (JSON) | ✅ (자연어) | ✅ (구조화) |
| [8] CURRENT_TIME | ✅ | ✅ | ✅ | ❌ |

### 7.4 컨텍스트 조립 파이프라인 (코드 구조)

`inbox.py`에 하드코딩된 프롬프트 조립을 **독립 모듈로 분리**한다.

```
backend/app/services/context.py   ← 신규 생성

함수:
  build_context(role: ModelRole, db: Session) → str
    1. role에 따라 필요한 블록 목록 결정
    2. 각 블록 로드:
       - AGENT_SOUL: 파일 읽기 (캐싱 가능, 변경 드묾)
       - USER_PROFILE: 파일 읽기 (캐싱 가능, 월 1회 변경)
       - WORKING_STATE: DB 쿼리 실행 (매번 새로 계산)
       - EPISODIC: 검색 실행 (Phase 4)
       - ROLE_INSTRUCTION: 모델별 상수
       - OUTPUT_FORMAT: 모델별 상수
       - CURRENT_TIME: 현재 시각 계산
    3. 배치 규칙(7.2)에 따라 순서대로 조합
    4. 토큰 수 추정 + 상한 체크
    5. 완성된 system prompt 반환

  get_working_state(db: Session) → str
    DB에서 현재 상태를 쿼리하여 텍스트로 반환:
    - pending task 수
    - 오늘 완료한 task 수
    - 오늘 남은 calendar_block
    - 다음 블록 시작 시각
    - (향후) 추정 에너지 레벨
```

**이점:**
- `inbox.py`는 `build_context(ModelRole.WORKER, db)`만 호출
- M2/M3 추가 시 같은 함수에 역할만 바꿔 호출
- Layer 0/2 추가 시 `build_context` 내부만 수정, 호출부는 변경 없음

### 7.5 구현 우선순위

Phase 1 안에서 처리할 것 (기존 Step 2.0에서 앞당김):

| 순서 | 작업 | 근거 |
|------|------|------|
| 1 | `context.py` 모듈 생성 + `inbox.py`에서 분리 | 코드 구조. 한번 잡으면 안 바뀜 |
| 2 | 프롬프트 배치 규칙(7.2) 적용 | M1 파싱 품질에 즉시 영향 |
| 3 | `USER_PROFILE.md` 포맷 검토 + 구조화 | LLM이 소화하기 좋은 형식으로 |
| 4 | `get_working_state()` 구현 (Layer 3) | M1이 현재 상황을 아는 것이 파싱 정확도의 핵심 |
| 5 | `AGENT_SOUL.md` 프롬프트 통합 | 응답 톤/일관성 향상 |
| 6 | `inbox_logs`에 컨텍스트 토큰 수 기록 시작 | 측정 없이 개선 불가 |

Phase 2 이후:
- Layer 0 (코드 규칙) 적용 → Phase 3
- Layer 2 (에피소드 검색) 적용 → Phase 4
- M4 Distiller의 자동 갱신 → Phase 4

### 7.6 토큰 예산 관리

| 블록 | 예산 | 비고 |
|------|------|------|
| AGENT_SOUL | ~200 tok | M1은 간소화 버전 ~50 tok |
| USER_PROFILE | ~500 tok | 상한 엄수. 초과 시 압축 |
| WORKING_STATE | ~300 tok | 고정 포맷, 항목 수 제한 |
| EPISODIC | 0~500 tok | Phase 4. 필요시만 |
| ROLE_INSTRUCTION | ~100 tok | 모델별 상수 |
| OUTPUT_FORMAT | ~100 tok | 모델별 상수 |
| CURRENT_TIME | ~20 tok | 한 줄 |
| **M1 합계** | **~1,070 tok** | 상한 ~1,200 |
| **M3 합계 (최대)** | **~1,720 tok** | 상한 2,000 |

`build_context()`는 조립 후 토큰 수를 추정하고, 상한 초과 시 경고 로그를 남긴다.

---

## 8. 연구 과제 (Research Questions)

> 아래는 장기적 연구 질문. 당장의 구현보다는 데이터 축적 후 검증할 주제들.

### RQ1: 컨텍스트 압축의 최적 비율은?
- 원본 100 tokens → 압축 후 몇 tokens이 최적인가?
- 압축률과 판단 정확도의 관계는?
- 카테고리별로 최적 압축률이 다른가?

### RQ2: 절차 기억(코드 규칙) 전환 시점은?
- 패턴이 몇 회 반복되면 코드 규칙으로 전환해도 안전한가?
- 잘못된 규칙을 감지하고 롤백하는 메커니즘은?
- 코드 규칙 vs 컨텍스트 주입의 정확도 차이는?

### RQ3: 장기 개인화의 수렴 곡선은?
- 데이터 N건 축적 시 개인화 정확도의 이론적 상한은?
- 어느 시점에서 추가 데이터의 한계효용이 급감하는가?
- 딥러닝 파인튜닝 대비 컨텍스트 주입의 성능 격차는?

### RQ4: 에피소드 검색의 최적 전략은?
- Top-K 검색에서 K는 몇이 최적인가?
- 시간 가중치(최근 에피소드 우선) vs 유사도 가중치의 균형은?
- 에피소드 임베딩의 최적 chunk 크기는?

### RQ5: 다중 모델 간 컨텍스트 일관성 보장은?
- M1, M2, M3가 같은 사용자를 다르게 이해할 위험은?
- 계층형 메모리가 단일 모델 대비 일관성에 미치는 영향은?

---

## 9. 실험 계획 (장기)

### Phase 1~2 (구현 중)
- 기본 inbox_logs 수집 시작
- Layer 1 (USER_PROFILE.md) 수동 작성 → 성능 baseline 측정
- Confidence calibration 기초 데이터 축적

### Phase 3 (개강 후)
- 학교 데이터 유입 → 패턴 다양화
- Layer 0 (코드 규칙) 첫 자동 생성 시도
- 압축 비율 실험 (RQ1)

### Phase 4 (학기 중)
- pgvector 도입 → Layer 2 에피소드 검색 실험
- M4 Distiller 본격 가동 → Layer 1 자동 재작성
- 전체 파이프라인 성능 측정

---

## 10. 성공 기준

| 지표 | 3개월 목표 | 6개월 목표 | 12개월 목표 |
|------|-----------|-----------|-----------|
| M1 파싱 정확도 (수정 불필요 비율) | 60% | 80% | 90%+ |
| 재질문 빈도 | 매번 | 2건 중 1건 | 5건 중 1건 |
| 컨텍스트 크기 (M3 기준) | ~1,500 tokens | ~1,800 tokens | ~2,000 tokens (상한 유지) |
| 사용자 체감 "나를 이해한다" | 낮음 | 중간 | 높음 |
| 코드 규칙 자동 생성 수 | 0 | ~10개 | ~50개+ |
