from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TeamData:
    """Normalized team data structure"""
    id: int
    name: str
    normalized_name: str
    country: Optional[str]
    league_id: Optional[int]
    logo_url: Optional[str]

@dataclass
class FixtureData:
    """Normalized fixture data structure"""
    id: int
    competition_id: int
    home_team: TeamData
    away_team: TeamData
    kickoff_time: datetime
    venue: Optional[str]
    status: str
    competition_name: str
    country: str

class DataProvider(ABC):
    """Abstract base class for data providers"""
    
    @abstractmethod
    async def search_teams(self, query: str) -> List[TeamData]:
        """Search for teams by name"""
        pass
    
    @abstractmethod
    async def get_team_by_id(self, team_id: int) -> Optional[TeamData]:
        """Get team by provider ID"""
        pass
    
    @abstractmethod
    async def search_fixtures(self, home_team_id: int, away_team_id: int) -> List[FixtureData]:
        """Search for fixtures between two teams"""
        pass
    
    @abstractmethod
    async def get_fixture(self, fixture_id: int) -> Optional[FixtureData]:
        """Get fixture by ID"""
        pass
    
    @abstractmethod
    async def get_recent_matches(self, team_id: int, limit: int = 10) -> List[Dict]:
        """Get recent matches for a team"""
        pass
    
    @abstractmethod
    async def get_h2h(self, team1_id: int, team2_id: int, limit: int = 10) -> List[Dict]:
        """Get head-to-head matches"""
        pass
    
    @abstractmethod
    async def get_standings(self, league_id: int) -> List[Dict]:
        """Get league standings"""
        pass
    
    @abstractmethod
    async def get_team_statistics(self, team_id: int, league_id: int) -> Dict:
        """Get team statistics for a season"""
        pass
    
    @abstractmethod
    async def get_odds(self, fixture_id: int) -> Dict:
        """Get match odds"""
        pass
