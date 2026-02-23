# 08 — RAG 시스템 학습 + The Agent 적용 계획

> 작성일: 2026-02-23
> News_Agent에서 파생된 RAG 학습 경험을 The Agent에 활용하는 로드맵.

---

## 배경

News_Agent 프로젝트에서 기사 기반 Q&A 챗봇(검색 + 프롬프트 생성기)을 구현하면서 RAG 인프라를 구축하게 되었다. 이 경험을 The Agent의 **메모리 시스템**에 직접 활용할 수 있다.

The Agent의 핵심 기능 중 하나인 "과거 대화/일정/노트를 기억하고 검색하여 맥락에 맞는 조언을 제공하는 것"이 정확히 RAG의 활용 사례다.

---

## RAG 학습 로드맵 (난이도별)

### Lv.1: 키워드 검색 + LLM 답변 (1~2일)

**개념**: 데이터를 DB에 저장 → 키워드로 검색 → 결과를 LLM에 전달 → 답변 생성

**기술 스택**:
- SQLite + FTS5 (Full Text Search)
- FastAPI (API 서버)
- Anthropic Haiku (경량 LLM)

**배우는 것**:
- DB 인덱싱과 풀텍스트 검색
- API 서버 구축 (FastAPI)
- LLM 프롬프트 엔지니어링 (컨텍스트 주입)
- 검색 결과를 LLM 입력으로 조합하는 방법

**실습 프로젝트**: News_Agent 챗봇 (현재 구현 예정)

```python
# 핵심 흐름
query = "지난주 반도체 뉴스"
results = db.execute("SELECT * FROM briefings_fts WHERE briefings_fts MATCH ?", [query])
context = format_results(results[:5])
answer = llm.generate(system="당신은 뉴스 분석가입니다.", user=f"{context}\n\n질문: {query}")
```

---

### Lv.2: 벡터 임베딩 RAG (3~5일)

**개념**: 텍스트를 벡터(숫자 배열)로 변환 → 의미적 유사도로 검색 → 키워드가 달라도 의미가 비슷한 문서를 찾음

**기술 스택**:
- 임베딩 모델 (OpenAI text-embedding-3-small 또는 Voyage)
- 벡터 DB (ChromaDB — 로컬, 설치 간편)
- 청킹 전략 (긴 문서를 적절한 크기로 분할)

**배우는 것**:
- 임베딩이 뭔지 — 텍스트를 1536차원 벡터로 변환하는 원리
- 코사인 유사도 — 벡터 간 거리로 의미적 유사성 측정
- 청킹 — 문서를 어떤 크기로 나눠야 검색 품질이 좋은지
- 벡터 DB CRUD — 저장, 검색, 업데이트, 삭제
- 하이브리드 검색 — 키워드 + 벡터 검색 결과 합산

**실습 프로젝트**: 옵시디언 노트 검색 챗봇

```python
# 핵심 흐름
from chromadb import Client

# 인덱싱 (1회)
collection = client.create_collection("notes")
for chunk in split_document(note):
    embedding = embed(chunk.text)
    collection.add(ids=[chunk.id], embeddings=[embedding], documents=[chunk.text])

# 검색
query_embedding = embed("ADHD 관련 할 일 관리 방법")
results = collection.query(query_embeddings=[query_embedding], n_results=5)
```

---

### Lv.3: 프로덕션 RAG (1~2주)

**개념**: 실제 서비스에서 사용할 수 있는 수준의 RAG 시스템

**추가 기술**:
- 리랭킹 (Cohere Rerank) — 검색 결과의 순서를 LLM으로 재정렬
- 멀티턴 대화 — 이전 질문/답변을 기억하면서 대화 이어가기
- 할루시네이션 감지 — LLM이 없는 내용을 지어내는 것 방지
- 출처 검증 — 답변의 근거가 되는 문서를 명시
- 평가 메트릭 — 검색 정밀도(Precision), 재현율(Recall), F1

**실습 프로젝트**: The Agent 메모리 시스템

---

## The Agent에 RAG를 적용하는 지점

### 1. 과거 대화 기억 (Memory RAG)

```
사용자: "저번에 데이터베이스 과제 언제까지라고 했지?"
    ↓
대화 이력 벡터 검색 → "10/15까지 DB 설계 과제 제출" 관련 대화 발견
    ↓
답변: "10월 15일까지 DB 설계 과제 제출이라고 하셨습니다."
```

doc 07-memory-architecture.md의 "대화 메모리" 구현에 직접 활용.

### 2. 학교 공지 검색

```
사용자: "이번 학기 수강철회 기간이 언제야?"
    ↓
크롤링된 학교 공지 FTS 검색 → 관련 공지 발견
    ↓
답변: "수강철회 기간은 4/1~4/5입니다. [공지 링크]"
```

### 3. 노트/메모 기반 학습 도우미

```
사용자: "운영체제 중간고사 범위 정리해줘"
    ↓
옵시디언 노트에서 "운영체제" 관련 노트 벡터 검색
    ↓
답변: 관련 노트 5개 기반으로 핵심 개념 정리
```

---

## News_Agent RAG → The Agent 재사용 가능한 컴포넌트

| 컴포넌트 | News_Agent | The Agent |
|----------|-----------|-----------|
| FastAPI 서버 구조 | `backend/main.py` | 동일 구조 재사용 |
| SQLite FTS5 검색 | `backend/db.py` | 대화/공지/노트 인덱싱에 재사용 |
| LLM 호출 래퍼 | `briefing_generator._call_llm` | 범용 LLM 클라이언트로 분리 |
| 프롬프트 템플릿 | `backend/prompt_api.py` | 메모리 기반 프롬프트 생성에 재사용 |
| 피드백 수집 | `backend/feedback_api.py` | 사용자 선호도 학습에 재사용 |

---

## 권장 학습 순서

```
1. News_Agent Lv.1 (FTS5 + Haiku)     ← 지금 할 예정
   └─ API 서버, DB, LLM 연동 기초
       ↓
2. 옵시디언 노트 RAG (Lv.2)            ← 별도 미니 프로젝트
   └─ 벡터 임베딩, ChromaDB, 청킹
       ↓
3. The Agent 메모리 시스템 (Lv.3)       ← 본 프로젝트에 통합
   └─ 멀티턴, 리랭킹, 할루시네이션 감지
```

각 단계에서 이전 단계의 코드를 재사용하므로, 점진적으로 복잡도를 올리면서 학습할 수 있다.
