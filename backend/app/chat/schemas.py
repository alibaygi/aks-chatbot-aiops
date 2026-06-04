import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    role: Literal["user", "assistant"]
    content: str
