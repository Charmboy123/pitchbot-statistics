from typing import List, Optional
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Bot Configuration
    BOT_NAME: str = "ELITE FOOTBALL AI"
    BOT_SUBTITLE: str = "DEEP MATCH ANALYZER"
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")  # Your chat ID for direct bot communication
    
    # Football API Configuration
    FOOTBALL_API_KEY: str = os.getenv("FOOTBALL_API_KEY", "")
    FOOTBALL_API_URL: str = os.getenv("FOOTBALL_API_URL", "https://v3.football.api-sports.io")
    FOOTBALL_API_PROVIDER: str = os.getenv("FOOTBALL_API_PROVIDER", "api_football")
    
    # Odds API Configuration
    ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")
    ODDS_API_URL: str = os.getenv("ODDS_API_URL", "https://api.the-odds-api.com/v4")
    ODDS_API_PROVIDER: str = os.getenv("ODDS_API_PROVIDER", "the_odds_api")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./elite_football.db")
    
    # Admin Configuration
    ADMIN_USER_IDS: List[int] = []
    
    # Analysis Configuration
    MIN_PROBABILITY: float = float(os.getenv("MIN_PROBABILITY", "0.75"))
    MIN_EDGE: float = float(os.getenv("MIN_EDGE", "0.05"))
    MIN_DATA_QUALITY: float = float(os.getenv("MIN_DATA_QUALITY", "0.50"))
    MIN_MODEL_CONSENSUS: float = float(os.getenv("MIN_MODEL_CONSENSUS", "0.60"))
    MONTE_CARLO_SIMULATIONS: int = int(os.getenv("MONTE_CARLO_SIMULATIONS", "50000"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    PORT: int = int(os.getenv("PORT", "8080"))
    
    # Model Configuration
    ELO_INITIAL: float = 1500.0
    ELO_K_FACTOR: float = 20.0
    HOME_ADVANTAGE: float = 100.0
    
    # Model Weights (must sum to 1.0)
    WEIGHT_POISSON: float = 0.30
    WEIGHT_ELO: float = 0.25
    WEIGHT_MONTE_CARLO: float = 0.25
    WEIGHT_FORM: float = 0.20
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Parse admin user IDs from environment
admin_ids = os.getenv("ADMIN_USER_IDS", "")
if admin_ids:
    settings.ADMIN_USER_IDS = [int(id.strip()) for id in admin_ids.split(",") if id.strip()]
