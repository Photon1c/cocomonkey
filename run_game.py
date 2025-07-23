"""
Main entry point for the Flying Coconuts game.
"""

import os
import asyncio
import argparse
from core.engine import GameEngine, GameConfig
from core.ui import GameUI
from core.market_data_loader import market_data
from core.save_manager import save_manager

async def initialize_game() -> GameConfig:
    """Initialize game configuration with market data."""
    market_state = market_data.get_market_state()
    config = GameConfig(
        SPOT_PRICE=market_state["price"],
        STRIKES=market_state["strikes"],
        IMPLIED_VOL=market_state["implied_vol"]
    )
    return config

async def main(config: GameConfig = None, save_enabled: bool = False, record_gif: bool = False):
    """Main game loop."""
    if config is None:
        config = await initialize_game()
    
    engine = GameEngine(config)
    ui = GameUI(engine)
    
    running = True
    last_save_frame = 0
    save_interval = 100  # Save every 100 frames when enabled
    
    # Start recording if enabled
    if record_gif:
        print("GIF recording enabled...")
        save_manager.start_recording()
    
    try:
        while running:
            running = ui.handle_events()
            await engine.update()
            ui.draw()
            
            # Capture frame for GIF if recording
            if record_gif:
                save_manager.capture_frame(ui.screen)
            
            # Auto-save if enabled
            if save_enabled and engine.frame > 0 and engine.frame % save_interval == 0:
                if engine.frame != last_save_frame:
                    save_manager.save_game_state(engine)
                    last_save_frame = engine.frame
        
        # Final save when game ends
        if save_enabled:
            print("Saving final game state...")
            # Stop recording before saving to include GIF
            if record_gif:
                print("Finalizing GIF recording...")
                save_manager.stop_recording()
            save_manager.save_game_state(engine)
    
    except Exception as e:
        print(f"Error during game execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ui.cleanup()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Flying Coconuts Game")
    parser.add_argument("--save", action="store_true", help="Enable auto-saving to output directory")
    parser.add_argument("--record", action="store_true", help="Record gameplay as GIF")
    parser.add_argument("--frames", type=int, default=100, help="Number of frames to record for GIF (default: 100)")
    return parser.parse_args()

if __name__ == "__main__":
    # Parse arguments
    args = parse_args()
    
    # Load environment variables if .env exists
    if os.path.exists(".env"):
        from dotenv import load_dotenv
        load_dotenv()
    
    # Create output directory if saving is enabled
    if args.save:
        os.makedirs("output", exist_ok=True)
    
    # Add imageio to requirements if recording
    if args.record and args.save:
        try:
            import imageio
            import numpy as np
            print("GIF recording dependencies verified.")
        except ImportError as e:
            print(f"Installing missing dependencies for GIF recording: {e}")
            os.system("pip install imageio numpy")
            import imageio
            import numpy as np
    
    # Ensure recording is only enabled with save
    record_gif = args.record and args.save
    if args.record and not args.save:
        print("Warning: --record requires --save. GIF recording will be disabled.")
    elif record_gif:
        # Update frame limit
        if args.frames < 1:
            print("Warning: Invalid frame count. Using default (100)")
            args.frames = 100
        save_manager.set_max_frames(args.frames)
        print(f"GIF recording enabled with {args.frames} frame limit.")
    
    asyncio.run(main(save_enabled=args.save, record_gif=record_gif)) 