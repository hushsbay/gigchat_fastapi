from fastapi import APIRouter, HTTPException

from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.graph.chat_graph import workflow, ChatState

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    text: str
    condition: Optional[Dict[str, Any]] = {}
    search: bool = False
    searchInResults: bool = False  # 결과내검색 플래그
    jobseekerId: Optional[int] = None  # 결과내검색용 사용자 ID
    similarityThreshold: float = 0.1  # 유사도 threshold (기본값 10%)

@router.post("")
def chat_endpoint(payload: ChatRequest):
    try:

        if payload.text:
            payload.condition['requirements'] = payload.text

        print(f'text===={payload.text}')
        print(f'condition===={payload.condition}')

        state = ChatState(
            user_id=payload.user_id,
            text=payload.text,
            condition=payload.condition or {},
            search=payload.search,
            searchInResults=payload.searchInResults,
            jobseekerId=payload.jobseekerId,
            similarityThreshold=payload.similarityThreshold,
        )

        result_state = workflow.invoke(state)

        return {
            "success": True,
            "response": result_state.get("response"),
            "result": result_state.get("result"),
            "state": result_state,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")
