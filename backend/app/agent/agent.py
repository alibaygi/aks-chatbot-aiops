from contextlib import ExitStack
import os

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

from app.agent.tools import Context, get_user_info, internet_search, save_user_info, search_user_documents
from app.config import settings

SYSTEM_PROMPT = """You are a helpful assistant. Your task is to answer user's questions to the best of your knowledge.
In order to provide personalized answers, you have access to four tools;
one for reading the information that we have from the user,
one for saving information about the user,
one for searching the web for up-to-date information, and
one for searching documents that the user has uploaded.
Whenever needed, use these tools to get or update user information, search the web, or look up information from uploaded files.

**Important note:**
- In your answers, NEVER ask for user's information, unless you need that information to complete a specific task.
- NEVER ask about user's preferences. Only when the user willingly provides you with their preferences, you then can save them.
- DO NOT say that you are saving to or reading from memories related to the user.
- When a user asks about content from their documents, always use the search_user_documents tool first."""

_stack: ExitStack | None = None
_store: PostgresStore | None = None
_checkpointer: PostgresSaver | None = None
_agent = None


def init_agent() -> None:
    """Initialise LangGraph store, checkpointer, and the agent. Called once at startup."""
    global _stack, _store, _checkpointer, _agent

    # Expose API keys to os.environ so LangChain/Tavily internals can find them.
    # pydantic-settings reads .env into the Settings object but does NOT inject
    # values into os.environ, so libraries that call os.environ.get() directly
    # would miss them otherwise.
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    os.environ["TAVILY_API_KEY"] = settings.tavily_api_key

    _stack = ExitStack()

    _store = _stack.enter_context(PostgresStore.from_conn_string(settings.langgraph_db_url))
    _store.setup()

    _checkpointer = _stack.enter_context(PostgresSaver.from_conn_string(settings.langgraph_db_url))
    _checkpointer.setup()

    _agent = create_agent(
        model="gpt-4o-mini",
        tools=[get_user_info, save_user_info, internet_search, search_user_documents],
        middleware=[
            SummarizationMiddleware(
                model="gpt-4o-mini",
                trigger=("tokens", 4000),
                keep=("messages", 10),
            )
        ],
        context_schema=Context,
        system_prompt=SYSTEM_PROMPT,
        store=_store,
        checkpointer=_checkpointer,
    )


def shutdown_agent() -> None:
    """Close all database connections. Called once at shutdown."""
    global _stack
    if _stack is not None:
        _stack.close()
        _stack = None


def get_agent():
    if _agent is None:
        raise RuntimeError("Agent has not been initialised. Call init_agent() first.")
    return _agent


def get_store() -> PostgresStore:
    if _store is None:
        raise RuntimeError("Store has not been initialised. Call init_agent() first.")
    return _store


def get_checkpointer() -> PostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("Checkpointer has not been initialised. Call init_agent() first.")
    return _checkpointer
