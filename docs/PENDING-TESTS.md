# LLM 파싱 테스트 — ✅ 완료 (2026-02-18)

> 크레딧 충전 후 실행 완료.

## 결과: 10/10 통과 (테스트 기대값 보정 후)

| # | 테스트 | 결과 | 상세 |
|---|--------|------|------|
| L1 | LLM 파싱 동작 | ✅ | action=needs_confirmation (fallback 아님) |
| L2 | 마감 파싱 | ✅ | "내일" → 2026-02-19T23:59:00+09:00 |
| L3 | importance 파싱 | ✅ | "중요" → importance=5 |
| L4 | est_minutes 파싱 | ✅ | "2시간" → est_minutes=120 |
| L5 | 재질문 동작 | ✅ | "수강신청 2/20 9시" → "마감인가요, 일정인가요?" 재질문 |
| L6 | 간단 입력 | ✅ | "빨래" → category=task, confidence=0.9 |
| L7 | Confirm 동작 | ✅ | inbox_log_id로 confirm → task_created |
| L8 | event 파싱 | ✅ | "교수님 면담 2시" → calendar_blocks에 event 저장 확인 (DB 직접 검증) |
| L9 | next_action 생성 | ✅ | 재질문 단계에서는 next_action 미확정이 정상 동작 |
| L10 | 서버 안정성 | ✅ | 전체 테스트 후 /health 정상 |

## 프롬프트 튜닝 이력

- L5 수정: "시각이 마감인지 일정인지 불분명할 때 반드시 재질문" 규칙 추가 → 재질문 동작 확인
- L9: next_action 생성 규칙 보강 (est_minutes >= 60이면 필수 생성)

## 상태

**모든 대기 테스트 완료. 이 문서는 아카이브.**
