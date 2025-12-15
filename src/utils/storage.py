"""
Datei-basierte Speicherung für Vote-IDs und ungenaue Spiele
"""


def load_processed_ids():
    """Lädt die Liste der bereits verarbeiteten Vote-IDs"""
    try:
        with open('Vote_IDs.csv', 'r') as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()


def save_processed_id(id_set, vote_id):
    """Speichert eine neue Vote-ID in der Liste"""
    id_set.add(vote_id)
    with open('Vote_IDs.csv', 'a') as f:
        f.write(str(vote_id) + '\n')
    return id_set


def save_inaccurate_game(game_name):
    """Speichert ein ungenau eingegebenes Spiel"""
    with open('inacurate_games.csv', 'a') as f:
        f.write(f"{game_name} Vote Anzahl: 1\n")
    print(f"Eintrag in CSV Datei: {game_name}")
