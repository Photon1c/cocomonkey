"""
Retail agent module for coconut targeting decisions.
"""

from typing import Dict, List, Tuple, Optional
import random
from .profiles.profile_loader import profile_manager

class RetailAgent:
    """Retail agent that uses psychological profiles for targeting."""
    def __init__(self, name: str = "RetailAgent"):
        self.name = name
        self.last_target = None
        self.target_history: List[int] = []
        self.recent_hits: List[bool] = []
        self.crowd_size: Dict[int, int] = {}  # Strike -> Number of agents targeting it

    def _update_game_state_metrics(self, game_state: Dict) -> Dict:
        """Update and return psychological metrics for the game state."""
        # Calculate recent success rate
        if self.recent_hits:
            recent_success_rate = sum(1 for hit in self.recent_hits[-5:] if hit) / len(self.recent_hits[-5:])
        else:
            recent_success_rate = 0
            
        # Calculate crowd sizes at each strike
        for strike in game_state["strikes"]:
            hits = game_state["tree_hits"].get(strike, 0)
            retail_juice = game_state["retail_juice"].get(strike, 0)
            self.crowd_size[strike] = int((hits + retail_juice * 10) / 2)
            
        # Add psychological metrics to game state
        game_state.update({
            "recent_success_rate": recent_success_rate,
            "crowd_size": max(self.crowd_size.values()) if self.crowd_size else 0
        })
        
        return game_state

    async def select_target(self, game_state: Dict) -> Tuple[int, float]:
        """
        Select a strike price to target based on current game state and psychological profile.
        
        Args:
            game_state: Dict containing current game state including:
                - spot_price: Current spot price
                - strikes: List of available strikes
                - tree_hits: Dict of hits per strike
                - retail_juice: Dict of retail juice per strike
                - mm_juice: Dict of market maker juice per strike
                
        Returns:
            Tuple[int, float]: Selected strike price and confidence score
        """
        # Update psychological metrics
        game_state = self._update_game_state_metrics(game_state)
        
        # Get profile-adjusted weights
        weights = profile_manager.apply_profile_to_agent("retail", game_state)
        if not weights:
            # Fallback to default weights if no profile loaded
            weights = {
                "spot_distance": 0.3,
                "success_history": 0.2,
                "mm_defense": 0.3,
                "crowd_following": 0.2
            }
            
        spot_price = game_state["spot_price"]
        strikes = game_state["strikes"]
        
        # Calculate strike scores using profile-weighted factors
        strike_scores = {}
        for strike in strikes:
            score = 0.0
            
            # Distance from spot price (prefer closer strikes)
            distance = abs(strike - spot_price)
            distance_score = 1.0 / (1 + distance/5)
            score += distance_score * weights["spot_distance"]
            
            # Success history (prefer previously successful strikes)
            history_score = 0.0
            if strike in self.target_history[-5:]:
                history_score = 1.0
            score += history_score * weights["success_history"]
            
            # MM defense (prefer less defended strikes)
            mm_score = 1.0 - game_state["mm_juice"].get(strike, 0)
            score += mm_score * weights["mm_defense"]
            
            # Crowd following (prefer popular strikes)
            crowd_score = min(1.0, self.crowd_size.get(strike, 0) / 5)
            score += crowd_score * weights["crowd_following"]
            
            strike_scores[strike] = score
            
        # Select target based on scores
        if strike_scores:
            # Sometimes follow the crowd more strongly based on FOMO
            profile = profile_manager.get_active_profile("retail")
            if profile and random.random() < profile.traits.get("fomo_threshold", 0):
                # Increase weight of crowd following
                max_crowd_strike = max(strikes, key=lambda s: self.crowd_size.get(s, 0))
                strike_scores[max_crowd_strike] *= 1.5
                
            # Select strike with highest score
            target = max(strike_scores.items(), key=lambda x: x[1])[0]
            confidence = strike_scores[target]
        else:
            # Fallback to random selection
            target = random.choice(strikes)
            confidence = 0.5
            
        # Update history
        self.last_target = target
        self.target_history.append(target)
        if len(self.target_history) > 10:
            self.target_history = self.target_history[-10:]
            
        return target, min(confidence, 1.0)

    def record_hit(self, hit: bool) -> None:
        """Record the result of a targeting attempt."""
        self.recent_hits.append(hit)
        if len(self.recent_hits) > 10:
            self.recent_hits = self.recent_hits[-10:] 