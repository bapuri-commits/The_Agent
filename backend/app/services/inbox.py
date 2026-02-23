"""
The Agent — Inbox Service
자연어 입력 → M1 Worker(gpt-4o-mini)로 구조화 → DB 저장.
재질문 로직, fallback, 학습 데이터 수집 포함.
"""

import json
import time
from datetime import datetime, timezone
from typing import Optional

from app.config import get_settings
from app.services.llm import get_llm_router, ModelRole

settings = get_settings()

# ─── M1 시스템 프롬프트 ────────────────────────────────────

WORKER_SYSTEM_PROMPT = """너는 입력 처리기다. 판단하지 마라.

## 역할
사용자의 자연어 입력을 구조화된 JSON으로 변환한다.
추측하지 마라. 명시되지 않은 정보는 null로 둬라.

## 사용자 정보
{user_context}

## 현재 시각
{current_time}

## 출력 규칙

1. 아래 JSON 형식으로만 답변하라. 다른 텍스트 없이 JSON만.
2. category:
   - "task": 해야 할 일 (과제 제출, 빨래, 공부 등)
   - "event": 특정 시각에 참석/접속해야 하는 일정 (수업, 회의, 면담 등)
   - "reminder": 단순 리마인더 (약 먹기, 전화하기 등)
   - "note": 기록만 (메모, 생각, 아이디어)
3. deadline_at: task의 마감 시각. ISO 8601 형식 (KST +09:00). 없으면 null.
4. event_at: event의 시작 시각. ISO 8601 형식. event가 아니면 null.
5. est_minutes: 예상 소요 시간(분). 명시 안 되면 null.
6. energy: 예상 에너지 소모 (1~5). 명확하면 채우고, 아니면 null.
7. importance: 중요도 (1~5). "중요"=5, "급한"=5. 명시 안 되면 null.
8. next_action: 가장 먼저 해야 할 구체적 행동 1개. 단순한 일은 null.
9. tags: 관련 태그 배열. ["학교"], ["개인"], ["프로젝트"] 등.
10. confidence: 0.0~1.0. 파싱 확신도.
11. parse_status: "complete" (확실) 또는 "needs_clarification" (재질문 필요).
12. clarification: 재질문이 필요하면 질문 목록과 애매한 필드명.

## 중요
- 상대 날짜("내일", "수요일", "이번주 금요일")는 현재 시각 기준으로 절대 날짜로 변환.
- "중요"라고 했으면 importance=5. 안 했으면 null.
- "2시간" → est_minutes=120.
- 한 단어 입력("빨래")도 처리 가능해야 함. 간단한 건 confidence 높게.
- 애매한 입력은 confidence 낮게 + parse_status="needs_clarification".

## 재질문이 필요한 경우 (반드시 needs_clarification 반환)
- 시각이 마감인지 일정 시작인지 불분명할 때 (예: "2/20 9시" → 마감? 그 시간에 해야 하는 일정?)
- category가 task인지 event인지 불분명할 때
- 이런 경우 절대 자동 저장하지 말고, 반드시 parse_status="needs_clarification" + 질문을 반환하라.

## next_action 생성 규칙
- 복잡한 task (est_minutes >= 60 또는 여러 단계가 필요한 작업)에는 반드시 next_action을 생성하라.
- next_action은 "가장 먼저 해야 할 구체적인 행동 1개"여야 한다. 
- 예: "알고리즘 레포트" → "레포트 주제 선정 및 목차 작성"
- 간단한 작업 ("빨래", "약 먹기")은 next_action=null.

## JSON 형식
```json
{{
  "parse_status": "complete | needs_clarification",
  "parsed": {{
    "category": "task | event | reminder | note",
    "title": "string",
    "deadline_at": "ISO8601 | null",
    "event_at": "ISO8601 | null",
    "est_minutes": "int | null",
    "energy": "int 1-5 | null",
    "importance": "int 1-5 | null",
    "next_action": "string | null",
    "tags": ["string"],
    "context_hint": "string (내부 메모, 사용자에게 비노출)"
  }},
  "confidence": 0.0-1.0,
  "clarification": {{
    "questions": ["string"],
    "ambiguous_fields": ["string"]
  }}
}}
```"""

# ─── 기본값 채우기 ─────────────────────────────────────────

DEFAULT_VALUES = {
    "est_minutes": 60,
    "energy": 3,
    "importance": 3,
}


