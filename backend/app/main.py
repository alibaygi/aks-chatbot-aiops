import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger.json import JsonFormatter
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.agent.agent import init_agent, shutdown_agent
from app.auth.router import router as auth_router
from app.chat.router import router as chat_router
from app.config import settings
from app.database import Base, engine
from app.ingestion.router import router as ingestion_router

# ── Structured JSON logging ────────────────────────────────────────────────────
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger(__name__)

# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure LangSmith tracing before agent initialisation
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        logger.info("LangSmith tracing enabled", extra={"project": settings.langsmith_project})

    # Create app-level tables (users, conversations, documents) if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialise LangGraph store, checkpointer, and the agent (blocking, runs once)
    init_agent()
    logger.info("Agent initialised")

    yield

    # Graceful shutdown
    shutdown_agent()
    await engine.dispose()


app = FastAPI(
    title="Chatbot API",
    version="1.0.0",
    description="LangGraph chatbot with short- and long-term memory, exposed via FastAPI.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["health"])
async def health():
    return {"status": "ok"}
