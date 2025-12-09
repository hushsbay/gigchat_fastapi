from fastapi import APIRouter, HTTPException, status
from typing import Union
from graph.chat_graph import workflow, ChatState
from common_fastapi.restful.rqst import ChatRequest
from common_fastapi.restful.resp import CodeMsgBase, Common, rsObj, rsError
from common_fastapi.shared.logger import logger
from common_fastapi.shared.constant import Const

router = APIRouter()

@router.post("", response_model=Union[Common, CodeMsgBase])
def chat_endpoint(payload: ChatRequest):
    try:        
        print(f'text===={payload.text}')
        print(f'condition===={payload.condition}')
        state = ChatState(
            userid=payload.userid,
            text=payload.text,
            condition=payload.condition or {},
            search=payload.search
        )
        result_state = workflow.invoke(state)
        print(f'result_state $$$$$ {result_state}')
        return rsObj({
            "job_related": result_state.get("job_related"),
            "condition": result_state.get("condition"),
            "result": result_state.get("result"),
            "reply": result_state.get("reply")
        })
    except Exception as e: # 예) raise Exception("Error")을 통해 여기로 전달됨
        logger.exception("chat_endpoint_error : %s", e)
        return rsError(Const.CODE_NOT_OK, str(e), True)
