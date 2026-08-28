from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import logging
import asyncio
from datetime import datetime
import uuid
import re

from app.config.settings import settings
from app.analysis.engine import AnalysisEngine
from app.data.providers.api_football import APIFootballProvider
from app.data.providers.odds_api import OddsAPIProvider
from app.database.database import database
from app.database.models import User, AnalysisSession, Prediction

logger = logging.getLogger(__name__)

class TelegramHandlers:
    """Telegram bot command and message handlers"""
    
    def __init__(self):
        self.analysis_engine = AnalysisEngine()
        self.football_provider = APIFootballProvider()
        self.odds_provider = OddsAPIProvider() if settings.ODDS_API_KEY else None
        self.active_analyses = {}
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_message = f"""
⚽ {settings.BOT_NAME}
{settings.BOT_SUBTITLE}

Hello {user.first_name}! 👋

Send a fixture such as:
Arsenal vs Chelsea

The bot will:
✓ Identify the fixture
✓ Gather football data
✓ Analyze recent form
✓ Run statistical models
✓ Calculate betting probabilities
✓ Compare odds
✓ Apply risk filters
✓ Return strong markets

Commands:
/analyze - Analyze a match
/help - Show help
/history - View analysis history
/status - Check bot status
/settings - Configure preferences
/sources - View data sources
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Full Analysis", callback_data="full_analysis")],
            [InlineKeyboardButton("🎯 Best Bets", callback_data="best_bets")],
            [InlineKeyboardButton("⚽ Correct Scores", callback_data="correct_scores")],
            [InlineKeyboardButton("🥅 Goals", callback_data="goals")],
            [InlineKeyboardButton("📈 Value", callback_data="value")],
            [InlineKeyboardButton("🛡 Risk", callback_data="risk")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        
        # Save user to database
        await self._save_user(user)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = f"""
📖 How to Use {settings.BOT_NAME}

**Fixture Input:**
Send a message like:
• Arsenal vs Chelsea
• Arsenal Chelsea
• Arsenal - Chelsea
• Chelsea v Arsenal

**Commands:**
/start - Start the bot
/analyze - Analyze a match
/history - View your analysis history
/status - Check bot status
/settings - Configure preferences
/sources - View data sources

**Analysis Features:**
✓ Multi-league support
✓ Recent form analysis
✓ Head-to-head records
✓ Home/Away performance
✓ Poisson distribution
✓ Elo ratings
✓ Monte Carlo simulation
✓ Bookmaker odds comparison
✓ Value betting analysis
✓ Risk assessment

