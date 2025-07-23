"""
UI module that handles the game's visual elements and user interaction.
"""

import pygame
from typing import Dict, List, Optional, Tuple
from .engine import GameEngine, GameConfig, Coconut
from .profiles.profile_loader import profile_manager

class GameUI:
    """Handles game visualization and user interaction."""
    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.config = engine.config
        
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.config.WIDTH, self.config.HEIGHT))
        pygame.display.set_caption("Flying Coconuts: Gamma Reflexivity Jungle")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font = pygame.font.SysFont(None, 22)
        self.title_font = pygame.font.SysFont(None, 32)
        
        # Colors
        self.COLORS = {
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "brown": (139, 69, 19),
            "green": (34, 139, 34),
            "orange": (255, 165, 0),
            "red": (255, 0, 0),
            "blue": (0, 0, 255),
            "gray": (128, 128, 128)
        }
        
        # UI state
        self.hover_strike = None
        self.show_instructions = True
        self.show_profiles = False
        self.show_memories = False
        self.show_slingshots = False

    def handle_events(self) -> bool:
        """Handle user input events. Returns False if game should quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.engine.toggle_pause()
                elif event.key == pygame.K_1:
                    self.engine.toggle_ai("retail")
                elif event.key == pygame.K_2:
                    self.engine.toggle_ai("monkey")
                elif event.key == pygame.K_r:
                    self.engine.reset()
                elif event.key == pygame.K_h:
                    self.show_instructions = not self.show_instructions
                elif event.key == pygame.K_p:
                    self.show_profiles = not self.show_profiles
                elif event.key == pygame.K_m:
                    self.show_memories = not self.show_memories
                elif event.key == pygame.K_s:
                    self.show_slingshots = not self.show_slingshots
                # Profile hot-swapping
                elif event.key in [pygame.K_F1, pygame.K_F2, pygame.K_F3]:
                    profile_idx = event.key - pygame.K_F1
                    self.engine.switch_profile("retail", profile_idx)
                elif event.key in [pygame.K_F5, pygame.K_F6, pygame.K_F7]:
                    profile_idx = event.key - pygame.K_F5
                    self.engine.switch_profile("monkey", profile_idx)
                # Slingshot selection
                elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3]:
                    slingshot_names = list(self.config.SLINGSHOTS.keys())
                    idx = event.key - pygame.K_1
                    if idx < len(slingshot_names):
                        self.engine.switch_slingshot(slingshot_names[idx])
                    
            elif event.type == pygame.MOUSEMOTION:
                self.update_hover(event.pos)
                
        return True

    def update_hover(self, mouse_pos: Tuple[int, int]) -> None:
        """Update hover state based on mouse position."""
        x, y = mouse_pos
        
        # Check if hovering over a tree
        for strike, tree_x in self.engine.TREE_X.items():
            if abs(x - tree_x) < 10 and abs(y - self.engine.TREE_Y) < 40:
                self.hover_strike = strike
                return
                
        # Check if hovering over a coconut
        for coconut in self.engine.coconuts:
            if abs(x - coconut.x) < 10 and abs(y - coconut.y) < 10:
                self.hover_strike = coconut.strike
                return
                
        self.hover_strike = None

    def draw_instructions(self) -> None:
        """Draw game instructions overlay."""
        if not self.show_instructions:
            return
            
        instructions = [
            "Controls:",
            "[Space] - Pause/Resume",
            "[1] - Toggle Retail AI",
            "[2] - Toggle Monkey AI",
            "[R] - Reset Game",
            "[H] - Hide/Show Help",
            "[P] - Show/Hide Profiles",
            "[M] - Show/Hide Memories",
            "[S] - Show/Hide Slingshots",
            "",
            "Profile Controls:",
            "[F1-F3] - Switch Retail Profile",
            "[F5-F7] - Switch Monkey Profile",
            "",
            "Slingshot Controls:",
            "[1-3] - Select Slingshot",
            "",
            f"Retail AI: {'ON' if self.engine.ai_enabled['retail'] else 'OFF'}",
            f"Monkey AI: {'ON' if self.engine.ai_enabled['monkey'] else 'OFF'}",
            f"Frame: {self.engine.frame}/{self.config.TRIALS}"
        ]
        
        # Draw semi-transparent background
        s = pygame.Surface((300, 400))
        s.set_alpha(128)
        s.fill(self.COLORS["white"])
        self.screen.blit(s, (10, 10))
        
        # Draw text
        for i, line in enumerate(instructions):
            text = self.font.render(line, True, self.COLORS["black"])
            self.screen.blit(text, (20, 20 + i * 20))

    def draw_profiles(self) -> None:
        """Draw current agent profiles."""
        if not self.show_profiles:
            return
            
        # Get current profiles
        retail_profile = profile_manager.get_active_profile("retail")
        monkey_profile = profile_manager.get_active_profile("monkey")
        
        if not retail_profile or not monkey_profile:
            return
            
        # Prepare profile info
        retail_info = [
            "Retail Profile:",
            f"Name: {retail_profile.name}",
            f"Risk Tolerance: {retail_profile.traits.get('risk_tolerance', 0):.1f}",
            f"FOMO: {retail_profile.traits.get('fomo_threshold', 0):.1f}",
            f"Optimism: {retail_profile.traits.get('optimism_bias', 0):.1f}"
        ]
        
        monkey_info = [
            "Monkey Profile:",
            f"Name: {monkey_profile.name}",
            f"Risk Aversion: {monkey_profile.traits.get('risk_aversion', 0):.1f}",
            f"Reflexivity: {monkey_profile.traits.get('reflexivity_awareness', False)}",
            f"Defense Radius: {monkey_profile.traits.get('defense_radius', 0)}"
        ]
        
        # Draw semi-transparent background
        s = pygame.Surface((300, 250))
        s.set_alpha(128)
        s.fill(self.COLORS["white"])
        self.screen.blit(s, (self.config.WIDTH - 310, 10))
        
        # Draw profile info
        y = 20
        for line in retail_info:
            text = self.font.render(line, True, self.COLORS["black"])
            self.screen.blit(text, (self.config.WIDTH - 300, y))
            y += 20
            
        y += 20  # Add space between profiles
        for line in monkey_info:
            text = self.font.render(line, True, self.COLORS["black"])
            self.screen.blit(text, (self.config.WIDTH - 300, y))
            y += 20

    def draw_slingshots(self) -> None:
        """Draw slingshot information."""
        if not self.show_slingshots:
            return
            
        slingshot_info = []
        current = self.engine.current_slingshot
        
        # Current slingshot info
        slingshot_info.extend([
            "Current Slingshot:",
            f"Name: {current['name']}",
            f"Power: {current['power']:.1f}",
            f"Accuracy: {current['accuracy']:.1f}",
            f"DTE: {current['dte']}",
            f"Type: {current['option_type'].upper()}",
            "",
            "Available Slingshots:"
        ])
        
        # List all slingshots
        for i, (name, slingshot) in enumerate(self.config.SLINGSHOTS.items()):
            slingshot_info.append(f"[{i+1}] {name}")
            
        # Draw background
        s = pygame.Surface((300, 250))
        s.set_alpha(128)
        s.fill(self.COLORS["white"])
        self.screen.blit(s, (self.config.WIDTH - 310, 200))
        
        # Draw text
        for i, line in enumerate(slingshot_info):
            text = self.font.render(line, True, self.COLORS["black"])
            self.screen.blit(text, (self.config.WIDTH - 300, 210 + i * 20))

    def draw_memories(self) -> None:
        """Draw agent memory insights."""
        if not self.show_memories:
            return
            
        # Get memory summaries
        retail_summary = self.engine.retail_memory.summarize_insights()
        monkey_summary = self.engine.monkey_memory.summarize_insights()
        
        # Split summaries into lines
        memory_lines = []
        memory_lines.extend(retail_summary.split("\n"))
        memory_lines.append("")  # Add spacing
        memory_lines.extend(monkey_summary.split("\n"))
        
        # Draw background
        height = len(memory_lines) * 20 + 20
        s = pygame.Surface((400, height))
        s.set_alpha(128)
        s.fill(self.COLORS["white"])
        self.screen.blit(s, (self.config.WIDTH - 410, 460))
        
        # Draw text
        for i, line in enumerate(memory_lines):
            text = self.font.render(line, True, self.COLORS["black"])
            self.screen.blit(text, (self.config.WIDTH - 400, 470 + i * 20))

    def draw_tooltip(self) -> None:
        """Draw tooltip for hovered strike."""
        if self.hover_strike is None:
            return
            
        strike = self.hover_strike
        info = [
            f"Strike: {strike}",
            f"Hits: {self.engine.tree_hits[strike]}",
            f"Retail Juice: {self.engine.retail_juice[strike]:.2f}",
            f"MM Juice: {self.engine.mm_juice[strike]:.2f}"
        ]
        
        # Find coconuts targeting this strike
        for coconut in self.engine.coconuts:
            if coconut.strike == strike:
                info.extend([
                    f"Source: {coconut.source_agent}",
                    f"Slingshot: {coconut.slingshot['name']}",
                    f"Type: {coconut.slingshot['option_type'].upper()}",
                    f"DTE: {coconut.frames_remaining//60}",
                    "Status: In Flight"
                ])
                break
                
        # Draw tooltip background
        width = 200
        height = len(info) * 20 + 10
        x, y = pygame.mouse.get_pos()
        x = min(x, self.config.WIDTH - width - 10)
        y = min(y, self.config.HEIGHT - height - 10)
        
        s = pygame.Surface((width, height))
        s.set_alpha(192)
        s.fill(self.COLORS["white"])
        self.screen.blit(s, (x, y))
        
        # Draw tooltip text
        for i, line in enumerate(info):
            text = self.font.render(line, True, self.COLORS["black"])
            self.screen.blit(text, (x + 10, y + 5 + i * 20))

    def draw_trees_and_juice(self) -> None:
        """Draw trees and juice bars."""
        # Draw gamma profile background
        for strike in self.engine.valid_strikes:
            x = self.engine.TREE_X[strike]
            y = self.engine.TREE_Y
            gamma = self.engine.config.GAMMA_STRENGTH[strike]
            
            # Draw gamma well - height based on gamma strength
            gamma_height = int(100 * gamma)
            gamma_rect = pygame.Rect(x - 10, y - gamma_height, 25, gamma_height)
            gamma_color = (100, 100, 255, int(128 * gamma))  # Semi-transparent blue
            s = pygame.Surface((25, gamma_height))
            s.set_alpha(int(128 * gamma))
            s.fill((100, 100, 255))
            self.screen.blit(s, (x - 10, y - gamma_height))
            
            # Tree trunk
            pygame.draw.rect(self.screen, self.COLORS["brown"], (x, y, 5, 20))
            
            # Juice bar
            total = self.engine.retail_juice[strike] + self.engine.mm_juice[strike]
            if total > 0:
                r_ratio = self.engine.retail_juice[strike] / total
                m_ratio = self.engine.mm_juice[strike] / total
                
                # Scale juice bars relative to gamma well
                bar_height = int(80 * total)
                
                # MM juice (orange)
                pygame.draw.rect(self.screen, self.COLORS["orange"],
                               (x + 6, y - int(m_ratio * bar_height), 8, int(m_ratio * bar_height)))
                               
                # Retail juice (green)
                pygame.draw.rect(self.screen, self.COLORS["green"],
                               (x + 6, y - bar_height, 8, int(r_ratio * bar_height)))
            
            # Spot price marker
            if abs(strike - self.engine.config.SPOT_PRICE) < 0.5:
                pygame.draw.rect(self.screen, self.COLORS["red"], (x - 10, y + 25, 25, 5))
                
            # Strike label
            label = self.font.render(str(strike), True, self.COLORS["black"])
            label_rect = label.get_rect(center=(x + 2, y + 45))
            self.screen.blit(label, label_rect)

    def draw_coconuts(self) -> None:
        """Draw flying coconuts."""
        for coconut in self.engine.coconuts:
            # Use slingshot color and size from dictionary
            color = tuple(coconut.slingshot["color"])
            size = coconut.slingshot["size"]
            pygame.draw.circle(self.screen, color, (int(coconut.x), int(coconut.y)), size)
            
            # Draw DTE indicator
            if coconut.frames_remaining > 0:
                dte_text = self.font.render(
                    f"{coconut.frames_remaining//60}", 
                    True, 
                    self.COLORS["white"]
                )
                text_rect = dte_text.get_rect(
                    center=(int(coconut.x), int(coconut.y))
                )
                self.screen.blit(dte_text, text_rect)

    def draw_scoreboard(self) -> None:
        """Draw the game scoreboard."""
        total_retail = sum(self.engine.retail_juice.values())
        total_mm = sum(self.engine.mm_juice.values())
        
        scores = [
            f"SPY: ${self.config.SPOT_PRICE:.2f}",  # Add SPY price at the top
            f"IV: {self.config.IMPLIED_VOL:.1f}%",  # Add implied volatility
            "",  # Add spacing
            f"Retail Total: {total_retail:.2f}",
            f"MM Total: {total_mm:.2f}",
            f"Frame: {self.engine.frame}/{self.config.TRIALS}"
        ]
        
        y = 10
        for score in scores:
            # Use different colors for price and IV
            if score.startswith("SPY:"):
                color = self.COLORS["blue"]
            elif score.startswith("IV:"):
                color = self.COLORS["orange"]
            else:
                color = self.COLORS["black"]
                
            text = self.title_font.render(score, True, color)
            self.screen.blit(text, (self.config.WIDTH - 250, y))
            y += 30 if score else 15  # Less spacing for empty lines

    def draw(self) -> None:
        """Draw the complete game frame."""
        # Clear screen
        self.screen.fill(self.COLORS["white"])
        
        # Draw game elements
        self.draw_trees_and_juice()
        self.draw_coconuts()
        self.draw_scoreboard()
        
        # Draw UI overlays
        self.draw_instructions()
        self.draw_profiles()
        self.draw_slingshots()
        self.draw_memories()
        self.draw_tooltip()
        
        # Update display
        pygame.display.flip()
        self.clock.tick(self.config.FPS)

    def cleanup(self) -> None:
        """Clean up pygame resources."""
        pygame.quit() 