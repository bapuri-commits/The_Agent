"""Quick API test for Step 1.1 verification."""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request
import json

BASE = "http://localhost:8000"


def post_json(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode("utf-8"))


def get_json(path):
    req = urllib.request.Request(f"{BASE}{path}")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode("utf-8"))


print("=" * 50)
print("The Agent — Step 1.1 API Test")
print("=" * 50)

# 1. Health check
health = get_json("/health")
print(f"\n[1] Health: {health['status']} (v{health['version']})")

# 2. Create task via inbox
print("\n[2] POST /inbox — 'OS과제 제출 2시간 중요'")
inbox_result = post_json("/api/v1/inbox", {"text": "내일 OS과제 제출 2시간 중요"})
task = inbox_result["task"]
print(f"    Task ID: {task['id']}")
print(f"    Title: {task['title']}")
print(f"    Status: {task['status']}")
print(f"    Est: {task['est_minutes']}min, Energy: {task['energy']}, Importance: {task['importance']}")
print(f"    Auto-filled: {inbox_result['auto_filled']}")

# 3. Create another task
print("\n[3] POST /inbox — '빨래'")
inbox2 = post_json("/api/v1/inbox", {"text": "빨래"})
print(f"    Task ID: {inbox2['task']['id']}, Title: {inbox2['task']['title']}")

# 4. List tasks
print("\n[4] GET /tasks")
tasks = get_json("/api/v1/tasks")
for t in tasks["tasks"]:
    print(f"    [{t['id']}] {t['title']} (status={t['status']})")
print(f"    Total: {tasks['total']}")

# 5. Complete task
print(f"\n[5] POST /tasks/{task['id']}/complete")
complete = post_json(f"/api/v1/tasks/{task['id']}/complete", {})
print(f"    Status: {complete['status']}")

# 6. Postpone task
print(f"\n[6] POST /tasks/{inbox2['task']['id']}/postpone")
postpone = post_json(f"/api/v1/tasks/{inbox2['task']['id']}/postpone", {"reason": "컨디션 안 좋음"})
print(f"    Postpone count: {postpone['postpone_count']}")

# 7. Final task list (all)
print("\n[7] GET /tasks?status=all")
all_tasks = get_json("/api/v1/tasks?status=all")
for t in all_tasks["tasks"]:
    print(f"    [{t['id']}] {t['title']} — {t['status']} (postpone: {t['postpone_count']})")

print("\n" + "=" * 50)
print("✅ Step 1.1 — All tests passed!")
print("=" * 50)
