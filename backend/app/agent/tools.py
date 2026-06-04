from dataclasses import dataclass
from typing import List, Literal

from langchain.tools import ToolRuntime, tool
from tavily import TavilyClient
from typing_extensions import TypedDict

from app.config import settings


@dataclass
class Context:
    user_id: str


class UserInfo(TypedDict):
    name: str
    language: str
    location: str
    interests: List[str]


@tool
def get_user_info(runtime: ToolRuntime[Context]) -> str:
    """Look up user info."""
    store = runtime.store
    user_id = runtime.context.user_id
    user_info = store.get(("users",), user_id)
    return str(user_info.value) if user_info else "Unknown user"


@tool
def save_user_info(user_info: UserInfo, runtime: ToolRuntime[Context]) -> str:
    """Save user info."""
    store = runtime.store
    user_id = runtime.context.user_id
    store.put(("users",), user_id, user_info)
    return "Successfully saved user info."


tavily_client = TavilyClient(api_key=settings.tavily_api_key)


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> dict:
    """Run a web search for up-to-date information."""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )


@tool
def search_user_documents(query: str, runtime: ToolRuntime[Context]) -> str:
    """Search the user's uploaded documents (PDF or Markdown files) for relevant information."""
    import asyncio
    import uuid

    from app.database import async_session_maker
    from app.ingestion.service import search_documents

    user_id = uuid.UUID(runtime.context.user_id)

    async def _run() -> list[str]:
        async with async_session_maker() as session:
            return await search_documents(query, user_id, session, top_k=5)

    chunks = asyncio.run(_run())
    if not chunks:
        return "No relevant information found in uploaded documents."
    return "\n\n---\n\n".join(chunks)
