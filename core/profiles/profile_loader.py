"""
Profile loader module for managing agent psychological profiles.
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AgentProfile:
    """Container for agent psychological profile data."""
    name: str
    goal: str
    traits: Dict[str, Any]
    strategies: list[str]
    biases: Dict[str, float]
    behavior_weights: Dict[str, float]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentProfile':
        """Create profile from dictionary."""
        return cls(
            name=data["name"],
            goal=data["goal"],
            traits=data["traits"],
            strategies=data["strategies"],
            biases=data["biases"],
            behavior_weights=data["behavior_weights"]
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "name": self.name,
            "goal": self.goal,
            "traits": self.traits,
            "strategies": self.strategies,
            "biases": self.biases,
            "behavior_weights": self.behavior_weights
        }

class ProfileManager:
    """Manages loading and hot-swapping of agent profiles."""
    
    def __init__(self):
        # Get the profiles directory path
        self.profiles_dir = Path(__file__).parent
        self.loaded_profiles: Dict[str, Dict[str, AgentProfile]] = {}
        self.active_profiles: Dict[str, str] = {
            "monkey": "monkey_profile.json",
            "retail": "retail_profile.json"
        }
        
        # Load all available profiles
        self._load_all_profiles()
        
    def _load_all_profiles(self) -> None:
        """Load all profile files from the profiles directory."""
        self.loaded_profiles = {
            "monkey": {},
            "retail": {}
        }
        
        try:
            # Load monkey profiles
            monkey_profiles = list(self.profiles_dir.glob("monkey_*.json"))
            if not monkey_profiles:
                print(f"Warning: No monkey profiles found in {self.profiles_dir}")
            for profile_path in monkey_profiles:
                profile = self._load_profile(profile_path)
                if profile:
                    self.loaded_profiles["monkey"][profile_path.name] = profile
                    
            # Load retail profiles
            retail_profiles = list(self.profiles_dir.glob("retail_*.json"))
            if not retail_profiles:
                print(f"Warning: No retail profiles found in {self.profiles_dir}")
            for profile_path in retail_profiles:
                profile = self._load_profile(profile_path)
                if profile:
                    self.loaded_profiles["retail"][profile_path.name] = profile
                    
            print(f"Loaded profiles from {self.profiles_dir}:")
            print(f"Monkey profiles: {list(self.loaded_profiles['monkey'].keys())}")
            print(f"Retail profiles: {list(self.loaded_profiles['retail'].keys())}")
            
        except Exception as e:
            print(f"Error loading profiles: {e}")
            print(f"Profiles directory: {self.profiles_dir}")
            print(f"Directory exists: {self.profiles_dir.exists()}")
            print(f"Directory contents: {list(self.profiles_dir.glob('*'))}")
    
    def _load_profile(self, profile_path: Path) -> Optional[AgentProfile]:
        """Load a single profile from file."""
        try:
            with open(profile_path, 'r') as f:
                data = json.load(f)
            return AgentProfile.from_dict(data)
        except Exception as e:
            print(f"Error loading profile {profile_path}: {e}")
            return None
            
    def get_active_profile(self, agent_type: str) -> Optional[AgentProfile]:
        """Get the currently active profile for an agent type."""
        if agent_type not in self.loaded_profiles:
            return None
            
        active_filename = self.active_profiles[agent_type]
        return self.loaded_profiles[agent_type].get(active_filename)
        
    def list_available_profiles(self, agent_type: str) -> list[str]:
        """List all available profiles for an agent type."""
        if agent_type not in self.loaded_profiles:
            return []
        return list(self.loaded_profiles[agent_type].keys())
        
    def switch_profile(self, agent_type: str, profile_name: str) -> bool:
        """Switch the active profile for an agent type."""
        if (agent_type not in self.loaded_profiles or 
            profile_name not in self.loaded_profiles[agent_type]):
            return False
            
        self.active_profiles[agent_type] = profile_name
        return True
        
    def apply_profile_to_agent(self, agent_type: str, game_state: Dict[str, Any]) -> Dict[str, float]:
        """Apply psychological profile to modify agent behavior weights."""
        profile = self.get_active_profile(agent_type)
        if not profile:
            return {}
            
        weights = profile.behavior_weights.copy()
        
        # Apply biases based on game state
        if agent_type == "retail":
            # Adjust weights based on retail psychological factors
            if game_state.get("recent_success_rate", 0) > 0.5:
                # Increase overconfidence when doing well
                weights["spot_distance"] *= (1 + profile.biases["overconfidence"])
                
            if game_state.get("crowd_size", 0) > 3:
                # Increase herd behavior when others are targeting same strikes
                weights["crowd_following"] *= (1 + profile.biases["herd_mentality"])
                
        elif agent_type == "monkey":
            # Adjust weights based on market maker psychological factors
            if game_state.get("recent_loss_rate", 0) > 0.3:
                # Increase defensive behavior when taking losses
                weights["spot_distance"] *= (1 + profile.biases["loss_aversion"])
                
            if game_state.get("retail_clustering", 0) > 0.5:
                # Increase focus on retail patterns when clustering is detected
                weights["retail_clustering"] *= (1 + profile.biases["recency"])
                
        # Normalize weights
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
            
        return weights

# Create global profile manager instance
profile_manager = ProfileManager() 