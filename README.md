# Elite Football AI - Deep Match Analyzer

A production-ready Telegram bot for deep football match analysis using multiple statistical models and real-time data.

## Your API Keys

You have:
- ✅ Telegram Bot Token
- ✅ Telegram Chat ID
- ✅ Football Data API Key
- ✅ Odds API Key

## Quick Deployment Guide

### 1. Local Setup

```bash
# Clone repository
git clone https://github.com/yourusername/elite-football-ai.git
cd elite-football-ai

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your actual API keys

# Run locally
uvicorn app.main:app --reload
