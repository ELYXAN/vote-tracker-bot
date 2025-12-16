"""
Sicherheitsprüfungen für Datenbank-Spreadsheet Synchronisation
Verhindert Datenverlust durch falsche Syncs
"""
import hashlib
import asyncio
import pandas as pd
import gspread
from .operations import get_all_games_sorted, get_stored_spreadsheet_info, mark_synced, get_pending_changes
from src.twitch.redemptions import cache
from src.utils.colors import error, warning, info, success, highlight


def calculate_data_hash(games_data):
    """Berechnet einen Hash der Spieldaten für Vergleichszwecke"""
    if not games_data:
        return ""
    
    # Sortiere nach Name für konsistenten Hash
    sorted_data = sorted(games_data, key=lambda x: (x['name'], x['votes']))
    data_string = "|".join([f"{g['name']}:{g['votes']}" for g in sorted_data])
    return hashlib.md5(data_string.encode()).hexdigest()


async def get_spreadsheet_data():
    """Lädt alle Daten aus dem Spreadsheet"""
    if not cache.get('worksheet'):
        return None
    
    try:
        all_records = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cache['worksheet'].get_all_records(numericise_ignore=['all'])
        )
        
        if not all_records:
            return []
        
        df = pd.DataFrame(all_records)
        
        if 'Votes' not in df.columns or 'Game' not in df.columns:
            return None
        
        # Konvertiere zu dict-Format
        games = []
        for _, row in df.iterrows():
            game_name = str(row['Game']).strip()
            try:
                votes = int(row['Votes'])
            except (ValueError, TypeError):
                votes = 0
            
            if game_name:
                games.append({'name': game_name, 'votes': votes})
        
        return games
    except Exception as e:
        print(error(f"✗ Fehler beim Laden der Spreadsheet-Daten: {e}"))
        return None


async def compare_data_sources(db_games, sheet_games):
    """
    Vergleicht Datenbank und Spreadsheet Daten
    
    Returns:
        dict mit Vergleichsergebnissen
    """
    if sheet_games is None:
        return {'error': 'Could not load spreadsheet data'}
    
    db_dict = {g['name']: g['votes'] for g in db_games}
    sheet_dict = {g['name']: g['votes'] for g in sheet_games}
    
    db_games_set = set(db_dict.keys())
    sheet_games_set = set(sheet_dict.keys())
    
    # Finde Unterschiede
    only_in_db = db_games_set - sheet_games_set
    only_in_sheet = sheet_games_set - db_games_set
    in_both = db_games_set & sheet_games_set
    
    # Finde unterschiedliche Vote-Zahlen
    vote_differences = {}
    for game in in_both:
        if db_dict[game] != sheet_dict[game]:
            vote_differences[game] = {
                'db': db_dict[game],
                'sheet': sheet_dict[game]
            }
    
    # Berechne Gesamt-Votes
    db_total = sum(db_dict.values())
    sheet_total = sum(sheet_dict.values())
    
    return {
        'db_games_count': len(db_games),
        'sheet_games_count': len(sheet_games),
        'db_total_votes': db_total,
        'sheet_total_votes': sheet_total,
        'only_in_db': list(only_in_db),
        'only_in_sheet': list(only_in_sheet),
        'vote_differences': vote_differences,
        'db_hash': calculate_data_hash(db_games),
        'sheet_hash': calculate_data_hash(sheet_games)
    }


