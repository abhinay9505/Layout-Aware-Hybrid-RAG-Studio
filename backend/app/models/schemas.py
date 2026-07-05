import re
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str = Field(
        min_length=2,
        max_length=4000
    )
    session_id: str
    top_k: Optional[int] = 5

class ChatSource(BaseModel):
    document_name: str
    page: Optional[int] = None
    chunk: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource]

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None

