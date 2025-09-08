from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    NEO4J_URI: str
    NEO4J_USERNAME: str                 # This file centralizes the values of secret variables from the env so that 
    NEO4J_PASSWORD: str                  # they can be imported easily elsewhere.
    APP_ENV: str = "dev"
    class Config: env_file = ".env"

settings = Settings()
