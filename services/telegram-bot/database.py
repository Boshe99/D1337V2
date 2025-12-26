import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg

from config import config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                config.DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created")
            await self._init_schema()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def _init_schema(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS telegram_users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    is_premium BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id SERIAL PRIMARY KEY,
                    telegram_user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    chat_type VARCHAR(50) NOT NULL,
                    message_text TEXT,
                    response_text TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    response_time_ms INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    granted_by BIGINT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_telegram_users_telegram_id 
                ON telegram_users(telegram_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_logs_telegram_user_id 
                ON usage_logs(telegram_user_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at 
                ON usage_logs(created_at)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_admin_users_telegram_id 
                ON admin_users(telegram_id)
            """)
            logger.info("Database schema initialized")
            
            await self._bootstrap_admins()

    async def _bootstrap_admins(self):
        if not config.INITIAL_ADMIN_IDS:
            return
        
        async with self.pool.acquire() as conn:
            for admin_id in config.INITIAL_ADMIN_IDS:
                try:
                    await conn.execute("""
                        INSERT INTO admin_users (telegram_id, granted_by)
                        VALUES ($1, $1)
                        ON CONFLICT (telegram_id) DO NOTHING
                    """, admin_id)
                    logger.info(f"Bootstrapped admin user: {admin_id}")
                except Exception as e:
                    logger.error(f"Failed to bootstrap admin {admin_id}: {e}")

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def get_or_create_user(
        self, 
        telegram_id: int, 
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> dict:
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM telegram_users WHERE telegram_id = $1",
                telegram_id
            )
            if user:
                if username or first_name or last_name:
                    await conn.execute("""
                        UPDATE telegram_users 
                        SET username = COALESCE($2, username),
                            first_name = COALESCE($3, first_name),
                            last_name = COALESCE($4, last_name),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE telegram_id = $1
                    """, telegram_id, username, first_name, last_name)
                return dict(user)
            
            user = await conn.fetchrow("""
                INSERT INTO telegram_users (telegram_id, username, first_name, last_name)
                VALUES ($1, $2, $3, $4)
                RETURNING *
            """, telegram_id, username, first_name, last_name)
            return dict(user)

    async def is_premium_user(self, telegram_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT is_premium FROM telegram_users WHERE telegram_id = $1",
                telegram_id
            )
            return result or False

    async def set_premium_status(self, telegram_id: int, is_premium: bool) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE telegram_users SET is_premium = $2, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = $1
            """, telegram_id, is_premium)
            return "UPDATE 1" in result

    async def is_admin(self, telegram_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM admin_users WHERE telegram_id = $1",
                telegram_id
            )
            return result > 0

    async def add_admin(self, telegram_id: int, granted_by: int) -> bool:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO admin_users (telegram_id, granted_by)
                    VALUES ($1, $2)
                    ON CONFLICT (telegram_id) DO NOTHING
                """, telegram_id, granted_by)
                return True
            except Exception as e:
                logger.error(f"Failed to add admin: {e}")
                return False

    async def remove_admin(self, telegram_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM admin_users WHERE telegram_id = $1",
                telegram_id
            )
            return "DELETE 1" in result

    async def log_usage(
        self,
        telegram_user_id: int,
        chat_id: int,
        chat_type: str,
        message_text: str,
        response_text: str,
        tokens_used: int = 0,
        response_time_ms: int = 0
    ):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO usage_logs 
                (telegram_user_id, chat_id, chat_type, message_text, response_text, tokens_used, response_time_ms)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, telegram_user_id, chat_id, chat_type, message_text, response_text, tokens_used, response_time_ms)

    async def get_user_stats(self, telegram_id: int) -> dict:
        async with self.pool.acquire() as conn:
            total_queries = await conn.fetchval(
                "SELECT COUNT(*) FROM usage_logs WHERE telegram_user_id = $1",
                telegram_id
            )
            total_tokens = await conn.fetchval(
                "SELECT COALESCE(SUM(tokens_used), 0) FROM usage_logs WHERE telegram_user_id = $1",
                telegram_id
            )
            user = await conn.fetchrow(
                "SELECT * FROM telegram_users WHERE telegram_id = $1",
                telegram_id
            )
            return {
                "total_queries": total_queries or 0,
                "total_tokens": total_tokens or 0,
                "is_premium": user["is_premium"] if user else False,
                "created_at": user["created_at"] if user else None
            }

    async def get_global_stats(self) -> dict:
        async with self.pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM telegram_users")
            premium_users = await conn.fetchval(
                "SELECT COUNT(*) FROM telegram_users WHERE is_premium = TRUE"
            )
            total_queries = await conn.fetchval("SELECT COUNT(*) FROM usage_logs")
            total_tokens = await conn.fetchval(
                "SELECT COALESCE(SUM(tokens_used), 0) FROM usage_logs"
            )
            return {
                "total_users": total_users or 0,
                "premium_users": premium_users or 0,
                "total_queries": total_queries or 0,
                "total_tokens": total_tokens or 0
            }


db = Database()
