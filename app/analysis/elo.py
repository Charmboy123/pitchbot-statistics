from typing import Dict, Tuple
import math
import logging

logger = logging.getLogger(__name__)

class EloModel:
    """Elo rating system for football match prediction"""
    
    def __init__(self, initial_rating: float = 1500.0, k_factor: float = 20.0):
        self.initial_rating = initial_rating
        self.k_factor = k_factor
        self.home_advantage = 100.0  # Home advantage in Elo points
    
    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for team A against team B"""
        return 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))
    
    def update_ratings(self, rating_a: float, rating_b: float, 
                       score_a: float, score_b: float) -> Tuple[float, float]:
        """Update Elo ratings based on match result"""
        expected_a = self.calculate_expected_score(rating_a, rating_b)
        expected_b = 1 - expected_a
        
        # Determine actual scores
        if score_a > score_b:
            actual_a, actual_b = 1.0, 0.0
        elif score_a < score_b:
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a, actual_b = 0.5, 0.5
        
        # Update ratings
        new_rating_a = rating_a + self.k_factor * (actual_a - expected_a)
        new_rating_b = rating_b + self.k_factor * (actual_b - expected_b)
        
        return new_rating_a, new_rating_b
    
    def calculate_match_probabilities(self, home_rating: float, away_rating: float) -> Dict:
        """Calculate match probabilities from Elo ratings"""
        # Apply home advantage
        adjusted_home = home_rating + self.home_advantage
        
        # Calculate expected scores
        expected_home = self.calculate_expected_score(adjusted_home, away_rating)
        expected_away = 1 - expected_home
        
        # Convert to probabilities with draw adjustment
        draw_probability = 0.25 * (1 - abs(expected_home - expected_away))
        home_probability = expected_home - draw_probability / 2
        away_probability = expected_away - draw_probability / 2
        
        # Ensure valid probabilities
        total = home_probability + draw_probability + away_probability
        home_probability /= total
        draw_probability /= total
        away_probability /= total
        
        return {
            "home": max(0.01, min(0.95, home_probability)),
            "draw": max(0.01, min(0.95, draw_probability)),
            "away": max(0.01, min(0.95, away_probability))
        }
    
    def estimate_team_ratings(self, recent_matches: list, 
                              current_rating: float = None) -> float:
        """Estimate team rating based on recent performances"""
        if not recent_matches:
            return self.initial_rating
        
        rating = current_rating or self.initial_rating
        
        for match in recent_matches:
            team_goals = match.get('team_goals', 0)
            opponent_goals = match.get('opponent_goals', 0)
            opponent_rating = match.get('opponent_rating', self.initial_rating)
            
            # Update rating based on match result
            if team_goals > opponent_goals:
                rating += self.k_factor * (1 - self.calculate_expected_score(rating, opponent_rating))
            elif team_goals < opponent_goals:
                rating += self.k_factor * (0 - self.calculate_expected_score(rating, opponent_rating))
            else:
                rating += self.k_factor * (0.5 - self.calculate_expected_score(rating, opponent_rating))
        
        return rating
