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
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {"players": {}, "settings": {"base_rating": 1500, "base_rd": 350, "base_vol": 0.06}}

    def save_db(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.db, f, indent=4)

    def get_player(self, name):
        """Retrieves player or initializes new profile with SOTA defaults."""
        if name not in self.db['players']:
            self.db['players'][name] = {
                "name": name,
                "rating": self.db['settings']['base_rating'],
                "rd": self.db['settings']['base_rd'],
                "vol": self.db['settings']['base_vol'],
                "style": "Attacker", "hand": "Right", "rubber": "Inverted"
            }
        p = self.db['players'][name]
        return Player(p['rating'], p['rd'], p['vol']), p

    def get_matchup_bias(self, p1_d, p2_d):
        """State-of-the-Art Style Interaction Matrix."""
        bias = 0.0
        # Handedness dynamics
        if p1_d['hand'] == 'Left' and p2_d['hand'] == 'Right': bias += 0.016
        # Equipment dynamics (Attackers vs defensive rubbers)
        if p2_d['rubber'] in ['Long Pips', 'Anti'] and p1_d['style'] == 'Attacker':
            bias -= 0.034
        return bias

    def run_simulation(self, p1_pt_prob, iterations=50000):
        """High-intensity 50k Monte Carlo iterations."""
        p1_wins = 0
        # Use fast vectorized numpy for 50k iterations if possible, 
        # but standard loop is safer for GitHub Action stability.
        for _ in range(iterations):
            g1, g2 = 0, 0
            while g1 < 3 and g2 < 3:
                s1, s2 = 0, 0
                while True:
                    if np.random.random() < p1_pt_prob: s1 += 1
                    else: s2 += 1
                    if s1 >= 11 and s1 - s2 >= 2:
                        g1 += 1; break
                    if s2 >= 11 and s2 - s1 >= 2:
                        g2 += 1; break
            if g1 == 3: p1_wins += 1
        return p1_wins / iterations

    def predict(self, p1_name, p2_name, market_odds=None):
        p1_obj, p1_d = self.get_player(p1_name)
        p2_obj, p2_d = self.get_player(p2_name)
        
        # Glicko-2 Strength Calculation
        expected_p1 = 1 / (1 + 10**((p2_obj.rating - p1_obj.rating) / 400))
        
        # Point-Win Probability Synthesis
        p1_pt_prob = 0.50 + (expected_p1 - 0.5) * 0.18 + self.get_matchup_bias(p1_d, p2_d)
        
        # Simulation
        win_prob = self.run_simulation(p1_pt_prob)
        
        print(f"RESULT: {p1_name} ({win_prob:.1%}) vs {p2_name}")
        
        if market_odds:
            m_prob = 1 / market_odds
            if win_prob > m_prob + 0.05: # 5% Edge Threshold
                self.send_alert(p1_name, p2_name, win_prob, m_prob)
        return win_prob

    def send_alert(self, p1, p2, prob, m_prob):
        msg = f"🏓 SOTA EDGE: {p1} vs {p2}\nModel: {prob:.1%}\nMarket: {m_prob:.1%}\nEdge: {prob-m_prob:.1%}"
        requests.post(self.ntfy_url, data=msg.encode('utf-8'))

    def update_learning(self, p1_name, p2_name, winner_name):
        """Autonomous Glicko-2 rating adjustment."""
        p1_obj, _ = self.get_player(p1_name)
        p2_obj, _ = self.get_player(p2_name)
        res = 1 if winner_name == p1_name else 0
        p1_obj.update_player([p2_obj.rating], [p2_obj.rd], [res])
        p2_obj.update_player([p1_obj.rating], [p1_obj.rd], [1-res])
        self.db['players'][p1_name].update({"rating": p1_obj.rating, "rd": p1_obj.rd, "vol": p1_obj.vol})
        self.db['players'][p2_name].update({"rating": p2_obj.rating, "rd": p2_obj.rd, "vol": p2_obj.vol})
        self.save_db()

    def fetch_free_results(self):
        """Retrieves match results from free public repositories/feeds."""
        # This is a placeholder for a public JSON results feed.
        # You can point this to any community-maintained result set.
        try:
            r = requests.get("https://raw.githubusercontent.com/stats-provider/tt-results/main/latest.json")
            if r.status_code == 200:
                for match in r.json():
                    self.update_learning(match['p1'], match['p2'], match['winner'])
        except:
            print("Autonomous feed offline; proceeding to manual queues.")

if __name__ == "__main__":
    oracle = TTOracleSOTA()
    oracle.fetch_free_results()
    
    # Process Results Queue (Learning)
    if os.path.exists('queue_results.json'):
        with open('queue_results.json', 'r') as f:
            for r in json.load(f):
                oracle.update_learning(r['p1'], r['p2'], r['winner'])
        os.remove('queue_results.json')

    # Process FanDuel/Prediction Queue
    if os.path.exists('queue_predict.json'):
        with open('queue_predict.json', 'r') as f:
            for m in json.load(f):
                oracle.predict(m['p1'], m['p2'], m.get('odds'))
        os.remove('queue_predict.json')
