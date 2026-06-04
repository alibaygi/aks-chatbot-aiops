import asyncio
import json
import threading
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from langchain_core.messages import AIMessageChunk
from langsmith import traceable
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import get_agent, get_checkpointer
from app.agent.tools import Context
from app.models import Conversation


async def list_conversations(
    user_id: uuid.UUID, session: AsyncSession
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def create_conversation(
    user_id: uuid.UUID, session: AsyncSession
) -> Conversation:
    conv = Conversation(user_id=user_id)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def get_conversation(
    thread_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession
) -> Conversation | None:
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == thread_id,
            Conversation.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_messages(thread_id: uuid.UUID) -> list[dict]:
    """Retrieve conversation history from the LangGraph checkpointer."""
    checkpointer = get_checkpointer()
    lg_config = {"configurable": {"thread_id": str(thread_id)}}

    def _fetch() -> list[dict]:
        checkpoint_tuple = checkpointer.get_tuple(lg_config)
        if checkpoint_tuple is None:
            return []
        messages = (
            checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])
        )
        result: list[dict] = []
        for msg in messages:
            msg_type = getattr(msg, "type", None)
            if msg_type == "human":
                result.append({"role": "user", "content": msg.content})
            elif msg_type == "ai":
                content = msg.content
                # content can be a list of content blocks (e.g. tool use)
                if isinstance(content, list):
                    content = " ".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict)
                    ).strip()
                if content:
                    result.append({"role": "assistant", "content": content})
        return result

    return await asyncio.to_thread(_fetch)


@traceable(name="stream_agent_response")
async def stream_agent_response(
    thread_id: uuid.UUID,
    user_id: str,
    message: str,
    is_first_message: bool,
    session: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Invoke the agent and yield SSE events with response chunks.

    Event types emitted:
      {"type": "chunk",  "content": "<token>"}   — partial LLM output
      {"type": "error",  "detail": "<msg>"}       — agent error
      {"type": "title",  "title":  "<title>"}     — only on first message
      {"type": "done"}                             — stream finished
    """
    agent = get_agent()
    context = Context(user_id=user_id)
    lg_config = {"configurable": {"thread_id": str(thread_id)}}

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _run() -> None:
        try:
            for chunk in agent.stream(
                {"messages": [{"role": "user", "content": message}]},
                context=context,
                config=lg_config,
                stream_mode="messages",
            ):
                # LangGraph stream_mode="messages" yields (AnyMessage, metadata).
                # Only forward AIMessageChunks that are pure text (no tool-call
                # chunks) — this skips ToolMessages (tool results) and the LLM
                # steps where it decides to invoke a tool.
                if isinstance(chunk, tuple):
                    msg_chunk, _ = chunk
                    if (
                        isinstance(msg_chunk, AIMessageChunk)
                        and not msg_chunk.tool_call_chunks
                    ):
                        content = msg_chunk.content
                        if content:
                            data = json.dumps({"type": "chunk", "content": content})
                            asyncio.run_coroutine_threadsafe(queue.put(data), loop)
        except Exception as exc:
            error = json.dumps({"type": "error", "detail": str(exc)})
            asyncio.run_coroutine_threadsafe(queue.put(error), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # sentinel

    threading.Thread(target=_run, daemon=True).start()

    # --- Stream chunks to the client ---
    while True:
        item = await queue.get()
        if item is None:
            break
        yield f"data: {item}\n\n"

    # --- Post-stream: persist metadata ---
    now = datetime.now(timezone.utc)
    title: str | None = None

    if is_first_message:
        title = (message[:77] + "...") if len(message) > 80 else message
        await session.execute(
            update(Conversation)
            .where(Conversation.id == thread_id)
            .values(title=title, updated_at=now)
        )
    else:
        await session.execute(
            update(Conversation)
            .where(Conversation.id == thread_id)
            .values(updated_at=now)
        )

    await session.commit()

    if title is not None:
        yield f"data: {json.dumps({'type': 'title', 'title': title})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"
