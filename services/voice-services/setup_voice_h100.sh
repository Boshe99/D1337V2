#!/bin/bash
# D1337 Voice Services Setup Script for H100 Cluster
# This script sets up Faster-Whisper (STT) and Fish-Speech/OpenAudio (TTS) on H100

set -e

echo "=========================================="
echo "D1337 Voice Services Setup for H100"
echo "=========================================="

# Configuration
VOICE_DIR="/data/voice-services"
STT_PORT=8002
TTS_PORT=8003

# Create directories
echo "[1/6] Creating directories..."
mkdir -p $VOICE_DIR/stt
mkdir -p $VOICE_DIR/tts
mkdir -p $VOICE_DIR/models
mkdir -p $VOICE_DIR/reference_voices

# Install system dependencies
echo "[2/6] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y ffmpeg libsndfile1

# Install Python dependencies for STT (Faster-Whisper)
echo "[3/6] Setting up STT service (Faster-Whisper)..."
pip3 install faster-whisper fastapi uvicorn python-multipart aiofiles

# Download Whisper model
echo "[3/6] Downloading Whisper Large-v3 model..."
python3 -c "
from faster_whisper import WhisperModel
print('Downloading whisper-large-v3...')
model = WhisperModel('large-v3', device='cuda', compute_type='float16')
print('Model downloaded successfully!')
"

# Create STT server
cat > $VOICE_DIR/stt/stt_server.py << 'EOF'
"""
D1337 STT Server - Faster-Whisper on GPU
Endpoint: POST /transcribe
"""
import os
import io
import time
import tempfile
import logging
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import uvicorn
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="D1337 STT Service")

# Load model on startup
model = None

@app.on_event("startup")
async def load_model():
    global model
    logger.info("Loading Whisper Large-v3 model...")
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    logger.info("Model loaded successfully!")

@app.get("/health")
async def health():
    return {"status": "ok", "model": "whisper-large-v3", "device": "cuda"}

@app.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form(None)
):
    start_time = time.time()
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Transcribe
        segments, info = model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True
        )
        
        # Collect text
        text = " ".join([segment.text for segment in segments])
        
        # Cleanup
        os.unlink(tmp_path)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return JSONResponse({
            "text": text.strip(),
            "language": info.language,
            "confidence": info.language_probability,
            "duration_ms": duration_ms
        })
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
EOF

# Install TTS dependencies (Fish-Speech)
echo "[4/6] Setting up TTS service (Fish-Speech)..."
pip3 install torch torchaudio transformers soundfile scipy

# Clone Fish-Speech
if [ ! -d "$VOICE_DIR/tts/fish-speech" ]; then
    cd $VOICE_DIR/tts
    git clone https://github.com/fishaudio/fish-speech.git
    cd fish-speech
    pip3 install -e .
fi

# Download Fish-Speech model
echo "[4/6] Downloading Fish-Speech 1.5 model..."
python3 -c "
from huggingface_hub import snapshot_download
print('Downloading Fish-Speech 1.5...')
snapshot_download(
    repo_id='fishaudio/fish-speech-1.5',
    local_dir='/data/voice-services/models/fish-speech-1.5'
)
print('Model downloaded successfully!')
"

# Create TTS server
cat > $VOICE_DIR/tts/tts_server.py << 'EOF'
"""
D1337 TTS Server - Fish-Speech on GPU
Endpoint: POST /synthesize
"""
import os
import io
import time
import base64
import logging
import tempfile
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
import uvicorn
import torch
import soundfile as sf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="D1337 TTS Service")

# Model paths
MODEL_PATH = "/data/voice-services/models/fish-speech-1.5"
REFERENCE_DIR = "/data/voice-services/reference_voices"

# Emotion to prosody mapping
EMOTION_PROSODY = {
    "neutral": {"speed": 1.0, "pitch": 1.0},
    "angry": {"speed": 1.1, "pitch": 1.1},
    "sad": {"speed": 0.9, "pitch": 0.9},
    "excited": {"speed": 1.2, "pitch": 1.15},
    "surprised": {"speed": 1.1, "pitch": 1.2},
    "nervous": {"speed": 1.05, "pitch": 1.05},
    "embarrassed": {"speed": 0.95, "pitch": 1.1},
    "confident": {"speed": 1.0, "pitch": 0.95},
    "joyful": {"speed": 1.1, "pitch": 1.1},
    "tsundere": {"speed": 1.05, "pitch": 1.15},
    "himedere": {"speed": 0.95, "pitch": 1.1},
    "yandere": {"speed": 0.9, "pitch": 1.0},
}

class SynthesizeRequest(BaseModel):
    text: str
    character: str = "default"
    speed: float = 1.0
    pitch: float = 1.0
    format: str = "ogg"
    reference_audio: Optional[str] = None  # Base64 encoded

# Global model
tts_model = None

@app.on_event("startup")
async def load_model():
    global tts_model
    logger.info("Loading Fish-Speech model...")
    try:
        # Import fish_speech modules
        import sys
        sys.path.insert(0, "/data/voice-services/tts/fish-speech")
        from fish_speech.inference import load_model as fs_load_model
        tts_model = fs_load_model(MODEL_PATH)
        logger.info("Fish-Speech model loaded!")
    except Exception as e:
        logger.warning(f"Fish-Speech not available, using fallback: {e}")
        tts_model = None

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": "fish-speech-1.5",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "model_loaded": tts_model is not None
    }

