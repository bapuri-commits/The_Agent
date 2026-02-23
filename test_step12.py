"""Step 1.2 테스트 — Inbox + LLM 파싱 (또는 fallback)."""

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
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        return {"error": e.code, "detail": error_body}


print("=" * 60)
print("Step 1.2 — Inbox + LLM Parsing Test")
print("=" * 60)

# Test 1: 자연어 입력
print("\n[1] POST /inbox — '내일 OS과제 제출 2시간 중요'")
r1 = post_json("/api/v1/inbox", {"text": "내일 OS과제 제출 2시간 중요"})
print(f"    action: {r1.get('action', 'N/A')}")
print(f"    message: {r1.get('message', 'N/A')}")
print(f"    confidence: {r1.get('confidence', 'N/A')}")
if r1.get("task"):
    t = r1["task"]
    print(f"    task: [{t['id']}] {t['title']} (est={t['est_minutes']}min, imp={t['importance']})")
if r1.get("parsed_preview"):
    pp = r1["parsed_preview"]
    print(f"    parsed_preview: {pp.get('title')} (category={pp.get('category')})")
if r1.get("clarification"):
    cl = r1["clarification"]
    if cl.get("questions"):
        print(f"    clarification: {cl['questions']}")

# Test 2: 간단한 입력
print("\n[2] POST /inbox — '빨래'")
r2 = post_json("/api/v1/inbox", {"text": "빨래"})
print(f"    action: {r2.get('action', 'N/A')}")
print(f"    confidence: {r2.get('confidence', 'N/A')}")

# Test 3: 애매한 입력
print("\n[3] POST /inbox — '수강신청 미리담기 2/20 9시'")
r3 = post_json("/api/v1/inbox", {"text": "수강신청 미리담기 2/20 9시"})
print(f"    action: {r3.get('action', 'N/A')}")
print(f"    confidence: {r3.get('confidence', 'N/A')}")
if r3.get("clarification", {}).get("questions"):
    print(f"    questions: {r3['clarification']['questions']}")

# Test 4: 빈 입력
print("\n[4] POST /inbox — '' (빈 텍스트)")
r4 = post_json("/api/v1/inbox", {"text": ""})
print(f"    result: {r4}")

print("\n" + "=" * 60)
print("Test Complete!")
if r1.get("action") == "saved_fallback":
    print("⚠️  LLM 크레딧 미충전 — fallback 모드로 동작 중")
    print("    크레딧 충전 후 재테스트 필요")
else:
    print("✅  LLM 파싱 정상 동작")
print("=" * 60)
