# D1337 Telegram Bot

A production-ready Telegram bot for D1337 AI with freemium model support.

## Features

- **Group Mentions**: Respond to mentions in groups (@D1337Bot)
- **DM Support**: Handle direct messages for premium users
- **Freemium Model**: 5 free queries per day in groups, unlimited for premium
- **Admin Commands**: /grant, /revoke, /status for user management
- **Rate Limiting**: Redis-based rate limiting
- **Usage Logging**: PostgreSQL logging for analytics

## Setup

### Prerequisites

- Python 3.11+
- Redis
- PostgreSQL
- Telegram Bot Token (from @BotFather)

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
BOT_TOKEN=your_telegram_bot_token
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:password@localhost:5432/d1337
HYPERBOLIC_KEY=your_hyperbolic_api_key
API_GATEWAY_URL=https://api.hyperbolic.xyz/v1
BOT_USERNAME=D1337Bot
```

### Installation

```bash
pip install -r requirements.txt
python bot.py
```

### Docker

```bash
docker build -t d1337-telegram-bot .
docker run -d --env-file .env d1337-telegram-bot
```

## Commands

### User Commands
- `/start` - Welcome message and usage info
- `/help` - Help information
- `/status` - Check your usage and premium status

### Admin Commands
- `/grant <user_id>` - Grant premium access to a user
- `/revoke <user_id>` - Revoke premium access from a user
- `/adminstatus` - View global bot statistics

## Usage

### In Groups
Mention the bot with your question:
```
@D1337Bot What is Python?
```

### In DMs (Premium Only)
Send your message directly to the bot.

## Database Schema

The bot automatically creates the following tables:
- `telegram_users` - User information and premium status
- `usage_logs` - Query logs for analytics
- `admin_users` - Admin user list

## Architecture

```
bot.py          - Main bot application
config.py       - Configuration management
database.py     - PostgreSQL database operations
rate_limiter.py - Redis rate limiting
api_gateway.py  - LLM API integration
```

## License

Part of the D1337 AI project by DESORDEN.
