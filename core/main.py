"""
Main module that initializes and runs the game.
"""

import asyncio
import pygame
from engine import GameEngine, GameConfig
from ui import GameUI
from market_data import market_data

async def main(config: GameConfig = None):
    """Initialize and run the game."""
    # Initialize game components
    if config is None:
        # Use default config if none provided
        config = GameConfig()
    
    engine = GameEngine(config)
    ui = GameUI(engine)
    
    # Set up market data refresh task
    async def refresh_market_data():
        while True:
            try:
                # Update market data every 5 minutes
                market_state = await market_data.get_market_data()
                engine.config.SPOT_PRICE = market_state["price"]
                engine.config.IMPLIED_VOL = market_state["implied_vol"]
                await asyncio.sleep(300)  # 5 minutes
            except Exception as e:
                print(f"Error refreshing market data: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    # Start market data refresh task
    refresh_task = asyncio.create_task(refresh_market_data())
    
    # Main game loop
    running = True
    while running:
        # Handle events
        running = ui.handle_events()
        
        # Update game state
        await engine.update()
        
        # Render frame
        ui.draw()
    
    # Cleanup
    refresh_task.cancel()
    ui.cleanup()

if __name__ == "__main__":
    # Run the async game loop
    asyncio.run(main()) 