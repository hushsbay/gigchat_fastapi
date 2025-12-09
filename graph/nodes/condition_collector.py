import json
from typing import Any, Dict
from common_fastapi.ai.llm_openai import LLMClient

llm = LLMClient()

# ✅ 카테고리 목록
CATEGORIES = [
    "기획·전략", "마케팅·홍보·조사", "회계·세무·재무", "인사·노무·HRD", "총무·법무·사무",
    "IT개발·데이터", "디자인", "영업·판매·무역", "고객상담·TM", "구매·자재·물류",
    "상품기획·MD", "운전·운송·배송", "서비스", "생산", "건설·건축", "의료",
    "연구·R&D", "교육", "미디어·문화·스포츠", "금융·보험", "공공·복지"
]

SCHEMA_HINT = f"""
너는 사용자의 문장에서 아르바이트 조건을 추출한다.
반드시 아래 JSON 형태로 출력하라.
불명확한 값은 null로 둔다.
또한 카테고리를 추출할 경우 아래의 21개 중 가장 관련된 하나를 선택해야만 한다.

카테고리 목록:
{', '.join(CATEGORIES)}

JSON 예시:
{{
  "gender": "male|female|any|null",
  "age": null | number,
  "place": "string|null",
  "work_days": "2025-11-12"(ISO 날짜 문자열 배열) | null,
  "start_time": "HH:MM|null",
  "end_time": "HH:MM|null",
  "hourly_wage": null | number,
  "requirements": "string|null",
  "category": "string|null"
}}
"""

def _safe_json_parse(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except Exception:
            return {}

def _normalize(cond: Dict[str, Any]) -> Dict[str, Any]:
    base = {
        "gender": None,
        "age": None,
        "place": None,
        "work_days": None,
        "start_time": None,
        "end_time": None,
        "hourly_wage": None,
        "category": None
    }
    base.update(cond or {})
    return base

def collect_conditions(state):
    user_text = state.text
    messages = [
        {"role": "system", "content": SCHEMA_HINT},
        {"role": "user", "content": user_text}
    ]
    raw = llm.chat(messages) or "{}"
    extracted = _normalize(_safe_json_parse(raw))

    merged = dict(state.condition or {})
    for k, v in extracted.items():
        if v not in (None, "", []):
            merged[k] = v

    state.condition = merged
    state.reply = "조건을 업데이트했습니다."
    return state
