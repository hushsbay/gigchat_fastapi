from fastapi import APIRouter, HTTPException, status
from typing import Union
# from graph.chat_graph import workflow, ChatState
from restful.rqst import ChatRequest
from restful.resp import CodeMsgBase, Common, rsObj, rsError
from common.logger import logger
from common.constant import Const

router = APIRouter()

@router.post("", response_model=Union[Common, CodeMsgBase])
def chat_endpoint(payload: ChatRequest):
    try:        
        print(f'text===={payload.text}')
        print(f'condition===={payload.condition}')
        # state = ChatState(
        #     userid=payload.userid,
        #     text=payload.text,
        #     condition=payload.condition or {}
        # )
        # result_state = workflow.invoke(state)
        # return {
        #     "success": True,
        #     "response": result_state.get("response"),
        #     "result": result_state.get("result"),
        #     "state": result_state,
        # }
        # raise Exception("text는 필수입니다!!!")
        return rsObj({ 
            "aaa": "11111", "bbb": "22222" 
        })
    except Exception as e:
        logger.exception("chat_endpoint_error : %s", e)
        return rsError(Const.CODE_NOT_OK, str(e), True)
