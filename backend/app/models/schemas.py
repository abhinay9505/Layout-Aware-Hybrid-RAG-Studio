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

class ChatResponse(BaseModel):
    success: bool
    source: str
    answer: str
    session_id: str
    cached: bool
    relevance_score: float
    retrieved_chunks: int
    documents_used: List[dict]
    rewritten_query: Optional[str] = None

class UserRegister(BaseModel):
    email: str = Field(..., min_length=10, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator('email')
    @classmethod
    def validate_gmail(cls, v: str) -> str:
        email = v.strip().lower()
        if not re.match(r"^[a-z0-9.+]+@gmail\.com$", email):
            raise ValueError("Must be a valid Gmail address (e.g. user@gmail.com)")
        return email

class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator('email')
    @classmethod
    def validate_gmail(cls, v: str) -> str:
        email = v.strip().lower()
        if not re.match(r"^[a-z0-9.+]+@gmail\.com$", email):
            raise ValueError("Must be a valid Gmail address (e.g. user@gmail.com)")
        return email

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

