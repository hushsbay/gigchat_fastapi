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

# Next.js와 동일한 스키마 및 규칙
JOB_CONDITION_SCHEMA = """{
  "gender": "남자" | "여자" | "남성" | "여성" | null,
  "age": 숫자 | "30대" | "30대 초반" | "30대 중반" | "30대 후반" | "40대" | "40대 초반" | "40대 중반" | "40대 후반" | "50대" | "50대 초반" | "50대 중반" | "50대 후반" | null,
  "place": "지역명" | null,
  "work_days": "월" | "화" | "수" | "목" | "금" | "토" | "일" | "월화수목금" | "토일" | null,
  "start_time": "HH:MM" | null,
  "end_time": "HH:MM" | null,
  "hourly_wage": "숫자" | "숫자 이상" | "숫자 이하" | "숫자 초과" | "숫자 미만" | null,
  "requirements": "기타 요구사항" | null,
  "category": "업종분류(카테고리)" | null
}"""

JOB_CONDITION_RULES = """중요 규칙:
1. 나이(age): 숫자 또는 문자로 표현 가능
   예시:
   - 사용자: "30세" → 30 (숫자만)
   - 사용자: "30대" → "30대" (문자 그대로)
   - 사용자: "30대 초반" → "30대 초반" (문자 그대로)
   - 사용자: "30대 중반" → "30대 중반" (문자 그대로)
   - 사용자: "30대 후반" → "30대 후반" (문자 그대로)
   - 사용자: "40대 초반 남성" → age: "40대 초반", gender: "남성"
   ⚠️ 주의: "30대 초반", "40대 중반" 등 문자로 표현할 때는 숫자만 추출하지 말고 전체 문자열 그대로 사용
2. 근무일(work_days)은 요일 여러 개를 지정할 수 있음 (예: 월화수)
   - 주중은 월화수목금, 주말은 토일을 의미함. 
3. 시급(hourly_wage)은 반드시 다음 형식 중 하나로 표현:
   - "숫자" (정확한 금액, 예: "20000")
   - "숫자 이상" (최소 금액, 예: "20000 이상")
   - "숫자 이하" (최대 금액, 예: "20000 이하")
   - "숫자 초과" (초과 금액, 예: "20000 초과")
   - "숫자 미만" (미만 금액, 예: "20000 미만")
   ⚠️ 주의: 숫자와 조건 사이에 "원"을 넣지 마세요!
   예시:
   - 사용자: "시급 2만원 이상" → "20000 이상" (O) / "20000원 이상" (X)
   - 사용자: "시급 15000원 넘는" → "15000 초과" (O) / "15000원 초과" (X)
   - 사용자: "시급 최소 18000원" → "18000 이상" (O)
   - 사용자: "시급 12000원 정도" → "12000" (O)
   - 사용자: "시급 25000원 안넘는" → "25000 이하" (O)
4. 카테고리(category)는 반드시 다음 21개 중 하나를 선택:
   {categories_list}
"""

def _safe_json_parse(text: str) -> Dict[str, Any]:
    """JSON 파싱 실패 시 빈 딕셔너리 반환"""
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
    """조건 정규화 - 모든 키가 존재하도록 보장"""
    base = {
        "gender": None,
        "age": None,
        "place": None,
        "work_days": None,
        "start_time": None,
        "end_time": None,
        "hourly_wage": None,
        "requirements": None,
        "category": None
    }
    base.update(cond or {})
    return base

def classify_input(state):
    """
    LLM 한 번 호출로 두 가지 작업 수행:
    1. 일자리 관련 여부 판단
    2. 관련되어 있으면 조건 추출
    """
    text = state.text
    
    # ✅ 통합 프롬프트: 일자리 관련 판단 + 조건 추출
    prompt = f"""당신은 일자리 챗봇입니다. 다음 작업을 수행하세요:

**1단계**: 사용자 입력이 아르바이트/일자리와 관련된 내용인지 판단
**2단계**: 관련되어 있다면, 입력에서 일자리 조건을 추출

### 조건 스키마
{JOB_CONDITION_SCHEMA}

### 중요 규칙
{JOB_CONDITION_RULES.replace('{categories_list}', ', '.join(CATEGORIES))}

### 응답 형식 (반드시 이 JSON 형식으로만 응답)
{{
  "job_related": true | false,
  "condition": {{
    "gender": null,
    "age": null,
    "place": null,
    "work_days": null,
    "start_time": null,
    "end_time": null,
    "hourly_wage": null,
    "requirements": null,
    "category": null
  }}
}}

### 예시
**입력**: "강남에서 주말 알바 구해요, 시급 2만원 이상"
**응답**:
{{
  "job_related": true,
  "condition": {{
    "place": "강남",
    "work_days": "토일",
    "hourly_wage": "20000 이상"
  }}
}}

**입력**: "오늘 날씨 어때?"
**응답**:
{{
  "job_related": false,
  "condition": {{}}
}}

---
사용자 입력: "{text}"
"""
    
    messages = [{"role": "user", "content": prompt}]
    raw_response = llm.chat(messages)
    
    print(f"[classify_input] LLM raw response: {raw_response}")
    
    # JSON 파싱
    parsed = _safe_json_parse(raw_response)
    
    # 일자리 관련 여부
    state.job_related = parsed.get("job_related", False)
    
    if not state.job_related:
        state.reply = "죄송합니다. 저는 일자리 검색과 관련된 질문에만 답변할 수 있습니다."
        print(f"[classify_input] Not job-related")
        return state
    
    # ✅ 조건 추출 및 병합
    extracted = _normalize(parsed.get("condition", {}))
    merged = dict(state.condition or {})
    
    for k, v in extracted.items():
        if v not in (None, "", []):
            merged[k] = v
    
    state.condition = merged
    state.reply = "조건을 업데이트했습니다."
    
    print(f"[classify_input] Job-related=True, extracted: {extracted}")
    print(f"[classify_input] Merged condition: {merged}")
    
    return state
