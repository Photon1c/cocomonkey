"""
Game engine module that manages the game state and mechanics.
"""

from typing import Dict, List, Optional, Tuple
import random
import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from .retail_agent import RetailAgent
from .monkey_agent import MonkeyAgent
from .profiles.profile_loader import profile_manager
from .memory_logger import MemoryLogger
from .market_data_loader import market_data

@dataclass
class GameConfig:
    """Game configuration parameters."""
    WIDTH: int = 1280
    HEIGHT: int = 720
    FPS: int = 60
    SPOT_PRICE: float = None
    STRIKES: List[int] = None
    GAMMA_STRENGTH: Dict[int, float] = None
    IMPLIED_VOL: float = None
    DTE: int = None
    TRIALS: int = 1000
    SLINGSHOTS: Dict[str, Dict] = field(default_factory=dict)
    DEFAULT_SLINGSHOT: str = None

    def __post_init__(self):
        # Load market data
        market_state = market_data.get_market_state()
        self.SPOT_PRICE = market_state["price"]
        self.IMPLIED_VOL = market_state["implied_vol"]
        
        # Load portfolio settings
        portfolio_path = Path(__file__).parent / "data" / "portfolio.json"
        with open(portfolio_path, 'r') as f:
            portfolio = json.load(f)
            self.SLINGSHOTS = {s["name"]: s for s in portfolio["slingshots"]}
            self.DEFAULT_SLINGSHOT = portfolio["default_slingshot"]
            self.DTE = portfolio["market_settings"]["default_dte"]
        
        # Generate strikes and gamma
        if self.STRIKES is None:
            self.STRIKES = market_state["strikes"]
        if self.GAMMA_STRENGTH is None:
            # Use actual gamma profile if available, otherwise generate synthetic
            gamma_profile = market_state.get("gamma_profile", {})
            if gamma_profile:
                # Normalize gamma values
                max_gamma = max(gamma_profile.values())
                self.GAMMA_STRENGTH = {
                    s: (gamma_profile.get(s, 0) / max_gamma) 
                    for s in self.STRIKES
                }
            else:
                # Synthetic gamma profile
                self.GAMMA_STRENGTH = {
                    s: 0.2 + 0.02 * abs(s - self.SPOT_PRICE) 
                    for s in self.STRIKES
                }

@dataclass
class Coconut:
    """Represents a flying coconut in the game."""
    strike: int
    x: float
    y: float
    target_x: float
    target_y: float
    slingshot: Dict  # Slingshot configuration
    t: float = 0
    speed: float = 0.02
    hit: bool = False
    retail_juice: float = 0
    mm_juice: float = 0
    source_agent: str = "retail"
    alive: bool = True
    frames_remaining: int = None
    option_type: str = "call"  # call or put

    def __post_init__(self):
        if self.frames_remaining is None:
            # Convert DTE to frames (assuming 60 FPS and accelerated time)
            self.frames_remaining = self.slingshot["dte"] * 60
        self.option_type = self.slingshot["option_type"]

    def update(self) -> None:
        """Update coconut position and state."""
        self.frames_remaining -= 1
        if self.frames_remaining <= 0:
            self.alive = False
            return

        self.t += self.speed * self.slingshot["power"]
        if self.t >= 1:
            self.alive = False
        else:
            # Enhanced arc path with slingshot accuracy
            accuracy_factor = random.uniform(
                1 - (1 - self.slingshot["accuracy"]), 
                1 + (1 - self.slingshot["accuracy"])
            )
            
            # Base path
            base_x = (1 - self.t) * self.x + self.t * self.target_x
            base_y = (1 - self.t) * self.y + self.t * self.target_y
            
            # Add arc and accuracy variation
            arc_height = 100 * self.slingshot["power"]
            arc_offset = arc_height * self.t * (1 - self.t)
            
            self.x = base_x * accuracy_factor
            self.y = base_y - arc_offset