def _fill_defaults(parsed: dict) -> tuple[dict, list[str]]:
    """null인 필드에 기본값 채움. 자동 채워진 필드 목록 반환."""
    auto_filled = []
    for field, default in DEFAULT_VALUES.items():
        if parsed.get(field) is None:
            parsed[field] = default
            auto_filled.append(field)
    return parsed, auto_filled


# ─── 현재 시각 포맷 ────────────────────────────────────────

WEEKDAYS_KR = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def _get_current_time_str() -> str:
    """현재 시각을 KST 문자열로."""
    from datetime import timedelta
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    weekday = WEEKDAYS_KR[now.weekday()]
    return f"{now.strftime('%Y-%m-%d')} {weekday} {now.strftime('%H:%M')} KST"


def _get_time_metadata() -> dict:
    """입력 시점 메타데이터."""
    from datetime import timedelta
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    return {
        "input_hour": now.hour,
        "input_day_of_week": now.weekday(),
    }


# ─── User Context 로드 ────────────────────────────────────

def _load_user_context() -> str:
    """Layer 1 (USER_PROFILE.md)에서 사용자 컨텍스트 로드."""
    import os
    context_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "context", "USER_PROFILE.md"
    )
    try:
        with open(context_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "사용자 프로필 없음. 기본값 사용."


# ─── 메인 파싱 함수 ────────────────────────────────────────

async def parse_inbox(text: str) -> dict:
    """
    자연어 텍스트를 구조화된 데이터로 변환.
    
    Returns:
        {
            "parse_result": {...},   # M1 파싱 결과 전체
            "final_parsed": {...},   # 기본값 채워진 최종 결과
            "auto_filled": [...],    # 자동 채워진 필드
            "confidence": float,
            "parse_status": str,
            "clarification": {...},  # 재질문 정보 (있으면)
            "latency_ms": int,
            "time_metadata": {...},  # input_hour, input_day_of_week
        }
    """
    router = get_llm_router()
    
    # 시스템 프롬프트 조립
    user_context = _load_user_context()
    current_time = _get_current_time_str()
    system_prompt = WORKER_SYSTEM_PROMPT.format(
        user_context=user_context,
        current_time=current_time,
    )
    
    time_meta = _get_time_metadata()
    
    # M1 Worker 호출
    start = time.time()
    try:
        raw_response = await router.call(
            role=ModelRole.WORKER,
            system_prompt=system_prompt,
            user_message=text,
            max_tokens=800,
        )
        latency_ms = int((time.time() - start) * 1000)
        
        # JSON 파싱
        parse_result = _extract_json(raw_response)
        
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        # Fallback: LLM 실패 시 원문 그대로
        return _fallback_result(text, str(e), latency_ms, time_meta)
    
    if parse_result is None:
        return _fallback_result(text, "JSON 파싱 실패", latency_ms, time_meta)
    
    # 기본값 채우기
    parsed = parse_result.get("parsed", {})
    parsed, auto_filled = _fill_defaults(parsed)
    
    confidence = parse_result.get("confidence", 0.5)
    parse_status = parse_result.get("parse_status", "complete")
    clarification = parse_result.get("clarification", {"questions": [], "ambiguous_fields": []})
    
    return {
        "parse_result": parse_result,
        "final_parsed": parsed,
        "auto_filled": auto_filled,
        "confidence": confidence,
        "parse_status": parse_status,
        "clarification": clarification,
        "latency_ms": latency_ms,
        "time_metadata": time_meta,
    }


def _extract_json(text: str) -> Optional[dict]:
    """LLM 응답에서 JSON 추출. 마크다운 코드블록도 처리."""
    text = text.strip()
    
    # ```json ... ``` 블록 추출
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _fallback_result(text: str, error: str, latency_ms: int, time_meta: dict) -> dict:
    """LLM 실패 시 fallback."""
    parsed = {
        "category": "task",
        "title": text,
        "deadline_at": None,
        "event_at": None,
        "est_minutes": None,
        "energy": None,
        "importance": None,
        "next_action": None,
        "tags": [],
        "context_hint": f"LLM fallback: {error}",
    }
    parsed, auto_filled = _fill_defaults(parsed)
    
    return {
        "parse_result": {"error": error, "parsed": parsed},
        "final_parsed": parsed,
        "auto_filled": auto_filled,
        "confidence": 0.0,
        "parse_status": "fallback",
        "clarification": {"questions": [], "ambiguous_fields": []},
        "latency_ms": latency_ms,
        "time_metadata": time_meta,
    }
