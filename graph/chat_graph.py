from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from graph.nodes.check_search import check_search
from graph.nodes.classify_input import classify_input
from graph.nodes.decide_search_type import decide_search_type
from graph.nodes.sql_search import sql_search
from graph.nodes.hybrid_search import hybrid_search

DEFAULT_CONDITION = {
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
graph.add_node("classify_input", classify_input)
graph.add_node("decide_search_type", decide_search_type)
graph.add_node("sql_search", sql_search)
graph.add_node("hybrid_search", hybrid_search)

# 분기 트리
# 1) 일자리조건 추가(classify_input)
# 2) 일자리조건만으로 검색(sql_search)
# 3) 일자리조건+채팅내용으로 검색(hybrid_search : 일반sql검색+vector검색)

# 1. check_search (false) > classify_input (일자리 관련이면 조건 추출) > END
#    check_search (false) > classify_input (일자리 관련 아니면) > END (일자리 관련 채팅하라고 안내)
# 2. check_search (true) > decide_search_type (채팅내용 있으면) > hybrid_search > END (일반sql검색+vector검색)
#    check_search (true) > decide_search_type (채팅내용 없으면) > sql_search > END

graph.set_entry_point("check_search")

graph.add_conditional_edges("check_search",
    lambda s: "decide_search_type" if s.search else "classify_input",
    {"decide_search_type": "decide_search_type", "classify_input": "classify_input"},
)

graph.add_conditional_edges("decide_search_type",
    lambda s: "hybrid_search" if s.text else "sql_search",
    {"hybrid_search": "hybrid_search", "sql_search": "sql_search"},
)

graph.add_edge("classify_input", END) # classify_input에서 바로 END (조건 추출까지 완료)
graph.add_edge("hybrid_search", END)
graph.add_edge("sql_search", END)

workflow = graph.compile()
