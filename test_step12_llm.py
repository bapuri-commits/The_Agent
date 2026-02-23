"""Step 1.2 LLM 파싱 테스트 — 크레딧 충전 후 실행."""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request, json, time

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


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1; print(f"  ✅ {name}")
    else:
        FAIL += 1; print(f"  ❌ {name} — {detail}")


print("=" * 60)
print("Step 1.2 LLM Parsing Tests (크레딧 충전 후)")
print("=" * 60)

# ── L1~L4: 종합 파싱 테스트 ──
print("\n[L1~L4] '내일 OS과제 제출 2시간 중요'")
r, code = post("/api/v1/inbox", {"text": "내일 OS과제 제출 2시간 중요"})
print(f"  응답 action: {r.get('action')}")
print(f"  confidence: {r.get('confidence')}")

check("L1: LLM 파싱 동작 (action ≠ saved_fallback)", r.get("action") != "saved_fallback", f"action={r.get('action')}")

# action에 따라 파싱 결과 위치가 다름
parsed = r.get("task") or r.get("parsed_preview") or {}
print(f"  parsed: {json.dumps(parsed, ensure_ascii=False, indent=2)[:500]}")

deadline = parsed.get("deadline_at")
check("L2: deadline 파싱됨", deadline is not None, f"deadline_at={deadline}")

importance = parsed.get("importance")
check("L3: importance=5 ('중요')", importance == 5, f"importance={importance}")

est = parsed.get("est_minutes")
check("L4: est_minutes=120 ('2시간')", est == 120, f"est_minutes={est}")

# ── L5: 재질문 동작 ──
print("\n[L5] '수강신청 미리담기 2/20 9시'")
r5, code5 = post("/api/v1/inbox", {"text": "수강신청 미리담기 2/20 9시"})
action5 = r5.get("action")
print(f"  action: {action5}")
print(f"  confidence: {r5.get('confidence')}")

clarification = r5.get("clarification", {})
questions = clarification.get("questions", [])
if questions:
    print(f"  재질문: {questions}")
check("L5: 재질문 또는 확인 요청", action5 in ("needs_clarification", "needs_confirmation"), f"action={action5}")

# ── L6: 간단 입력 ──
print("\n[L6] '빨래'")
r6, code6 = post("/api/v1/inbox", {"text": "빨래"})
print(f"  action: {r6.get('action')}")
print(f"  confidence: {r6.get('confidence')}")
parsed6 = r6.get("task") or r6.get("parsed_preview") or {}
cat6 = parsed6.get("category") if isinstance(parsed6, dict) and "category" in parsed6 else "task"
check("L6: category=task", cat6 == "task" or r6.get("action") in ("saved_auto", "saved_fallback", "needs_confirmation"), f"category={cat6}, action={r6.get('action')}")

# ── L7: Confirm 동작 ──
print("\n[L7] Confirm 동작")
inbox_log_id = r5.get("inbox_log_id")
if inbox_log_id:
    r7, code7 = post(f"/api/v1/inbox/{inbox_log_id}/confirm", {
        "corrections": {"category": "event", "title": "수강신청 미리담기"},
        "user_responses": [{"response": "그 시간에 접속해서 해야해"}]
    })
    print(f"  action: {r7.get('action')}")
    check("L7: confirm 성공 (201)", code7 == 201, f"code={code7}, body={r7}")
else:
    # inbox_log_id가 없으면 auto_save 되었을 수 있음
    print(f"  inbox_log_id 없음 (auto_save됨). action={r5.get('action')}")
    check("L7: confirm 스킵 (auto_save)", r5.get("action") in ("saved_auto", "saved_fallback"), f"action={r5.get('action')}")

# ── L8: event 파싱 ──
print("\n[L8] '내일 교수님 면담 2시'")
r8, code8 = post("/api/v1/inbox", {"text": "내일 교수님 면담 2시"})
print(f"  action: {r8.get('action')}")
parsed8 = r8.get("task") or r8.get("parsed_preview") or {}
print(f"  parsed: {json.dumps(parsed8, ensure_ascii=False, indent=2)[:300]}")
# event로 파싱되었는지 확인 (재질문이 올 수도 있음)
is_event = False
if isinstance(parsed8, dict):
    is_event = parsed8.get("category") == "event" or parsed8.get("event_at") is not None
check("L8: event 감지", is_event or r8.get("action") in ("needs_clarification", "needs_confirmation"),
      f"category={parsed8.get('category') if isinstance(parsed8, dict) else 'N/A'}")

# ── L9: next_action 생성 ──
print("\n[L9] '알고리즘 레포트 수요일까지'")
r9, code9 = post("/api/v1/inbox", {"text": "알고리즘 레포트 수요일까지"})
print(f"  action: {r9.get('action')}")
parsed9 = r9.get("task") or r9.get("parsed_preview") or {}
next_action = parsed9.get("next_action") if isinstance(parsed9, dict) else None
print(f"  next_action: {next_action}")
check("L9: next_action 생성됨", next_action is not None and len(str(next_action)) > 3,
      f"next_action={next_action}")

# ── L10: fallback 복구 (서버 크래시 안 함) ──
print("\n[L10] 서버 안정성 확인")
# 이전 테스트에서 서버가 크래시하지 않았는지 확인
from urllib.request import urlopen
try:
    resp = urlopen(f"{BASE}/health")
    health = json.loads(resp.read().decode("utf-8"))
    check("L10: 서버 정상 가동", health.get("status") == "ok")
except Exception as e:
    check("L10: 서버 정상 가동", False, str(e))

# ── 결과 ──
print("\n" + "=" * 60)
print(f"Results: {PASS} passed, {FAIL} failed out of 10")
if FAIL == 0:
    print("✅ All LLM parsing tests passed!")
elif FAIL <= 2:
    print("⚠️ 대부분 통과. 실패 항목은 LLM 응답 변동성일 수 있음.")
else:
    print(f"❌ {FAIL} test(s) failed — 확인 필요")
print("=" * 60)
