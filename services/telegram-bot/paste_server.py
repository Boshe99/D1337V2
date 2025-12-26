import asyncio
import logging
import secrets
from typing import Optional
from dataclasses import dataclass

import redis.asyncio as redis
from aiohttp import web

from config import config

logger = logging.getLogger(__name__)

PASTE_TTL = 1200  # 20 minutes in seconds
PASTE_PREFIX = "d1337:paste:"


@dataclass
class PasteData:
    content: str
    command: str
    exit_code: int
    execution_time_ms: int
    created_at: float


TERMINAL_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>D1337 Terminal</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #1a1a2e;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .terminal-window {
            background: #0d0d0d;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            width: 100%;
            max-width: 900px;
            overflow: hidden;
        }
        
        .terminal-header {
            background: linear-gradient(180deg, #3d3d3d 0%, #2d2d2d 100%);
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .terminal-buttons {
            display: flex;
            gap: 8px;
        }
        
        .terminal-button {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .btn-close { background: #ff5f56; }
        .btn-minimize { background: #ffbd2e; }
        .btn-maximize { background: #27ca40; }
        
        .terminal-title {
            flex: 1;
            text-align: center;
            color: #999;
            font-size: 13px;
            font-weight: 500;
        }
        
        .terminal-body {
            padding: 20px;
            min-height: 300px;
            max-height: 600px;
            overflow-y: auto;
        }
        
        .command-line {
            color: #27ca40;
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
            font-size: 14px;
            margin-bottom: 16px;
            display: flex;
            align-items: flex-start;
        }
        
        .prompt {
            color: #ff79c6;
            margin-right: 8px;
            white-space: nowrap;
        }
        
        .command {
            color: #f8f8f2;
            word-break: break-all;
        }
        
        .output {
            color: #f8f8f2;
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .output.error {
            color: #ff5555;
        }
        
        .cursor {
            display: inline-block;
            width: 8px;
            height: 16px;
            background: #27ca40;
            animation: blink 1s step-end infinite;
            vertical-align: middle;
            margin-left: 4px;
        }
        
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
        }
        
        .terminal-footer {
            padding: 12px 20px;
            border-top: 1px solid #2d2d2d;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: #666;
        }
        
        .exit-code {
            padding: 4px 8px;
            border-radius: 4px;
            font-family: monospace;
        }
        
        .exit-code.success { background: #1a3d1a; color: #27ca40; }
        .exit-code.error { background: #3d1a1a; color: #ff5555; }
        
        .meta-info {
            display: flex;
            gap: 16px;
        }
        
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #1a1a1a;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #444;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
</head>
<body>
    <div class="terminal-window">
        <div class="terminal-header">
            <div class="terminal-buttons">
                <div class="terminal-button btn-close"></div>
                <div class="terminal-button btn-minimize"></div>
                <div class="terminal-button btn-maximize"></div>
            </div>
            <div class="terminal-title">D1337 Terminal - {title}</div>
            <div style="width: 52px;"></div>
        </div>
        <div class="terminal-body">
            <div class="command-line">
                <span class="prompt">d1337@sandbox:~$</span>
                <span class="command">{command}</span>
            </div>
            <div class="output {output_class}">{output}</div>
            <span class="cursor"></span>
        </div>
        <div class="terminal-footer">
            <div class="exit-code {exit_class}">Exit: {exit_code}</div>
            <div class="meta-info">
                <span>Execution: {execution_time}ms</span>
                <span>D1337 Sandbox</span>
            </div>
        </div>
    </div>
</body>
</html>'''


class PasteServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.redis: Optional[redis.Redis] = None
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self._base_url: Optional[str] = None

    async def connect(self, redis_client: redis.Redis, base_url: Optional[str] = None):
        self.redis = redis_client
        self._base_url = base_url or f"http://{self.host}:{self.port}"
        
        self.app = web.Application()
        self.app.router.add_get("/p/{paste_id}", self.handle_paste_html)
        self.app.router.add_get("/p/{paste_id}/raw", self.handle_paste_raw)
        self.app.router.add_get("/health", self.handle_health)
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        logger.info(f"Paste server started on {self.host}:{self.port}")

    async def close(self):
        if self.runner:
            await self.runner.cleanup()
            logger.info("Paste server stopped")

    def _generate_paste_id(self) -> str:
        return secrets.token_urlsafe(16)

    async def create_paste(
        self,
        content: str,
        command: str,
        exit_code: int,
        execution_time_ms: int
    ) -> str:
        paste_id = self._generate_paste_id()
        key = f"{PASTE_PREFIX}{paste_id}"
        
        import json
        import time
        
        data = json.dumps({
            "content": content,
            "command": command,
            "exit_code": exit_code,
            "execution_time_ms": execution_time_ms,
            "created_at": time.time()
        })
        
        await self.redis.setex(key, PASTE_TTL, data)
        return f"{self._base_url}/p/{paste_id}"

    async def get_paste(self, paste_id: str) -> Optional[dict]:
        key = f"{PASTE_PREFIX}{paste_id}"
        data = await self.redis.get(key)
        
        if not data:
            return None
        
        import json
        return json.loads(data)

    async def handle_paste_html(self, request: web.Request) -> web.Response:
        paste_id = request.match_info["paste_id"]
        paste = await self.get_paste(paste_id)
        
        if not paste:
            return web.Response(
                text="Paste not found or expired",
                status=404,
                content_type="text/plain"
            )
        
        import html
        
        output_class = "error" if paste["exit_code"] != 0 else ""
        exit_class = "error" if paste["exit_code"] != 0 else "success"
        
        html_content = TERMINAL_HTML_TEMPLATE.format(
            title=html.escape(paste["command"][:50]),
            command=html.escape(paste["command"]),
            output=html.escape(paste["content"]),
            output_class=output_class,
            exit_class=exit_class,
            exit_code=paste["exit_code"],
            execution_time=paste["execution_time_ms"]
        )
        
        return web.Response(
            text=html_content,
            content_type="text/html"
        )

    async def handle_paste_raw(self, request: web.Request) -> web.Response:
        paste_id = request.match_info["paste_id"]
        paste = await self.get_paste(paste_id)
        
        if not paste:
            return web.Response(
                text="Paste not found or expired",
                status=404,
                content_type="text/plain"
            )
        
        return web.Response(
            text=paste["content"],
            content_type="text/plain"
        )

    async def handle_health(self, request: web.Request) -> web.Response:
        return web.Response(text="OK", content_type="text/plain")


paste_server = PasteServer()
