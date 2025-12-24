import os
from dataclasses import dataclass


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    HYPERBOLIC_KEY: str = os.getenv("HYPERBOLIC_KEY", "")
    
    FREE_QUERY_LIMIT: int = 5
    RATE_LIMIT_WINDOW: int = 86400
    
    API_GATEWAY_URL: str = os.getenv("API_GATEWAY_URL", "https://api.hyperbolic.xyz/v1")
    
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "D1337Bot")


config = Config()