@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    start_time = time.time()
    
    try:
        text = request.text
        
        # Extract emotion from text if present
        emotion = "neutral"
        for emo in EMOTION_PROSODY.keys():
            if f"({emo})" in text.lower():
                emotion = emo
                text = text.replace(f"({emo})", "").strip()
                break
        
        # Apply emotion prosody
        prosody = EMOTION_PROSODY.get(emotion, EMOTION_PROSODY["neutral"])
        speed = request.speed * prosody["speed"]
        pitch = request.pitch * prosody["pitch"]
        
        # Handle reference audio for voice cloning
        reference_path = None
        if request.reference_audio:
            ref_bytes = base64.b64decode(request.reference_audio)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(ref_bytes)
                reference_path = tmp.name
        elif request.character != "default":
            # Check for pre-saved reference voice
            char_ref = os.path.join(REFERENCE_DIR, f"{request.character}.wav")
            if os.path.exists(char_ref):
                reference_path = char_ref
        
        # Generate audio
        if tts_model is not None:
            # Use Fish-Speech
            import sys
            sys.path.insert(0, "/data/voice-services/tts/fish-speech")
            from fish_speech.inference import synthesize as fs_synthesize
            
            audio_data = fs_synthesize(
                tts_model,
                text,
                reference_audio=reference_path,
                speed=speed
            )
        else:
            # Fallback: generate silence (placeholder)
            logger.warning("TTS model not loaded, returning placeholder")
            import numpy as np
            sample_rate = 24000
            duration = len(text) * 0.05  # ~50ms per character
            audio_data = np.zeros(int(sample_rate * duration), dtype=np.float32)
        
        # Convert to requested format
        with tempfile.NamedTemporaryFile(suffix=f".{request.format}", delete=False) as tmp:
            sf.write(tmp.name, audio_data, 24000)
            with open(tmp.name, "rb") as f:
                audio_bytes = f.read()
            os.unlink(tmp.name)
        
        # Cleanup reference if temporary
        if reference_path and request.reference_audio:
            os.unlink(reference_path)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Return as binary audio
        return Response(
            content=audio_bytes,
            media_type=f"audio/{request.format}",
            headers={
                "X-Duration-Ms": str(duration_ms),
                "X-Sample-Rate": "24000",
                "X-Emotion": emotion
            }
        )
        
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )

@app.post("/upload_reference")
async def upload_reference(character: str, audio: bytes):
    """Upload reference voice for a character"""
    try:
        ref_path = os.path.join(REFERENCE_DIR, f"{character}.wav")
        with open(ref_path, "wb") as f:
            f.write(audio)
        return {"status": "ok", "character": character, "path": ref_path}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
EOF

# Create systemd services
echo "[5/6] Creating systemd services..."

# STT Service
sudo tee /etc/systemd/system/d1337-stt.service << EOF
[Unit]
Description=D1337 STT Service (Faster-Whisper)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$VOICE_DIR/stt
ExecStart=/usr/bin/python3 $VOICE_DIR/stt/stt_server.py
Restart=always
RestartSec=10
Environment="CUDA_VISIBLE_DEVICES=0"

[Install]
WantedBy=multi-user.target
EOF

# TTS Service
sudo tee /etc/systemd/system/d1337-tts.service << EOF
[Unit]
Description=D1337 TTS Service (Fish-Speech)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$VOICE_DIR/tts
ExecStart=/usr/bin/python3 $VOICE_DIR/tts/tts_server.py
Restart=always
RestartSec=10
Environment="CUDA_VISIBLE_DEVICES=1"

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable d1337-stt d1337-tts

echo "[6/6] Starting services..."
sudo systemctl start d1337-stt
sudo systemctl start d1337-tts

# Wait for services to start
sleep 5

# Test services
echo ""
echo "=========================================="
echo "Testing services..."
echo "=========================================="

echo "STT Health Check:"
curl -s http://localhost:$STT_PORT/health | python3 -m json.tool || echo "STT not ready yet"

echo ""
echo "TTS Health Check:"
curl -s http://localhost:$TTS_PORT/health | python3 -m json.tool || echo "TTS not ready yet"

echo ""
echo "=========================================="
echo "D1337 Voice Services Setup Complete!"
echo "=========================================="
echo ""
echo "Services:"
echo "  STT: http://0.0.0.0:$STT_PORT (Faster-Whisper Large-v3)"
echo "  TTS: http://0.0.0.0:$TTS_PORT (Fish-Speech 1.5)"
echo ""
echo "Commands:"
echo "  sudo systemctl status d1337-stt"
echo "  sudo systemctl status d1337-tts"
echo "  sudo journalctl -u d1337-stt -f"
echo "  sudo journalctl -u d1337-tts -f"
echo ""
echo "Reference voices directory: $VOICE_DIR/reference_voices/"
echo "Upload .wav files there for voice cloning"
