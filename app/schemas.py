from pydantic import BaseModel
from typing import List, Optional


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str
    keys: Optional[str] = ""
    duration: Optional[str] = ""
    languages: Optional[str] = ""


class ChatResponse(BaseModel):
    reply: str
    recommendations: Optional[List[Recommendation]] = None
    end_of_conversation: bool