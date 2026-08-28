import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class MonteCarloEngine:
    """Monte Carlo simulation for football match prediction"""
    
    def __init__(self, simulations: int = 50000):
        self.simulations = simulations
        self.rng = np.random.default_rng()
    
    def simulate_match(self, home_xg: float, away_xg: float) -> Dict:
        """Run Monte Carlo simulation for a match"""
        # Generate random goals from Poisson distribution
        home_goals = self.rng.poisson(home_xg, self.simulations)
        away_goals = self.rng.poisson(away_xg, self.simulations)
        
        # Calculate market probabilities
        results = self._calculate_markets(home_goals, away_goals)
        
        return results
    
    def _calculate_markets(self, home_goals: np.ndarray, away_goals: np.ndarray) -> Dict:
        """Calculate market probabilities from simulation results"""
        total_goals = home_goals + away_goals
        
        # Match result
        home_wins = np.sum(home_goals > away_goals) / self.simulations
        draws = np.sum(home_goals == away_goals) / self.simulations
        away_wins = np.sum(home_goals < away_goals) / self.simulations
        
        # BTTS
        btts_yes = np.sum((home_goals > 0) & (away_goals > 0)) / self.simulations
        
        # Totals
        over_2_5 = np.sum(total_goals > 2.5) / self.simulations
        over_1_5 = np.sum(total_goals > 1.5) / self.simulations
        over_3_5 = np.sum(total_goals > 3.5) / self.simulations
        over_0_5 = np.sum(total_goals > 0.5) / self.simulations
        over_4_5 = np.sum(total_goals > 4.5) / self.simulations
        
        # Correct scores (top 10)
        correct_scores = {}
        for i in range(6):
            for j in range(6):
                mask = (home_goals == i) & (away_goals == j)
                prob = np.sum(mask) / self.simulations
                if prob > 0.001:  # Only include reasonable probabilities
                    correct_scores[f"{i}-{j}"] = prob
        
        top_scores = sorted(correct_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "match_result": {
                "home": float(home_wins),
                "draw": float(draws),
                "away": float(away_wins)
            },
            "btts": {
                "yes": float(btts_yes),
                "no": float(1 - btts_yes)
            },
            "totals": {
                "over_0_5": float(over_0_5),
                "over_1_5": float(over_1_5),
                "over_2_5": float(over_2_5),
                "over_3_5": float(over_3_5),
                "over_4_5": float(over_4_5),
                "under_0_5": float(1 - over_0_5),
                "under_1_5": float(1 - over_1_5),
                "under_2_5": float(1 - over_2_5),
                "under_3_5": float(1 - over_3_5),
                "under_4_5": float(1 - over_4_5)
            },
            "correct_scores": top_scores
        }
