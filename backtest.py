import pandas as pd
import numpy as np
import json
import os
from oracle import TTOracleSOTA # Matches the class name in oracle.py

class SOTABacktester:
    def __init__(self, history_path='history.csv'):
        self.history_path = history_path
        self.oracle = TTOracleSOTA()
        if not os.path.exists(self.history_path):
            # Create a dummy history if it doesn't exist to prevent crash
            pd.DataFrame(columns=['p1_name', 'p2_name', 'winner']).to_csv(self.history_path, index=False)
        self.history = pd.read_csv(self.history_path)

    def calculate_brier_score(self, predictions, actuals):
        if not predictions: return 1.0
        return np.mean((np.array(predictions) - np.array(actuals))**2)

    def optimize_math(self):
        print("SOTA Optimization: Searching for best Calibration...")
        
        # Grid search for best weights
        best_score = float('inf')
        best_l = 0.018
        best_p = 0.035
        
        # Test a few variations against history
        if len(self.history) > 10:
            test_data = self.history.tail(50)
            for l_w in [0.015, 0.02, 0.025]:
                for p_w in [0.03, 0.04, 0.05]:
                    self.oracle.db['style_matrix']['lefty_vs_righty_bonus'] = l_w
                    self.oracle.db['style_matrix']['long_pips_vs_attacker_penalty'] = p_w
                    
                    preds = []
                    actuals = []
                    for _, row in test_data.iterrows():
                        # Quick point-prob calculation (no sim needed for backtest)
                        p = self.oracle.calculate_sota_point_prob(row['p1_name'], row['p2_name'])
                        preds.append(p)
                        actuals.append(1 if row['winner'] == row['p1_name'] else 0)
                    
                    score = self.calculate_brier_score(preds, actuals)
                    if score < best_score:
                        best_score = score
                        best_l, best_p = l_w, p_w

        # Save the best weights found
        self.oracle.db['style_matrix']['lefty_vs_righty_bonus'] = best_l
        self.oracle.db['style_matrix']['long_pips_vs_attacker_penalty'] = best_p
        self.oracle.save_db()
        print(f"Calibration Complete. Weights set to Lefty: {best_l}, Pips: {best_p}")

if __name__ == "__main__":
    tester = SOTABacktester()
    tester.optimize_math()
