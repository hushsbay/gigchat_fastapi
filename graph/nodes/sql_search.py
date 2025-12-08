'''
# 현재 상태에서 조건을 추출해 쿼리 생성 후 데이터베이스에서 조회하는 로직을 구현해야 함

from app.db.database import PostgresDB
db = PostgresDB()

def sql_search(state):
# 조건에 맞는 SQL 쿼리를 생성 후 데이터베이스에서 조회
# 작성 예정
    return
'''

# 더미 데이터 사용
# 폐기 예정
def sql_search(state):
    print("[sql_search] 실행됨")

    dummy_results = [
        {"id": 1, "title": "편의점 야간 알바", "region": "서울 강남", "pay": 12000},
        {"id": 2, "title": "카페 바리스타", "region": "서울 강남", "pay": 11000},
    ]

    state.result = dummy_results
    state.response = f"SQL 검색으로 {len(dummy_results)}개의 공고를 찾았습니다."
    return state
