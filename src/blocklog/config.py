from os import getenv

from pydantic import BaseModel, Field


class BlocklogConfig(BaseModel):
    base_url: str = Field(default_factory=lambda: getenv("BLOCKLOG_BASE_URL", "https://blocklogsecurity.com/api/v1"))
    api_key: str = Field(default_factory=lambda: getenv("BLOCKLOG_API_KEY", ""))
    signing_key: str = Field(default_factory=lambda: getenv("BLOCKLOG_SDK_SIGNING_KEY", ""))
    timeout: float = Field(default_factory=lambda: float(getenv("BLOCKLOG_TIMEOUT", "10")))
    max_retries: int = Field(default_factory=lambda: int(getenv("BLOCKLOG_MAX_RETRIES", "3")))
    batch_size: int = Field(default_factory=lambda: int(getenv("BLOCKLOG_BATCH_SIZE", "100")))
    flush_interval: float = Field(default_factory=lambda: float(getenv("BLOCKLOG_FLUSH_INTERVAL", "2")))
    debug: bool = False

    @classmethod
    def from_env(cls) -> "BlocklogConfig":
        return cls()
