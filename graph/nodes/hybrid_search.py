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


def hybrid_search(state):
    
    print(f"[state]: {state}")
    return state
