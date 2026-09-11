import requests
from bs4 import BeautifulSoup
import json
import os

def fetch_automated_results():
    print("Searching for new match results...")
    results_queue = []
    
    # Target: Setka Cup Results (Most common on FanDuel)
    try:
        url = "https://setkacup.com/results"
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        
        # SOTA Scraping Logic: Finding match rows
        matches = soup.find_all('div', class_='match-item')
        for match in matches:
            try:
                p1 = match.find('div', class_='player-1').text.strip()
                p2 = match.find('div', class_='player-2').text.strip()
                score = match.find('div', class_='score').text.strip()
                
                # Determine winner from score (e.g., "3:1")
                s1, s2 = map(int, score.split(':'))
                winner = p1 if s1 > s2 else p2
                
                results_queue.append({"p1": p1, "p2": p2, "winner": winner})
            except:
                continue
    except Exception as e:
        print(f"Setka Scrape failed: {e}")

    # Save to the results queue for the oracle to process
    if results_queue:
        print(f"Found {len(results_queue)} new results.")
        with open('queue_results.json', 'w') as f:
            json.dump(results_queue, f, indent=4)
    else:
        print("No new results found.")

if __name__ == "__main__":
    fetch_automated_results()
