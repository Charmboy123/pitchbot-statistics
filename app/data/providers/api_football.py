import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from app.data.base import DataProvider, TeamData, FixtureData
from app.config.settings import settings
import unicodedata
import re

logger = logging.getLogger(__name__)

class APIFootballProvider(DataProvider):
    """API-Football.com data provider implementation"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or settings.FOOTBALL_API_KEY
        self.base_url = base_url or settings.FOOTBALL_API_URL
        self.headers = {
            "x-apisports-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request to API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{endpoint}"
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:
                        logger.error(f"Rate limit exceeded for {endpoint}")
                        # Wait and retry
                        import asyncio
                        await asyncio.sleep(2)
                        return await self._make_request(endpoint, params)
                    else:
                        logger.error(f"API request failed: {response.status} - {url}")
                        return None
        except Exception as e:
            logger.error(f"API request error: {e}")
            return None
    
    async def search_teams(self, query: str) -> List[TeamData]:
        """Search for teams by name"""
        endpoint = "/teams"
        params = {"search": query}
        
        response = await self._make_request(endpoint, params)
        teams = []
        
        if response and "response" in response:
            for item in response["response"]:
                team = item.get("team", {})
                team_data = TeamData(
                    id=team.get("id"),
                    name=team.get("name", ""),
                    normalized_name=self._normalize_team_name(team.get("name", "")),
                    country=team.get("country"),
                    league_id=None,
                    logo_url=team.get("logo")
                )
                teams.append(team_data)
        
        return teams
    
    async def get_team_by_id(self, team_id: int) -> Optional[TeamData]:
        """Get team by provider ID"""
        endpoint = "/teams"
        params = {"id": team_id}
        
        response = await self._make_request(endpoint, params)
        
        if response and "response" in response and response["response"]:
            team = response["response"][0].get("team", {})
            return TeamData(
                id=team.get("id"),
                name=team.get("name", ""),
                normalized_name=self._normalize_team_name(team.get("name", "")),
                country=team.get("country"),
                league_id=None,
                logo_url=team.get("logo")
            )
        
        return None
    
    async def search_fixtures(self, home_team_id: int, away_team_id: int) -> List[FixtureData]:
        """Search for fixtures between two teams"""
        endpoint = "/fixtures"
        params = {
            "team": home_team_id,
            "season": datetime.now().year
        }
        
        response = await self._make_request(endpoint, params)
        fixtures = []
        
        if response and "response" in response:
            for item in response["response"]:
                fixture = item.get("fixture", {})
                league = item.get("league", {})
                teams = item.get("teams", {})
                
                if teams.get("away", {}).get("id") == away_team_id:
                    fixture_data = self._parse_fixture(fixture, league, teams)
                    if fixture_data:
                        fixtures.append(fixture_data)
        
        return fixtures
    
    async def get_fixture(self, fixture_id: int) -> Optional[FixtureData]:
        """Get fixture by ID"""
        endpoint = "/fixtures"
        params = {"id": fixture_id}
        
        response = await self._make_request(endpoint, params)
        
        if response and "response" in response:
            item = response["response"][0]
            fixture = item.get("fixture", {})
            league = item.get("league", {})
            teams = item.get("teams", {})
            
            return self._parse_fixture(fixture, league, teams)
        
        return None
    
    async def get_recent_matches(self, team_id: int, limit: int = 10) -> List[Dict]:
        """Get recent matches for a team"""
        endpoint = "/fixtures"
        params = {
            "team": team_id,
            "last": limit
        }
        
        response = await self._make_request(endpoint, params)
        matches = []
        
        if response and "response" in response:
            for item in response["response"]:
                match_data = self._parse_match(item)
                if match_data:
                    matches.append(match_data)
        
        return matches
    
    async def get_h2h(self, team1_id: int, team2_id: int, limit: int = 10) -> List[Dict]:
        """Get head-to-head matches"""
        endpoint = "/fixtures/headtohead"
        params = {
            "h2h": f"{team1_id}-{team2_id}",
            "last": limit
        }
        
        response = await self._make_request(endpoint, params)
        matches = []
        
        if response and "response" in response:
            for item in response["response"]:
                match_data = self._parse_match(item)
                if match_data:
                    matches.append(match_data)
        
        return matches
    
    async def get_standings(self, league_id: int) -> List[Dict]:
        """Get league standings"""
        endpoint = "/standings"
        params = {
            "league": league_id,
            "season": datetime.now().year
        }
        
        response = await self._make_request(endpoint, params)
        standings = []
        
        if response and "response" in response:
            for group in response["response"]:
                league_data = group.get("league", {})
                for entry in league_data.get("standings", []):
                    for team_standing in entry:
                        standings.append({
                            "team_id": team_standing.get("team", {}).get("id"),
                            "team_name": team_standing.get("team", {}).get("name"),
                            "rank": team_standing.get("rank"),
                            "points": team_standing.get("points"),
                            "played": team_standing.get("all", {}).get("played"),
                            "won": team_standing.get("all", {}).get("win"),
                            "drawn": team_standing.get("all", {}).get("draw"),
                            "lost": team_standing.get("all", {}).get("lose"),
                            "goals_for": team_standing.get("all", {}).get("goals", {}).get("for"),
                            "goals_against": team_standing.get("all", {}).get("goals", {}).get("against")
                        })
        
        return standings
    
    async def get_team_statistics(self, team_id: int, league_id: int) -> Dict:
        """Get team statistics for a season"""
        endpoint = "/teams/statistics"
        params = {
            "team": team_id,
            "league": league_id,
            "season": datetime.now().year
        }
        
        response = await self._make_request(endpoint, params)
        
        if response and "response" in response:
            return response["response"]
        
        return {}
    
    async def get_odds(self, fixture_id: int) -> Dict:
        """Get match odds from API-Football"""
        endpoint = "/odds"
        params = {"fixture": fixture_id}
        
        response = await self._make_request(endpoint, params)
        
        if response and "response" in response:
            odds_data = {}
            for item in response["response"]:
                bookmakers = item.get("bookmakers", [])
                for bookmaker in bookmakers:
                    odds_data[bookmaker.get("name")] = bookmaker.get("bets", [])
            return odds_data
        
        return {}
    
    def _parse_fixture(self, fixture: Dict, league: Dict, teams: Dict) -> Optional[FixtureData]:
        """Parse fixture data from API response"""
        try:
            home_team_data = teams.get("home", {})
            away_team_data = teams.get("away", {})
            
            home_team = TeamData(
                id=home_team_data.get("id"),
                name=home_team_data.get("name", ""),
                normalized_name=self._normalize_team_name(home_team_data.get("name", "")),
                country=None,
                league_id=league.get("id"),
                logo_url=home_team_data.get("logo")
            )
            
            away_team = TeamData(
                id=away_team_data.get("id"),
                name=away_team_data.get("name", ""),
                normalized_name=self._normalize_team_name(away_team_data.get("name", "")),
                country=None,
                league_id=league.get("id"),
                logo_url=away_team_data.get("logo")
            )
            
            kickoff = datetime.fromtimestamp(fixture.get("timestamp", 0), tz=timezone.utc)
            
            return FixtureData(
                id=fixture.get("id"),
                competition_id=league.get("id"),
                home_team=home_team,
                away_team=away_team,
                kickoff_time=kickoff,
                venue=fixture.get("venue", {}).get("name"),
                status=fixture.get("status", {}).get("short"),
                competition_name=league.get("name", ""),
                country=league.get("country", "")
            )
        except Exception as e:
            logger.error(f"Failed to parse fixture: {e}")
            return None
    
    def _parse_match(self, item: Dict) -> Optional[Dict]:
        """Parse match data from API response"""
        try:
            fixture = item.get("fixture", {})
            teams = item.get("teams", {})
            goals = item.get("goals", {})
            score = item.get("score", {})
            
            return {
                "fixture_id": fixture.get("id"),
                "date": fixture.get("date"),
                "home_team_id": teams.get("home", {}).get("id"),
                "home_team_name": teams.get("home", {}).get("name"),
                "away_team_id": teams.get("away", {}).get("id"),
                "away_team_name": teams.get("away", {}).get("name"),
                "home_goals": goals.get("home"),
                "away_goals": goals.get("away"),
                "status": fixture.get("status", {}).get("short"),
                "halftime_home": score.get("halftime", {}).get("home"),
                "halftime_away": score.get("halftime", {}).get("away"),
                "fulltime_home": score.get("fulltime", {}).get("home"),
                "fulltime_away": score.get("fulltime", {}).get("away")
            }
        except Exception as e:
            logger.error(f"Failed to parse match: {e}")
            return None
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalize team name for matching"""
        # Remove accents
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        
        # Lowercase
        name = name.lower()
        
        # Remove punctuation
        name = re.sub(r'[^\w\s]', '', name)
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name
