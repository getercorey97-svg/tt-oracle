import numpy as np
import json
import requests
import os
from glicko2 import Player

class TTOracleSOTA:
    def __init__(self, db_path='players.json'):
        self.db_path = db_path
        # Pulls the ntfy topic from your GitHub Secrets
        self.ntfy_url = "https://ntfy.sh/" + os.getenv("NTFY_TOPIC", "tt_engine_alerts")
        self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {"players": {}, "settings": {"base_rating": 1500, "base_rd": 350, "base_vol": 0.06}, "style_weights": {"lefty_bonus": 0.018, "pips_penalty": 0.035}}

    def save_db(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.db, f, indent=4)

    def get_player(self, name):
        if name not in self.db['players']:
            self.db['players'][name] = {
                "name": name, "rating": self.db['settings']['base_rating'],
                "rd": self.db['settings']['base_rd'], "vol": self.db['settings']['base_vol'],
                "style": "Attacker", "hand": "Right", "rubber": "Inverted"
            }
        p = self.db['players'][name]
        return Player(p['rating'], p['rd'], p['vol']), p

    def get_matchup_modifier(self, p1_d, p2_d):
        m = 0.0
        w = self.db.get('style_weights', {"lefty_bonus": 0.018, "pips_penalty": 0.035})
        if p1_d['hand'] == 'Left' and p2_d['hand'] == 'Right': m += w['lefty_bonus']
        if p2_d['rubber'] in ['Long Pips', 'Anti'] and p1_d['style'] == 'Attacker': m -= w['pips_penalty']
        return m

    def simulate(self, p1_pt_prob, iterations=50000):
        p1_wins = 0
        for _ in range(iterations):
            g1, g2 = 0, 0
            while g1 < 3 and g2 < 3:
                s1, s2 = 0, 0
                while True:
                    if np.random.random() < p1_pt_prob: s1 += 1
                    else: s2 += 1
                    if s1 >= 11 and s1 - s2 >= 2: g1 += 1; break
                    if s2 >= 11 and s2 - s1 >= 2: g2 += 1; break
            if g1 == 3: p1_wins += 1
        return p1_wins / iterations

    def predict(self, p1_name, p2_name, market_odds=None):
        p1_obj, p1_d = self.get_player(p1_name)
        p2_obj, p2_d = self.get_player(p2_name)
        
        # Skill calculation
        expected_p1 = 1 / (1 + 10**((p2_obj.rating - p1_obj.rating) / 400))
        p1_pt_prob = 0.50 + (expected_p1 - 0.5) * 0.18 + self.get_matchup_modifier(p1_d, p2_d)
        
        # 50,000 Iterations
        p1_win_prob = self.simulate(p1_pt_prob)
        p2_win_prob = 1 - p1_win_prob
        
        # Determine Predicted Winner
        if p1_win_prob >= p2_win_prob:
            winner = p1_name
            conf = p1_win_prob
        else:
            winner = p2_name
            conf = p2_win_prob

        print(f"Prediction: {winner} to win ({conf:.1%})")

        # Market Edge Logic
        if market_odds:
            market_prob = 1 / market_odds
            edge = p1_win_prob - market_prob if winner == p1_name else p2_win_prob - (1 - market_prob)
            if edge > 0.05: # Threshold for alert
                self.send_alert(p1_name, p2_name, winner, conf, edge)
        
        return winner, conf

    def send_alert(self, p1, p2, winner, conf, edge):
        msg = (f"🎯 PREDICTED WINNER: {winner}\n"
               f"Confidence: {conf:.1%}\n"
               f"Match: {p1} vs {p2}\n"
               f"FanDuel Edge: +{edge:.1%}")
        
        requests.post(self.ntfy_url, data=msg.encode('utf-8'), headers={"Title": "SOTA Prediction"})

if __name__ == "__main__":
    oracle = TTOracleSOTA()
    if os.path.exists('queue_predict.json'):
        with open('queue_predict.json', 'r') as f:
            for m in json.load(f):
                oracle.predict(m['p1'], m['p2'], m.get('odds'))
