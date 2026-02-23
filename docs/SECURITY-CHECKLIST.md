# API 키 & 보안 체크리스트

> 모든 Phase/Sprint에서 참조. 특히 VPS 배포(Step 3.2) 전에 전수 확인.

---

## 1. 사용자가 지켜야 할 규칙

| # | 규칙 | 왜 |
|---|------|-----|
| 1 | **채팅/메신저에 API 키를 절대 붙여넣지 않기** | 대화 기록에 남아 노출됨. 키 변경은 `.env` 파일에서 직접 |
| 2 | **git push 전에 `git status` 확인** | `.env`가 실수로 staged 되어 있는지 반드시 확인 |
| 3 | **API 사이트에서 월 상한(spending limit) 설정** | 키 유출 시 피해 제한 |
| 4 | **3개월마다 키 회전** | 기존 키 삭제 → 새 키 발급 → `.env` 업데이트 |
| 5 | **공용 PC에서 작업 시 `.env` 삭제 후 자리 뜨기** | 키가 로컬에 남으면 안 됨 |

### 월 상한 설정 방법

**OpenAI:**
1. https://platform.openai.com/ → Settings → Limits
2. "Monthly budget" 설정 (권장: $30~50)

**Anthropic:**
1. https://console.anthropic.com/ → Settings → Limits
2. "Spend limit" 설정 (권장: $30~50)

---

## 2. 프로그램에서 적용된 보안 조치

| # | 항목 | 파일 | 상태 |
|---|------|------|------|
| 1 | `.env`가 `.gitignore`에 포함 | `.gitignore` 36행 | ✅ |
| 2 | `.env.example`에 실제 키 없음 (플레이스홀더만) | `.env.example` | ✅ |
| 3 | 코드에 키 하드코딩 없음 | `config.py` (환경변수만 사용) | ✅ |
| 4 | Docker 내부에서만 키 사용 | `docker-compose.yml` | ✅ |
| 5 | `frontend/.env`도 `.gitignore`에 포함 | `.gitignore` 68행 | ✅ |

---

## 3. VPS 배포 시 추가 필요 사항 (Phase 1 Step 3.2)

| # | 항목 | 설명 |
|---|------|------|
| 1 | **HTTPS 강제** | Let's Encrypt + Nginx/Caddy. API 키가 HTTP 평문으로 전송되면 안 됨 |
| 2 | **프로덕션 모드** | `APP_ENV=production` → SQL 로그 비활성화 (키가 로그에 남을 위험 방지) |
| 3 | **방화벽** | VPS에서 8000(백엔드)/5432(DB) 포트 외부 직접 접근 차단. Nginx만 80/443 노출 |
| 4 | **SSH 키 인증** | VPS 접속을 비밀번호가 아닌 SSH 키로만 허용 |
| 5 | **Docker secrets** (선택) | `.env` 대신 Docker secrets 사용 권장. 컨테이너 내부에서만 접근 가능 |

---

## 4. 학교 시스템 연동 시 추가 사항 (Phase 3)

| # | 항목 | 설명 |
|---|------|------|
| 1 | **학교 로그인 정보도 `.env`에 저장** | 코드에 하드코딩 절대 금지 |
| 2 | **Playwright headless에서만 사용** | 브라우저 자동화 내부에서만 자격증명 사용 |
| 3 | **자격증명 로깅 금지** | audit_log에 학교 비밀번호가 남지 않도록 payload 필터링 |

---

## 5. git push 전 체크리스트

매번 push 전에 확인:

```bash
# 1. .env가 staged 되어 있지 않은지 확인
git status

# 2. 혹시 .env가 tracked 되어 있다면 즉시 제거
git rm --cached .env

# 3. 커밋 히스토리에 키가 없는지 확인 (최초 1회)
git log --all --full-history -- .env
# → 결과가 나오면 히스토리에서 제거 필요 (git filter-branch 또는 BFG)
```

---

## 6. 키 유출 시 대응

만약 키가 노출되었다면:

1. **즉시** API 사이트에서 해당 키 삭제 (revoke)
2. 새 키 발급
3. `.env` 업데이트
4. `docker compose restart backend`
5. 노출 경로 확인 (git 히스토리? 채팅? 스크린샷?)
6. 해당 경로에서 키 제거
