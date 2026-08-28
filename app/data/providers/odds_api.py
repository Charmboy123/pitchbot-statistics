import aiohttp
import logging
from typing import Dict, List, Optional
from app.config.settings import settings
import asyncio

logger = logging.getLogger(__name__)

class OddsAPIProvider:
    """The Odds API provider implementation"""
    
    def __init__(self):
        self.api_key = settings.ODDS_API  # Using your odds API key
        self.base_url = settings.ODDS_API_URL
        self.headers = {
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request to Odds API"""
        try:
            if params is None:
                params = {}
            params["apiKey"] = self.api_key
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{endpoint}"
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:
                        logger.error(f"Rate limit exceeded for {endpoint}")
                        await asyncio.sleep(5)
                        return await self._make_request(endpoint, params)
                    elif response.status == 401:
                        logger.error(f"Unauthorized - Check ODDS_API key")
                        return None
                    elif response.status == 404:
                        logger.error(f"Not found - {url}")
                        return None
                    else:
                        logger.error(f"Odds API request failed: {response.status} - {url}")
                        return None
        except Exception as e:
            logger.error(f"Odds API request error: {e}")
            return None
    
    async def get_sports(self) -> List[Dict]:
        """Get available sports"""
        endpoint = "/sports"
        response = await self._make_request(endpoint)
        
        if response:
            return response
        
        return []
    
    async def get_odds(self, sport_key: str = "soccer_epl", regions: str = "eu") -> List[Dict]:
        """Get odds for a sport"""
        endpoint = f"/sports/{sport_key}/odds"
        params = {
            "regions": regions,
            "markets": "h2h,totals,btts"
        }
        
        response = await self._make_request(endpoint, params)
        
        if response:
            return response
        
        return []
    
    async def get_football_odds(self, match_name: str) -> List[Dict]:
        """Get football odds for a specific match"""
        # Try different soccer leagues
        soccer_leagues = [
            "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a",
            "soccer_germany_bundesliga", "soccer_france_ligue_one",
            "soccer_uefa_champs_league", "soccer_uefa_europa_league"
        ]
        
        all_odds = []
        
        for league in soccer_leagues:
            odds = await self.get_odds(league)
            if odds:
                # Filter for matching teams
                for match_odds in odds:
                    home_team = match_odds.get("home_team", "").lower()
                    away_team = match_odds.get("away_team", "").lower()
                    
                    if match_name.lower() in f"{home_team} vs {away_team}":
                        all_odds.append(match_odds)
        
        return all_odds
    
    async def calculate_implied_probability(self, odds_data: Dict) -> Dict:
        """Calculate implied probability from odds"""
        try:
            bookmakers = odds_data.get("bookmakers", [])
            
            if not bookmakers:
                return {}
            
            # Use first bookmaker for simplicity
            bookmaker = bookmakers[0]
            markets = bookmaker.get("markets", [])
            
            result = {
                "bookmaker": bookmaker.get("title"),
                "home_odds": None,
                "draw_odds": None,
                "away_odds": None,
                "home_probability": None,
                "draw_probability": None,
                "away_probability": None,
                "over_under": {}
            }
            
            for market in markets:
                key = market.get("key")
                outcomes = market.get("outcomes", [])
                
                if key == "h2h":
                    for outcome in outcomes:
                        if outcome.get("name") == "Home":
                            result["home_odds"] = outcome.get("price")
                            result["home_probability"] = 1 / outcome.get("price")
                        elif outcome.get("name") == "Draw":
                            result["draw_odds"] = outcome.get("price")
                            result["draw_probability"] = 1 / outcome.get("price")
                        elif outcome.get("name") == "Away":
                            result["away_odds"] = outcome.get("price")
                            result["away_probability"] = 1 / outcome.get("price")
                
                elif key == "totals":
                    for outcome in outcomes:
                        result["over_under"][outcome.get("name")] = {
                            "point": outcome.get("point"),
                            "price": outcome.get("price"),
                            "probability": 1 / outcome.get("price")
                        }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to calculate implied probability: {e}")
            return {}