class GameEngine:
    """Manages game state and mechanics."""
    def __init__(self, config: GameConfig):
        self.config = config
        self.retail_agent = RetailAgent()
        self.monkey_agent = MonkeyAgent()
        
        # Initialize memory loggers
        self.retail_memory = MemoryLogger("retail")
        self.monkey_memory = MemoryLogger("monkey")
        
        # Game state - ensure strikes are sorted for consistency
        self.valid_strikes = sorted(config.STRIKES)
        self.tree_hits = {s: 0 for s in self.valid_strikes}
        self.retail_juice = {s: 0 for s in self.valid_strikes}
        self.mm_juice = {s: 0 for s in self.valid_strikes}
        self.coconuts: List[Coconut] = []
        self.frame = 0
        self.paused = False
        self.ai_enabled = {"retail": True, "monkey": True}
        
        # Calculate tree positions with proper spacing
        strike_range = max(self.valid_strikes) - min(self.valid_strikes)
        spacing = min(30, (self.config.WIDTH - 100) / (len(self.valid_strikes) + 1))
        start_x = 50
        
        self.TREE_X = {
            strike: start_x + i * spacing 
            for i, strike in enumerate(self.valid_strikes)
        }
        self.TREE_Y = config.HEIGHT - 120
        
        # Available profiles
        self.retail_profiles = profile_manager.list_available_profiles("retail")
        self.monkey_profiles = profile_manager.list_available_profiles("monkey")
        
        # Current slingshot
        self.current_slingshot = self.config.SLINGSHOTS[self.config.DEFAULT_SLINGSHOT]
        
        # Initialize gamma profile
        if self.config.GAMMA_STRENGTH is None:
            self._initialize_gamma_profile()
            
    def _initialize_gamma_profile(self) -> None:
        """Initialize gamma profile with proper scaling."""
        spot_price = self.config.SPOT_PRICE
        
        # Get actual gamma profile if available
        gamma_profile = market_data.get_gamma_profile()
        
        if gamma_profile:
            # Normalize gamma values
            max_gamma = max(gamma_profile.values())
            if max_gamma > 0:
                self.config.GAMMA_STRENGTH = {
                    s: (gamma_profile.get(s, 0) / max_gamma) 
                    for s in self.valid_strikes
                }
                print(f"Using actual gamma profile: {self.config.GAMMA_STRENGTH}")
                return
        
        # Generate synthetic gamma profile
        # Higher gamma near spot price, decaying as we move away
        self.config.GAMMA_STRENGTH = {}
        for strike in self.valid_strikes:
            distance = abs(strike - spot_price)
            # Exponential decay with distance
            gamma = 1.0 * pow(0.9, distance)
            self.config.GAMMA_STRENGTH[strike] = gamma
            
        print(f"Using synthetic gamma profile around {spot_price}")
        
    def _get_valid_strike(self, strike: int) -> int:
        """Get nearest valid strike price."""
        if strike not in self.valid_strikes:
            strike = min(self.valid_strikes, key=lambda x: abs(x - strike))
            print(f"Adjusted strike {strike} to nearest valid strike")
        return strike

    def _get_tree_position(self, strike: int) -> Tuple[float, float]:
        """Get tree position for a strike, adjusting if needed."""
        strike = self._get_valid_strike(strike)
        return self.TREE_X[strike], self.TREE_Y

    def _update_game_state(self, strike: int, hit: bool, retail: float, mm: float) -> None:
        """Update game state with validated strike."""
        valid_strike = self._get_valid_strike(strike)
        if hit:
            self.tree_hits[valid_strike] += 1
            self.retail_juice[valid_strike] += retail
            self.mm_juice[valid_strike] += mm

    def get_game_state(self) -> Dict:
        """Get current game state for agents."""
        return {
            "spot_price": self.config.SPOT_PRICE,
            "strikes": self.valid_strikes,
            "tree_hits": self.tree_hits,
            "retail_juice": self.retail_juice,
            "mm_juice": self.mm_juice,
            "frame": self.frame,
            "current_slingshot": self.current_slingshot["name"],
            "option_type": self.current_slingshot["option_type"]
        }

    async def simulate_slingshot_hit(self, spot_price: float, strike_price: int) -> Tuple[bool, float, float]:
        """Simulate if a coconut hits and calculate juice distribution."""
        # Validate strike price
        if strike_price not in self.valid_strikes:
            print(f"Warning: Strike {strike_price} out of valid range {min(self.valid_strikes)}-{max(self.valid_strikes)}")
            strike_price = self._get_valid_strike(strike_price)

        delta_distance = abs(spot_price - strike_price)
        base_hit_chance = 1.0 / (1 + delta_distance)
        
        # Get monkey defense prediction
        if self.ai_enabled["monkey"]:
            predictions = await self.monkey_agent.predict_targets(self.get_game_state())
            defense_strikes = [p[0] for p in predictions]
            if strike_price in defense_strikes:
                base_hit_chance *= 0.5  # Reduce hit chance if monkey predicted the strike
                
                # Record defense result based on final hit chance
                defense_success = random.random() > base_hit_chance
                self.monkey_agent.record_defense_result(defense_success)
                
                # Add memory
                if defense_success:
                    self.monkey_memory.add_memory(
                        f"Successfully defended {self.current_slingshot['option_type']} strike {strike_price}",
                        0.8
                    )
                else:
                    self.monkey_memory.add_memory(
                        f"Failed to defend {self.current_slingshot['option_type']} strike {strike_price}",
                        0.6
                    )
        
        # Apply modifiers
        wind_penalty = self.config.IMPLIED_VOL / 100
        gamma_penalty = self.config.GAMMA_STRENGTH[strike_price] / 10
        decay_penalty = max(0.1, self.current_slingshot["dte"] / 30)
        
        # Apply slingshot properties
        accuracy_bonus = self.current_slingshot["accuracy"] * 0.2
        power_factor = self.current_slingshot["power"] * 0.1
        
        # Option type modifier
        if self.current_slingshot["option_type"] == "call":
            # Calls are more effective when price is rising
            option_mod = 1.1 if spot_price > strike_price else 0.9
        else:
            # Puts are more effective when price is falling
            option_mod = 1.1 if spot_price < strike_price else 0.9
        
        final_hit_chance = (
            base_hit_chance * 
            (1 - wind_penalty) * 
            (1 - gamma_penalty) * 
            (1 / decay_penalty) *
            (1 + accuracy_bonus) *
            (1 + power_factor) *
            option_mod
        )
        final_hit_chance = max(0, min(final_hit_chance, 1))
        
        hit = random.random() < final_hit_chance
        mm_juice = 0.7 if hit else 0
        retail_juice = 1 - mm_juice if hit else 0
        
        # Record retail hit result and memory
        self.retail_agent.record_hit(hit)
        if hit:
            self.retail_memory.add_memory(
                f"Hit {self.current_slingshot['option_type']} strike {strike_price} at spot {spot_price}",
                0.7
            )
        else:
            self.retail_memory.add_memory(
                f"Missed {self.current_slingshot['option_type']} strike {strike_price}",
                0.5
            )
        
        return hit, retail_juice, mm_juice

    async def launch_coconut(self) -> Optional[Coconut]:
        """Launch a new coconut, using retail agent if enabled."""
        if self.frame >= self.config.TRIALS:
            return None
            
        if self.ai_enabled["retail"]:
            # Get valid targets for current slingshot
            targets = market_data.get_slingshot_targets(
                self.current_slingshot["name"],
                self.config.SPOT_PRICE
            )
            
            if targets:
                # Use most attractive target
                target_data = targets[0]
                target = target_data["strike"]
                confidence = target_data["attractiveness"]
            else:
                # Fallback to agent selection with valid strike range
                target, confidence = await self.retail_agent.select_target(self.get_game_state())
                # Ensure target is within valid range
                target = self._get_valid_strike(target)
        else:
            target = random.choice(self.valid_strikes)  # Always choose from valid strikes
            confidence = 1.0
            
        if target is None:
            return None
            
        hit, retail, mm = await self.simulate_slingshot_hit(self.config.SPOT_PRICE, target)
        
        # Get tree position for target
        tree_x, tree_y = self._get_tree_position(target)
        
        coconut = Coconut(
            strike=target,
            x=self.config.WIDTH // 2,
            y=0,
            target_x=tree_x + 10,  # Add offset for better targeting
            target_y=tree_y,
            speed=random.uniform(0.01, 0.03),
            hit=hit,
            retail_juice=retail,
            mm_juice=mm,
            source_agent="retail" if self.ai_enabled["retail"] else "random",
            slingshot=self.current_slingshot
        )
        
        return coconut

    def switch_slingshot(self, slingshot_name: str) -> bool:
        """Switch to a different slingshot."""
        if slingshot_name in self.config.SLINGSHOTS:
            self.current_slingshot = self.config.SLINGSHOTS[slingshot_name]
            return True
        return False

    async def update(self) -> None:
        """Update game state for one frame."""
        if self.paused:
            return
            
        # Launch new coconut
        coconut = await self.launch_coconut()
        if coconut:
            self.coconuts.append(coconut)
            self.frame += 1
            
        # Update existing coconuts
        for coconut in self.coconuts[:]:
            coconut.update()
            if not coconut.alive:
                # Update game state with validated strike
                self._update_game_state(
                    coconut.strike,
                    coconut.hit,
                    coconut.retail_juice,
                    coconut.mm_juice
                )
                self.coconuts.remove(coconut)

    def toggle_pause(self) -> None:
        """Toggle game pause state."""
        self.paused = not self.paused

    def toggle_ai(self, agent_type: str) -> None:
        """Toggle AI for specified agent type."""
        if agent_type in self.ai_enabled:
            self.ai_enabled[agent_type] = not self.ai_enabled[agent_type]

    def switch_profile(self, agent_type: str, profile_idx: int) -> bool:
        """Switch to a different profile for the specified agent."""
        if agent_type == "retail" and profile_idx < len(self.retail_profiles):
            return profile_manager.switch_profile("retail", self.retail_profiles[profile_idx])
        elif agent_type == "monkey" and profile_idx < len(self.monkey_profiles):
            return profile_manager.switch_profile("monkey", self.monkey_profiles[profile_idx])
        return False

    def reset(self) -> None:
        """Reset game state."""
        self.tree_hits = {s: 0 for s in self.valid_strikes}
        self.retail_juice = {s: 0 for s in self.valid_strikes}
        self.mm_juice = {s: 0 for s in self.valid_strikes}
        self.coconuts = []
        self.frame = 0 