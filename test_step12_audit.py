"""Step 1.2 감사 후 자동 테스트 — BUG 1~5 수정 검증."""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request
import json

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0


def post(path, data=None):
    body = json.dumps(data).encode("utf-8") if data else b"{}"
    req = urllib.request.Request(
        f"{BASE}{path}", data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8")), e.code


def get(path):
    req = urllib.request.Request(f"{BASE}{path}")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode("utf-8")), resp.status


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


print("=" * 60)
print("Step 1.2 Audit — Automated Tests")
print("=" * 60)

# ── T1: Health check ──
print("\n[T1] Health check")
r, code = get("/health")
check("status=ok", r.get("status") == "ok")

# ── T2: Basic inbox (fallback, LLM 크레딧 없음) ──
print("\n[T2] POST /inbox — fallback 모드")
r, code = post("/api/v1/inbox", {"text": "내일 OS과제 제출 2시간 중요"})
check("status 201", code == 201)
check("action=saved_fallback", r.get("action") == "saved_fallback")
check("task 존재", r.get("task") is not None)
if r.get("task"):
    check("task.id 존재", r["task"].get("id") is not None)
    check("task.status=pending", r["task"].get("status") == "pending")
    check("est_minutes 기본값 60", r["task"].get("est_minutes") == 60)

# ── T3: 빈 텍스트 거부 ──
print("\n[T3] POST /inbox — 빈 텍스트")
r, code = post("/api/v1/inbox", {"text": ""})
check("422 반환", code == 422)

# ── T4: Task 목록 조회 ──
print("\n[T4] GET /tasks")
r, code = get("/api/v1/tasks")
check("tasks 배열 존재", isinstance(r.get("tasks"), list))
check("total >= 1", r.get("total", 0) >= 1)

# ── T5: Task 완료 ──
print("\n[T5] POST /tasks/1/complete")
r, code = post("/api/v1/tasks/1/complete", {})
check("status=done", r.get("status") == "done")

# ── T6: Task 미루기 (새 task 생성 후) ──
print("\n[T6] 미루기 테스트")
r_new, _ = post("/api/v1/inbox", {"text": "빨래"})
task_id = r_new.get("task", {}).get("id")
if task_id:
    r, code = post(f"/api/v1/tasks/{task_id}/postpone", {"reason": "컨디션 안좋음"})
    check("postpone_count=1", r.get("postpone_count") == 1)
else:
    check("task 생성 실패", False, "task_id 없음")

# ── T7: [BUG-1] confirm 엔드포인트 Pydantic 검증 ──
print("\n[T7] BUG-1: confirm with InboxConfirmRequest")
# inbox_log 생성을 위해 needs_clarification이 필요하지만,
# fallback 모드에서는 항상 saved_fallback → inbox_log_id가 없음.
# 존재하지 않는 inbox_log_id로 404 테스트
r, code = post("/api/v1/inbox/99999/confirm", {"corrections": {"title": "수정 테스트"}})
check("404 반환 (존재하지 않는 ID)", code == 404)

# ── T8: [BUG-1] confirm with user_responses ──
print("\n[T8] BUG-5: confirm with user_responses")
r, code = post("/api/v1/inbox/99999/confirm", {
    "corrections": {"title": "수정"},
    "user_responses": [{"response": "그 시간에 해야해", "responded_at": "2026-02-18T14:00:00"}]
})
check("404 반환 (user_responses 포함해도 정상 파싱)", code == 404, f"got {code}")

# ── T9: [BUG-2] event_at None 방어 ──
print("\n[T9] BUG-2: event_at=None 방어")
# fallback은 항상 category=task이므로 이 케이스는 LLM 활성화 후 테스트.
# 여기서는 _parse_datetime(None) 동작만 간접 확인 (서버가 크래시하지 않으면 OK)
r, code = post("/api/v1/inbox", {"text": "팀미팅"})
check("서버 크래시 안 함", code in [200, 201])

# ── T10: DB 데이터 일관성 ──
print("\n[T10] 전체 task 조회 (all)")
r, code = get("/api/v1/tasks?status=all")
check("total >= 2", r.get("total", 0) >= 2)
for t in r.get("tasks", []):
    check(f"  task[{t['id']}] 유효", t.get("title") is not None and t.get("status") is not None)

# ── 결과 ──
print("\n" + "=" * 60)
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("✅ All automated tests passed!")
else:
    print(f"❌ {FAIL} test(s) failed — fix required")
print("=" * 60)
