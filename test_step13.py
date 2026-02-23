"""Step 1.3 — Priority Engine 테스트."""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request, json

BASE = "http://localhost:8000"
PASS = FAIL = 0

def post(path, data=None):
    body = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=body,
        headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
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
        PASS += 1; print(f"  ✅ {name}")
    else:
        FAIL += 1; print(f"  ❌ {name} — {detail}")

print("=" * 60)
print("Step 1.3 — Priority Engine Tests")
print("=" * 60)

# ── 준비: task 여러 개 생성 ──
print("\n[Setup] Creating test tasks...")
# 이미 DB에 이전 테스트 데이터가 있을 수 있으므로, 새로 3개 추가
t1, _ = post("/api/v1/inbox", {"text": "긴급 과제 제출"})  # 기본 importance=3
t2, _ = post("/api/v1/inbox", {"text": "빨래"})             # 간단한 task
t3, _ = post("/api/v1/inbox", {"text": "장기 프로젝트"})     # 기본

# 하나는 postpone 2번
t2_id = t2.get("task", {}).get("id")
if t2_id:
    post(f"/api/v1/tasks/{t2_id}/postpone", {"reason": "test1"})
    post(f"/api/v1/tasks/{t2_id}/postpone", {"reason": "test2"})

# ── T1: GET /tasks에 priority_score 존재 ──
print("\n[T1] priority_score 반환 확인")
r, code = get("/api/v1/tasks?status=pending")
check("200 응답", code == 200)
tasks = r.get("tasks", [])
check("task 존재", len(tasks) >= 2)
if tasks:
    first = tasks[0]
    check("priority_score 필드 존재", first.get("priority_score") is not None, f"got {first.get('priority_score')}")
    check("priority_score > 0", (first.get("priority_score") or 0) > 0)

# ── T2: 내림차순 정렬 확인 ──
print("\n[T2] priority_score 내림차순 정렬")
scores = [t.get("priority_score", 0) for t in tasks if t.get("priority_score") is not None]
if len(scores) >= 2:
    is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    check("내림차순 정렬됨", is_sorted, f"scores={scores}")
else:
    check("정렬 확인 (데이터 부족)", False, f"scores={scores}")

# ── T3: postpone가 점수에 반영되는지 ──
print("\n[T3] postpone_count 반영 확인")
if t2_id:
    postponed = [t for t in tasks if t["id"] == t2_id]
    if postponed:
        check("postpone 2회 반영", postponed[0]["postpone_count"] == 2)
        # postpone된 task의 점수가 0보다 높아야 함
        check("postpone → 점수 > 0", (postponed[0].get("priority_score") or 0) > 0)

# ── T4: 결정론성 확인 (같은 요청 2번 → 같은 결과) ──
print("\n[T4] 결정론성 (같은 요청 2번)")
r1, _ = get("/api/v1/tasks?status=pending")
r2, _ = get("/api/v1/tasks?status=pending")
scores1 = [(t["id"], t.get("priority_score")) for t in r1["tasks"]]
scores2 = [(t["id"], t.get("priority_score")) for t in r2["tasks"]]
check("동일한 결과", scores1 == scores2, f"\n    1st: {scores1}\n    2nd: {scores2}")

# ── T5: done/cancelled task에는 priority_score 안 달림 ──
print("\n[T5] done task에 priority_score=null")
r_all, _ = get("/api/v1/tasks?status=all")
done_tasks = [t for t in r_all["tasks"] if t["status"] == "done"]
if done_tasks:
    check("done task → priority_score=null", done_tasks[0].get("priority_score") is None)
else:
    print("  (done task 없음, 스킵)")

# ── 결과 ──
print("\n" + "=" * 60)
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("✅ All Priority Engine tests passed!")
else:
    print(f"❌ {FAIL} test(s) failed")
print("=" * 60)
