import numpy as np
import json
import requests
import os
from glicko2 import Player

class TTOracleSOTA:
    def __init__(self, db_path='players.json'):
        self.db_path = db_path
        self.ntfy_url = "https://ntfy.sh/" + os.getenv("NTFY_TOPIC", "tt_engine_alerts")
        self.load_db()

    def load_db(self):
        with open(self.db_path, 'r') as f:
            self.db = json.load(f)

    def save_db(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.db, f, indent=4)

    def get_player(self, name):
        if name not in self.db['players']:
            self.db['players'][name] = {
                "name": name, "rating": 1500, "rd": 350, "vol": 0.06,
                "style": "Attacker", "hand": "Right", "rubber": "Inverted",
                "league": "Default", "matches_today": 0
            }
        p = self.db['players'][name]
        return Player(p['rating'], p['rd'], p['vol']), p

    def calculate_sota_point_prob(self, p1_name, p2_name):
        """The Master Algorithm: Synthesizes all variables into a single point-prob."""
        p1_obj, p1_d = self.get_player(p1_name)
        p2_obj, p2_d = self.get_player(p2_name)
        
        # 1. League-Weighted Rating Difference
        l_mult = self.db['league_multipliers']
        p1_eff = p1_obj.rating * l_mult.get(p1_d['league'], 0.9)
        p2_eff = p2_obj.rating * l_mult.get(p2_d['league'], 0.9)
        
        # 2. Base Probability (Glicko-2)
        # Using 0.22 as the Table Tennis scaling constant
        base_diff = (p1_eff - p2_eff)
        win_prob_match = 1 / (1 + 10**(-base_diff / 400))
        p = 0.50 + (win_prob_match - 0.5) * 0.22
        
        # 3. Style Interaction Matrix
        sm = self.db['style_matrix']
        if p1_d['hand'] == 'Left' and p2_d['hand'] == 'Right': p += sm['lefty_vs_righty_bonus']
        if p2_d['rubber'] == 'Long Pips' and p1_d['style'] == 'Attacker': p -= sm['long_pips_vs_attacker_penalty']
        if p2_d['rubber'] == 'Anti' and p1_d['style'] == 'Attacker': p -= sm['anti_spin_vs_power_bonus']
        
        # 4. Fatigue Modeling
        # SOTA: Performance drops 0.7% for every match played previously today
        p -= (p1_d.get('matches_today', 0) * sm['fatigue_decay_rate'])
        p += (p2_d.get('matches_today', 0) * sm['fatigue_decay_rate'])

        # 5. Stochastic Uncertainty (Using RD)
        # If RD is high, we introduce a random 'form' variance for this simulation cycle
        p1_form = np.random.normal(0, p1_obj.rd / 2000)
        p2_form = np.random.normal(0, p2_obj.rd / 2000)
        p += (p1_form - p2_form)

        return np.clip(p, 0.30, 0.70)

    def vectorized_monte_carlo(self, p_win, iterations=50000):
        """Simulates 50,000 matches simultaneously in memory."""
        p1_sets = np.zeros(iterations)
        p2_sets = np.zeros(iterations)

        while np.max(p1_sets) < 3 and np.max(p2_sets) < 3:
            p1_pts = np.zeros(iterations)
            p2_pts = np.zeros(iterations)
            active = (p1_sets < 3) & (p2_sets < 3)
            
            # Simulate a Set
            while np.any(active):
                rolls = np.random.random(iterations)
                p1_pts[active & (rolls < p_win)] += 1
                p2_pts[active & (rolls >= p_win)] += 1
                
                set_ended = active & (((p1_pts >= 11) | (p2_pts >= 11)) & (np.abs(p1_pts - p2_pts) >= 2))
                p1_sets[set_ended & (p1_pts > p2_pts)] += 1
                p2_sets[set_ended & (p2_pts > p1_pts)] += 1
                active[set_ended] = False
                
        return np.mean(p1_sets >= 3)

    def predict_queue(self):
        if not os.path.exists('queue_predict.json'):
            return
        
        with open('queue_predict.json', 'r') as f:
            matches = json.load(f)

        for m in matches:
            p1, p2 = m['p1'], m['p2']
            market_odds = m.get('odds', 2.0)
            
            # Run simulation with the integrated SOTA p-prob
            p_win = self.calculate_sota_point_prob(p1, p2)
            sim_result = self.vectorized_monte_carlo(p_win)
            
            winner = p1 if sim_result > 0.5 else p2
            confidence = sim_result if sim_result > 0.5 else 1 - sim_result
            
            # Edge Calculation
            market_prob = 1 / market_odds
            edge = confidence - market_prob if winner == p1 else confidence - (1 - market_prob)
            
            if edge > 0.02: # Alert if edge > 2%
                self.send_alert(p1, p2, winner, confidence, edge)

    def send_alert(self, p1, p2, winner, conf, edge):
        msg = f"💎 SOTA EDGE: {winner}\nConf: {conf:.1%}\nEdge: +{edge:.1%}\nMatch: {p1} vs {p2}"
        requests.post(self.ntfy_url, data=msg.encode('utf-8'))

if __name__ == "__main__":
    oracle = TTOracleSOTA()
    oracle.predict_queue()
