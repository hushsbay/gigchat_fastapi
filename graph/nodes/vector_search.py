# from app.vector.embedderKo import EmbedderKo
# from app.db.database import PostgresDB

# embedder = EmbedderKo() # sentence-transformer 모델 사용
# db = PostgresDB()

def conditions_to_text(condition: dict, text: str) -> str:
    """
    조건을 자연어 문장으로 변환
    """
    user_input = text.strip() if text else ''
    condition_parts = []
    
    # 조건들을 일자리 조건 카드와 동일한 형식으로 변환
    if condition.get('place'):
        condition_parts.append(f"지역({condition['place']})")
    if condition.get('category'):
        condition_parts.append(f"직종({condition['category']})")
    if condition.get('work_days'):
        condition_parts.append(f"근무일({condition['work_days']})")
    if condition.get('hourly_wage'):
        # formatWage 로직 간소화 - 필요시 별도 함수로 분리
        wage = condition['hourly_wage']
        if isinstance(wage, str):
            condition_parts.append(f"시급({wage})")
        elif isinstance(wage, (int, float)):
            condition_parts.append(f"시급({wage:,}원)")
    if condition.get('start_time') and condition.get('end_time'):
        condition_parts.append(f"시간({condition['start_time']}~{condition['end_time']})")
    if condition.get('gender'):
        condition_parts.append(f"성별({condition['gender']})")
    if condition.get('age'):
        condition_parts.append(f"나이({condition['age']})")
    if condition.get('requirements'):
        condition_parts.append(f"기타({condition['requirements']})")
    
    # 사용자 입력과 조건 결합
    if user_input and condition_parts:
        return f"{user_input}\n\n일자리 조건: {', '.join(condition_parts)}"
    elif user_input:
        return user_input
    elif condition_parts:
        return f"일자리 조건: {', '.join(condition_parts)}"
    
    return ''


def vector_search(state):
    """
    Vector 기반 의미 검색 (결과내검색 지원)
    """
    print("[vector_search] 실행됨")
    print(f"[vector_search] Text: {state.text}")
    print(f"[vector_search] Conditions: {state.condition}")
    print(f"[vector_search] SearchInResults: {state.searchInResults}")
    print(f"[vector_search] JobseekerId: {state.jobseekerId}")
    print(f"[vector_search] SimilarityThreshold: {state.similarityThreshold}")

    # try:
    #     # 조건을 자연어 문장으로 변환
    #     search_query = conditions_to_text(state.condition, state.text)
        
    #     if not search_query.strip():
    #         state.response = '검색 조건이 없습니다. 원하시는 일자리 조건을 말씀해주세요.'
    #         state.result = []
    #         return state
        
    #     print(f"[vector_search] Search query: {search_query}")
        
    #     # 텍스트를 임베딩으로 변환
    #     embedding = embedder.create_embedding(search_query)
        
    #     # 유사도 threshold
    #     threshold = state.similarityThreshold if state.similarityThreshold else 0.1
        
    #     # 결과내검색 여부에 따라 다른 쿼리 실행
    #     if state.searchInResults and state.jobseekerId:
    #         print(f"[vector_search] Performing search in results for jobseeker: {state.jobseekerId}")
    #         query = """
    #             SELECT j.*, 
    #                 1 - (j.embedding <=> %s::vector) AS similarity
    #             FROM jobs j
    #             INNER JOIN result_search rs ON j.id = rs.job_id
    #             WHERE rs.jobseeker_id = %s
    #                 AND j.status = 'ACTIVE' 
    #                 AND j.embedding IS NOT NULL
    #                 AND (1 - (j.embedding <=> %s::vector)) >= %s
    #             ORDER BY j.embedding <=> %s::vector
    #             LIMIT %s
    #         """
    #         params = (embedding, state.jobseekerId, embedding, threshold, embedding, 10)
    #     else:
    #         print("[vector_search] Performing normal search")
    #         query = """
    #             SELECT *, 
    #                 1 - (embedding <=> %s::vector) AS similarity
    #             FROM jobs
    #             WHERE status = 'ACTIVE' 
    #                 AND embedding IS NOT NULL
    #                 AND (1 - (embedding <=> %s::vector)) >= %s
    #             ORDER BY embedding <=> %s::vector
    #             LIMIT %s
    #         """
    #         params = (embedding, embedding, threshold, embedding, 10)

    #     rows = db.execute_query(query, params)
        
    #     print(f"[vector_search] Found {len(rows)} jobs")
        
    #     if len(rows) == 0:
    #         message = '결과내검색에서 조건에 맞는 일자리를 찾지 못했습니다.' if state.searchInResults \
    #                   else '조건에 맞는 일자리를 찾지 못했습니다. 다른 조건으로 검색해보세요.'
    #         state.response = message
    #         state.result = []
    #         return state
        
    #     # similarity 값과 함께 결과 목록 생성
    #     prefix = '결과내검색 완료!\n\n' if state.searchInResults else ''
        
    #     result_list = []
    #     for idx, job in enumerate(rows, 1):
    #         similarity = job.get('similarity', 0)
    #         similarity_pct = f"{similarity * 100:.1f}" if similarity else "0.0"
    #         company = job.get('company') or '회사명 없음'
    #         title = job.get('title') or '제목 없음'
    #         result_list.append(f"{idx}. [{similarity_pct}%] {company} - {title}")
        
    #     result_text = '\n'.join(result_list)
    #     print(f"[vector_search] Result list:\n{result_text}")
        
    #     final_response = f"{prefix}{search_query}\n\n검색 결과 {len(rows)}개의 일자리를 찾았습니다. 우측 패널에서 확인하세요.\n\n{result_text}"
    #     print(f"[vector_search] Final response: {final_response}")
        
    #     state.result = rows
    #     state.response = final_response

    # except Exception as e:
    #     print(f"[vector_search] Error: {e}")
    #     import traceback
    #     traceback.print_exc()
        
    #     # 사용자에게 더 자세한 오류 메시지 제공
    #     error_message = '검색 중 오류가 발생했습니다.'
        
    #     error_str = str(e).lower()
    #     if 'pgvector' in error_str or 'vector' in error_str:
    #         error_message = '벡터 검색 설정에 문제가 있습니다. 관리자에게 문의하세요.'
    #     elif 'dimension' in error_str:
    #         error_message = f'벡터 차원 불일치 오류: {str(e)}'
        
    #     state.response = error_message
    #     state.result = []
    
    return state
