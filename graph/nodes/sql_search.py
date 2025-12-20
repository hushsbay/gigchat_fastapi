from common_fastapi.shared.db import get_db_connection
from common_fastapi.shared.logger import logger
import re  # 정규식 처리를 위한 Python 표준 라이브러리

async def sql_search(state):
    """
    일반 SQL 검색 (requirements 제외)
    jobseeker의 조건과 employer의 jobs 테이블 데이터를 매칭
    """
    logger.info(f"[sql_search] 시작 - condition: {state.condition}")
    
    condition = state.condition
    
    # start_time과 end_time 검증: 둘 중 하나만 있으면 에러
    has_start = condition.get("start_time") not in (None, "")
    has_end = condition.get("end_time") not in (None, "")
    
    if has_start != has_end:  # XOR: 둘 중 하나만 있으면
        error_msg = "근무 시작시각과 종료시각은 둘 다 입력하거나 둘 다 비워야 합니다."
        logger.error(f"[sql_search] {error_msg}")
        state.result = []
        state.reply = error_msg
        return state
    
    # SQL 쿼리 기본 구조
    query = """
        SELECT id, company, title, location, hourly_wage, work_days, start_time, end_time,
               category, gender, age, description, deadline, status
          FROM public.jobs1
         WHERE status = 'ACTIVE'
    """
    params = []
    param_count = 0
    
    # 1. gender 조건: 남성인 경우 gender in ('무관', '남성')
    # 알바가 내거는 조건에는 무관 없이 남성/여성만 받음
    if condition.get("gender"):
        param_count += 1
        query += f" AND gender IN ('무관', ${param_count})"
        params.append(condition["gender"])
    
    # 2. age 조건: varchar 배열 필드에서 '20대' 같은 값 찾기
    # condition.get("age"): age 키가 없으면 None 반환 (예외 발생 안함)
    # condition["age"]: age 키가 없으면 KeyError 발생 (예외 발생)
    if condition.get("age"):
        age_value = condition["age"]  # 이미 get()으로 확인했으므로 ["age"] 사용 가능
        
        # age가 숫자인 경우 연령대 계산 (예: 25 -> "20대", 32 -> "30대")
        if isinstance(age_value, (int, float)):
            age_range = f"{int(age_value) // 10 * 10}대"
        # age가 문자열인 경우 (예: "20대", "30대")
        elif isinstance(age_value, str):
            age_range = age_value  # 그대로 사용 (10배수 + '대' 형식이어야 함)
        else:
            age_range = str(age_value)  # 기타 타입은 문자열로 변환
        
        param_count += 1
        query += f" AND ${param_count}::varchar = ANY(age)"
        params.append(age_range)
    
    # 3. place 조건: 시/군까지만 매칭 (제주도는 제주도까지만)
    # 특별시/광역시/특별자치시/특별자치도 등의 정규화 처리
    # 예) "경기도 수원시 권선구 팔달동" -> "경기도 수원시"까지만 추출하여 매칭
    if condition.get("place"):
        place = condition["place"]
        
        # 행정구역 명칭 정규화 함수
        def normalize_region(region_name):
            """
            특별시/광역시/특별자치시/특별자치도 등을 간소화
            예) 서울특별시 -> 서울시, 광주광역시 -> 광주시
            예) 제주특별자치도 -> 제주도, 세종특별자치시 -> 세종시
            """
            # 특별자치도 -> 도 (제주특별자치도, 강원특별자치도, 전북특별자치도)
            region_name = region_name.replace("특별자치도", "도")
            # 특별자치시 -> 시 (세종특별자치시)
            region_name = region_name.replace("특별자치시", "시")
            # 특별시 -> 시 (서울특별시)
            region_name = region_name.replace("특별시", "시")
            # 광역시 -> 시 (부산, 인천, 대구, 대전, 광주, 울산)
            region_name = region_name.replace("광역시", "시")
            return region_name
        
        # 입력값 정규화
        place = normalize_region(place)
        
        # 제주도는 "제주"만 추출, 그 외는 시/군까지 추출
        if place.startswith("제주"):
            # 제주도/제주시/제주 등 모두 "제주"로 통일
            region_pattern = "제주"
        else:
            # re는 Python 표준 라이브러리 (regular expression, 정규표현식)
            # r'^(.+[시군도])(?:\s|$)' 의미:
            #   ^ : 문자열의 시작
            #   (.+[시군도]) : 1개 이상의 문자 + '시' 또는 '군' 또는 '도'로 끝남 (greedy)
            #   (?:\s|$) : 공백 또는 문자열 끝 (캡처하지 않음)
            # 예) "경기도 수원시 권선구" -> "경기도 수원시" 추출
            # 예) "경상북도 군위군 군위읍" -> "경상북도 군위군" 추출 (군위읍은 제외)
            # 예) "서울시" -> "서울시" 추출 (서울특별시에서 정규화됨)
            # 예) "강원도" -> "강원도" 추출 (강원특별자치도에서 정규화됨)
            match = re.match(r'^(.+[시군도])(?:\s|$)', place)
            if match:
                region_pattern = match.group(1)  # 첫 번째 그룹 추출
            else:
                region_pattern = place  # 매칭 실패 시 전체 사용
        
        param_count += 1
        # location 필드도 같은 방식으로 정규화하여 매칭
        # REGEXP_REPLACE를 사용하여 location 필드의 특별/광역 등을 제거한 후 비교
        # 예) region_pattern이 "서울시"면
        #     location이 "서울특별시 XXX" 또는 "서울시 XXX" 모두 매칭
        query += f"""
            AND REGEXP_REPLACE(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(location, '특별자치도', '도', 'g'),
                        '특별자치시', '시', 'g'),
                    '특별시', '시', 'g'),
                '광역시', '시', 'g'
            ) LIKE ${param_count} || '%'
        """
        params.append(region_pattern)
    
    # 4. work_days 조건: varchar 배열 필드에서 월, 화 등 포함 여부
    if condition.get("work_days"):
        work_days = condition["work_days"]
        # work_days가 문자열인 경우 (예: "월화" 또는 "월,화")
        if isinstance(work_days, str):
            # 쉼표로 구분된 경우와 그냥 붙어있는 경우 모두 처리
            if "," in work_days:
                days_list = [day.strip() for day in work_days.split(",")]
            else:
                # "월화수"를 ['월', '화', '수']로 분리
                days_list = [work_days[i:i+1] for i in range(0, len(work_days), 1)]
            
            # work_days 필드가 varchar[] 타입이므로 && 연산자 사용
            param_count += 1
            query += f" AND work_days && ${param_count}::varchar[]"
            params.append(days_list)
    
    # 5-6. start_time, end_time 조건: 전후 1시간 범위
    if has_start and has_end:
        start_time = condition["start_time"]
        end_time = condition["end_time"]
        
        param_count += 1
        start_param = param_count
        param_count += 1
        end_param = param_count
        
        query += f"""
            AND start_time::time BETWEEN (${start_param}::text::time - interval '1 hour')
                                     AND (${start_param}::text::time + interval '1 hour')
            AND end_time::time BETWEEN (${end_param}::text::time - interval '1 hour')
                                   AND (${end_param}::text::time + interval '1 hour')
        """
        params.append(start_time)
        params.append(end_time)
    
    # 7. hourly_wage 조건: 최소 시급 이상
    # hourly_wage는 int4 타입으로 salary 필드 대신 사용
    if condition.get("hourly_wage"):
        wage = condition["hourly_wage"]
        # wage가 문자열인 경우 숫자만 추출
        if isinstance(wage, str):
            wage = int(''.join(filter(str.isdigit, wage)))
        
        param_count += 1
        query += f" AND hourly_wage >= ${param_count}"
        params.append(int(wage))
    
    # 8. category 조건
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
            
            # 파라미터가 치환된 실제 SQL문 생성 (테스트용)
            actual_query = query
            for i, param in enumerate(params, 1):
                # 문자열이면 작은따옴표로 감싸고, 숫자는 그대로, 리스트는 ARRAY[] 형식으로
                if isinstance(param, list):
                    # 배열은 ARRAY['val1', 'val2'] 형식으로
                    array_values = "', '".join(str(v) for v in param)
                    replacement = f"ARRAY['{array_values}']::varchar[]"
                elif isinstance(param, str):
                    replacement = f"'{param}'"
                else:
                    replacement = str(param)
                
                # $1, $2 등을 실제 값으로 치환
                actual_query = actual_query.replace(f"${i}", replacement, 1)
            
            logger.info(f"[sql_search] 테스트용 SQL (\ubcf5사하여 사용 가능):\n{actual_query}")
            
            rows = await conn.fetch(query, *params)
            
            # 결과를 딕셔너리 리스트로 변환
            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "company": row["company"],
                    "title": row["title"],
                    "location": row["location"],
                    "hourly_wage": row["hourly_wage"],
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
