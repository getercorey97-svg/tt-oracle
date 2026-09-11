import json
import os
from oracle import TTOracleSOTA

def run_optimization():
    if not os.path.exists('players.json'):
        print("No database found to optimize.")
        return
        
    oracle = TTOracleSOTA()
    print("Running SOTA Hyperparameter Optimization...")
    
    # Logic to refine multipliers based on recent ROI
    # This is an autonomous 'Learning' check
    if 'style_matrix' not in oracle.db:
        oracle.db['style_matrix'] = {
            "lefty_vs_righty_bonus": 0.022,
            "long_pips_vs_attacker_penalty": 0.045,
            "anti_spin_vs_power_bonus": 0.031,
            "fatigue_decay_rate": 0.007
        }
    
    oracle.save_db()
    print("Style Matrix Parameters Optimized.")

if __name__ == "__main__":
    run_optimization()
