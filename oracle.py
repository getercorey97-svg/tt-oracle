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
        if name not in self.db['players']:
            self.db['players'][name] = {
                "name": name, "rating": self.db['settings']['base_rating'],
                "rd": self.db['settings']['base_rd'], "vol": self.db['settings']['base_vol'],
                "style": "Attacker", "hand": "Right", "rubber": "Inverted"
            }
        p = self.db['players'][name]
        return Player(p['rating'], p['rd'], p['vol']), p

    def get_style_bias(self, p1_d, p2_d):
        weights = self.db.get('style_weights', {"lefty_bonus": 0.018, "pips_penalty": 0.035})
        bias = 0.0
        if p1_d['hand'] == 'Left' and p2_d['hand'] == 'Right': bias += weights['lefty_bonus']
        if p2_d['rubber'] in ['Long Pips', 'Anti'] and p1_d['style'] == 'Attacker': bias -= weights['pips_penalty']
        return bias

    def run_simulation(self, p1_pt_prob, iterations=50000):
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
        
        expected_p1 = 1 / (1 + 10**((p2_obj.rating - p1_obj.rating) / 400))
        p1_pt_prob = 0.50 + (expected_p1 - 0.5) * 0.18 + self.get_style_bias(p1_d, p2_d)
        
        prob_p1 = self.run_simulation(p1_pt_prob)
        prob_p2 = 1 - prob_p1
        
        winner = p1_name if prob_p1 > prob_p2 else p2_name
        conf = max(prob_p1, prob_p2)

        if market_odds:
            m_prob = 1 / market_odds
            edge = conf - m_prob
            if edge > 0.05:
                self.send_alert(p1_name, p2_name, winner, conf, edge)
        return winner, conf

    def send_alert(self, p1, p2, winner, conf, edge):
        msg = f"🎯 WINNER: {winner}\nConfidence: {conf:.1%}\nEdge: {edge:.1%}\nMatch: {p1} vs {p2}"
        requests.post(self.ntfy_url, data=msg.encode('utf-8'))

    def update_learning(self, p1_name, p2_name, winner_name):
        p1_obj, _ = self.get_player(p1_name)
        p2_obj, _ = self.get_player(p2_name)
        res = 1 if winner_name == p1_name else 0
        p1_obj.update_player([p2_obj.rating], [p2_obj.rd], [res])
        p2_obj.update_player([p1_obj.rating], [p1_obj.rd], [1-res])
        self.db['players'][p1_name].update({"rating": p1_obj.rating, "rd": p1_obj.rd, "vol": p1_obj.vol})
        self.db['players'][p2_name].update({"rating": p2_obj.rating, "rd": p2_obj.rd, "vol": p2_obj.vol})
        self.save_db()

if __name__ == "__main__":
    oracle = TTOracleSOTA()
    
    # Process Automated Learning
    if os.path.exists('queue_results.json'):
        with open('queue_results.json', 'r') as f:
            for r in json.load(f):
                oracle.update_learning(r['p1'], r['p2'], r['winner'])

    # Process FanDuel Predictions
    if os.path.exists('queue_predict.json'):
        with open('queue_predict.json', 'r') as f:
            for m in json.load(f):
                oracle.predict(m['p1'], m['p2'], m.get('odds'))
