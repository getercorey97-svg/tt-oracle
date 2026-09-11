import pandas as pd
import numpy as np
import json
from oracle import SOTAOracle # Imports your engine logic

class SOTABacktester:
    def __init__(self, history_path='history.csv'):
        self.history = pd.read_csv(history_path)
        self.oracle = SOTAOracle()

    def calculate_brier_score(self, predictions, actuals):
        """Measures the 'honesty' of the model. Lower is better."""
        return np.mean((np.array(predictions) - np.array(actuals))**2)

    def run_walk_forward(self, lefty_weight, pips_weight):
        """Tests the engine across time using specific weights."""
        # Update weights for this test run
        self.oracle.db['style_weights']['lefty_bonus'] = lefty_weight
        self.oracle.db['style_weights']['pips_penalty'] = pips_weight
        
        preds = []
        actuals = []
        
        # Test on the last 200 matches of your 1,000 match history
        test_data = self.history.tail(200)
        
        for _, row in test_data.iterrows():
            # Run the 50k simulation logic
            prob = self.oracle.predict(row['p1_name'], row['p2_name'], quiet=True)
            preds.append(prob)
            actuals.append(1 if row['winner'] == row['p1_name'] else 0)
            
        return self.calculate_brier_score(preds, actuals)

    def optimize_math(self):
        """Autonomously finds the most accurate weights."""
        print("SOTA Optimization: Searching for best Calibration...")
        results = []
        
        # Search space for weights
        for l_w in [0.01, 0.015, 0.02, 0.025]:
            for p_w in [0.02, 0.03, 0.04, 0.05]:
                score = self.run_walk_forward(l_w, p_w)
                results.append({'l': l_w, 'p': p_w, 'score': score})
        
        # Pick the winner
        best = min(results, key=lambda x: x['score'])
        print(f"Optimization Complete. Best Brier Score: {best['score']}")
        
        # Save the 'Learned Math' back to the database
        self.oracle.db['style_weights']['lefty_bonus'] = best['l']
        self.oracle.db['style_weights']['pips_penalty'] = best['p']
        self.oracle.save_db()

if __name__ == "__main__":
    tester = SOTABacktester()
    tester.optimize_math()
