import logging
import asyncio
import re
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ChatType, ParseMode

from config import config
from database import db
from rate_limiter import rate_limiter
from api_gateway import api_gateway, SYSTEM_PROMPT, SYSTEM_PROMPTS, get_system_prompt
from sandbox import sandbox, SandboxImage
from paste_server import paste_server
from voice_services import voice_services, VoiceEmotion, VoiceCharacter

# User mode storage (in-memory, resets on restart)
# Format: {user_id: "security" | "roleplay" | "vam"}
user_modes: dict[int, str] = {}

MAX_TELEGRAM_MESSAGE_LENGTH = 4096

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    is_premium = await db.is_premium_user(user.id)
    is_admin = await db.is_admin(user.id)
    remaining = await rate_limiter.get_remaining_queries(user.id, is_premium)
    
    welcome_msg = f"Welcome to D1337 AI, {user.first_name}!\n\n"
    welcome_msg += "I'm an advanced AI assistant created by DESORDEN.\n\n"
    
    if is_premium:
        welcome_msg += "You have Premium access with unlimited queries.\n\n"
    else:
        welcome_msg += f"You have {remaining}/{config.FREE_QUERY_LIMIT} free queries remaining today.\n\n"
    
    welcome_msg += (
        "How to use me:\n"
        "- In groups: Mention me with @D1337Bot\n"
        "- In DMs: Just send me a message (Premium only)\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/help - Get help\n"
        "/status - Check your usage status\n"
        "/mode - Switch AI mode (security/roleplay/vam)"
    )
    
    if is_admin:
        welcome_msg += (
            "\n\nAdmin Commands:\n"
            "/exec <cmd> - Execute command in sandbox\n"
            "/pt <cmd> - Pentesting tools (BlackArch)\n"
            "/do <task> - Natural language to command"
        )
    
    await update.message.reply_text(welcome_msg, quote=False)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = await db.is_admin(user.id)
    
    help_text = (
        "D1337 AI Help\n\n"
        "Usage:\n"
        "- In groups: Mention me with @D1337Bot followed by your question\n"
        "- In DMs: Send me a message directly (Premium users only)\n\n"
        "Commands:\n"
        "/start - Welcome message\n"
        "/help - This help message\n"
        "/status - Check your usage and premium status\n"
        "/mode - Switch AI mode (security/roleplay/vam)\n\n"
        "AI Modes:\n"
        "- security: Cybersecurity & pentesting expert\n\n"
        "Free Tier:\n"
        f"- {config.FREE_QUERY_LIMIT} queries per day in groups\n"
        "- No DM access\n\n"
        "Premium:\n"
        "- Unlimited queries\n"
        "- DM access\n"
        "- Priority support"
    )
    
    if is_admin:
        help_text += (
            "\n\nAdmin Commands:\n"
            "/exec <command> - Execute command in Alpine sandbox\n"
            "/pt <command> - Execute pentesting tools (BlackArch, network enabled)\n"
            "/do <description> - Convert natural language to command and execute\n"
            "/grant <user_id> - Grant premium to user\n"
            "/revoke <user_id> - Revoke premium from user\n"
            "/adminstatus - View bot statistics"
        )
    
    await update.message.reply_text(help_text, quote=False)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    stats = await db.get_user_stats(user.id)
    is_premium = stats["is_premium"]
    remaining = await rate_limiter.get_remaining_queries(user.id, is_premium)
    
    status_msg = f"Status for {user.first_name}\n\n"
    status_msg += f"Account Type: {'Premium' if is_premium else 'Free'}\n"
    
    if is_premium:
        status_msg += "Queries: Unlimited\n"
    else:
        status_msg += f"Queries Today: {config.FREE_QUERY_LIMIT - remaining}/{config.FREE_QUERY_LIMIT} used\n"
        status_msg += f"Remaining: {remaining}\n"
    
    status_msg += f"\nTotal Queries (All Time): {stats['total_queries']}\n"
    status_msg += f"Total Tokens Used: {stats['total_tokens']}"
    
    await update.message.reply_text(status_msg, quote=False)


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch between different AI modes: security, roleplay, vam"""
    user = update.effective_user
    is_admin = await db.is_admin(user.id)
    
    # Restricted modes only for admin/owner
    restricted_modes = ["roleplay", "vam"]
    
    # Show available modes based on user role
    if is_admin:
        available_modes = list(SYSTEM_PROMPTS.keys())
    else:
        available_modes = [m for m in SYSTEM_PROMPTS.keys() if m not in restricted_modes]
    
    if not context.args:
        current_mode = user_modes.get(user.id, "security")
        mode_list = "\n".join([f"- {m}" + (" (current)" if m == current_mode else "") for m in available_modes])
        
        help_text = (
            f"Current mode: {current_mode}\n\n"
            f"Available modes:\n{mode_list}\n\n"
            "Usage: /mode <mode_name>\n\n"
            "Modes:\n"
            "- security: Cybersecurity & pentesting expert"
        )
        
        if is_admin:
            help_text += (
                "\n- roleplay: Creative roleplay & storytelling (Admin only)"
                "\n- vam: Virt-A-Mate & VR assistant (Admin only)"
            )
        
        await update.message.reply_text(help_text, quote=False)
        return
    
    requested_mode = context.args[0].lower()
    
    # Check if mode exists
    if requested_mode not in SYSTEM_PROMPTS:
        await update.message.reply_text(
            f"Invalid mode: {requested_mode}\n"
            f"Available modes: {', '.join(available_modes)}",
            quote=False
        )
        return
    
    # Check if user has permission for restricted modes
    if requested_mode in restricted_modes and not is_admin:
        await update.message.reply_text(
            f"Mode '{requested_mode}' is restricted to admin/owner only.",
            quote=False
        )
        return
    
    user_modes[user.id] = requested_mode
    
    mode_descriptions = {
        "security": "Cybersecurity expert mode - pentesting, exploits, security research",
        "roleplay": "Creative roleplay mode - storytelling, characters, immersive scenarios",
        "vam": "VAM assistant mode - Virt-A-Mate, VR, 3D character creation"
    }
    
    await update.message.reply_text(
        f"Mode switched to: {requested_mode}\n\n"
        f"{mode_descriptions.get(requested_mode, '')}",
        quote=False
    )
    logger.info(f"User {user.id} switched to mode: {requested_mode}")


async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await db.is_admin(user.id):
        await update.message.reply_text("Admin only command.", quote=False)
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /exec <command>", quote=False)
        return
    
    command = " ".join(context.args)
    await _execute_in_sandbox(update, command, SandboxImage.ALPINE, enable_network=False)


async def pt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await db.is_admin(user.id):
        await update.message.reply_text("Admin only command.", quote=False)
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /pt <command>\n\n"
            "Examples:\n"
            "/pt nmap -sV target.com\n"
            "/pt nikto -h http://target.com\n"
            "/pt sqlmap -u 'http://target.com/?id=1'",
            quote=False
        )
        return
    
    command = " ".join(context.args)
    await _execute_in_sandbox(update, command, SandboxImage.BLACKARCH, enable_network=True)


async def do_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await db.is_admin(user.id):
        await update.message.reply_text("Admin only command.", quote=False)
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /do <natural language description>\n\n"
            "Examples:\n"
            "/do list all files in current directory\n"
            "/do show system info\n"
            "/do find all python files",
            quote=False
        )
        return
    
    task_description = " ".join(context.args)
    thinking_msg = await update.message.reply_text("Converting to command...", quote=False)
    
    try:
        nl_to_cmd_prompt = """You are a command-line expert. Convert the user's natural language request into a single shell command.
