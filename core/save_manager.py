"""
Save manager module for saving game states and replays.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import pandas as pd
import pygame
import numpy as np
import imageio

class SaveManager:
    """Manages saving game states and statistics."""
    
    def __init__(self, base_dir: str = "output", max_frames: int = 100):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.recording = False
        self.frames: List[np.ndarray] = []
        self.max_frames = max_frames
        print(f"SaveManager initialized with {max_frames} frame limit")
        
    def start_recording(self) -> None:
        """Start recording frames for GIF."""
        self.recording = True
        self.frames = []
        print(f"Started recording (limit: {self.max_frames} frames)")
        
    def stop_recording(self) -> None:
        """Stop recording frames."""
        self.recording = False
        
    def capture_frame(self, screen: pygame.Surface) -> None:
        """Capture current frame if recording is active."""
        if self.recording and len(self.frames) < self.max_frames:
            try:
                # Convert pygame surface to numpy array
                frame = pygame.surfarray.array3d(screen)
                # Transpose to correct dimensions
                frame = frame.transpose([1, 0, 2])
                self.frames.append(frame)
                frames_left = self.max_frames - len(self.frames)
                if len(self.frames) % 30 == 0:  # Log every second
                    print(f"Captured frame {len(self.frames)}/{self.max_frames} ({frames_left} remaining)")
                if frames_left == 0:
                    print("Frame limit reached, stopping recording...")
                    self.stop_recording()
            except Exception as e:
                print(f"Error capturing frame: {e}")
            
    def save_game_state(self, engine, timestamp: Optional[str] = None) -> str:
        """Save current game state to a JSON file."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        # Create session directory
        session_dir = self.base_dir / timestamp
        session_dir.mkdir(exist_ok=True)
        
        # Save GIF if we have recorded frames
        if self.frames:
            print(f"Preparing to save GIF with {len(self.frames)} frames...")
            gif_path = session_dir / "replay.gif"
            try:
                # Ensure frames are valid
                if not all(isinstance(f, np.ndarray) for f in self.frames):
                    print("Error: Invalid frame data")
                    for i, f in enumerate(self.frames):
                        print(f"Frame {i} type: {type(f)}")
                    raise ValueError("Invalid frame data")

                # Check frame dimensions
                if self.frames:
                    print(f"Frame dimensions: {self.frames[0].shape}")

                # Reduce size to save space
                print("Resizing frames...")
                frames = [self._resize_frame(frame, 0.5) for frame in self.frames]
                
                print(f"Saving GIF to {gif_path}...")
                imageio.mimsave(str(gif_path), frames, fps=30)
                print(f"Successfully saved replay GIF with {len(self.frames)} frames")
                
                # Clear frames after saving
                self.frames = []
            except Exception as e:
                print(f"Error saving GIF: {e}")
                import traceback
                traceback.print_exc()
        
        # Save other game state data
        try:
            # Collect game state
            state = {
                "timestamp": timestamp,
                "spot_price": engine.config.SPOT_PRICE,
                "implied_vol": engine.config.IMPLIED_VOL,
                "frame": engine.frame,
                "strikes": engine.valid_strikes,
                "tree_hits": engine.tree_hits,
                "retail_juice": engine.retail_juice,
                "mm_juice": engine.mm_juice,
                "gamma_profile": engine.config.GAMMA_STRENGTH,
                "ai_enabled": engine.ai_enabled,
                "current_slingshot": engine.current_slingshot,
            }
            
            # Save main state
            state_file = session_dir / "game_state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            # Save agent memories
            self._save_memories(engine.retail_memory, session_dir / "retail_memories.json")
            self._save_memories(engine.monkey_memory, session_dir / "monkey_memories.json")
            
            # Save statistics as CSV
            self._save_statistics(engine, session_dir / "statistics.csv")
            
            print(f"Game state saved to {session_dir}")
            return str(session_dir)
        except Exception as e:
            print(f"Error saving game state: {e}")
            import traceback
            traceback.print_exc()
            return str(session_dir)
        
    def _resize_frame(self, frame: np.ndarray, scale: float) -> np.ndarray:
        """Resize frame to reduce GIF size."""
        try:
            if scale == 1:
                return frame
            # Use simple downsampling instead of interpolation
            return frame[::2, ::2]
        except Exception as e:
            print(f"Error resizing frame: {e}")
            return frame
        
    def _save_memories(self, memory_logger, filepath: Path) -> None:
        """Save agent memories to JSON."""
        memories = [memory.to_dict() for memory in memory_logger.memories]
        with open(filepath, 'w') as f:
            json.dump(memories, f, indent=2)
            
    def _save_statistics(self, engine, filepath: Path) -> None:
        """Save game statistics to CSV."""
        stats = []
        for strike in engine.valid_strikes:
            stats.append({
                "strike": strike,
                "hits": engine.tree_hits[strike],
                "retail_juice": engine.retail_juice[strike],
                "mm_juice": engine.mm_juice[strike],
                "gamma": engine.config.GAMMA_STRENGTH.get(strike, 0),
            })
        
        df = pd.DataFrame(stats)
        df.to_csv(filepath, index=False)
        
    def load_game_state(self, timestamp: str) -> Dict:
        """Load a saved game state."""
        session_dir = self.base_dir / timestamp
        if not session_dir.exists():
            raise FileNotFoundError(f"No saved game found for timestamp {timestamp}")
            
        # Load main state
        state_file = session_dir / "game_state.json"
        with open(state_file, 'r') as f:
            state = json.load(f)
            
        # Load statistics
        stats_file = session_dir / "statistics.csv"
        if stats_file.exists():
            state["statistics"] = pd.read_csv(stats_file).to_dict('records')
            
        return state
        
    def list_saved_games(self) -> list:
        """List all saved game sessions."""
        saved_games = []
        for session_dir in self.base_dir.iterdir():
            if session_dir.is_dir():
                state_file = session_dir / "game_state.json"
                if state_file.exists():
                    with open(state_file, 'r') as f:
                        state = json.load(f)
                        saved_games.append({
                            "timestamp": state["timestamp"],
                            "spot_price": state["spot_price"],
                            "frame": state["frame"],
                            "has_replay": (session_dir / "replay.gif").exists()
                        })
        return saved_games

    def set_max_frames(self, max_frames: int) -> None:
        """Update the maximum number of frames to record."""
        self.max_frames = max_frames
        print(f"Updated frame limit to {max_frames}")

# Create global save manager instance
save_manager = SaveManager() 