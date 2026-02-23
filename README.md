# The Agent — Personal AI Secretary

> ADHD-friendly, performance-first personal AI secretary system.

## What is this?

학교 + 일상 전반의 정보를 **자동 수집 → 구조화 → 계획 → 실행 지원 → 마무리**까지 end-to-end로 커버하는 AI 비서.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React (Vite) + Tailwind + shadcn/ui |
| Backend | FastAPI + WebSocket |
| Database | Postgres + SQLAlchemy |
| LLM | gpt-4o-mini (Fast) + Claude 3.5 Sonnet (Smart) |
| Scheduler | APScheduler |
| Deploy | Docker Compose + VPS |

## Quick Start

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env에 API 키 등 실제 값 입력

# 2. Docker로 실행
docker compose up --build

# 3. 확인
# Backend: http://localhost:8000/health
# API Docs: http://localhost:8000/docs
```

## Project Structure

```
The_Agent/
├── backend/          # FastAPI 백엔드
│   ├── app/
│   │   ├── api/      # REST 엔드포인트
│   │   ├── services/  # 비즈니스 로직
│   │   ├── context/   # AI 컨텍스트 ("제2의 두뇌")
│   │   └── integrations/ # 외부 연동
│   └── Dockerfile
├── frontend/         # React 프론트엔드 (Phase 1 Sprint 2)
├── docs/             # 설계 문서
├── docker-compose.yml
└── .env.example
```

## Design Docs

See `docs/` directory for full architecture and design documents.
