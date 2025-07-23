import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import random

# Constants
spot_price = 628.86
implied_vol = 13.7
dte = 5
strikes = list(range(610, 646))
gamma_strengths = {s: 0.2 + 0.02 * abs(s - 628) for s in strikes}
trials = 1000

# Initialize result storage
hits = {s: 0 for s in strikes}
retail_juice = {s: 0.0 for s in strikes}
mm_juice = {s: 0.0 for s in strikes}

# Flying coconut tracker
flying_coconuts = []

# Simulation function
def simulate_slingshot_hit(spot_price, strike_price, gamma_strength, implied_vol, dte):
    delta_distance = abs(spot_price - strike_price)
    base_hit_chance = 1.0 / (1 + delta_distance)
    wind_penalty = implied_vol / 100
    gamma_penalty = gamma_strength / 10
    decay_penalty = max(0.1, dte / 30)
    final_hit_chance = base_hit_chance * (1 - wind_penalty) * (1 - gamma_penalty) * (1 / decay_penalty)
    final_hit_chance = max(0, min(final_hit_chance, 1))
    hit = random.random() < final_hit_chance
    mm_juice_sip = 0.7 if hit else 0
    retail_juice = (1 - mm_juice_sip) if hit else 0
    return hit, retail_juice, mm_juice_sip

# Simulate chaos
for t in range(trials):
    for s in strikes:
        hit, retail, mm = simulate_slingshot_hit(spot_price, s, gamma_strengths[s], implied_vol, dte)
        if hit:
            hits[s] += 1
            retail_juice[s] += retail
            mm_juice[s] += mm
            # Add flying coconut
            flying_coconuts.append((t, s))

# Create DataFrame for plotting
df = pd.DataFrame({
    'strike': strikes,
    'hits': [hits[s] for s in strikes],
    'retail_juice': [retail_juice[s] for s in strikes],
    'mm_juice': [mm_juice[s] for s in strikes]
})

# Static plot to visualize results
fig, ax = plt.subplots(figsize=(14, 6))
bar1 = ax.bar(df['strike'], df['retail_juice'], label='Retail Juice', color='green')
bar2 = ax.bar(df['strike'], df['mm_juice'], bottom=df['retail_juice'], label='MM Juice', color='orange')
ax.axvline(x=spot_price, color='red', linestyle='--', label='Spot Price')
ax.set_xlabel("Strike Price")
ax.set_ylabel("Total Juice (Simulated)")
ax.set_title("Gamma Defense Coconut Simulation - Chaos Mode")
ax.legend()
plt.tight_layout()
plt.show()

# Show data in a table
import ace_tools as tools; tools.display_dataframe_to_user(name="Jungle Chaos Coconut Stats", dataframe=df)
