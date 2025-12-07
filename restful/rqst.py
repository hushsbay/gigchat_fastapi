from pydantic import BaseModel
from typing import Any, Dict, Optional

class ChatRequest(BaseModel):
    userid: Optional[str] = None
    text: str
    condition: Optional[Dict[str, Any]] = {}