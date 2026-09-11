import numpy as np
import json
import requests
import os
from datetime import datetime
from glicko2 import Player

class TTOracleSOTA:
    def __init__(self, db_path='players.json', ledger_path='active_matches.json'):
        self.db_path = db_path
        self.ledger_path = ledger_path
        self.ntfy_url = "https://ntfy.sh/" + os.getenv("NTFY_TOPIC", "tt_engine_alerts")
        self.load_db()
        self.load_ledger()

    def load_db(self):
        with open(self.db_path, 'r') as f:
            self.db = json.load(f)

    def load_ledger(self):
        if os.path.exists(self.ledger_path):
            with open(self.ledger_path, 'r') as f:
                self.ledger = json.load(f)
        else:
            self.ledger = []

    def save_state(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.db, f, indent=4)
        with open(self.ledger_path, 'w') as f:
            json.dump(self.ledger, f, indent=4)

    def get_player(self, name):
        if name not in self.db['players']:
            self.db['players'][name] = {
                "name": name, "rating": 1500, "rd": 350, "vol": 0.06,
                "style": "Attacker", "hand": "Right", "rubber": "Inverted",
                "league": "Default", "matches_today": 0
            }
        p = self.db['players'][name]
        return Player(p['rating'], p['rd'], p['vol']), p

    def vectorized_monte_carlo(self, p_win, iterations=50000):
        p1_sets = np.zeros(iterations)
        p2_sets = np.zeros(iterations)
        while np.max(p1_sets) < 3 and np.max(p2_sets) < 3:
            p1_pts = np.zeros(iterations); p2_pts = np.zeros(iterations)
            active = (p1_sets < 3) & (p2_sets < 3)
            while np.any(active):
                rolls = np.random.random(iterations)
                p1_pts[active & (rolls < p_win)] += 1
                p2_pts[active & (rolls >= p_win)] += 1
                set_ended = active & (((p1_pts >= 11) | (p2_pts >= 11)) & (np.abs(p1_pts - p2_pts) >= 2))
                p1_sets[set_ended & (p1_pts > p2_pts)] += 1
                p2_sets[set_ended & (p2_pts > p1_pts)] += 1
                active[set_ended] = False
        return np.mean(p1_sets >= 3)

    def predict_and_store(self, p1, p2, market_odds=2.0, league="Default"):
        """Predicts and adds match to the Live Ledger."""
        # Check if already in ledger to avoid duplicates
        if any(m['p1'] == p1 and m['p2'] == p2 for m in self.ledger):
            return

        p1_obj, p1_d = self.get_player(p1)
        p2_obj, p2_d = self.get_player(p2)
        
        # SOTA Probability Synthesis
        diff = (p1_obj.rating - p2_obj.rating)
        p_pt = 0.50 + (1 / (1 + 10**(-diff / 400)) - 0.5) * 0.22 
        
        win_prob = self.vectorized_monte_carlo(p_pt)
        winner = p1 if win_prob > 0.5 else p2
        confidence = win_prob if win_prob > 0.5 else 1 - win_prob
        
        # Add to Memory (Ledger)
        self.ledger.append({
            "p1": p1, "p2": p2, "odds": market_odds,
            "predicted_winner": winner, "confidence": confidence,
            "timestamp": str(datetime.now()), "status": "Live"
        })
        
        # Alert ntfy
        market_prob = 1 / market_odds
        edge = confidence - market_prob if winner == p1 else confidence - (1 - market_prob)
        self.send_alert(p1, p2, winner, confidence, edge)
        self.save_state()

    def send_alert(self, p1, p2, winner, conf, edge):
        msg = f"💎 SOTA PREDICTION: {winner}\nConf: {conf:.1%}\nEdge: +{edge:.1%}\nMatch: {p1} vs {p2}"
        requests.post(self.ntfy_url, data=msg.encode('utf-8'))

if __name__ == "__main__":
    oracle = TTOracleSOTA()
    if os.path.exists('queue_predict.json'):
        with open('queue_predict.json', 'r') as f:
            matches = json.load(f)
            for m in matches:
                oracle.predict_and_store(m['p1'], m['p2'], m.get('odds', 2.0), m.get('league', 'Default'))
        os.remove('queue_predict.json')
