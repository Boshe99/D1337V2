"""
D1337 Voice Services - Self-hosted STT/TTS client
Connects to Faster-Whisper (STT) and OpenAudio-S1/Fish-Speech (TTS) on H100 cluster
"""
import logging
import httpx
import io
import base64
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VoiceEmotion(Enum):
    """Supported emotions for TTS"""
    NEUTRAL = "neutral"
    ANGRY = "angry"
    SAD = "sad"
    EXCITED = "excited"
    SURPRISED = "surprised"
    NERVOUS = "nervous"
    EMBARRASSED = "embarrassed"
    CONFIDENT = "confident"
    JOYFUL = "joyful"
    TSUNDERE = "tsundere"
    HIMEDERE = "himedere"
    YANDERE = "yandere"


class VoiceCharacter(Enum):
    """Pre-configured voice characters"""
    DEFAULT = "default"
    ANIME_FEMALE = "anime_female"
    ANIME_MALE = "anime_male"
    ASSISTANT = "assistant"
    CUSTOM = "custom"


@dataclass
class STTResult:
    """Speech-to-text result"""
    text: str
    language: str
    confidence: float
    duration_ms: int


@dataclass
class TTSResult:
    """Text-to-speech result"""
    audio_data: bytes
    format: str
    duration_ms: int
    sample_rate: int


