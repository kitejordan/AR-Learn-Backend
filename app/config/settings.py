from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    NEO4J_URI: str
    NEO4J_USERNAME: str                 # This file centralizes the values of secret variables from the env so that 
    NEO4J_PASSWORD: str                  # they can be imported easily elsewhere.
    APP_ENV: str = "dev"

    PG_HOST: str = "localhost"
    PG_PORT: int = 5432
    PG_DATABASE: str = "arlearn"
    PG_USER: str = "postgres"
    PG_PASSWORD: str = "postgres"

    CHROMA_DIR: str = "./.chroma"
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    MAX_CHUNKS: int = 8
    TOP_K_CHROMA: int = 6
    TOP_K_GRAPH: int = 6

    class Config:
        env_file = ".env"

settings = Settings()
