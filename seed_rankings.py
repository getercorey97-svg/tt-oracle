import json
import os

def seed_real_data():
    # SOTA Mapping: Known Tier Rankings (Elo Equivalents)
    # 2500+ = World Class, 2000 = Elite Regional, 1500 = Standard
    historic_data = {
        "Bartosz Sulkowski": {"rating": 1950, "rd": 80, "style": "Attacker", "hand": "Right", "rubber": "Inverted"},
        "Stapor Rafal": {"rating": 1720, "rd": 95, "style": "Counter-Hitter", "hand": "Right", "rubber": "Inverted"},
        "Jakub Pruszkowski": {"rating": 2100, "rd": 70, "style": "Attacker", "hand": "Right", "rubber": "Inverted"},
        "Rafal Skotniczny": {"rating": 1850, "rd": 85, "style": "Defender", "hand": "Left", "rubber": "Long Pips"},
        "Zbigniew Sobkow": {"rating": 1600, "rd": 110, "style": "Attacker", "hand": "Right", "rubber": "Inverted"},
        "Mariusz Baron": {"rating": 1780, "rd": 90, "style": "Attacker", "hand": "Right", "rubber": "Inverted"},
        "Maciej Kolek": {"rating": 2250, "rd": 60, "style": "Attacker", "hand": "Left", "rubber": "Inverted"},
        "Maciej Nowalinski": {"rating": 1650, "rd": 120, "style": "Defender", "hand": "Right", "rubber": "Anti"},
        "Pawel Kurek": {"rating": 1900, "rd": 85, "style": "Attacker", "hand": "Right", "rubber": "Inverted"},
        "Grzegorz Wichowski": {"rating": 1550, "rd": 130, "style": "Counter-Hitter", "hand": "Right", "rubber": "Inverted"}
    }

    if os.path.exists('players.json'):
        with open('players.json', 'r') as f:
            db = json.load(f)
    else:
        db = {"players": {}, "settings": {"base_rating": 1500, "base_rd": 350, "base_vol": 0.06}}

    # Merge historic data into your active database
    for name, stats in historic_data.items():
        db['players'][name] = {
            "name": name,
            "rating": stats['rating'],
            "rd": stats['rd'],
            "vol": 0.06,
            "style": stats['style'],
            "hand": stats['hand'],
            "rubber": stats['rubber']
        }

    with open('players.json', 'w') as f:
        json.dump(db, f, indent=4)
    print("Database seeded with historical player profiles.")

if __name__ == "__main__":
    seed_real_data()
