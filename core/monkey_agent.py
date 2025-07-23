"""
Market maker (monkey) agent module for predicting and defending against coconut launches.
"""

from typing import Dict, List, Tuple, Optional
import random
from .profiles.profile_loader import profile_manager

class MonkeyAgent:
    """Market maker agent that uses psychological profiles for defense."""
    def __init__(self, name: str = "MonkeyAgent"):
        self.name = name
        self.defense_history: List[int] = []
        self.last_defense = None
        self.recent_losses: List[bool] = []  # True = loss, False = successful defense
        self.retail_clusters: Dict[int, float] = {}  # Strike -> Clustering score

    def _update_game_state_metrics(self, game_state: Dict) -> Dict:
        """Update and return psychological metrics for the game state."""
        # Calculate recent loss rate
        if self.recent_losses:
            recent_loss_rate = sum(1 for loss in self.recent_losses[-5:] if loss) / len(self.recent_losses[-5:])
        else:
            recent_loss_rate = 0
            
        # Calculate retail clustering at each strike
        total_hits = sum(game_state["tree_hits"].values())
        total_juice = sum(game_state["retail_juice"].values())
        
        # Initialize all strikes with minimal clustering
        self.retail_clusters = {strike: 0.01 for strike in game_state["strikes"]}
        
        if total_hits > 0 or total_juice > 0:
            for strike in game_state["strikes"]:
                hits_ratio = game_state["tree_hits"].get(strike, 0) / (total_hits + 1)
                juice_ratio = game_state["retail_juice"].get(strike, 0) / (total_juice + 1)
                self.retail_clusters[strike] = max(0.01, (hits_ratio + juice_ratio) / 2)
        
        # Add psychological metrics to game state
        game_state.update({
            "recent_loss_rate": recent_loss_rate,
            "retail_clustering": max(self.retail_clusters.values())
        })
        
        return game_state

    async def predict_targets(self, game_state: Dict) -> List[Tuple[int, float]]:
        """
        Predict likely strike targets based on current game state and psychological profile.
        
        Args:
            game_state: Dict containing current game state including:
                - spot_price: Current spot price
                - strikes: List of available strikes
                - tree_hits: Dict of hits per strike
                - retail_juice: Dict of retail juice per strike
                - mm_juice: Dict of market maker juice per strike
                
        Returns:
            List[Tuple[int, float]]: List of (strike, probability) predictions
        """
        # Update psychological metrics
        game_state = self._update_game_state_metrics(game_state)
        
        # Get profile-adjusted weights
        weights = profile_manager.apply_profile_to_agent("monkey", game_state)
        if not weights:
            # Fallback to default weights if no profile loaded
            weights = {
                "spot_distance": 0.3,
                "hit_history": 0.2,
                "juice_collection": 0.3,
                "retail_clustering": 0.2
            }
            
        spot_price = game_state["spot_price"]
        strikes = game_state["strikes"]
        
        # Calculate strike scores using profile-weighted factors
        strike_scores = {}
        for strike in strikes:
            score = 0.0
            
            # Distance from spot price
            distance = abs(strike - spot_price)
            distance_score = 1.0 / (1 + distance/5)
            score += distance_score * weights["spot_distance"]
            
            # Hit history
            hits = game_state["tree_hits"].get(strike, 0)
            hit_score = min(1.0, hits / 10)  # Cap at 10 hits
            score += hit_score * weights["hit_history"]
            
            # Juice collection patterns
            retail_juice = game_state["retail_juice"].get(strike, 0)
            juice_score = min(1.0, retail_juice)
            score += juice_score * weights["juice_collection"]
            
            # Retail clustering
            cluster_score = self.retail_clusters.get(strike, 0.01)  # Default to minimal clustering
            score += cluster_score * weights["retail_clustering"]
            
            strike_scores[strike] = score
            
        # Apply psychological modifiers
        profile = profile_manager.get_active_profile("monkey")
        if profile:
            # Risk aversion: Focus more on defending successful strikes when losses are high
            if game_state["recent_loss_rate"] > profile.traits.get("risk_aversion", 0):
                for strike in strikes:
                    if strike in self.defense_history[-3:]:
                        strike_scores[strike] *= 1.2
                        
            # Reflexivity awareness: Adjust predictions based on recent retail patterns
            if profile.traits.get("reflexivity_awareness", False):
                # Find strike with highest clustering
                max_cluster_strike = max(self.retail_clusters.items(), key=lambda x: x[1])[0]
                strike_scores[max_cluster_strike] *= 1.3
                
        # Sort strikes by score and calculate probabilities
        sorted_strikes = sorted(strike_scores.items(), key=lambda x: x[1], reverse=True)
        total_score = sum(score for _, score in sorted_strikes[:3])
        
        if total_score > 0:
            predictions = [(strike, score/total_score) for strike, score in sorted_strikes[:3]]
        else:
            # Fallback to defending strikes near spot price
            nearby_strikes = sorted(strikes, key=lambda s: abs(s - spot_price))[:3]
            predictions = [(s, 1/3) for s in nearby_strikes]
            
        # Update defense history
        self.last_defense = predictions[0][0]
        self.defense_history.append(self.last_defense)
        if len(self.defense_history) > 10:
            self.defense_history = self.defense_history[-10:]
            
        return predictions

    def record_defense_result(self, success: bool) -> None:
        """Record the result of a defense attempt."""
        self.recent_losses.append(not success)
        if len(self.recent_losses) > 10:
            self.recent_losses = self.recent_losses[-10:] 