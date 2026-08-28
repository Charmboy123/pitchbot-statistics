from typing import Dict, Optional, List
import logging
import numpy as np
from datetime import datetime, timezone

from app.analysis.poisson import PoissonModel
from app.analysis.elo import EloModel
from app.analysis.monte_carlo import MonteCarloEngine
from app.config.settings import settings

logger = logging.getLogger(__name__)

class AnalysisEngine:
    """Main analysis engine for football match prediction"""
    
    def __init__(self):
        self.poisson_model = PoissonModel()
        self.elo_model = EloModel()
        self.monte_carlo = MonteCarloEngine(settings.MONTE_CARLO_SIMULATIONS)
    
    async def analyze_match(self, home_team_data: Dict, away_team_data: Dict,
                           league_avg_goals: float = 1.4) -> Dict:
        """Analyze a football match and generate predictions"""
        try:
            # Calculate expected goals using Poisson model
            home_xg, away_xg = self.poisson_model.calculate_expected_goals(
                home_team_data, away_team_data, league_avg_goals
            )
            
            # Run Poisson model
            score_matrix = self.poisson_model.calculate_score_matrix(home_xg, away_xg)
            poisson_markets = self.poisson_model.calculate_market_probabilities(score_matrix)
            
            # Run Elo model
            home_rating = self.elo_model.estimate_team_ratings(
                home_team_data.get('recent_matches', []),
                home_team_data.get('elo_rating', 1500)
            )
            away_rating = self.elo_model.estimate_team_ratings(
                away_team_data.get('recent_matches', []),
                away_team_data.get('elo_rating', 1500)
            )
            elo_probabilities = self.elo_model.calculate_match_probabilities(home_rating, away_rating)
            
            # Run Monte Carlo simulation
            mc_results = self.monte_carlo.simulate_match(home_xg, away_xg)
            
            # Combine models (ensemble)
            ensemble = self._combine_models(poisson_markets, elo_probabilities, mc_results)
            
            # Calculate consensus score
            consensus_score = self._calculate_consensus(poisson_markets, elo_probabilities, mc_results)
            
            # Calculate first half probabilities
            first_half = self.poisson_model.calculate_first_half_probabilities(home_xg, away_xg)
            
            # Prepare final results
            results = {
                "expected_goals": {
                    "home": round(home_xg, 2),
                    "away": round(away_xg, 2),
                    "total": round(home_xg + away_xg, 2)
                },
                "poisson": poisson_markets,
                "elo": elo_probabilities,
                "monte_carlo": mc_results,
                "ensemble": ensemble,
                "first_half": first_half,
                "consensus_score": round(consensus_score, 1),
                "data_quality": self._assess_data_quality(home_team_data, away_team_data),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    
    def _combine_models(self, poisson: Dict, elo: Dict, mc: Dict) -> Dict:
        """Combine model predictions using weighted average"""
        weights = {
            'poisson': settings.WEIGHT_POISSON,
            'elo': settings.WEIGHT_ELO,
            'monte_carlo': settings.WEIGHT_MONTE_CARLO
        }
        
        # Combine match result probabilities
        home_prob = (
            poisson['match_result']['home'] * weights['poisson'] +
            elo['home'] * weights['elo'] +
            mc['match_result']['home'] * weights['monte_carlo']
        )
        draw_prob = (
            poisson['match_result']['draw'] * weights['poisson'] +
            elo['draw'] * weights['elo'] +
            mc['match_result']['draw'] * weights['monte_carlo']
        )
        away_prob = (
            poisson['match_result']['away'] * weights['poisson'] +
            elo['away'] * weights['elo'] +
            mc['match_result']['away'] * weights['monte_carlo']
        )
        
        # Normalize
        total = home_prob + draw_prob + away_prob
        home_prob /= total
        draw_prob /= total
        away_prob /= total
        
        # Combine BTTS
        btts_yes = (
            poisson['btts']['yes'] * weights['poisson'] +
            mc['btts']['yes'] * weights['monte_carlo']
        ) / (weights['poisson'] + weights['monte_carlo'])
        
        # Combine totals
        over_2_5 = (
            poisson['totals']['over_2_5'] * weights['poisson'] +
            mc['totals']['over_2_5'] * weights['monte_carlo']
        ) / (weights['poisson'] + weights['monte_carlo'])
        
        return {
            "match_result": {
                "home": home_prob,
                "draw": draw_prob,
                "away": away_prob
            },
            "btts": {
                "yes": btts_yes,
                "no": 1 - btts_yes
            },
            "totals": {
                "over_2_5": over_2_5,
                "under_2_5": 1 - over_2_5
            }
        }
    
    def _calculate_consensus(self, poisson: Dict, elo: Dict, mc: Dict) -> float:
        """Calculate model consensus score"""
        # Extract home win probabilities
        home_probs = [
            poisson['match_result']['home'],
            elo['home'],
            mc['match_result']['home']
        ]
        
        # Calculate standard deviation
        std_dev = np.std(home_probs)
        
        # Convert to consensus score (lower std = higher consensus)
        consensus = max(0, min(100, 100 - (std_dev * 200)))
        
        return consensus
    
    def _assess_data_quality(self, home_team: Dict, away_team: Dict) -> float:
        """Assess data quality score"""
        quality_score = 50.0  # Base score
        
        # Check data completeness
        if home_team.get('matches_played', 0) > 0:
            quality_score += 10
        if away_team.get('matches_played', 0) > 0:
            quality_score += 10
        
        # Check if we have goals data
        if home_team.get('goals_scored') is not None:
            quality_score += 5
        if away_team.get('goals_scored') is not None:
            quality_score += 5
        
        # Check if we have recent form
        if len(home_team.get('recent_matches', [])) > 0:
            quality_score += 10
        if len(away_team.get('recent_matches', [])) > 0:
            quality_score += 10
        
        return max(0, min(100, quality_score))
    
    def generate_report(self, home_team_name: str, away_team_name: str, 
                        analysis_results: Dict, odds_data: Dict = None) -> str:
        """Generate formatted Telegram report"""
        expected_goals = analysis_results['expected_goals']
        ensemble = analysis_results['ensemble']
        poisson = analysis_results['poisson']
        consensus = analysis_results['consensus_score']
        data_quality = analysis_results['data_quality']
        
        report = f"""
⚽ {settings.BOT_NAME}
{settings.BOT_SUBTITLE}

🏟 {home_team_name.upper()} vs {away_team_name.upper()}

📊 DATA QUALITY
{data_quality}/100 — {self._get_quality_label(data_quality)}

🧠 MODEL CONSENSUS
{consensus}/100 — {self._get_consensus_label(consensus)}

⚽ EXPECTED GOALS
{home_team_name}: {expected_goals['home']}
{away_team_name}: {expected_goals['away']}
Total: {expected_goals['total']}

🏆 MATCH RESULT
{home_team_name}: {ensemble['match_result']['home']*100:.1f}%
Draw: {ensemble['match_result']['draw']*100:.1f}%
{away_team_name}: {ensemble['match_result']['away']*100:.1f}%

🥅 GOALS
Over 1.5: {poisson['totals']['over_1_5']*100:.1f}%
Over 2.5: {poisson['totals']['over_2_5']*100:.1f}%
Under 2.5: {poisson['totals']['under_2_5']*100:.1f}%
Over 3.5: {poisson['totals']['over_3_5']*100:.1f}%

🤝 BTTS
Yes: {poisson['btts']['yes']*100:.1f}%
No: {poisson['btts']['no']*100:.1f}%

⏱ HALF TIME
HT Home: {analysis_results['first_half']['match_result']['home']*100:.1f}%
HT Draw: {analysis_results['first_half']['match_result']['draw']*100:.1f}%
HT Away: {analysis_results['first_half']['match_result']['away']*100:.1f}%

🎯 TOP CORRECT SCORES
"""
        
        for i, (score, prob) in enumerate(poisson['correct_scores'][:5], 1):
            report += f"{i}. {score} — {prob*100:.1f}%\n"
        
        report += f"""
🔥 HIGH-CONFIDENCE MARKETS
"""
        
        # Find high probability markets
        high_prob_markets = []
        if poisson['totals']['over_1_5'] > settings.MIN_PROBABILITY:
            high_prob_markets.append(f"1. Over 1.5 — {poisson['totals']['over_1_5']*100:.1f}%")
        if poisson['totals']['under_3_5'] > settings.MIN_PROBABILITY:
            high_prob_markets.append(f"2. Under 3.5 — {poisson['totals']['under_3_5']*100:.1f}%")
        
        if high_prob_markets:
            for market in high_prob_markets[:3]:
                report += f"{market}\n"
        else:
            report += "No markets above threshold\n"
        
        # Add odds if available
        if odds_data and 'home_probability' in odds_data and odds_data['home_probability']:
            report += f"""
💰 VALUE ANALYSIS
Market: Match Result
Model Home: {ensemble['match_result']['home']*100:.1f}%
Bookmaker Home: {odds_data['home_probability']*100:.1f}%
Fair Odds: {1/ensemble['match_result']['home']:.2f}
Available Odds: {odds_data['home_odds']:.2f}
"""
        
        # Risk assessment
        risk_level = self._assess_risk(consensus, data_quality, poisson)
        
        report += f"""
🛡 RISK
{risk_level}

📌 FINAL VERDICT
{self._get_verdict(risk_level, high_prob_markets)}

⚠️ Probabilities are estimates, not guarantees.
"""
        
        return report
    
    def _get_quality_label(self, score: float) -> str:
        """Get quality label from score"""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Very Strong"
        elif score >= 70:
            return "Strong"
        elif score >= 60:
            return "Moderate"
        elif score >= 50:
            return "Weak"
        else:
            return "Poor"
    
    def _get_consensus_label(self, score: float) -> str:
        """Get consensus label from score"""
        if score >= 80:
            return "Strong"
        elif score >= 60:
            return "Moderate"
        else:
            return "Weak"
    
    def _assess_risk(self, consensus: float, data_quality: float, markets: Dict) -> str:
        """Assess overall risk level"""
        if data_quality < 50:
            return "HIGH"
        elif consensus < 60:
            return "MEDIUM/HIGH"
        elif consensus < 80:
            return "MEDIUM"
        else:
            return "LOW/MEDIUM"
    
    def _get_verdict(self, risk_level: str, high_prob_markets: List[str]) -> str:
        """Get final verdict"""
        if risk_level == "HIGH":
            return "NO BET - Insufficient data quality"
        elif not high_prob_markets:
            return "WATCH - No high-probability markets"
        elif risk_level in ["MEDIUM/HIGH", "MEDIUM"]:
            return "WATCH - Moderate confidence"
        else:
            return "BET - Strong statistical support"
