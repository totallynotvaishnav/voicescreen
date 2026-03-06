from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5434/voicescreen"
    BOLNA_API_KEY: str = ""
    BOLNA_AGENT_ID: str = ""
    OPENAI_API_KEY: str = ""
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "arcee-ai/trinity-large-preview:free"
    BOLNA_API_BASE_URL: str = "https://api.bolna.ai"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    return Settings()