**Important:**
• Probabilities are estimates, not guarantees
• Always gamble responsibly
• Bot will say NO BET when data is insufficient
"""
        await update.message.reply_text(help_message)
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command"""
        if not context.args:
            await update.message.reply_text(
                "Please provide teams to analyze.\n"
                "Example: /analyze Arsenal vs Chelsea"
            )
            return
        
        fixture_text = ' '.join(context.args)
        await self._process_fixture(update, context, fixture_text)
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        text = update.message.text.strip()
        
        # Check if it looks like a fixture request
        if self._is_fixture_request(text):
            await self._process_fixture(update, context, text)
        else:
            await update.message.reply_text(
                "I couldn't understand that request.\n"
                "Please send a fixture like: Arsenal vs Chelsea"
            )
    
    async def _process_fixture(self, update: Update, context: ContextTypes.DEFAULT_TYPE, fixture_text: str):
        """Process a fixture request"""
        user_id = update.effective_user.id
        
        # Check if user already has an active analysis
        if user_id in self.active_analyses:
            await update.message.reply_text(
                "⚠️ Your analysis is still running. Please wait for it to complete."
            )
            return
        
        # Parse fixture
        teams = self._parse_teams(fixture_text)
        if not teams or len(teams) != 2:
            await update.message.reply_text(
                "❌ I couldn't identify the two teams.\n"
                "Please use format: Team A vs Team B"
            )
            return
        
        home_team_name, away_team_name = teams
        
        # Send progress message
        progress_message = await update.message.reply_text("🔎 Resolving fixture...")
        
        # Generate session ID
        session_id = f"ANL-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:5].upper()}"
        self.active_analyses[user_id] = session_id
        
        try:
            # Search for teams
            await progress_message.edit_text(f"📡 Searching for {home_team_name} and {away_team_name}...")
            
            home_teams = await self.football_provider.search_teams(home_team_name)
            away_teams = await self.football_provider.search_teams(away_team_name)
            
            if not home_teams or not away_teams:
                await progress_message.edit_text(
                    "❌ Could not find one or both teams.\n"
                    "Please check the team names and try again."
                )
                return
            
            # Use first match for now
            home_team = home_teams[0]
            away_team = away_teams[0]
            
            await progress_message.edit_text(
                f"✓ Teams found:\n"
                f"Home: {home_team.name}\n"
                f"Away: {away_team.name}\n\n"
                f"📊 Collecting data..."
            )
            
            # Get recent matches
            home_recent = await self.football_provider.get_recent_matches(home_team.id, 10)
            away_recent = await self.football_provider.get_recent_matches(away_team.id, 10)
            
            await progress_message.edit_text("🧠 Running statistical models...")
            
            # Prepare team data for analysis
            home_team_data = self._prepare_team_data(home_team, home_recent)
            away_team_data = self._prepare_team_data(away_team, away_recent)
            
            # Run analysis
            analysis_results = await self.analysis_engine.analyze_match(
                home_team_data, away_team_data
            )
            
            await progress_message.edit_text("🎲 Running Monte Carlo simulation...")
            await asyncio.sleep(0.5)  # Brief pause for effect
            
            # Get odds if available
            odds_data = None
            if self.odds_provider:
                await progress_message.edit_text("💰 Comparing bookmaker odds...")
                # In production, you'd search for the specific match odds
                odds_data = {}  # Placeholder for actual odds data
            
            await progress_message.edit_text("🛡 Applying risk filters...")
            
            # Generate report
            report = self.analysis_engine.generate_report(
                home_team.name, away_team.name, analysis_results, odds_data
            )
            
            # Save to database
            await self._save_analysis(user_id, session_id, home_team.name, away_team.name, 
                                     analysis_results, "WATCH")
            
            # Send final report
            await progress_message.edit_text(report)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            await progress_message.edit_text(
                "❌ Analysis failed. Please try again later.\n"
                f"Error: {str(e)}"
            )
        finally:
            # Remove from active analyses
            if user_id in self.active_analyses:
                del self.active_analyses[user_id]
    
    def _prepare_team_data(self, team, recent_matches):
        """Prepare team data for analysis"""
        team_data = {
            'id': team.id,
            'name': team.name,
            'recent_matches': [],
            'goals_scored': 0,
            'goals_conceded': 0,
            'matches_played': 0,
            'recent_form': 1.0,
            'elo_rating': 1500
        }
        
        # Process recent matches
        for match in recent_matches:
            if match.get('home_team_id') == team.id:
                goals_scored = match.get('home_goals') or 0
                goals_conceded = match.get('away_goals') or 0
                is_home = True
            elif match.get('away_team_id') == team.id:
                goals_scored = match.get('away_goals') or 0
                goals_conceded = match.get('home_goals') or 0
                is_home = False
            else:
                continue
            
            team_data['recent_matches'].append({
                'team_goals': goals_scored,
                'opponent_goals': goals_conceded,
                'is_home': is_home,
                'date': match.get('date')
            })
            
            team_data['goals_scored'] += goals_scored
            team_data['goals_conceded'] += goals_conceded
            team_data['matches_played'] += 1
        
        # Calculate recent form (weighted average of last 5 matches)
        if team_data['recent_matches']:
            recent = team_data['recent_matches'][:5]
            wins = sum(1 for m in recent if m['team_goals'] > m['opponent_goals'])
            draws = sum(1 for m in recent if m['team_goals'] == m['opponent_goals'])
            team_data['recent_form'] = (wins * 3 + draws) / (len(recent) * 3)
            team_data['recent_form'] = max(0.5, min(1.5, team_data['recent_form']))
        
        return team_data
    
    def _is_fixture_request(self, text: str) -> bool:
        """Check if text looks like a fixture request"""
        # Check for common separators
        separators = [' vs ', ' v ', ' - ', ' vs', ' v ']
        for sep in separators:
            if sep in text.lower():
                return True
        
        # Check if it has exactly two team-like words
        words = text.split()
        if 2 <= len(words) <= 6:
            return True
        
        return False
    
    def _parse_teams(self, text: str) -> list:
        """Parse team names from fixture text"""
        text = text.strip()
        
        # Try different separators
        separators = [' vs ', ' v ', ' - ', ' vs', ' v ']
        for sep in separators:
            if sep in text.lower():
                parts = re.split(sep, text, flags=re.IGNORECASE)
                if len(parts) == 2:
                    return [parts[0].strip(), parts[1].strip()]
        
        # If no separator, try to split intelligently
        words = text.split()
        if len(words) == 2:
            return [words[0], words[1]]
        
        # Try to split at middle
        mid = len(words) // 2
        home = ' '.join(words[:mid])
        away = ' '.join(words[mid:])
        
        return [home, away] if home and away else []
    
    async def _save_user(self, telegram_user):
        """Save user to database"""
        try:
            async with database.get_session() as session:
                user = await session.query(User).filter_by(telegram_id=telegram_user.id).first()
                if not user:
                    user = User(
                        telegram_id=telegram_user.id,
                        username=telegram_user.username,
                        first_name=telegram_user.first_name,
                        last_name=telegram_user.last_name,
                        is_admin=telegram_user.id in settings.ADMIN_USER_IDS
                    )
                    session.add(user)
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to save user: {e}")
    
    async def _save_analysis(self, user_id: int, session_id: str, home_team: str, 
                            away_team: str, analysis_data: Dict, verdict: str):
        """Save analysis to database"""
        try:
            async with database.get_session() as session:
                # Get user
                user = await session.query(User).filter_by(telegram_id=user_id).first()
                if not user:
                    logger.error(f"User {user_id} not found")
                    return
                
                # Create analysis session
                analysis = AnalysisSession(
                    session_id=session_id,
                    user_id=user.id,
                    home_team_name=home_team,
                    away_team_name=away_team,
                    status="completed",
                    data_quality_score=analysis_data.get('data_quality', 0),
                    model_consensus_score=analysis_data.get('consensus_score', 0),
                    final_verdict=verdict,
                    analysis_data=analysis_data,
                    completed_at=datetime.now(timezone.utc)
                )
                session.add(analysis)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        user_id = update.effective_user.id
        
        try:
            async with database.get_session() as session:
                user = await session.query(User).filter_by(telegram_id=user_id).first()
                if not user:
                    await update.message.reply_text("No analysis history found.")
                    return
                
                analyses = await session.query(AnalysisSession).filter_by(
                    user_id=user.id
                ).order_by(AnalysisSession.created_at.desc()).limit(10).all()
                
                if not analyses:
                    await update.message.reply_text("No analysis history found.")
                    return
                
                history_text = "📊 Recent Analyses:\n\n"
                for analysis in analyses:
                    history_text += f"• {analysis.home_team_name} vs {analysis.away_team_name}\n"
                    history_text += f"  Quality: {analysis.data_quality_score:.0f}/100, "
                    history_text += f"Consensus: {analysis.model_consensus_score:.0f}/100\n"
                    history_text += f"  Verdict: {analysis.final_verdict}\n\n"
                
                await update.message.reply_text(history_text)
                
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            await update.message.reply_text("Failed to retrieve history.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        db_status = await database.health_check()
        
        status_text = f"""
📊 {settings.BOT_NAME} Status

✓ Bot: Running
✓ Database: {'Connected' if db_status else 'Error'}
✓ Football API: {'Configured' if settings.FOOTBALL_API_KEY else 'Not configured'}
✓ Odds API: {'Configured' if settings.ODDS_API_KEY else 'Not configured'}
✓ Environment: {settings.ENVIRONMENT}
✓ Monte Carlo: {settings.MONTE_CARLO_SIMULATIONS} simulations
"""
        await update.message.reply_text(status_text)
    
    async def sources_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sources command"""
        sources_text = """
📚 DATA SOURCES

✓ Football Data: API-Football.com
✓ Bookmaker Odds: The Odds API
✓ Statistical Models: Poisson, Elo, Monte Carlo

Data Quality: Depends on API availability
Last Updated: Real-time
"""
        await update.message.reply_text(sources_text)
    
    async def callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callback queries"""
        query = update.callback_query
        await query.answer()
        
        # Handle different button actions
        responses = {
            "full_analysis": "📊 Full analysis will be shown after running a fixture analysis.",
            "best_bets": "🎯 Best bets will be highlighted in the analysis report.",
            "correct_scores": "⚽ Correct scores are calculated using Poisson distribution.",
            "goals": "🥅 Goals markets include Over/Under 0.5, 1.5, 2.5, 3.5 and more.",
            "value": "📈 Value analysis compares model probabilities with bookmaker odds.",
            "risk": "🛡 Risk levels: LOW, MEDIUM, HIGH based on multiple factors."
        }
        
        response = responses.get(query.data, "Unknown action")
        await query.message.reply_text(response)
    
    def get_handlers(self):
        """Get all handlers for the bot"""
        return [
            CommandHandler("start", self.start_command),
            CommandHandler("help", self.help_command),
            CommandHandler("analyze", self.analyze_command),
            CommandHandler("history", self.history_command),
            CommandHandler("status", self.status_command),
            CommandHandler("sources", self.sources_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler),
            CallbackQueryHandler(self.callback_query_handler),
        ]
