from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Walk up from  backend/app/config.py  →  backend/app  →  backend  →  project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        extra="ignore",
    )

    # LangGraph uses plain psycopg (sync) connections for store and checkpointer
    langgraph_db_url: str = (
        "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
    )
    # SQLAlchemy async engine (asyncpg) for app-level tables (users, conversations)
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5442/postgres"
    )

    # JWT
    secret_key: str = "change-me-to-a-random-secret-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS — comma-separated list of allowed frontend origins
    # Example in .env: ALLOWED_ORIGINS=["http://localhost:3000","https://yourdomain.com"]
    allowed_origins: list[str] = ["http://localhost:3000"]

    # OpenAI
    openai_api_key: str = ""

    # Tavily
    tavily_api_key: str = ""

    # Embeddings (for pgvector document search)
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # LangSmith observability
    langsmith_api_key: str = ""
    langsmith_project: str = "aks-chatbot"
    langsmith_tracing: bool = False


settings = Settings()
