"""
Async Worker für Google Sheets Synchronisation
Läuft parallel und synct die Datenbank mit Google Sheets ohne die Performance zu beeinträchtigen
"""
import asyncio
import gspread
import pandas as pd
from .operations import get_all_games_sorted, mark_synced, get_pending_changes
from src.twitch.redemptions import cache
from src.utils.colors import success, error, warning, info


async def sync_to_sheets(config):
    """
    Synchronisiert die Datenbank mit Google Sheets
    Schnell und effizient - nur wenn es Änderungen gibt
    """
    if not cache.get('worksheet'):
        print(warning("⚠️  Worksheet nicht verfügbar, Sync übersprungen"))
        return False
    
    try:
        # Prüfe ob es Änderungen gibt
        pending = await get_pending_changes()
        if pending == 0:
            # Keine Änderungen - Skip (keine Ausgabe für stille Syncs)
            return True
        
        # Stille Syncs - keine Ausgabe um Prompt nicht zu stören
        # Nur bei Fehlern wird ausgegeben
        
        # Hole sortierte Daten aus Datenbank (sehr schnell!)
        games = await get_all_games_sorted()
        
        if not games:
            # Nur bei Fehler ausgeben
            return True
        
        # Erstelle DataFrame für Sheets
        df = pd.DataFrame(games)
        df = df[['votes', 'name']]  # Nur Votes und Name, ohne Rank
        df.columns = ['Votes', 'Game']
        
        # Update vorbereiten (Header + Daten)
        update_data = [df.columns.values.tolist()] + df.values.tolist()
        
        # Range berechnen
        range_to_update = f'A1:{gspread.utils.rowcol_to_a1(len(update_data), 2)}'
        
        # Sync zu Sheets (async-freundlich mit run_in_executor)
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cache['worksheet'].update(range_name=range_to_update, values=update_data)
        )
        
        # Markiere als synchronisiert
        await mark_synced()
        
        # Erfolgsmeldung entfernt - Sync läuft still im Hintergrund
        return True
        
    except gspread.exceptions.APIError as e:
        print(error(f"✗ Google Sheets API Fehler beim Sync: {e}"))
        # Bei API-Fehler nicht als synced markieren - wird beim nächsten Mal erneut versucht
        return False
    except Exception as e:
        print(error(f"✗ Fehler beim Sync: {str(e)}"))
        import traceback
        traceback.print_exc()
        return False


async def sheets_sync_worker(config, interval_seconds=5):
    """
    Worker der kontinuierlich im Hintergrund läuft und synchronisiert
    
    Args:
        config: Bot-Konfiguration
        interval_seconds: Sync-Intervall in Sekunden (Standard: 5)
    """
    print(f"\n{'='*60}")
    print(f"📊 Google Sheets Sync-Worker gestartet")
    print(f"   Sync-Intervall: {interval_seconds} Sekunden")
    print(f"{'='*60}\n")
    
    sync_count = 0
    error_count = 0
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            
            # Sync durchführen
            success = await sync_to_sheets(config)
            
            if success:
                sync_count += 1
                error_count = 0  # Reset bei Erfolg
            else:
                error_count += 1
                
                # Bei wiederholten Fehlern: Warnung
                if error_count >= 3:
                    print(warning(f"⚠️  Sync-Worker: {error_count} Fehler in Folge"))
                
                # Bei vielen Fehlern: Längere Pause
                if error_count >= 10:
                    print(warning(f"⚠️  Viele Sync-Fehler - warte 60 Sekunden..."))
                    await asyncio.sleep(60)
                    error_count = 0
            
            # Statusmeldung entfernt - Sync läuft still im Hintergrund
            # Nur Fehler werden ausgegeben
                
        except asyncio.CancelledError:
            print("\n→ Sync-Worker wird beendet...")
            # Ein letzter Sync vor dem Beenden
            try:
                await sync_to_sheets(config)
                print("✓ Finaler Sync abgeschlossen")
            except:
                pass
            break
        except Exception as e:
            print(f"✗ Unerwarteter Fehler im Sync-Worker: {str(e)}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(interval_seconds)


async def migrate_sheets_to_database(config):
    """
    Einmalige Migration: Lädt bestehende Daten aus Google Sheets in die Datenbank
    Wird beim Start ausgeführt, falls die Datenbank leer ist
    """
    from .operations import add_or_update_vote, get_all_games_sorted
    
    print("\n→ Prüfe ob Migration von Google Sheets nötig ist...")
    
    # Prüfe ob DB leer ist
    db_games = await get_all_games_sorted()
    if db_games:
        print(f"✓ Datenbank enthält bereits {len(db_games)} Spiele - Migration übersprungen")
        return
    
    # DB ist leer - migriere von Sheets
    if not cache.get('worksheet'):
        print("⚠️  Worksheet nicht verfügbar - Migration übersprungen")
        return
    
    try:
        print("→ Lade Daten aus Google Sheets...")
        
        # Hole alle Daten aus Sheets
        all_records = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cache['worksheet'].get_all_records(numericise_ignore=['all'])
        )
        
        if not all_records:
            print("✓ Keine Daten in Google Sheets - Migration übersprungen")
            return
        
        df = pd.DataFrame(all_records)
        
        if 'Votes' not in df.columns or 'Game' not in df.columns:
            print("✗ Google Sheets hat nicht das erwartete Format (Votes, Game)")
            return
        
        # Migriere jedes Spiel
        migrated = 0
        for _, row in df.iterrows():
            game_name = str(row['Game']).strip()
            try:
                votes = int(row['Votes'])
            except (ValueError, TypeError):
                votes = 0
            
            if game_name and votes > 0:
                # Füge zur Datenbank hinzu (ohne History, da Migration)
                await add_or_update_vote(
                    game_name=game_name,
                    vote_weight=votes,
                    user_name='[Migration]',
                    vote_type='migration'
                )
                migrated += 1
        
        print(f"✓ Migration abgeschlossen: {migrated} Spiele importiert")
        
    except Exception as e:
        print(f"✗ Fehler bei der Migration: {str(e)}")
        import traceback
        traceback.print_exc()
