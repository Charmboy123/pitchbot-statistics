from fastapi import FastAPI, Request
from telegram.ext import Application, ApplicationBuilder
import logging
import asyncio
from contextlib import asynccontextmanager
import json

from app.config.settings import settings
from app.bot.handlers import TelegramHandlers
from app.database.database import database

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
telegram_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global telegram_app
    
    # Startup
    logger.info(f"Starting {settings.BOT_NAME}...")
    
    # Initialize database
    await database.initialize()
    logger.info("Database initialized")
    
    # Initialize Telegram bot
    if settings.TELEGRAM_BOT_TOKEN:
        handlers = TelegramHandlers()
        telegram_app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        for handler in handlers.get_handlers():
            telegram_app.add_handler(handler)
        
        # Start bot
        if settings.ENVIRONMENT == "production" and settings.WEBHOOK_URL:
            # Use webhook in production
            await telegram_app.initialize()
            await telegram_app.start()
            logger.info("Telegram bot started with webhook")
        else:
            # Use polling in development
            await telegram_app.initialize()
            await telegram_app.start()
            await telegram_app.updater.start_polling()
            logger.info("Telegram bot started with polling")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not configured")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.BOT_NAME}...")
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Elite Football AI",
    description="Deep Match Analyzer Telegram Bot",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.BOT_NAME,
        "subtitle": settings.BOT_SUBTITLE,
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    db_status = await database.health_check()
    
    return {
        "status": "ok" if db_status else "degraded",
        "database": "ok" if db_status else "error",
        "telegram": "ok" if telegram_app else "not_initialized",
        "environment": settings.ENVIRONMENT
    }

@app.get("/status")
async def status():
    """Detailed status endpoint"""
    return {
        "bot_name": settings.BOT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": "configured" if settings.DATABASE_URL else "missing",
        "telegram_token": "configured" if settings.TELEGRAM_BOT_TOKEN else "missing",
        "football_api_key": "configured" if settings.FOOTBALL_API_KEY else "missing",
        "odds_api_key": "configured" if settings.ODDS_API_KEY else "missing",
        "monte_carlo_simulations": settings.MONTE_CARLO_SIMULATIONS,
        "version": "1.0.0"
    }

@app.post("/webhook")
async def webhook(request: Request):
    """Telegram webhook endpoint"""
    if telegram_app:
        try:
            data = await request.json()
            await telegram_app.update_queue.put(
                telegram_app.update_queue._bot.parse_update(data)
            )
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return {"status": "error", "message": str(e)}, 500
    else:
        return {"status": "error", "message": "Bot not initialized"}, 503

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
