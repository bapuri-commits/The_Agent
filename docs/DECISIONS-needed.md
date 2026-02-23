# 결정 필요 사항 (v2, 2026-02-15 업데이트)

> **이 문서의 목적:**
> MVP 개발 착수 전 확정해야 하는 사항.
> ✅ = 확정됨, ❓ = 미결

---

## ✅ 확정된 사항

### ✅ 메인 채널
> **결정: 자체 Web UI (React)**
> Telegram은 보조 알림 채널로 Phase 3에서 추가.

### ✅ DB
> **결정: Postgres (Docker Compose)**
> SQLite 대신 처음부터 Postgres. 마이그레이션 비용 제거.

### ✅ LLM 제공자
> **결정: gpt-4o-mini (파싱) + Claude 3.5 Sonnet (추론)**
> 성능 최우선. 비용 제한 없음. API 키 필요 (OpenAI + Anthropic).

### ✅ OpenClaw
> **결정: 제외**
> 아키텍처 충돌 (이중 SSOT, 제어권, 보안). MCP는 Python SDK로 직접 사용.

### ✅ 배포
> **결정: VPS + Docker Compose**
> 24/7 가동, 멀티 디바이스 브라우저 접속.

### ✅ 학교 시스템
> **확인 완료:**
> - e-Class (eclass.dongguk.edu) — 과제/강의자료
> - nDRIMS (ndrims.dongguk.edu) — 학적/수강신청
> - dongguk.edu — 학사 공지
> - ai.dongguk.edu — 학과 공지

### ✅ 개강일
> **2026-03-03** (동국대 학사일정 확인 완료)
> 수강신청 확인 및 정정: 03/03~03/09

### ✅ 옵시디언 연동
> **결정: 읽기 + 쓰기 모두**
> The Record 볼트 구조를 이해하고, 데일리 노트/프로젝트 _index.md 읽기 및 쓰기.

---

## ❓ 남은 결정 사항

### ✅ VPS 선택

> **결정: Contabo (~$4/월)**
> 가성비 우선. Phase 1 Sprint 3에서 세팅.

---

### 2. API 키 발급

LLM 사용을 위해 API 키가 필요함. Phase 1 Sprint 1 시작 전에 필요.

**필요한 키:**
- OpenAI API Key (gpt-4o-mini용): https://platform.openai.com/
- Anthropic API Key (Claude용): https://console.anthropic.com/

> 답변: (Sprint 1 시작 전 발급 필요)

---

### 3. 학기 중 시간대 설정

현재는 방학 기준 설정 (09:00 기상, 00:00~01:00 취침).
개강 후 수업 시간표가 확정되면 업데이트 필요.

> 답변: (개강 후 시간표 확정 시 업데이트)

---

## 답변 완료 후

남은 항목(1~2)을 확정한 후 Phase 1 Sprint 1 코드 구현 시작.
3번은 개강 후 확정.
