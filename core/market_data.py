"""
Alternative market data implementation using Alpha Vantage API.
This module is currently not in use, as the game uses historical CSV data instead (see market_data_loader.py).

Features:
- Real-time data fetching from Alpha Vantage API
- Local caching mechanism
- Async data retrieval
- Synthetic data generation for fallback

Requirements:
- Alpha Vantage API key (set as ALPHA_VANTAGE_KEY environment variable)
- aiohttp for async API calls
"""

import json
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import os
from pathlib import Path

class MarketData:
    """Handles fetching and caching of market data."""
    
    def __init__(self):
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "spy_cache.json"
        
        # Default values in case API fails
        self.default_price = 628.86
        self.default_strikes = list(range(610, 646))
        self.default_vol = 13.7
        
        # Cache settings
        self.cache_duration = timedelta(minutes=5)
        self.last_update: Optional[datetime] = None
        self.cached_data: Dict = {}

    async def _fetch_spy_data(self) -> Dict:
        """Fetch SPY data from a free API."""
        try:
            # Using Alpha Vantage free API (you can replace with your preferred source)
            api_key = os.getenv("ALPHA_VANTAGE_KEY", "demo")
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=SPY&apikey={api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "Global Quote" in data:
                            quote = data["Global Quote"]
                            return {
                                "price": float(quote.get("05. price", self.default_price)),
                                "volume": int(quote.get("06. volume", 0)),
                                "timestamp": datetime.now().isoformat()
                            }
            return self._get_default_data()
        except Exception as e:
            print(f"Error fetching SPY data: {e}")
            return self._get_default_data()

    def _get_default_data(self) -> Dict:
        """Get default market data."""
        return {
            "price": self.default_price,
            "strikes": self.default_strikes,
            "implied_vol": self.default_vol,
            "timestamp": datetime.now().isoformat()
        }

    def _load_cache(self) -> Dict:
        """Load cached market data."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    if data.get("timestamp"):
                        self.last_update = datetime.fromisoformat(data["timestamp"])
                    return data
        except Exception as e:
            print(f"Error loading cache: {e}")
        return self._get_default_data()

    def _save_cache(self, data: Dict) -> None:
        """Save market data to cache."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def _generate_strikes(self, spot_price: float) -> List[int]:
        """Generate strike prices around the spot price."""
        base = round(spot_price)
        return list(range(base - 15, base + 16))

    def _calculate_implied_vol(self, price: float, volume: int) -> float:
        """Simple IV calculation based on price and volume."""
        # This is a very simplified calculation
        # In reality, you'd want to use actual options data
        base_vol = 13.7  # Base volatility
        vol_factor = volume / 1000000  # Volume impact
        price_factor = abs(price - self.cached_data.get("price", price)) / price
        
        return base_vol * (1 + vol_factor * 0.1 + price_factor * 5)

    async def get_market_data(self, force_refresh: bool = False) -> Dict:
        """Get current market data, using cache if available."""
        now = datetime.now()
        
        # Check if we need to refresh the data
        if (not self.cached_data or 
            force_refresh or 
            not self.last_update or 
            (now - self.last_update) > self.cache_duration):
            
            # Fetch new data
            new_data = await self._fetch_spy_data()
            
            # Update cached data
            self.cached_data = {
                "price": new_data["price"],
                "strikes": self._generate_strikes(new_data["price"]),
                "implied_vol": self._calculate_implied_vol(
                    new_data["price"],
                    new_data.get("volume", 0)
                ),
                "timestamp": new_data["timestamp"]
            }
            
            # Update cache
            self.last_update = now
            self._save_cache(self.cached_data)
            
        return self.cached_data

    async def get_price_history(self, lookback_days: int = 30) -> List[Tuple[str, float]]:
        """Get historical price data (simplified version)."""
        # In a real implementation, you'd fetch this from an API
        # For now, we'll generate synthetic data
        history = []
        base_price = self.cached_data.get("price", self.default_price)
        
        for i in range(lookback_days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            # Add some random variation
            price = base_price * (1 + (hash(date) % 100 - 50) / 1000)
            history.append((date, price))
            
        return list(reversed(history))

# Create global market data instance
market_data = MarketData() 