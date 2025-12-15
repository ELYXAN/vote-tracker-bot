"""
Google Sheets Manager - Initialisierung und Cache-Verwaltung
"""
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from src.twitch.redemptions import cache


async def init_google_sheets(config):
    """Initialisiert die Verbindung zu Google Sheets"""
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'Vote tracking.json',
            scope
        )
        client = gspread.authorize(creds)
        
        spreadsheet = client.open_by_key(config['spreadsheet_id'])
        worksheet = spreadsheet.sheet1
        
        cache['spreadsheet'] = spreadsheet
        cache['worksheet'] = worksheet
        
        print("✓ Google Sheets erfolgreich initialisiert")
        
        # Initiales Laden der Spieleliste
        await update_games_cache()
        
    except FileNotFoundError:
        print("FEHLER: 'Vote tracking.json' nicht gefunden!")
        print("Bitte erstelle einen Google Service Account und platziere die JSON-Datei im Projektverzeichnis.")
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"FEHLER: Spreadsheet mit ID '{config['spreadsheet_id']}' nicht gefunden!")
        print("Überprüfe die spreadsheet_id in der config.json")
    except Exception as e:
        print(f"Fehler bei der Google Sheets Initialisierung: {str(e)}")
        import traceback
        traceback.print_exc()


async def update_games_cache():
    """Aktualisiert den Cache der Spieleliste aus dem Google Sheet"""
    if not cache.get('worksheet'):
        print("Worksheet nicht verfügbar, Cache-Update übersprungen.")
        return
    
    try:
        all_values = cache['worksheet'].get_all_values()
        
        if len(all_values) > 1:
            cache['games_list'] = [row[1] for row in all_values[1:] if len(row) > 1 and row[1].strip()]
            cache['last_cache_update'] = time.time()
            print(f"Spieleliste aktualisiert: {len(cache['games_list'])} Spiele geladen.")
        else:
            print("Keine Spiele im Sheet gefunden (nur Header vorhanden).")
            cache['games_list'] = []
            
    except Exception as e:
        print(f"Fehler beim Aktualisieren des Spiele-Cache: {str(e)}")