async def check_sync_safety(config):
    """
    Prüft ob ein Sync sicher durchgeführt werden kann
    
    Returns:
        dict mit {
            'safe': bool,
            'warning': str oder None,
            'action': 'sync' | 'migrate' | 'abort'
        }
    """
    current_spreadsheet_id = config.get('spreadsheet_id')
    stored_info = await get_stored_spreadsheet_info()
    stored_id = stored_info.get('spreadsheet_id')
    stored_hash = stored_info.get('spreadsheet_hash')
    
    # Lade Daten aus beiden Quellen
    db_games = await get_all_games_sorted()
    sheet_games = await get_spreadsheet_data()
    
    if sheet_games is None:
        return {
            'safe': False,
            'warning': 'Could not load spreadsheet data',
            'action': 'abort'
        }
    
    # Prüfe Spreadsheet-ID Mismatch
    if stored_id and stored_id != current_spreadsheet_id:
        comparison = await compare_data_sources(db_games, sheet_games)
        
        return {
            'safe': False,
            'warning': f"⚠️  KRITISCH: Spreadsheet-ID stimmt nicht überein!\n"
                      f"   Gespeicherte ID: {stored_id}\n"
                      f"   Aktuelle ID: {current_spreadsheet_id}\n"
                      f"   Dies deutet darauf hin, dass die Datenbank von einem anderen System kopiert wurde.\n"
                      f"   DB hat {comparison['db_games_count']} Spiele ({comparison['db_total_votes']} Votes)\n"
                      f"   Spreadsheet hat {comparison['sheet_games_count']} Spiele ({comparison['sheet_total_votes']} Votes)",
            'action': 'abort',
            'comparison': comparison
        }
    
    # Prüfe Hash-Mismatch (wenn Datenbank bereits Daten hat)
    if db_games and stored_hash:
        db_hash = calculate_data_hash(db_games)
        sheet_hash = calculate_data_hash(sheet_games)
        
        if db_hash != stored_hash and sheet_hash != stored_hash:
            # Beide haben sich geändert - möglicherweise Konflikt
            comparison = await compare_data_sources(db_games, sheet_games)
            
            if comparison['sheet_total_votes'] > comparison['db_total_votes'] * 1.1:
                # Spreadsheet hat deutlich mehr Daten - möglicherweise neuer
                return {
                    'safe': False,
                    'warning': f"⚠️  WARNUNG: Spreadsheet scheint neuere Daten zu haben!\n"
                              f"   DB: {comparison['db_games_count']} Spiele, {comparison['db_total_votes']} Votes\n"
                              f"   Spreadsheet: {comparison['sheet_games_count']} Spiele, {comparison['sheet_total_votes']} Votes\n"
                              f"   Sync würde Spreadsheet-Daten überschreiben!",
                    'action': 'migrate',
                    'comparison': comparison
                }
    
    # Keine Probleme - Sync ist sicher
    return {
        'safe': True,
        'warning': None,
        'action': 'sync'
    }


async def safe_sync_to_sheets(config, force=False):
    """
    Sicherer Sync mit vorheriger Prüfung
    
    Args:
        config: Bot-Konfiguration
        force: Wenn True, überspringt Sicherheitsprüfungen (nur für Notfälle)
    
    Returns:
        bool: Erfolg
    """
    if not cache.get('worksheet'):
        print(warning("⚠️  Worksheet nicht verfügbar, Sync übersprungen"))
        return False
    
    if not force:
        # Führe Sicherheitsprüfung durch
        safety_check = await check_sync_safety(config)
        
        if not safety_check['safe']:
            print("\n" + "="*70)
            print(error("✗ SICHERHEITSPRÜFUNG FEHLGESCHLAGEN"))
            print("="*70)
            print(warning(safety_check['warning']))
            print()
            print(info("Mögliche Lösungen:"))
            print("  1. Wenn die Datenbank von einem anderen System kopiert wurde:")
            print("     → Lösche die Datenbank-Datei (votes.db) und starte den Bot neu")
            print("     → Der Bot wird dann die Daten aus dem Spreadsheet laden")
            print()
            print("  2. Wenn das Spreadsheet die neueren Daten hat:")
            print("     → Lösche die Datenbank-Datei (votes.db) und starte den Bot neu")
            print()
            print("  3. Wenn die Datenbank die neueren Daten hat:")
            print("     → Starte den Bot mit --force-sync (nur wenn du sicher bist!)")
            print()
            print("="*70 + "\n")
            return False
    
    # Sicherer Sync durchführen (direkt, ohne circular import)
    from .operations import get_pending_changes
    import gspread
    
    try:
        # Prüfe ob es Änderungen gibt
        pending = await get_pending_changes()
        if pending == 0:
            return True
        
        # Hole sortierte Daten aus Datenbank
        db_games = await get_all_games_sorted()
        
        if not db_games:
            return True
        
        # Erstelle DataFrame für Sheets
        df = pd.DataFrame(db_games)
        df = df[['votes', 'name']]
        df.columns = ['Votes', 'Game']
        
        # Update vorbereiten
        update_data = [df.columns.values.tolist()] + df.values.tolist()
        range_to_update = f'A1:{gspread.utils.rowcol_to_a1(len(update_data), 2)}'
        
        # Sync zu Sheets
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cache['worksheet'].update(range_name=range_to_update, values=update_data)
        )
        
        # Aktualisiere Spreadsheet-ID und Hash
        spreadsheet_hash = calculate_data_hash(db_games)
        await mark_synced(
            spreadsheet_id=config.get('spreadsheet_id'),
            spreadsheet_hash=spreadsheet_hash
        )
        
        return True
        
    except gspread.exceptions.APIError as e:
        print(error(f"✗ Google Sheets API Fehler beim Sync: {e}"))
        return False
    except Exception as e:
        print(error(f"✗ Fehler beim Sync: {str(e)}"))
        import traceback
        traceback.print_exc()
        return False

