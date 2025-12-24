import logging
import time
from typing import Optional

import httpx

from config import config

logger = logging.getLogger(__name__)


class APIGateway:
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.base_url = config.API_GATEWAY_URL

    async def connect(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={
                "Authorization": f"Bearer {config.HYPERBOLIC_KEY}",
                "Content-Type": "application/json"
            }
        )
        logger.info("API Gateway client initialized")

    async def close(self):
        if self.client:
            await self.client.aclose()
            logger.info("API Gateway client closed")

    async def chat_completion(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: str = "deepseek-ai/DeepSeek-V3"
    ) -> tuple[str, int, int]:
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 2048,
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            
            data = response.json()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            
            return content, tokens_used, response_time_ms
            
        except httpx.HTTPStatusError as e:
            logger.error(f"API Gateway HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"API Gateway error: {e}")
            raise


api_gateway = APIGateway()


SYSTEM_PROMPT = """You are D1337, an advanced AI assistant created by DESORDEN. You are helpful, knowledgeable, and provide accurate information.

Key traits:
- You are concise but thorough in your responses
- You maintain a professional yet friendly tone
- You are honest about your limitations
- You prioritize user safety and ethical considerations

When responding:
- Be direct and helpful
- Provide accurate information
- If you don't know something, say so
- Keep responses focused and relevant"""
