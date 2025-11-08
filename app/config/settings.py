# app/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str

    # Neo4j Aura
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    APP_ENV: str = "dev"

    # Prefer a full DB URL (e.g. Supabase transaction pooler)
    SUPABASE_DB_URL: str | None = None

    # Fallback for local/dev Postgres if SUPABASE_DB_URL is not set
    PG_HOST: str | None = "localhost"
    PG_PORT: int | None = 5432
    PG_DATABASE: str | None = "arlearn"
    PG_USER: str | None = "postgres"
    PG_PASSWORD: str | None = "postgres"

    CHROMA_DIR: str = "./.chroma"
    LLM_MODEL: str = "gpt-4o-mini"

    # IMPORTANT: match your pgvector schema (1536)
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    MAX_CHUNKS: int = 8
    TOP_K_CHROMA: int = 6
    TOP_K_GRAPH: int = 6

    class Config:
        env_file = ".env"

settings = Settings()
