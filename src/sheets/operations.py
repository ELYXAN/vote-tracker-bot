"""
Google Sheets Operationen - Sortierung und Updates
"""
import time
import pandas as pd
import gspread
from src.twitch.redemptions import cache


async def sort_spreadsheet_and_notify(config):
    """Sortiert das Spreadsheet nach Votes"""
    if not cache.get('worksheet'):
        print("Spreadsheet nicht verfügbar, Sortierung übersprungen.")
        return

    try:
        print("Sortiere Spreadsheet (im Hintergrund)...")
        all_records = cache['worksheet'].get_all_records(numericise_ignore=['all'])

        if not all_records:
            print("Keine Daten im Spreadsheet gefunden.")
            return

        df = pd.DataFrame(all_records)

        vote_column = 'Votes'
        game_column = 'Game'
        
        if vote_column not in df.columns:
            print(f"FEHLER: Spalte '{vote_column}' nicht im Spreadsheet gefunden!")
            return
        if game_column not in df.columns:
            print(f"FEHLER: Spalte '{game_column}' nicht im Spreadsheet gefunden!")
            return

        # Daten bereinigen
        df[vote_column] = pd.to_numeric(df[vote_column], errors='coerce').fillna(0).astype(int)
        df[game_column] = df[game_column].astype(str).str.strip()
        df = df[df[game_column] != '']

        # Sortieren
        sorted_df = df.sort_values(by=[vote_column, game_column], ascending=[False, True])

        # Update vorbereiten
        update_data = [sorted_df.columns.values.tolist()] + sorted_df.astype(str).values.tolist()

        range_to_update = f'A1:{gspread.utils.rowcol_to_a1(len(update_data), len(update_data[0]))}'
        cache['worksheet'].update(range_name=range_to_update, values=update_data)

        print(f"Spreadsheet erfolgreich sortiert und aktualisiert (Bereich: {range_to_update}).")

        # Cache aktualisieren
        cache['games_list'] = sorted_df[game_column].tolist()
        cache['last_cache_update'] = time.time()
        print(f"Lokaler Spiele-Cache mit {len(cache['games_list'])} Spielen aktualisiert.")

    except gspread.exceptions.APIError as e:
        print(f"Google Sheets API Fehler beim Sortieren/Aktualisieren: {e}")
    except Exception as e:
        print(f"Unerwarteter Fehler beim Sortieren des Spreadsheets: {str(e)}")
        import traceback
        traceback.print_exc()
