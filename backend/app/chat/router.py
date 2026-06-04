import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.schemas import ConversationResponse, MessageRequest, MessageResponse
from app.chat.service import (
    create_conversation,
    get_conversation,
    get_messages,
    list_conversations,
    stream_agent_response,
)
from app.database import get_async_session
from app.dependencies import get_current_user
from app.main import limiter
from app.models import User

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_user_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Return all conversations for the authenticated user, newest first."""
    return await list_conversations(current_user.id, session)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def new_conversation(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Create an empty conversation. The title is set after the first message."""
    return await create_conversation(current_user.id, session)


@router.get("/{thread_id}", response_model=ConversationResponse)
async def get_conversation_detail(
    thread_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    conv = await get_conversation(thread_id, current_user.id, session)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    thread_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Remove a conversation from the user's list. LangGraph state is retained."""
    conv = await get_conversation(thread_id, current_user.id, session)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    await session.delete(conv)
    await session.commit()


@router.get("/{thread_id}/messages", response_model=list[MessageResponse])
async def get_conversation_messages(
    thread_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Return the full message history for a conversation."""
    conv = await get_conversation(thread_id, current_user.id, session)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return await get_messages(thread_id)


@router.post("/{thread_id}/messages")
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    thread_id: uuid.UUID,
    body: MessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Send a message and receive a streaming SSE response.

    The client should consume `text/event-stream` events:
    - `{"type": "chunk", "content": "..."}` — partial assistant token
    - `{"type": "title", "title": "..."}` — emitted once, on the first message only
    - `{"type": "error", "detail": "..."}` — agent-level error
    - `{"type": "done"}` — stream finished
    """
    conv = await get_conversation(thread_id, current_user.id, session)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    return StreamingResponse(
        stream_agent_response(
            thread_id=thread_id,
            user_id=str(current_user.id),
            message=body.content,
            is_first_message=conv.title is None,
            session=session,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
