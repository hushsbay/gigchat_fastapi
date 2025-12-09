from fastapi import FastAPI, status # https://fastapi.tiangolo.com/reference/status/
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.requests import Request
import os, sys, json, asyncpg, re # type: ignore
from pathlib import Path
from dotenv import load_dotenv # type: ignore
from typing import Union, List, Optional
from pydantic import BaseModel
from pgvector.asyncpg import register_vector # type: ignore
from contextlib import asynccontextmanager
from common_fastapi.shared.logger import logger
from common_fastapi.shared.constant import Const

from route.chat import router as chat_router

origins = ["http://localhost:5173", "http://localhost:3000"]

load_dotenv()
DATABASE_URL = os.getenv("NEON_DATABASE_URL")

# Application lifespan: 생성시 DB풀 만들고 종료시 닫음 (기존 on_event('startup'/'shutdown')는 deprecated)
# - 풀은 app.state.pool에 저장
# - 기존 코드의 전역 `pool` 변수를 사용하던 곳을 위해 module-level pool 변수도 설정
pool = None  # 데이터베이스 연결 풀 (하위 호환을 위해 module-level 변수 유지)
@asynccontextmanager # 애플리케이션 시작/종료시 리소스 관리(연결/초기화 등)하는 데 사용되는 데코레이터
async def lifespan(app: FastAPI):
    global pool
    # Ensure pgvector's type codec is registered on every new connection created by the pool
    # by passing the `init` callback. This prevents intermittent "expected str, got list" errors
    # where some pool connections lack the pgvector encoder registration.
    # 위 내용 정리 : 아래 create_pool(...)에 init=register_vector를 전달하도록 수정
    # 이로써 풀에서 생성되는 모든 커넥션에 pgvector 타입 코덱이 등록되어 간헐적인 "expected str, got list" 오류를 방지
    # 안전을 위해 풀 생성 직후 단일 커넥션에 대해 호출하던 await register_vector(conn)도 그대로 남겨둠 (무해하며 충돌 없음)
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10, command_timeout=60, init=register_vector)
    async with pool.acquire() as conn: # conn = pool.acquire()를 비동기적으로 호출하고 아래 블럭이 끝나면 자동으로 리소스 해제함
        await register_vector(conn) # 한번만 등록 (위 설명 참조)
    app.state.pool = pool # app.state에 보관해 다른 핸들러에서 접근 가능하도록 함
    # try: # load server keys once and store in app.state so all routers share the same source-of-truth
    #     app.state.serverkeyArr = get_server_keys()
    # except Exception:
    #     app.state.serverkeyArr = []
    try:
        yield # 여기까지 실행하고, 이제 애플리케이션(또는 엔드포인트)이 요청을 처리하도록 넘겨줘라고 하는 것임
    finally: # yield를 사용한 의존성 컨텍스트가 끝날 때) 실행 : 여기서는 FastAPI가 종료될 때를 의미함
        try:
            await pool.close()
        except Exception:
            logger.exception("Error closing DB pool on shutdown")

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

print(f"sys.executable={sys.executable}")
print(f"sys.version={sys.version.splitlines()[0]}")

app.include_router(chat_router, prefix="/chat")

# 예를 들어, localhost:8000/gigwork/doc_query/docid 라우팅인데 localhost:8000/gigwork/doc_query 만으로 요청시
# fastapi가 { "detail": "Not Found" }으로 응답하는데 아래 @app.exception_handler(Exception)로 걸리지 않고 있음
# 이 부분은 클라이언트에서 응답핸들링 공통 모듈을 작성하기로 함 
# - 그 경우 1) 아래 { "detail": { "code": Const.CODE_NOT_OK, "msg": str(ex) } }과 2) code,msg 없는 경우 둘 다 커버하기
    
# CORS 미들웨어가 이미 설정되어 있지만, 전역 예외 핸들러가 별도의 응답을 반환할 때는 명시적으로 CORS 헤더를 포함해 주는 것이 안전
# 더 좋은 방법은 예외 핸들러가 직접 CORS 처리를 하느니 CORS 미들웨어가 항상 응답 헤더를 붙이도록 설정하거나, 
# 예외 핸들러에서 app.middleware('http') 같은 공통 로직을 통해 헤더를 보장하는 구조를 향후 고려
@app.exception_handler(Exception) # FastAPIHTTPException)
async def custom_http_exception_handler(request: Request, ex: Exception): # FastAPIHTTPException):
    logger.exception("Unhandled exception : %s", ex)
    # Browser may block access to response body if CORS headers are missing
    # Ensure we echo the Origin header (if present) so the browser can read the response
    origin = request.headers.get("origin")
    cors_headers = {}
    if origin:
        cors_headers["Access-Control-Allow-Origin"] = origin
        cors_headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse( # Return a JSON body with details. Use ex.__str__() so messages propagate
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={ "detail": { "code": Const.CODE_NOT_OK, "msg": str(ex) } },
        headers=cors_headers
    )
