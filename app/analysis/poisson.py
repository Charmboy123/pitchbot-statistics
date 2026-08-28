import numpy as np
from scipy.stats import poisson
from typing import Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)

class PoissonModel:
    """Poisson distribution model for football match prediction"""
    
    def __init__(self, max_goals: int = 10):
        self.max_goals = max_goals
    
    def calculate_expected_goals(self, home_team_data: Dict, away_team_data: Dict, 
                                 league_avg_goals: float = 1.4) -> Tuple[float, float]:
        """Calculate expected goals for home and away team"""
        # Calculate team strengths
        home_attack = self._calculate_attack_strength(home_team_data, league_avg_goals)
        home_defense = self._calculate_defense_strength(home_team_data, league_avg_goals)
        away_attack = self._calculate_attack_strength(away_team_data, league_avg_goals)
        away_defense = self._calculate_defense_strength(away_team_data, league_avg_goals)
        
        # Home advantage factor
        home_advantage = 1.15
        
        # Calculate expected goals
        home_xg = league_avg_goals * home_attack * away_defense * home_advantage
        away_xg = league_avg_goals * away_attack * home_defense * (1/home_advantage)
        
        # Apply recent form adjustment
        home_form = home_team_data.get('recent_form', 1.0)
        away_form = away_team_data.get('recent_form', 1.0)
        
        home_xg *= home_form
        away_xg *= away_form
        
        # Ensure minimum values
        home_xg = max(0.1, min(home_xg, 5.0))
        away_xg = max(0.1, min(away_xg, 5.0))
        
        return home_xg, away_xg
    
    def _calculate_attack_strength(self, team_data: Dict, league_avg: float) -> float:
        """Calculate team attack strength"""
        goals_scored = team_data.get('goals_scored', 0)
        matches_played = team_data.get('matches_played', 1)
        
        if matches_played == 0:
            return 1.0
        
        avg_goals = goals_scored / matches_played
        return max(0.5, min(2.0, avg_goals / league_avg))
    
    def _calculate_defense_strength(self, team_data: Dict, league_avg: float) -> float:
        """Calculate team defense strength"""
        goals_conceded = team_data.get('goals_conceded', 0)
        matches_played = team_data.get('matches_played', 1)
        
        if matches_played == 0:
            return 1.0
        
        avg_conceded = goals_conceded / matches_played
        return max(0.5, min(2.0, avg_conceded / league_avg))
    
    def calculate_score_matrix(self, home_xg: float, away_xg: float) -> np.ndarray:
        """Calculate probability matrix for all possible scores"""
        score_matrix = np.zeros((self.max_goals + 1, self.max_goals + 1))
        
        for i in range(self.max_goals + 1):
            for j in range(self.max_goals + 1):
                score_matrix[i, j] = poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)
        
        return score_matrix
    
    def calculate_market_probabilities(self, score_matrix: np.ndarray) -> Dict:
        """Calculate all market probabilities from score matrix"""
        # Match result (1X2)
        home_win = 0
        draw = 0
        away_win = 0
        
        # Over/Under markets
        over_0_5 = 0
        over_1_5 = 0
        over_2_5 = 0
        over_3_5 = 0
        over_4_5 = 0
        over_5_5 = 0
        over_6_5 = 0
        
        # BTTS
        btts_yes = 0
        btts_no = 0
        
        # Team totals
        home_over_0_5 = 0
        home_over_1_5 = 0
        away_over_0_5 = 0
        away_over_1_5 = 0
        
        # Correct scores dictionary
        correct_scores = {}
        
        for i in range(self.max_goals + 1):
            for j in range(self.max_goals + 1):
                prob = score_matrix[i, j]
                
                # Match result
                if i > j:
                    home_win += prob
                elif i == j:
                    draw += prob
                else:
                    away_win += prob
                
                # Total goals
                total_goals = i + j
                if total_goals > 0.5:
                    over_0_5 += prob
                if total_goals > 1.5:
                    over_1_5 += prob
                if total_goals > 2.5:
                    over_2_5 += prob
                if total_goals > 3.5:
                    over_3_5 += prob
                if total_goals > 4.5:
                    over_4_5 += prob
                if total_goals > 5.5:
                    over_5_5 += prob
                if total_goals > 6.5:
                    over_6_5 += prob
                
                # BTTS
                if i > 0 and j > 0:
                    btts_yes += prob
                else:
                    btts_no += prob
                
                # Home team totals
                if i > 0.5:
                    home_over_0_5 += prob
                if i > 1.5:
                    home_over_1_5 += prob
                
                # Away team totals
                if j > 0.5:
                    away_over_0_5 += prob
                if j > 1.5:
                    away_over_1_5 += prob
                
                # Correct scores (only for reasonable scorelines)
                if i <= 5 and j <= 5:
                    correct_scores[f"{i}-{j}"] = prob
        
        # Sort correct scores
        top_scores = sorted(correct_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "match_result": {
                "home": home_win,
                "draw": draw,
                "away": away_win
            },
            "double_chance": {
                "home_draw": home_win + draw,
                "away_draw": away_win + draw,
                "home_away": home_win + away_win
            },
            "totals": {
                "over_0_5": over_0_5,
                "under_0_5": 1 - over_0_5,
                "over_1_5": over_1_5,
                "under_1_5": 1 - over_1_5,
                "over_2_5": over_2_5,
                "under_2_5": 1 - over_2_5,
                "over_3_5": over_3_5,
                "under_3_5": 1 - over_3_5,
                "over_4_5": over_4_5,
                "under_4_5": 1 - over_4_5,
                "over_5_5": over_5_5,
                "under_5_5": 1 - over_5_5,
                "over_6_5": over_6_5,
                "under_6_5": 1 - over_6_5
            },
            "btts": {
                "yes": btts_yes,
                "no": btts_no
            },
            "team_totals": {
                "home_over_0_5": home_over_0_5,
                "home_under_0_5": 1 - home_over_0_5,
                "home_over_1_5": home_over_1_5,
                "home_under_1_5": 1 - home_over_1_5,
                "away_over_0_5": away_over_0_5,
                "away_under_0_5": 1 - away_over_0_5,
                "away_over_1_5": away_over_1_5,
                "away_under_1_5": 1 - away_over_1_5
            },
            "correct_scores": top_scores,
            "clean_sheets": {
                "home_yes": sum(score_matrix[i, 0] for i in range(1, self.max_goals + 1)),
                "home_no": 1 - sum(score_matrix[i, 0] for i in range(1, self.max_goals + 1)),
                "away_yes": sum(score_matrix[0, j] for j in range(1, self.max_goals + 1)),
                "away_no": 1 - sum(score_matrix[0, j] for j in range(1, self.max_goals + 1))
            }
        }
    
    def calculate_first_half_probabilities(self, home_xg: float, away_xg: float) -> Dict:
        """Calculate first half probabilities (typically 45% of full match goals)"""
        home_xg_ht = home_xg * 0.45
        away_xg_ht = away_xg * 0.45
        
        score_matrix = self.calculate_score_matrix(home_xg_ht, away_xg_ht)
        markets = self.calculate_market_probabilities(score_matrix)
        
        return {
            "match_result": markets["match_result"],
            "totals": markets["totals"],
            "btts": markets["btts"],
            "correct_scores": markets["correct_scores"][:5]
        }
