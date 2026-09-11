import numpy as np
import json
import requests
import os
from glicko2 import Player

class TTOracleSOTA:
    def __init__(self, db_path='players.json'):
        self.db_path = db_path
        # The NTFY_TOPIC is pulled from your GitHub Secrets
        self.ntfy_url = "https://ntfy.sh/" + os.getenv("NTFY_TOPIC", "default_tt_topic")
        self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {"players": {}, "settings": {"base_rating": 1500, "base_rd": 350, "base_vol": 0.06}}

    def save_db(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.db, f, indent=4)

    def get_player_data(self, name):
        """Retrieves player or initializes with SOTA defaults."""
        if name not in self.db['players']:
            self.db['players'][name] = {
                "name": name,
                "rating": self.db['settings']['base_rating'],
                "rd": self.db['settings']['base_rd'],
                "vol": self.db['settings']['base_vol'],
                "style": "Attacker", 
                "hand": "Right", 
                "rubber": "Inverted"
            }
        p = self.db['players'][name]
        return Player(p['rating'], p['rd'], p['vol']), p

    def get_style_modifier(self, p1_d, p2_d):
        """Calculates matchup friction based on Table Tennis dynamics."""
        mod = 0.0
        # Left-Handed Advantage (Statistically significant in TT)
        if p1_d['hand'] == 'Left' and p2_d['hand'] == 'Right': mod += 0.018
        if p2_d['hand'] == 'Left' and p1_d['hand'] == 'Right': mod -= 0.018
        
        # Style/Equipment Conflicts (e.g., Attackers struggle vs Long Pips)
        if p2_d['rubber'] in ['Long Pips', 'Anti'] and p1_d['style'] == 'Attacker':
            mod -= 0.035
        if p1_d['rubber'] in ['Long Pips', 'Anti'] and p2_d['style'] == 'Attacker':
            mod += 0.035
            
        return mod

    def run_monte_carlo(self, p1_pt_prob, iterations=50000):
        """Simulates 50,000 matches point-by-point."""
        p1_match_wins = 0
        for _ in range(iterations):
            g1, g2 = 0, 0
            while g1 < 3 and g2 < 3: # Best of 5 sets
                s1, s2 = 0, 0
                while True:
                    if np.random.random() < p1_pt_prob: s1 += 1
                    else: s2 += 1
                    # Set win logic
                    if s1 >= 11 and (s1 - s2) >= 2:
                        g1 += 1
                        break
                    if s2 >= 11 and (s2 - s1) >= 2:
                        g2 += 1
                        break
            if g1 == 3: p1_match_wins += 1
        return p1_match_wins / iterations

    def predict(self, p1_name, p2_name, market_odds=None):
        p1_obj, p1_d = self.get_player_data(p1_name)
        p2_obj, p2_d = self.get_player_data(p2_name)
        
        # 1. Base Elo Probability
        expected_p1 = 1 / (1 + 10**((p2_obj.rating - p1_obj.rating) / 400))
        
        # 2. Convert to Point-Probability + Style Matrix
        # Slope factor 0.18 scales match-win likelihood to point-win likelihood
        p1_pt_prob = 0.50 + (expected_p1 - 0.5) * 0.18 + self.get_style_modifier(p1_d, p2_d)
        
        # 3. 50k Simulations
        win_prob = self.run_monte_carlo(p1_pt_prob)
        
        # 4. Market Edge Analysis
        if market_odds:
            market_prob = 1 / market_odds
            edge = win_prob - market_prob
            if edge > 0.05: # Send alert if model finds > 5% value
                self.send_ntfy(p1_name, p2_name, win_prob, market_prob)
        
        return win_prob

    def send_ntfy(self, p1, p2, prob, m_prob):
        msg = f"🎯 SOTA EDGE: {p1} vs {p2}\nModel Win: {prob:.1%}\nFanDuel Implied: {m_prob:.1%}\nEdge: {(prob-m_prob):.1%}"
        requests.post(self.ntfy_url, data=msg.encode('utf-8'))

    def update_result(self, p1_name, p2_name, winner_name):
        """Autonomous Learning: Updates Glicko-2 ratings."""
        p1_obj, _ = self.get_player_data(p1_name)
        p2_obj, _ = self.get_player_data(p2_name)
        
        outcome = 1 if winner_name == p1_name else 0
        p1_obj.update_player([p2_obj.rating], [p2_obj.rd], [outcome])
        p2_obj.update_player([p1_obj.rating], [p1_obj.rd], [1 - outcome])
        
        # Save back to DB
        self.db['players'][p1_name].update({"rating": p1_obj.rating, "rd": p1_obj.rd, "vol": p1_obj.vol})
        self.db['players'][p2_name].update({"rating": p2_obj.rating, "rd": p2_obj.rd, "vol": p2_obj.vol})
        self.save_db()

if __name__ == "__main__":
    oracle = TTOracleSOTA()
    
    # Check for Outcomes Queue (Learning Phase)
    if os.path.exists('queue_results.json'):
        with open('queue_results.json', 'r') as f:
            data = json.load(f)
            for r in data:
                oracle.update_result(r['p1'], r['p2'], r['winner'])
        os.remove('queue_results.json')

    # Check for FanDuel Queue (Prediction Phase)
    if os.path.exists('queue_predict.json'):
        with open('queue_predict.json', 'r') as f:
            data = json.load(f)
            for m in data:
                oracle.predict(m['p1'], m['p2'], m.get('odds'))
        os.remove('queue_predict.json')
