"""
Market data loader that manages historical CSV data.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd
from .data.data_loader import load_stock_data, load_option_data

class MarketDataLoader:
    """Handles loading and managing market data from CSV files."""
    
    def __init__(self):
        # Load portfolio settings
        self.portfolio_file = Path(__file__).parent / "data" / "portfolio.json"
        self.settings = self._load_portfolio_settings()
        
        # Load historical data
        self.historical_data = self._load_historical_data()
        
        # Current market state
        self.current_data = self._get_current_state()

    def _load_portfolio_settings(self) -> Dict:
        """Load settings from portfolio.json."""
        try:
            with open(self.portfolio_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading portfolio settings: {e}")
            return {
                "market_settings": {
                    "ticker": "SPY",
                    "data_path": "data/historical",
                    "default_dte": 5,
                    "strike_range": [-15, 15]
                },
                "data_settings": {
                    "max_historical_days": 30,
                    "fallback_price": 628.86,
                    "fallback_vol": 13.7
                }
            }

    def _load_historical_data(self) -> Dict:
        """Load historical stock and options data."""
        ticker = self.settings["market_settings"]["ticker"]
        try:
            # Load stock data
            stock_data = load_stock_data(ticker)
            if "Date" in stock_data.columns:
                stock_data["Date"] = pd.to_datetime(stock_data["Date"])
                stock_data.set_index("Date", inplace=True)
            stock_data = stock_data.sort_index(ascending=True)
            
            # Get the most recent price
            last_price = float(stock_data["Close/Last"].iloc[-1])
            print(f"Loaded stock price: {last_price}")
            last_volume = int(stock_data["Volume"].iloc[-1])
            
            # Load options data
            try:
                options_data = load_option_data(ticker)
                print("Options data columns:", options_data.columns.tolist())
                
                # Process options data for strike range and gamma
                if not options_data.empty:
                    # Get current date from stock data
                    current_date = stock_data.index[-1]
                    
                    # Clean strike prices - ensure they're numeric
                    strike_col = "Strike Price" if "Strike Price" in options_data.columns else "Strike"
                    options_data[strike_col] = pd.to_numeric(options_data[strike_col], errors='coerce')
                    options_data = options_data.dropna(subset=[strike_col])
                    
                    # Get strikes around current price
                    strikes = sorted(options_data[strike_col].unique())
                    strikes = [s for s in strikes if abs(s - last_price) <= 50]  # Within $50 of current price
                    
                    if len(strikes) >= 2:
                        min_strike = max(s for s in strikes if s <= last_price)
                        max_strike = min(s for s in strikes if s >= last_price)
                        
                        # Calculate gamma profile
                        gamma_profile = {}
                        gamma_col = "Gamma" if "Gamma" in options_data.columns else "gamma"
                        if gamma_col in options_data.columns:
                            for strike in strikes:
                                strike_options = options_data[options_data[strike_col] == strike]
                                if not strike_options.empty:
                                    total_gamma = strike_options[gamma_col].sum()
                                    gamma_profile[int(strike)] = float(total_gamma)
                        
                        print(f"Loaded options data: {len(options_data)} contracts")
                        print(f"Strike range: {min_strike}-{max_strike}")
                        print(f"Number of strikes with gamma: {len(gamma_profile)}")
                        
                        return {
                            "stock": stock_data,
                            "options": options_data,
                            "last_price": last_price,
                            "last_volume": last_volume,
                            "min_strike": int(min_strike),
                            "max_strike": int(max_strike),
                            "strikes": sorted([int(s) for s in strikes]),
                            "gamma_profile": gamma_profile
                        }
            
            except Exception as e:
                print(f"Error processing options data: {e}")
            
            # Fallback to simple range if no options data
            print("Using synthetic strike range around last price:", last_price)
            strikes = range(int(last_price - 15), int(last_price + 16))
            return {
                "stock": stock_data,
                "last_price": last_price,
                "last_volume": last_volume,
                "min_strike": int(last_price - 15),
                "max_strike": int(last_price + 15),
                "strikes": list(strikes)
            }
            
        except Exception as e:
            print(f"Error loading historical data: {e}")
            if 'options_data' in locals():
                print("Options data columns:", options_data.columns.tolist())
            if 'stock_data' in locals():
                print("Stock data columns:", stock_data.columns.tolist())
            return {
                "last_price": self.settings["data_settings"]["fallback_price"],
                "last_volume": 0,
                "min_strike": 610,
                "max_strike": 646,
                "strikes": list(range(610, 647))
            }

    def _calculate_implied_vol(self, price: float, volume: int) -> float:
        """Calculate implied volatility from historical data."""
        try:
            if "options" in self.historical_data:
                # Use actual IV from options if available
                options_data = self.historical_data["options"]
                strike_col = "Strike Price" if "Strike Price" in options_data.columns else "Strike"
                iv_col = "Implied Volatility" if "Implied Volatility" in options_data.columns else "IV"
                
                atm_options = options_data[
                    (options_data[strike_col] > price * 0.95) & 
                    (options_data[strike_col] < price * 1.05)
                ]
                if not atm_options.empty and iv_col in atm_options.columns:
                    return float(atm_options[iv_col].mean())
            
            # Fallback to historical volatility calculation
            if "stock" in self.historical_data:
                df = self.historical_data["stock"]
                returns = df["Close/Last"].pct_change().dropna()
                hist_vol = returns.std() * (252 ** 0.5) * 100
                
                # Adjust for current volume
                vol_ratio = volume / df["Volume"].mean() if volume > 0 else 1
                return hist_vol * vol_ratio
                
        except Exception as e:
            print(f"Error calculating IV: {e}")
            
        return self.settings["data_settings"]["fallback_vol"]

    def _generate_strikes(self, spot_price: float) -> List[int]:
        """Generate strike prices based on available options data."""
        # Get min/max strikes from historical data or use default range
        min_strike = self.historical_data.get("min_strike")
        max_strike = self.historical_data.get("max_strike")
        
        if min_strike is None or max_strike is None:
            # Default to ±15 points around spot price
            base = round(spot_price)
            min_strike = base - 15
            max_strike = base + 15
            
        # Ensure we have enough strikes for visualization
        if max_strike - min_strike < 10:
            # Expand range if too narrow
            center = (min_strike + max_strike) / 2
            min_strike = int(center - 10)
            max_strike = int(center + 10)
            
        # Generate strikes with consistent spacing
        strikes = list(range(int(min_strike), int(max_strike) + 1))
        
        print(f"Generated strikes around {spot_price}: {min_strike}-{max_strike}")
        return strikes

    def get_gamma_profile(self) -> Dict[int, float]:
        """Get gamma profile for available strikes."""
        return self.historical_data.get("gamma_profile", {})

    def _get_current_state(self) -> Dict:
        """Get current market state from historical data."""
        price = self.historical_data["last_price"]
        volume = self.historical_data["last_volume"]
        
        return {
            "price": price,
            "strikes": self._generate_strikes(price),
            "implied_vol": self._calculate_implied_vol(price, volume),
            "volume": volume,
            "gamma_profile": self.get_gamma_profile(),
            "timestamp": datetime.now().isoformat()
        }

    def get_market_state(self) -> Dict:
        """Get current market state."""
        return self.current_data

    def get_slingshot_targets(self, slingshot_name: str, spot_price: float) -> List[Dict]:
        """Get valid strike targets for a slingshot."""
        slingshots = {s["name"]: s for s in self.settings["slingshots"]}
        if slingshot_name not in slingshots:
            return []
            
        slingshot = slingshots[slingshot_name]
        strikes = self._generate_strikes(spot_price)
        
        # Apply strike bias based on option type
        bias = slingshot["strike_bias"]
        base_strike = round(spot_price)
        
        targets = []
        for strike in strikes:
            # Calculate strike's attractiveness based on bias and gamma
            if slingshot["option_type"] == "call":
                # For calls, positive bias prefers higher strikes
                attractiveness = 1.0 / (1 + abs(strike - (base_strike + bias)))
            else:
                # For puts, negative bias prefers lower strikes
                attractiveness = 1.0 / (1 + abs(strike - (base_strike + bias)))
                
            # Adjust attractiveness based on gamma if available
            gamma = self.historical_data.get("gamma_profile", {}).get(strike, 0.1)
            attractiveness *= (1 + gamma)
                
            if attractiveness > 0.3:  # Minimum attractiveness threshold
                targets.append({
                    "strike": strike,
                    "attractiveness": attractiveness,
                    "option_type": slingshot["option_type"],
                    "dte": slingshot["dte"]
                })
                
        # Sort by attractiveness
        targets.sort(key=lambda x: x["attractiveness"], reverse=True)
        return targets

    def get_price_history(self, lookback_days: int = None) -> List[Tuple[str, float]]:
        """Get historical price data."""
        if lookback_days is None:
            lookback_days = self.settings["data_settings"]["max_historical_days"]
            
        try:
            if "stock" in self.historical_data:
                df = self.historical_data["stock"].tail(lookback_days)
                return [(date.strftime("%Y-%m-%d"), price) 
                        for date, price in zip(df.index, df["Close/Last"])]
        except Exception as e:
            print(f"Error getting price history: {e}")
            
        # Fallback to synthetic data
        return [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(lookback_days)]

# Create global market data instance
market_data = MarketDataLoader() 