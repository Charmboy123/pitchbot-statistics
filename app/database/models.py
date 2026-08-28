from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database.database import Base

class User(Base):
    """Telegram user model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    chat_id = Column(String(100), nullable=True)
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    analyses = relationship("AnalysisSession", back_populates="user")

class Team(Base):
    """Football team model"""
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), index=True)
    normalized_name = Column(String(255), index=True)
    country = Column(String(100), nullable=True)
    league_id = Column(Integer, nullable=True)
    logo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Competition(Base):
    """Football competition/league model"""
    __tablename__ = "competitions"
    
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), index=True)
    country = Column(String(100))
    season = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Fixture(Base):
    """Football fixture model"""
    __tablename__ = "fixtures"
    
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, unique=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"))
    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))
    kickoff_time = Column(DateTime(timezone=True))
    venue = Column(String(255), nullable=True)
    status = Column(String(50))
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    competition = relationship("Competition")

class AnalysisSession(Base):
    """Analysis session model"""
    __tablename__ = "analysis_sessions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(50), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    fixture_id = Column(Integer, ForeignKey("fixtures.id"), nullable=True)
    home_team_name = Column(String(255))
    away_team_name = Column(String(255))
    status = Column(String(50))
    data_quality_score = Column(Float, nullable=True)
    model_consensus_score = Column(Float, nullable=True)
    final_verdict = Column(String(50), nullable=True)
    analysis_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="analyses")
    fixture = relationship("Fixture")
    predictions = relationship("Prediction", back_populates="session")

class Prediction(Base):
    """Prediction model"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("analysis_sessions.id"))
    market_type = Column(String(100))
    market_name = Column(String(255))
    probability = Column(Float)
    confidence = Column(Float)
    fair_odds = Column(Float, nullable=True)
    bookmaker_odds = Column(Float, nullable=True)
    edge = Column(Float, nullable=True)
    risk_level = Column(String(50))
    recommendation = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("AnalysisSession", back_populates="predictions")

class ModelPerformance(Base):
    """Model performance tracking"""
    __tablename__ = "model_performance"
    
    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"))
    actual_outcome = Column(String(100))
    brier_score = Column(Float, nullable=True)
    log_loss = Column(Float, nullable=True)
    correct = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
