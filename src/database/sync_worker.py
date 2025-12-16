"""
Async Worker für Google Sheets Synchronisation
Läuft parallel und synct die Datenbank mit Google Sheets ohne die Performance zu beeinträchtigen
"""
import asyncio
import gspread
import pandas as pd
import sqlite3
from .operations import get_all_games_sorted, mark_synced, get_pending_changes
from .safety_check import safe_sync_to_sheets, calculate_data_hash
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
        
        # Markiere als synchronisiert (mit Spreadsheet-ID und Hash)
        spreadsheet_hash = calculate_data_hash(games)
        await mark_synced(
            spreadsheet_id=config.get('spreadsheet_id'),
            spreadsheet_hash=spreadsheet_hash
        )
        
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
            
            # Sync durchführen (mit Sicherheitsprüfung)
            success = await safe_sync_to_sheets(config, force=False)
            
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
                await safe_sync_to_sheets(config, force=False)
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
    Wird beim Start ausgeführt, falls die Datenbank leer ist oder Spreadsheet-ID mismatch
    """
    from .operations import add_or_update_vote, get_all_games_sorted, get_stored_spreadsheet_info
    from .safety_check import check_sync_safety, calculate_data_hash, get_spreadsheet_data
    from .models import DB_FILE
    import os
    
    print("\n→ Prüfe ob Migration von Google Sheets nötig ist...")
    
    # Prüfe Spreadsheet-ID Mismatch
    stored_info = await get_stored_spreadsheet_info()
    stored_id = stored_info.get('spreadsheet_id')
    current_id = config.get('spreadsheet_id')
    
    db_games = await get_all_games_sorted()
    
    # Debug-Ausgabe
    print(info(f"   Gespeicherte Spreadsheet-ID: {stored_id or '(nicht gesetzt)'}"))
    print(info(f"   Aktuelle Spreadsheet-ID: {current_id}"))
    print(info(f"   Spiele in DB: {len(db_games)}"))
    
    # Wenn Spreadsheet-ID nicht übereinstimmt UND DB Daten hat -> Bestätigung fragen
    if stored_id and stored_id != current_id and db_games:
        # Lade Spreadsheet-Daten für Vergleich
        sheet_games = await get_spreadsheet_data()
        
        print("\n" + "="*70)
        print(warning("⚠️  WICHTIG: Spreadsheet-ID Mismatch erkannt!"))
        print("="*70)
        print(f"   Gespeicherte ID: {stored_id}")
        print(f"   Aktuelle ID: {current_id}")
        print()
        
        if sheet_games is not None:
            print(f"   Datenbank: {len(db_games)} Spiele, {sum(g['votes'] for g in db_games)} Votes")
            print(f"   Spreadsheet: {len(sheet_games)} Spiele, {sum(g['votes'] for g in sheet_games)} Votes")
        else:
            print(f"   Datenbank: {len(db_games)} Spiele")
            print(f"   Spreadsheet: Konnte nicht geladen werden")
        
        print()
        print("   Die Datenbank wurde für ein anderes Spreadsheet erstellt.")
        print("   Um mit dem neuen Spreadsheet zu arbeiten, muss die Datenbank")
        print("   gelöscht und neu initialisiert werden.")
        print()
        print("   ⚠️  WICHTIG: Auch wenn die Anzahl der Spiele gleich ist,")
        print("   könnten die Vote-Zahlen oder Positionen unterschiedlich sein!")
        print()
        print("   ⚠️  WARNUNG: Alle Datenbank-Daten gehen verloren!")
        print("   Die Daten werden aus dem neuen Spreadsheet geladen.")
        print("="*70)
        print()
        
        # Bestätigung einholen
        while True:
            try:
                response = input(info("   Möchtest du die Datenbank löschen und neu initialisieren? (ja/nein): ")).strip().lower()
                if response in ['ja', 'j', 'yes', 'y']:
                    print()
                    print(warning("   → Lösche Datenbank..."))
                    
                    # Schließe alle DB-Verbindungen vor dem Löschen
                    import aiosqlite
                    # Warte kurz, damit alle Verbindungen geschlossen werden
                    await asyncio.sleep(0.5)
                    
                    # Lösche die Datenbank-Datei
                    if os.path.exists(DB_FILE):
                        os.remove(DB_FILE)
                        print(success(f"   ✓ Datenbank '{DB_FILE}' gelöscht"))
                    
                    # Initialisiere neue Datenbank
                    from .models import init_database
                    await init_database()
                    print(success("   ✓ Neue Datenbank initialisiert"))
                    print()
                    
                    # Setze db_games auf leer, damit Migration durchgeführt wird
                    db_games = []
                    break
                elif response in ['nein', 'n', 'no']:
                    print()
                    print(warning("   → Migration abgebrochen. Bot wird mit bestehender Datenbank fortgesetzt."))
                    print(warning("   ⚠️  Sync wird blockiert, bis die Datenbank gelöscht oder die Spreadsheet-ID korrigiert wird."))
                    print()
                    return
                else:
                    print(warning("   Bitte antworte mit 'ja' oder 'nein'"))
            except (EOFError, KeyboardInterrupt):
                print()
                print(warning("   → Migration abgebrochen. Bot wird mit bestehender Datenbank fortgesetzt."))
                print()
                return
    
    # Prüfe ob Migration nötig ist
    # WICHTIG: Wenn Spreadsheet-ID sich geändert hat, IMMER neu migrieren,
    # auch wenn die Anzahl der Spiele gleich ist (Vote-Zahlen könnten unterschiedlich sein!)
    
    # Wenn Spreadsheet-ID mismatch UND DB ist leer -> automatisch migrieren
    if stored_id and stored_id != current_id and not db_games:
        print(warning(f"⚠️  Spreadsheet-ID geändert (von {stored_id} zu {current_id})"))
        print(warning("   Datenbank wird mit Daten aus dem neuen Spreadsheet initialisiert..."))
        # Weiter mit Migration (db_games ist bereits leer)
    
    # Wenn DB Daten hat UND Spreadsheet-ID stimmt überein -> Migration nicht nötig
    elif db_games and stored_id == current_id:
        print(f"✓ Datenbank enthält bereits {len(db_games)} Spiele - Migration übersprungen")
        print(info("   (Spreadsheet-ID stimmt überein)"))
        return
    
    # Wenn DB Daten hat ABER keine gespeicherte Spreadsheet-ID -> Migration durchführen
    # um die Spreadsheet-ID zu setzen (aber nur wenn DB leer ist oder wenn explizit gewünscht)
    # ABER: Wenn DB Daten hat, sollten wir nicht automatisch migrieren, da das Daten überschreibt
    # Stattdessen: Wenn stored_id None ist, beim ersten Sync die ID speichern
    # Wenn sich die ID danach ändert, wird die Migration ausgelöst
    # Für jetzt: Wenn stored_id None ist UND DB hat Daten -> Migration überspringen, ID wird beim Sync gesetzt
    elif db_games and not stored_id:
        print(f"✓ Datenbank enthält bereits {len(db_games)} Spiele")
        print(info("   (Keine gespeicherte Spreadsheet-ID - wird beim nächsten Sync gespeichert)"))
        print(warning("   ⚠️  Wenn sich die Spreadsheet-ID geändert hat, lösche die Datenbank"))
        print(warning("   manuell (votes.db) und starte den Bot neu für eine Migration."))
        return
    
    # Wenn DB leer ist UND keine gespeicherte Spreadsheet-ID -> normale Migration
    elif not db_games and not stored_id:
        # Normale Migration für neue Datenbank
        pass
    
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
        updated = 0
        skipped = 0
        duplicates = 0
        seen_games = set()  # Track bereits verarbeitete Spiele in dieser Migration
        
        for _, row in df.iterrows():
            game_name = str(row['Game']).strip()
            try:
                votes = int(row['Votes'])
            except (ValueError, TypeError):
                votes = 0
            
            # Migriere ALLE Spiele mit Namen, auch die mit 0 Votes
            if game_name:
                # Prüfe auf Duplikate innerhalb der Migration
                if game_name.lower() in seen_games:
                    duplicates += 1
                    skipped += 1
                    continue
                
                seen_games.add(game_name.lower())
                
                # Für Migration: Setze die Vote-Anzahl direkt (nicht addieren!)
                from .models import DB_FILE
                import aiosqlite
                
                try:
                    async with aiosqlite.connect(DB_FILE) as db:
                        # Prüfe ob Spiel bereits existiert
                        cursor = await db.execute("SELECT votes FROM games WHERE name = ?", (game_name,))
                        result = await cursor.fetchone()
                        
                        if result:
                            # Spiel existiert bereits -> aktualisiere Vote-Anzahl direkt
                            await db.execute("""
                                UPDATE games 
                                SET votes = ?, last_updated = CURRENT_TIMESTAMP 
                                WHERE name = ?
                            """, (votes, game_name))
                            updated += 1
                        else:
                            # Spiel existiert nicht -> erstelle es mit der Vote-Anzahl aus dem Sheet
                            await db.execute("""
                                INSERT INTO games (name, votes, last_updated, created_at)
                                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """, (game_name, votes))
                            migrated += 1
                        
                        await db.commit()
                except sqlite3.IntegrityError:
                    # UNIQUE constraint violation - Spiel existiert bereits (Race condition)
                    duplicates += 1
                    skipped += 1
                except Exception as e:
                    print(error(f"   ✗ Fehler beim Migrieren von '{game_name}': {e}"))
                    skipped += 1
            else:
                skipped += 1
        
        # Speichere Spreadsheet-ID und Hash nach Migration
        # WICHTIG: Auch wenn nur Updates durchgeführt wurden (migrated == 0, updated > 0),
        # müssen wir die Spreadsheet-ID und Hash speichern!
        if migrated > 0 or updated > 0:
            migrated_games = await get_all_games_sorted()
            spreadsheet_hash = calculate_data_hash(migrated_games)
            await mark_synced(
                spreadsheet_id=config.get('spreadsheet_id'),
                spreadsheet_hash=spreadsheet_hash
            )
        
        # Zeige detaillierte Statistik
        total_processed = migrated + updated
        if duplicates > 0 or skipped > 0:
            details = []
            if migrated > 0:
                details.append(f"{migrated} neu")
            if updated > 0:
                details.append(f"{updated} aktualisiert")
            if duplicates > 0:
                details.append(f"{duplicates} Duplikate")
            if skipped > 0:
                details.append(f"{skipped} übersprungen")
            
            print(f"✓ Migration abgeschlossen: {total_processed} Spiele verarbeitet ({', '.join(details)})")
        else:
            print(f"✓ Migration abgeschlossen: {total_processed} Spiele verarbeitet")
        
    except Exception as e:
        print(f"✗ Fehler bei der Migration: {str(e)}")
        import traceback
        traceback.print_exc()
