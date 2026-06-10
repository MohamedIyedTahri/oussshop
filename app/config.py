import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    PORT: int = 8000
    DATABASE_URL: str
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "nvidia/llama-nemotron-rerank-vl-1b-v2"
    FEED_URL: str = "https://equip-home.tn/api/meta/meta-feed.xml"
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v
    
    # We can specify .env file location relative to the project root
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        extra="ignore"
    )

settings = Settings()