class VoiceServices:
    """Client for self-hosted voice services on H100 cluster"""
    
    def __init__(
        self,
        stt_url: str = "http://147.185.41.81:8002",
        tts_url: str = "http://147.185.41.81:8003",
        timeout: float = 60.0
    ):
        self.stt_url = stt_url.rstrip("/")
        self.tts_url = tts_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._stt_available = False
        self._tts_available = False
    
    async def connect(self):
        """Initialize HTTP client and check service availability"""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        
        # Check STT service
        try:
            response = await self._client.get(f"{self.stt_url}/health")
            self._stt_available = response.status_code == 200
            if self._stt_available:
                logger.info(f"STT service available at {self.stt_url}")
        except Exception as e:
            logger.warning(f"STT service not available: {e}")
            self._stt_available = False
        
        # Check TTS service
        try:
            response = await self._client.get(f"{self.tts_url}/health")
            self._tts_available = response.status_code == 200
            if self._tts_available:
                logger.info(f"TTS service available at {self.tts_url}")
        except Exception as e:
            logger.warning(f"TTS service not available: {e}")
            self._tts_available = False
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @property
    def stt_available(self) -> bool:
        return self._stt_available
    
    @property
    def tts_available(self) -> bool:
        return self._tts_available
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None
    ) -> Optional[STTResult]:
        """
        Transcribe audio to text using Faster-Whisper
        
        Args:
            audio_data: Audio bytes (supports ogg, mp3, wav, etc.)
            language: Optional language hint (e.g., "id", "en", "ja")
        
        Returns:
            STTResult with transcribed text, or None if failed
        """
        if not self._client or not self._stt_available:
            logger.warning("STT service not available")
            return None
        
        try:
            # Prepare multipart form data
            files = {"audio": ("audio.ogg", audio_data, "audio/ogg")}
            data = {}
            if language:
                data["language"] = language
            
            response = await self._client.post(
                f"{self.stt_url}/transcribe",
                files=files,
                data=data
            )
            
            if response.status_code != 200:
                logger.error(f"STT error: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            return STTResult(
                text=result.get("text", ""),
                language=result.get("language", "unknown"),
                confidence=result.get("confidence", 0.0),
                duration_ms=result.get("duration_ms", 0)
            )
            
        except Exception as e:
            logger.error(f"STT transcription failed: {e}")
            return None
    
    async def synthesize(
        self,
        text: str,
        emotion: VoiceEmotion = VoiceEmotion.NEUTRAL,
        character: VoiceCharacter = VoiceCharacter.DEFAULT,
        speed: float = 1.0,
        pitch: float = 1.0,
        reference_audio: Optional[bytes] = None
    ) -> Optional[TTSResult]:
        """
        Synthesize text to speech using OpenAudio-S1/Fish-Speech
        
        Args:
            text: Text to synthesize
            emotion: Voice emotion/style
            character: Pre-configured voice character
            speed: Speech speed multiplier (0.5-2.0)
            pitch: Pitch multiplier (0.5-2.0)
            reference_audio: Optional reference audio for voice cloning
        
        Returns:
            TTSResult with audio data, or None if failed
        """
        if not self._client or not self._tts_available:
            logger.warning("TTS service not available")
            return None
        
        try:
            # Add emotion tag to text if not neutral
            if emotion != VoiceEmotion.NEUTRAL:
                text = f"({emotion.value}) {text}"
            
            # Prepare request
            payload = {
                "text": text,
                "character": character.value,
                "speed": max(0.5, min(2.0, speed)),
                "pitch": max(0.5, min(2.0, pitch)),
                "format": "ogg"
            }
            
            # Add reference audio for voice cloning
            if reference_audio:
                payload["reference_audio"] = base64.b64encode(reference_audio).decode()
            
            response = await self._client.post(
                f"{self.tts_url}/synthesize",
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"TTS error: {response.status_code} - {response.text}")
                return None
            
            # Check if response is JSON (metadata) or binary (audio)
            content_type = response.headers.get("content-type", "")
            
            if "application/json" in content_type:
                result = response.json()
                audio_data = base64.b64decode(result.get("audio", ""))
                return TTSResult(
                    audio_data=audio_data,
                    format=result.get("format", "ogg"),
                    duration_ms=result.get("duration_ms", 0),
                    sample_rate=result.get("sample_rate", 24000)
                )
            else:
                # Direct audio response
                return TTSResult(
                    audio_data=response.content,
                    format="ogg",
                    duration_ms=0,
                    sample_rate=24000
                )
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None
    
    async def voice_chat(
        self,
        audio_input: bytes,
        llm_response: str,
        emotion: VoiceEmotion = VoiceEmotion.NEUTRAL,
        character: VoiceCharacter = VoiceCharacter.DEFAULT
    ) -> Tuple[Optional[str], Optional[bytes]]:
        """
        Full voice chat pipeline: STT -> (external LLM) -> TTS
        
        Args:
            audio_input: Input audio from user
            llm_response: Response text from LLM (already processed)
            emotion: Voice emotion for response
            character: Voice character for response
        
        Returns:
            Tuple of (transcribed_text, response_audio)
        """
        # Transcribe input
        stt_result = await self.transcribe(audio_input)
        if not stt_result:
            return None, None
        
        # Synthesize response
        tts_result = await self.synthesize(
            text=llm_response,
            emotion=emotion,
            character=character
        )
        
        audio_response = tts_result.audio_data if tts_result else None
        return stt_result.text, audio_response
    
    def detect_emotion_from_text(self, text: str) -> VoiceEmotion:
        """
        Detect appropriate emotion from LLM response text
        Simple heuristic-based detection
        """
        text_lower = text.lower()
        
        # Tsundere patterns
        if any(word in text_lower for word in ["baka", "bodoh", "hmph", "b-bukan"]):
            return VoiceEmotion.TSUNDERE
        
        # Angry patterns
        if any(word in text_lower for word in ["marah", "kesal", "angry", "!!!"]):
            return VoiceEmotion.ANGRY
        
        # Excited patterns
        if any(word in text_lower for word in ["wow", "amazing", "keren", "hebat"]):
            return VoiceEmotion.EXCITED
        
        # Sad patterns
        if any(word in text_lower for word in ["sedih", "sad", "maaf", "sorry"]):
            return VoiceEmotion.SAD
        
        # Nervous patterns
        if any(word in text_lower for word in ["um", "uh", "e-eh", "..."]):
            return VoiceEmotion.NERVOUS
        
        return VoiceEmotion.NEUTRAL


# Global instance
voice_services = VoiceServices()
