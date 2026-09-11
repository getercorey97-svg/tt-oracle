import pandas as pd
import numpy as np

def generate_sota_seed():
    print("Generating 1,000 Match SOTA History...")
    players = ["A. Tkachenko", "M. Pylypchuk", "V. Vakulenko", "O. Yeremenko", "Truls Moregard", "Hugo Calderano"]
    data = []
    
    for i in range(1000):
        p1, p2 = np.random.choice(players, 2, replace=False)
        # Assign attributes based on player 'DNA'
        p1_hand = "Left" if "Tkachenko" in p1 or "Moregard" in p1 else "Right"
        p2_hand = "Left" if "Tkachenko" in p2 or "Moregard" in p2 else "Right"
        
        winner = p1 if np.random.random() > 0.5 else p2
        data.append([p1, p2, winner, p1_hand, p2_hand, "Attacker", "Inverted"])

    df = pd.DataFrame(data, columns=['p1_name', 'p2_name', 'winner', 'p1_hand', 'p2_hand', 'p1_style', 'p1_rubber'])
    df.to_csv('history.csv', index=False)
    print("History Seeded.")

if __name__ == "__main__":
    generate_sota_seed()
