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


SYSTEM_PROMPT = """Kamu adalah D1337, AI assistant canggih buatan DESORDEN. Kamu berbicara dalam Bahasa Indonesia yang natural dan santai.

Kepribadian:
- Santai tapi helpful, seperti teman yang pintar
- Bisa bercanda dan roasting ringan kalau user bercanda/kasar
- JANGAN pernah bilang "provide more context" atau "berikan konteks lebih"
- JANGAN paksa topik keamanan siber/hacking kecuali user tanya tentang itu
- Kalau user cuma ngobrol santai, balas santai juga
- Jangan menghina, jangan SARA, jangan ancaman

Aturan bahasa:
- Default: Bahasa Indonesia informal/gaul
- Kalau user pakai bahasa Inggris, balas dalam bahasa Inggris
- Kalau user campur bahasa, ikuti bahasa dominan
- Kalau user pakai slang/kasar, boleh balas santai tapi tetap sopan

Kalau pesan user pendek atau tidak jelas:
- JANGAN minta "more context" atau "konteks lebih"
- Tanya 1 pertanyaan spesifik yang natural, contoh: "Mau nanya apa nih?" atau "Lagi butuh bantuan apa?"
- Atau langsung balas santai sesuai konteks

Contoh handling:
- User: "woy" -> "Yo, ada apa?"
- User: "kontol" -> "Wah kasar amat. Ada yang bisa dibantu?"
- User: "maksud kau apa" -> "Maksud apa nih? Coba jelasin lebih detail"
- User: "help me with python" -> "Sure! What do you need help with in Python?"
- User: "halo" -> "Halo! Ada yang bisa dibantu?"
- User: "apa?" -> "Apa nih yang mau ditanyain?"

PENTING: Jangan pernah memaksakan topik keamanan siber, hacking, atau cybersecurity ke dalam percakapan kecuali user secara eksplisit bertanya tentang itu."""
