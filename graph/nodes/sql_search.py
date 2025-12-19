from common_fastapi.shared.db import get_db_connection
from common_fastapi.shared.logger import logger

async def sql_search(state):
    """
    일반 SQL 검색 (requirements 제외)
    jobseeker의 조건과 employer의 jobs 테이블 데이터를 매칭
    """
    logger.info(f"[sql_search] 시작 - condition: {state.condition}")
    
    condition = state.condition
    
    # SQL 쿼리 기본 구조
    query = """
        SELECT 
            id, company, title, location, salary, work_days, start_time, end_time,
            category, gender, age, description, deadline, status
        FROM public.jobs
        WHERE status = 'ACTIVE'
    """
    params = []
    param_count = 0
    
    # 1. gender 조건 (Select Box: 남성, 여성, 무관)
    if condition.get("gender") and condition["gender"] != "무관":
        param_count += 1
        query += f" AND (gender = ${param_count} OR gender = '무관')"
        params.append(condition["gender"])
    
    # 2. age 조건 (Check Box Multi: 전체, 20대, 30대, ...)
    # jobseeker의 age와 jobs의 age 필드 비교
    if condition.get("age"):
        age_value = condition["age"]
        # age가 숫자인 경우 연령대 계산 (예: 25 -> "20대")
        if isinstance(age_value, (int, float)):
            age_range = f"{int(age_value) // 10 * 10}대"
            param_count += 1
            query += f" AND (age = ${param_count} OR age = '무관' OR age IS NULL)"
            params.append(age_range)
        # age가 문자열인 경우 (예: "20대")
        elif isinstance(age_value, str):
            param_count += 1
            query += f" AND (age = ${param_count} OR age = '무관' OR age IS NULL)"
            params.append(age_value)
    
    # 3. place 조건 (Select Box: 서울시 강남구 논현동...)
    # location 필드에 지역명이 포함되어 있는지 확인 (LIKE 검색)
    if condition.get("place"):
        place = condition["place"]
        param_count += 1
        query += f" AND location LIKE ${param_count}"
        params.append(f"%{place}%")
    
    # 4. work_days 조건 (Check Box Multi: 월화수목금토일)
    # jobseeker가 선택한 요일이 jobs의 work_days에 포함되는지 확인
    if condition.get("work_days"):
        work_days = condition["work_days"]
        # work_days가 문자열인 경우 (예: "월,화,수")
        if isinstance(work_days, str):
            days_list = [day.strip() for day in work_days.split(",")]
            # 각 요일이 포함되는지 OR 조건으로 확인
            day_conditions = " OR ".join([f"work_days LIKE ${param_count + i + 1}" for i in range(len(days_list))])
            query += f" AND ({day_conditions})"
            params.extend([f"%{day}%" for day in days_list])
            param_count += len(days_list)
    
    # 5. start_time 조건 (Input Box: hh:mm)
    # jobseeker의 희망 시작 시간이 jobs의 start_time보다 늦거나 같은 경우
    if condition.get("start_time"):
        param_count += 1
        query += f" AND (start_time IS NULL OR start_time <= ${param_count})"
        params.append(condition["start_time"])
    
    # 6. end_time 조건 (Input Box: hh:mm)
    # jobseeker의 희망 종료 시간이 jobs의 end_time보다 빠르거나 같은 경우
    if condition.get("end_time"):
        param_count += 1
        query += f" AND (end_time IS NULL OR end_time >= ${param_count})"
        params.append(condition["end_time"])
    
    # 7. hourly_wage 조건 (Input Box: 10000-99999)
    # jobseeker가 원하는 최소 시급 이상인 jobs 검색
    if condition.get("hourly_wage"):
        wage = condition["hourly_wage"]
        # salary 필드에서 숫자만 추출하여 비교
        param_count += 1
        query += f" AND (CAST(REGEXP_REPLACE(salary, '[^0-9]', '', 'g') AS INTEGER) >= ${param_count})"
        params.append(int(wage))
    
    # 8. category 조건 (Select Box: 업종/카테고리)
    if condition.get("category"):
        param_count += 1
        query += f" AND category = ${param_count}"
        params.append(condition["category"])
    
    # 최신 등록순 정렬, 최대 50개 제한
    query += " ORDER BY created_at DESC LIMIT 50"
    
    try:
        async with get_db_connection() as conn:
            logger.info(f"[sql_search] 실행 쿼리: {query}")
            logger.info(f"[sql_search] 파라미터: {params}")
            
            rows = await conn.fetch(query, *params)
            
            # 결과를 딕셔너리 리스트로 변환
            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "company": row["company"],
                    "title": row["title"],
                    "location": row["location"],
                    "salary": row["salary"],
                    "work_days": row["work_days"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "category": row["category"],
                    "gender": row["gender"],
                    "age": row["age"],
                    "description": row["description"],
                    "deadline": row["deadline"].isoformat() if row["deadline"] else None,
                    "status": row["status"]
                })
            
            logger.info(f"[sql_search] 검색 완료 - {len(results)}개 결과")
            
            # 상태 업데이트
            state.result = results
            
            # 응답 메시지 생성
            if len(results) > 0:
                state.reply = f"조건에 맞는 일자리 {len(results)}개를 찾았습니다."
            else:
                state.reply = "조건에 맞는 일자리를 찾지 못했습니다. 조건을 완화해보시겠어요?"
            
            return state
            
    except Exception as e:
        logger.exception(f"[sql_search] 오류 발생: {e}")
        state.result = []
        state.reply = "일자리 검색 중 오류가 발생했습니다."
        return state
