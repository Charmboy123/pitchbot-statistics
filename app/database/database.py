from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import logging
from typing import Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

class Database:
    """Database connection manager"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        
    async def initialize(self):
        """Initialize database connection"""
        try:
            if self.database_url.startswith("sqlite"):
                self.engine = create_async_engine(
                    self.database_url,
                    echo=False,
                    future=True
                )
            else:
                self.engine = create_async_engine(
                    self.database_url,
                    echo=False,
                    future=True,
                    pool_size=20,
                    max_overflow=10
                )
            
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """Get a database session"""
        if not self.session_factory:
            await self.initialize()
        return self.session_factory()
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

database = Database(settings.DATABASE_URL)
