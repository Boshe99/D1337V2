import os
from dataclasses import dataclass, field
from typing import List


def _parse_admin_ids() -> List[int]:
    ids_str = os.getenv("INITIAL_ADMIN_IDS", "")
    if not ids_str:
        return []
    try:
        return [int(id.strip()) for id in ids_str.split(",") if id.strip()]
    except ValueError:
        return []


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    HYPERBOLIC_KEY: str = os.getenv("HYPERBOLIC_KEY", "")
    
    FREE_QUERY_LIMIT: int = 5
    RATE_LIMIT_WINDOW: int = 86400
    
    API_GATEWAY_URL: str = os.getenv("API_GATEWAY_URL", "http://147.185.41.81:8000/v1")
    D1337_MODEL: str = os.getenv("D1337_MODEL", "d1337-agent")
    
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "D1337Bot")
    
    PASTE_SERVER_URL: str = os.getenv("PASTE_SERVER_URL", "")
    PASTE_SERVER_PORT: int = int(os.getenv("PASTE_SERVER_PORT", "8080"))
    
    # Voice services (self-hosted on H100 cluster)
    STT_SERVICE_URL: str = os.getenv("STT_SERVICE_URL", "http://147.185.41.81:8002")
    TTS_SERVICE_URL: str = os.getenv("TTS_SERVICE_URL", "http://147.185.41.81:8003")
    VOICE_ENABLED: bool = os.getenv("VOICE_ENABLED", "true").lower() == "true"
    VOICE_RESPONSE_ENABLED: bool = os.getenv("VOICE_RESPONSE_ENABLED", "true").lower() == "true"
    
    INITIAL_ADMIN_IDS: List[int] = field(default_factory=_parse_admin_ids)


config = Config()
