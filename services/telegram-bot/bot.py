import logging
import asyncio
import re
from typing import Optional

from telegram import Update, Bot
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
from api_gateway import api_gateway, SYSTEM_PROMPT

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
    remaining = await rate_limiter.get_remaining_queries(user.id, is_premium)
    
    welcome_msg = (
        f"Welcome to D1337 AI, {user.first_name}!\n\n"
        "I'm an advanced AI assistant created by DESORDEN.\n\n"
    )
    
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
        "/status - Check your usage status"
    )
    
    await update.message.reply_text(welcome_msg)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "D1337 AI Help\n\n"
        "Usage:\n"
        "- In groups: Mention me with @D1337Bot followed by your question\n"
        "- In DMs: Send me a message directly (Premium users only)\n\n"
        "Commands:\n"
        "/start - Welcome message\n"
        "/help - This help message\n"
        "/status - Check your usage and premium status\n\n"
        "Free Tier:\n"
        f"- {config.FREE_QUERY_LIMIT} queries per day in groups\n"
        "- No DM access\n\n"
        "Premium:\n"
        "- Unlimited queries\n"
        "- DM access\n"
        "- Priority support"
    )
    await update.message.reply_text(help_text)


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
    
    await update.message.reply_text(status_msg)


async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await db.is_admin(user.id):
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /grant <user_id or @username>")
        return
    
    target = context.args[0]
    
    if target.startswith("@"):
        await update.message.reply_text(
            "Please provide the numeric user ID. "
            "You can get it by having the user send /status first."
        )
        return
    
    try:
        target_id = int(target)
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.")
        return
    
    await db.get_or_create_user(telegram_id=target_id)
    success = await db.set_premium_status(target_id, True)
    
    if success:
        await update.message.reply_text(f"Premium access granted to user {target_id}")
        logger.info(f"Admin {user.id} granted premium to {target_id}")
    else:
        await update.message.reply_text(f"Failed to grant premium to user {target_id}")


async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await db.is_admin(user.id):
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /revoke <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric ID.")
        return
    
    success = await db.set_premium_status(target_id, False)
    
    if success:
        await update.message.reply_text(f"Premium access revoked from user {target_id}")
        logger.info(f"Admin {user.id} revoked premium from {target_id}")
    else:
        await update.message.reply_text(f"Failed to revoke premium from user {target_id}")


async def admin_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await db.is_admin(user.id):
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    global_stats = await db.get_global_stats()
    
    status_msg = (
        "D1337 Bot Admin Status\n\n"
        f"Total Users: {global_stats['total_users']}\n"
        f"Premium Users: {global_stats['premium_users']}\n"
        f"Total Queries: {global_stats['total_queries']}\n"
        f"Total Tokens: {global_stats['total_tokens']}"
    )
    
    await update.message.reply_text(status_msg)


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
    is_private = chat.type == ChatType.PRIVATE
    is_group = chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
    
    if is_private:
        if not is_premium:
            await update.message.reply_text(
                "DM access is only available for Premium users.\n\n"
                "You can still use me in groups by mentioning @D1337Bot!"
            )
            return
        query_text = message_text
    elif is_group:
        bot_username = context.bot.username
        mention_pattern = rf"@{bot_username}\s*(.*)"
        match = re.match(mention_pattern, message_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            if f"@{bot_username}" not in message_text.lower():
                return
            query_text = message_text.replace(f"@{bot_username}", "").strip()
        else:
            query_text = match.group(1).strip()
        
        if not query_text:
            await update.message.reply_text(
                "Please include your question after mentioning me!\n"
                f"Example: @{bot_username} What is Python?"
            )
            return
    else:
        return
    
    can_query, remaining = await rate_limiter.can_query(user.id, is_premium)
    
    if not can_query:
        ttl = await rate_limiter.get_ttl(user.id)
        hours = ttl // 3600
        minutes = (ttl % 3600) // 60
        
        await update.message.reply_text(
            f"You've reached your daily limit of {config.FREE_QUERY_LIMIT} free queries.\n\n"
            f"Your limit resets in {hours}h {minutes}m.\n\n"
            "Upgrade to Premium for unlimited queries!"
        )
        return
    
    thinking_msg = await update.message.reply_text("Thinking...")
    
    try:
        response_text, tokens_used, response_time_ms = await api_gateway.chat_completion(
            message=query_text,
            system_prompt=SYSTEM_PROMPT
        )
        
        await rate_limiter.increment_query_count(user.id)
        
        await db.log_usage(
            telegram_user_id=user.id,
            chat_id=chat.id,
            chat_type=chat.type,
            message_text=query_text,
            response_text=response_text,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms
        )
        
        await thinking_msg.edit_text(response_text)
        
        if not is_premium:
            new_remaining = remaining - 1
            if new_remaining <= 2 and new_remaining > 0:
                await update.message.reply_text(
                    f"You have {new_remaining} free queries remaining today."
                )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await thinking_msg.edit_text(
            "Sorry, I encountered an error processing your request. Please try again later."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")


async def post_init(application: Application):
    await db.connect()
    await rate_limiter.connect()
    await api_gateway.connect()
    logger.info("All services connected")


async def post_shutdown(application: Application):
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
    application.add_handler(CommandHandler("grant", grant_command))
    application.add_handler(CommandHandler("revoke", revoke_command))
    application.add_handler(CommandHandler("adminstatus", admin_status_command))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    application.add_error_handler(error_handler)
    
    logger.info("Starting D1337 Telegram Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
