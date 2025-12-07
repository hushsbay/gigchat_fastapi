from pydantic import BaseModel
from typing import Optional

class DocCreate(BaseModel):
    title: str
    content: str
    metadata: Optional[dict] = None

class DocSearch(BaseModel):
    query: str
    limit: int = 5
