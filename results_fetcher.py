import requests
from bs4 import BeautifulSoup
import json
import os
from glicko2 import Player

class SOTACloser:
    def __init__(self):
        with open('active_matches.json', 'r') as f: self.ledger = json.load(f)
        with open('players.json', 'r') as f: self.db = json.load(f)

    def fetch_results(self):
        print("Closing Live Ledger Matches...")
        # Target results from Setka, TT Elite, etc.
        try:
            r = requests.get("https://setkacup.com/results", timeout=10)
            soup = BeautifulSoup(r.content, 'lxml')
            
            remaining_matches = []
            for match in self.ledger:
                found = False
                # Logic to find the match in the scraped HTML
                # (Pseudocode for finding names and winners)
                # if found_on_page:
                #    self.update_glicko(match, winner)
                #    found = True
                if not found:
                    remaining_matches.append(match)
            
            self.ledger = remaining_matches
            self.save()
        except:
            print("Results feed temporarily offline.")

    def update_glicko(self, match, actual_winner):
        # Professional Glicko-2 update logic here
        pass

    def save(self):
        with open('active_matches.json', 'w') as f: json.dump(self.ledger, f, indent=4)
        with open('players.json', 'w') as f: json.dump(self.db, f, indent=4)

if __name__ == "__main__":
    if os.path.exists('active_matches.json'):
        closer = SOTACloser()
        closer.fetch_results()
