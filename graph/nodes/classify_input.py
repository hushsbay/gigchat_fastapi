from common_fastapi.ai.llm_openai import LLMClient

llm = LLMClient()

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
"""

def classify_input(state):
    text = state.text
    
    # Next.js와 동일한 프롬프트 사용
    prompt = f"""다음 사용자 입력이 아르바이트/일자리와 관련된 내용인지 판단해주세요.
"예" 또는 "아니오"로만 답변하세요.

만일, 아르바이트/일자리와 관련된 내용이 아니더라도 아래 조건에 들어갈 수 있는 유사 단어나 문구가 있으면 "예"로 답변하세요.

{JOB_CONDITION_SCHEMA}

{JOB_CONDITION_RULES}

사용자 입력: "{text}" """
    
    messages = [
        {"role": "user", "content": prompt}
    ]
    res = llm.chat(messages)
    
    state.job_related = "예" in res
    
    if not state.job_related:
        state.response = "죄송합니다. 저는 일자리 검색과 관련된 질문에만 답변할 수 있습니다."
    
    print(f"[classify_input] LLM response: '{res}', job_related={state.job_related}")
    return state
