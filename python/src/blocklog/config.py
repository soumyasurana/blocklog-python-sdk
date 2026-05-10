from os import getenv

from pydantic import BaseModel, Field


class BlocklogConfig(BaseModel):
    base_url: str = Field(default_factory=lambda: getenv("BLOCKLOG_BASE_URL", "http://127.0.0.1:8000/api/v1"))
    api_key: str = Field(default_factory=lambda: getenv("BLOCKLOG_API_KEY", ""))
    timeout: float = 10.0
    max_retries: int = 3
    batch_size: int = 100
    flush_interval: float = 2.0

    @classmethod
    def from_env(cls) -> "BlocklogConfig":
        return cls()