Rules:
- Output ONLY the command, nothing else
- Use common Linux utilities (ls, cat, grep, find, curl, etc.)
- Keep commands safe and non-destructive
- If the request is unclear, use the most likely interpretation

User request: """ + task_description
        
        command, _, _ = await api_gateway.chat_completion(
            message=nl_to_cmd_prompt,
            system_prompt=None
        )
        
        command = command.strip().strip('`').strip()
        if command.startswith("bash") or command.startswith("sh"):
            command = command.split(None, 2)[-1] if len(command.split()) > 2 else command
        
        await thinking_msg.edit_text(f"Executing: {command}")
        await _execute_in_sandbox(update, command, SandboxImage.ALPINE, enable_network=False, status_msg=thinking_msg)
        
    except Exception as e:
        logger.error(f"Error in /do command: {e}")
        await thinking_msg.edit_text(f"Error: {str(e)}")


async def _execute_in_sandbox(
    update: Update,
    command: str,
    image: SandboxImage,
    enable_network: bool = False,
    status_msg=None
):
    user = update.effective_user
    
    if status_msg is None:
        status_msg = await update.message.reply_text(
            f"Executing in {'BlackArch' if image == SandboxImage.BLACKARCH else 'Alpine'} sandbox...",
            quote=False
        )
    
    try:
        result = await sandbox.execute(
            command=command,
            image=image,
            enable_network=enable_network,
            timeout=120 if image == SandboxImage.BLACKARCH else 60
        )
        
        output = result.stdout if result.stdout else result.stderr
        if result.error:
            output = f"Error: {result.error}"
        if result.timed_out:
            output = f"Command timed out\n\n{output}" if output else "Command timed out"
        
        if not output:
            output = "(no output)"
        
        paste_url = await paste_server.create_paste(
            content=output,
            command=command,
            exit_code=result.exit_code,
            execution_time_ms=result.execution_time_ms
        )
        
        if len(output) > MAX_TELEGRAM_MESSAGE_LENGTH - 200:
            response = (
                f"Command: {command}\n"
                f"Exit: {result.exit_code} | Time: {result.execution_time_ms}ms\n\n"
                f"Output too long. View here:\n{paste_url}"
            )
        else:
            response = (
                f"Command: {command}\n"
                f"Exit: {result.exit_code} | Time: {result.execution_time_ms}ms\n\n"
                f"```\n{output[:3500]}\n```\n\n"
                f"Full output: {paste_url}"
            )
        
        await status_msg.delete()
        await update.message.reply_text(
            response,
            quote=False,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )
        
        await db.log_usage(
            telegram_user_id=user.id,
            chat_id=update.effective_chat.id,
            chat_type=str(update.effective_chat.type),
            message_text=f"/exec {command}",
            response_text=output[:1000],
            tokens_used=0,
            response_time_ms=result.execution_time_ms
        )
        
    except Exception as e:
        logger.error(f"Sandbox execution error: {e}")
        await status_msg.edit_text(f"Execution failed: {str(e)}")


async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await db.is_admin(user.id):
        await update.message.reply_text("You don't have permission to use this command.", quote=False)
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /grant <user_id or @username>", quote=False)
        return
    
    target = context.args[0]
    
    if target.startswith("@"):
        await update.message.reply_text(
            "Please provide the numeric user ID. "
            "You can get it by having the user send /status first.",
            quote=False
        )
        return
    
    try:
        target_id = int(target)
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.", quote=False)
        return
    
    await db.get_or_create_user(telegram_id=target_id)
    success = await db.set_premium_status(target_id, True)
    
    if success:
        await update.message.reply_text(f"Premium access granted to user {target_id}", quote=False)
        logger.info(f"Admin {user.id} granted premium to {target_id}")
    else:
        await update.message.reply_text(f"Failed to grant premium to user {target_id}", quote=False)


async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await db.is_admin(user.id):
        await update.message.reply_text("You don't have permission to use this command.", quote=False)
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /revoke <user_id>", quote=False)
        return
    
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.", quote=False)
        return
    
    success = await db.set_premium_status(target_id, False)
    
    if success:
        await update.message.reply_text(f"Premium access revoked from user {target_id}", quote=False)
        logger.info(f"Admin {user.id} revoked premium from {target_id}")
    else:
        await update.message.reply_text(f"Failed to revoke premium from user {target_id}", quote=False)


async def admin_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await db.is_admin(user.id):
        await update.message.reply_text("You don't have permission to use this command.", quote=False)
        return
    
    global_stats = await db.get_global_stats()
    docker_available = await sandbox.check_docker_available()
    
    status_msg = (
        "D1337 Bot Admin Status\n\n"
        f"Total Users: {global_stats['total_users']}\n"
        f"Premium Users: {global_stats['premium_users']}\n"
        f"Total Queries: {global_stats['total_queries']}\n"
        f"Total Tokens: {global_stats['total_tokens']}\n\n"
        f"Docker Status: {'Available' if docker_available else 'Not Available'}"
    )
    
    await update.message.reply_text(status_msg, quote=False)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    message_text = update.message.text
    
    await db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    is_premium = await db.is_premium_user(user.id)
    is_admin = await db.is_admin(user.id)
    is_private = chat.type == ChatType.PRIVATE
    is_group = chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
    
    if is_admin and is_private:
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, message_text)
        if urls and len(message_text.split()) <= 3:
            domain = urls[0].split('/')[2] if len(urls[0].split('/')) > 2 else urls[0]
            await update.message.reply_text(
                f"Detected URL: {urls[0]}\n\n"
                "Quick scan options:\n"
                f"/pt nmap -sV -Pn {domain}\n"
                f"/pt nikto -h {urls[0]}",
                quote=False
            )
            return
    
    if is_private:
        if not is_premium and not is_admin:
            await update.message.reply_text(
                "DM access is only available for Premium users.\n\n"
                "You can still use me in groups by mentioning @D1337Bot!",
                quote=False
            )
            return
        query_text = message_text
    elif is_group:
        bot_username = context.bot.username
        mention_pattern = rf"@{bot_username}\s*(.*)"
        match = re.match(mention_pattern, message_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            if f"@{bot_username.lower()}" not in message_text.lower():
                return
            query_text = re.sub(rf"@{bot_username}", "", message_text, flags=re.IGNORECASE).strip()
        else:
            query_text = match.group(1).strip()
        
        if not query_text:
            return
    else:
        return
    
    can_query, remaining = await rate_limiter.can_query(user.id, is_premium or is_admin)
    
    if not can_query:
        ttl = await rate_limiter.get_ttl(user.id)
        hours = ttl // 3600
        minutes = (ttl % 3600) // 60
        
        await update.message.reply_text(
            f"You've reached your daily limit of {config.FREE_QUERY_LIMIT} free queries.\n\n"
            f"Your limit resets in {hours}h {minutes}m.\n\n"
            "Upgrade to Premium for unlimited queries!",
            quote=False
        )
        return
    
    thinking_msg = await update.message.reply_text("Thinking...", quote=False)
    
    try:
        logger.info(f"Processing message from user {user.id} in {chat.type}: {query_text[:50]}...")
        
        # Get user's current mode and corresponding system prompt
        current_mode = user_modes.get(user.id, "security")
        system_prompt = get_system_prompt(current_mode)
        
        response_text, tokens_used, response_time_ms = await api_gateway.chat_completion(
            message=query_text,
            system_prompt=system_prompt
        )
        
        logger.info(f"API response received in {response_time_ms}ms, tokens: {tokens_used}")
        
        await rate_limiter.increment_query_count(user.id)
        
        await db.log_usage(
            telegram_user_id=user.id,
            chat_id=chat.id,
            chat_type=str(chat.type),
            message_text=query_text,
            response_text=response_text,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms
        )
        
        await thinking_msg.delete()
        await update.message.reply_text(
            response_text,
            quote=False,
            disable_web_page_preview=False
        )
        
        if not is_premium and not is_admin:
            new_remaining = remaining - 1
            if new_remaining <= 2 and new_remaining > 0:
                await update.message.reply_text(
                    f"You have {new_remaining} free queries remaining today.",
                    quote=False
                )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await thinking_msg.edit_text(
            "Sorry, I encountered an error processing your request. Please try again later."
        )


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages - transcribe and process with self-hosted voice services"""
    user = update.effective_user
    chat = update.effective_chat
    
    await db.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    is_premium = await db.is_premium_user(user.id)
    is_admin = await db.is_admin(user.id)
    is_private = chat.type == ChatType.PRIVATE
    current_mode = user_modes.get(user.id, "security")
    
    # Voice features are ADMIN ONLY for roleplay/vam modes
    # Security mode voice is available to premium users
    restricted_modes = ["roleplay", "vam"]
    if current_mode in restricted_modes and not is_admin:
        await update.message.reply_text(
            "Voice features for this mode are admin-only.",
            quote=False
        )
        return
    
    # Check permissions for security mode
    if is_private and not is_premium and not is_admin:
        await update.message.reply_text(
            "Voice messages are only available for Premium users in DMs.\n"
            "Use me in groups instead!",
            quote=False
        )
        return
    
    # Rate limit check
    can_query, remaining = await rate_limiter.can_query(user.id, is_premium or is_admin)
    if not can_query:
        await update.message.reply_text(
            f"You've reached your daily limit. Try again later.",
            quote=False
        )
        return
    
    thinking_msg = await update.message.reply_text("Processing voice message...", quote=False)
    
    try:
        # Download voice file
        voice = update.message.voice
        voice_file = await context.bot.get_file(voice.file_id)
        
        # Download to memory
        import io
        voice_bytes = io.BytesIO()
        await voice_file.download_to_memory(voice_bytes)
        audio_data = voice_bytes.getvalue()
        
        # Try self-hosted STT first (Faster-Whisper on H100)
        transcribed_text = None
        
        if config.VOICE_ENABLED and voice_services.stt_available:
            stt_result = await voice_services.transcribe(audio_data)
            if stt_result:
                transcribed_text = stt_result.text
                logger.info(f"Self-hosted STT: {transcribed_text[:50]}... (lang: {stt_result.language})")
        
        # Fallback to OpenAI Whisper API if self-hosted not available
        if not transcribed_text and config.OPENAI_API_KEY:
            try:
                import openai
                import tempfile
                client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
                
                with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name
                
                with open(tmp_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                    transcribed_text = transcript.text
                
                import os
                os.unlink(tmp_path)
                logger.info(f"OpenAI Whisper fallback: {transcribed_text[:50]}...")
                
            except Exception as e:
                logger.warning(f"Whisper transcription failed: {e}")
        
        if not transcribed_text:
            await thinking_msg.edit_text(
                "Voice transcription not available. Self-hosted STT service may be offline."
            )
            return
        
        await thinking_msg.edit_text(f"Transcribed: {transcribed_text[:100]}...\n\nProcessing...")
        
        # Get system prompt for current mode
        system_prompt = get_system_prompt(current_mode)
        
        response_text, tokens_used, response_time_ms = await api_gateway.chat_completion(
            message=transcribed_text,
            system_prompt=system_prompt
        )
        
        await rate_limiter.increment_query_count(user.id)
        
        await db.log_usage(
            telegram_user_id=user.id,
            chat_id=chat.id,
            chat_type=str(chat.type),
            message_text=f"[VOICE] {transcribed_text}",
            response_text=response_text,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms
        )
        
        await thinking_msg.delete()
        
        # For admin in roleplay/vam mode, try to send voice response
        if is_admin and current_mode in restricted_modes and config.VOICE_RESPONSE_ENABLED and voice_services.tts_available:
            try:
                # Detect emotion from response
                emotion = voice_services.detect_emotion_from_text(response_text)
                
                # Choose character based on mode
                character = VoiceCharacter.ANIME_FEMALE if current_mode in ["roleplay", "vam"] else VoiceCharacter.ASSISTANT
                
                tts_result = await voice_services.synthesize(
                    text=response_text[:500],  # Limit TTS length
                    emotion=emotion,
                    character=character
                )
                
                if tts_result and tts_result.audio_data:
                    # Send voice response
                    voice_io = io.BytesIO(tts_result.audio_data)
                    voice_io.name = "response.ogg"
                    await update.message.reply_voice(
                        voice=voice_io,
                        caption=response_text[:1000] if len(response_text) > 500 else None,
                        quote=False
                    )
                    logger.info(f"Voice response sent for user {user.id} (mode: {current_mode}, emotion: {emotion.value})")
                    return
            except Exception as e:
                logger.warning(f"TTS failed, falling back to text: {e}")
        
        # Default: send text response
        await update.message.reply_text(
            response_text,
            quote=False,
            disable_web_page_preview=False
        )
        
        logger.info(f"Voice message processed for user {user.id}: {transcribed_text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await thinking_msg.edit_text(
            "Sorry, I couldn't process your voice message. Please try again or send text."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")


async def post_init(application: Application):
    await db.connect()
    await rate_limiter.connect()
    await api_gateway.connect()
    
    await paste_server.connect(
        redis_client=rate_limiter.redis,
        base_url=config.PASTE_SERVER_URL if hasattr(config, 'PASTE_SERVER_URL') else None
    )
    
    # Connect voice services (self-hosted STT/TTS on H100)
    if config.VOICE_ENABLED:
        voice_services._client = None  # Reset client
        voice_services.stt_url = config.STT_SERVICE_URL
        voice_services.tts_url = config.TTS_SERVICE_URL
        await voice_services.connect()
        if voice_services.stt_available:
            logger.info(f"Voice STT service connected: {config.STT_SERVICE_URL}")
        if voice_services.tts_available:
            logger.info(f"Voice TTS service connected: {config.TTS_SERVICE_URL}")
    
    if await sandbox.check_docker_available():
        logger.info("Docker available, pulling sandbox images...")
        asyncio.create_task(sandbox.pull_images())
    else:
        logger.warning("Docker not available - sandbox commands will fail")
    
    logger.info("All services connected")


async def post_shutdown(application: Application):
    await paste_server.close()
    await voice_services.close()
    await db.close()
    await rate_limiter.close()
    await api_gateway.close()
    logger.info("All services disconnected")


def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("mode", mode_command))
    application.add_handler(CommandHandler("exec", exec_command))
    application.add_handler(CommandHandler("pt", pt_command))
    application.add_handler(CommandHandler("do", do_command))
    application.add_handler(CommandHandler("grant", grant_command))
    application.add_handler(CommandHandler("revoke", revoke_command))
    application.add_handler(CommandHandler("adminstatus", admin_status_command))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # Voice message handler
    application.add_handler(MessageHandler(
        filters.VOICE,
        handle_voice_message
    ))
    
    application.add_error_handler(error_handler)
    
    logger.info("Starting D1337 Telegram Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
