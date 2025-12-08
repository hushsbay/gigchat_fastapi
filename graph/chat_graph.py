from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from graph.nodes.check_search import check_search
from graph.nodes.decide_search_type import decide_search_type
from graph.nodes.classify_input import classify_input
from graph.nodes.condition_collector import collect_conditions
from graph.nodes.sql_search import sql_search
from graph.nodes.vector_search import vector_search

DEFAULT_CONDITION = { # 기본 condition 키를 모두 빈값으로 초기화
    "gender": None,
    "age": None,
    "place": None,
    "work_days": None,
    "start_time": None,
    "end_time": None,
    "hourly_wage": None,
    "category": None
}

class ChatState(BaseModel):
    userid: Optional[str] = None
    text: str
    condition: Dict[str, Any] = DEFAULT_CONDITION.copy()
    search: bool = False
    job_related: Optional[bool] = None
    result: Optional[List[Dict[str, Any]]] = []
    reply: Optional[str] = None

graph = StateGraph(ChatState)

graph.add_node("check_search", check_search)
graph.add_node("decide_search_type", decide_search_type)
graph.add_node("classify_input", classify_input)
graph.add_node("collect_conditions", collect_conditions)
graph.add_node("sql_search", sql_search)
graph.add_node("vector_search", vector_search)

# 분기 트리는 아래와 같음. 라디오버튼은 3개 제공됨 
# 1) 일자리조건 추가(collect_conditions) 
# 2) 일자리조건만으로 검색(=sql_search) 
# 3) 일자리조건+채팅내용으로 검색(=vector_search : 일반sql검색+vector검색임)

# 1. check_search (true) > decide_search_type (채팅내용 있으면) > vector_search > END
#    check_search (true) > decide_search_type (채팅내용 없으면) > sql_search > END
# 2. check_search (false) > classify_input (일자리 관련이면) > collect_conditions > END
#    check_search (false) > classify_input (일자리 관련아니면) > END (일자리 관련 채팅하라고 안내)

graph.set_entry_point("check_search")

graph.add_conditional_edges("check_search",
    lambda s: "decide_search_type" if s.search else "classify_input",
    {"decide_search_type": "decide_search_type", "classify_input": "classify_input"},
)

graph.add_conditional_edges("classify_input",
    lambda s: "collect_conditions" if s.job_related else END,
    {"collect_conditions": "collect_conditions", END: END},
)

graph.add_conditional_edges("decide_search_type",
    lambda s: "vector_search" if s.text else "sql_search",
    {"vector_search": "vector_search", "sql_search": "sql_search"},
)

graph.add_edge("collect_conditions", END)
graph.add_edge("vector_search", END)
graph.add_edge("sql_search", END)

workflow = graph.compile()
