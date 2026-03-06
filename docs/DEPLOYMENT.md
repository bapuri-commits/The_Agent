# The_Agent — VPS 배포 가이드

> ⚠️ **초안 문서** — 각 Stage 진행 시 실제 환경에 맞게 수정될 수 있음.

> Contabo VPS에 Docker Compose로 배포하는 절차.
> DevOps 학습 로드맵 Stage 3, 4, 5, 6에서 사용.

---

## 아키텍처 개요

```
[클라이언트] → [nginx (80/443)] → [Frontend (정적 빌드)]
                                 → [Backend (FastAPI :8000)]
                                 → [WebSocket (/ws)]
                                        ↓
                                 [PostgreSQL :5432]
```

---

## 사전 요구사항

- Docker + Docker Compose
- nginx (호스트)
- 도메인 + SSL 인증서 (Stage 6 이후)

---

## 환경변수

`.env.example`을 복사하여 `.env` 생성:

| 변수 | 필수 | 설명 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | GPT-4o-mini (M1 Worker) |
| `ANTHROPIC_API_KEY` | ✅ | Claude (M2, M3, M4) |
| `POSTGRES_USER` | ✅ | DB 사용자 (기본: theagent) |
| `POSTGRES_PASSWORD` | ✅ | DB 비밀번호 |
| `POSTGRES_DB` | ✅ | DB 이름 (기본: theagent) |
| `DATABASE_URL` | ✅ | 연결 문자열 |
| `APP_ENV` | | production / development |
| `APP_SECRET_KEY` | ✅ | 세션 암호화 키 |
| `ALLOWED_ORIGINS` | ✅ | CORS 허용 Origin |

Frontend 빌드 시:

| 변수 | 설명 |
|------|------|
| `VITE_API_URL` | REST API 주소 (예: https://agent.도메인/api) |
| `VITE_WS_URL` | WebSocket 주소 (예: wss://agent.도메인/ws/chat) |

---

## Stage 3 — Docker Compose 배포

### 기본 실행

```bash
cp .env.example .env
# .env 편집

docker compose up -d --build
docker ps
docker logs the_agent-backend-1 -f
```

### Frontend 프로덕션 빌드 (TODO)

현재 `frontend/Dockerfile`이 `npm run dev`로 실행됨. 프로덕션에서는:

1. 멀티 스테이지 빌드: `npm run build` → nginx로 정적 파일 서빙
2. 또는 호스트 nginx에서 빌드된 `dist/` 폴더를 직접 서빙

---

## Stage 4 — nginx 리버스 프록시 설정

### /etc/nginx/sites-available/the-agent

```nginx
# TODO: Stage 5에서 작성
# server {
#     listen 80;
#     server_name agent.도메인;
#
#     location / {
#         proxy_pass http://localhost:5173;
#     }
#
#     location /api/ {
#         proxy_pass http://localhost:8000;
#     }
#
#     location /ws/ {
#         proxy_pass http://localhost:8000;
#         proxy_http_version 1.1;
#         proxy_set_header Upgrade $http_upgrade;
#         proxy_set_header Connection "upgrade";
#     }
# }
```

---

## Stage 5 — HTTPS

```bash
# TODO: Stage 6에서 실행
# sudo certbot --nginx -d agent.도메인
```

---

## Stage 6 — CI/CD

### GitHub Actions (.github/workflows/deploy.yml)

```yaml
# TODO: Stage 7에서 작성
# on: push to main
# steps:
#   - SSH into VPS
#   - git pull
#   - docker compose up -d --build
```

---

## 포트 사용

| 포트 | 서비스 | 외부 노출 |
|------|--------|----------|
| 80 | nginx (HTTP) | ✅ |
| 443 | nginx (HTTPS) | ✅ |
| 8000 | Backend (FastAPI) | ❌ (nginx만 접근) |
| 5173 | Frontend (dev) | ❌ (nginx만 접근) |
| 5432 | PostgreSQL | ❌ (내부만) |

---

## 알려진 이슈

- Frontend Dockerfile이 dev 모드(`npm run dev`)로 실행됨 → 프로덕션 빌드 전환 필요
- Alembic migrations 폴더 미생성 → 스키마 변경 시 마이그레이션 도입 필요
- APScheduler 설정 미구현 (main.py에 TODO만 존재)
