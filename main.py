"""
Vote Tracker Bot - Haupteinstiegspunkt
Version 3.0 - Modular Architecture + Database

Dieser Bot überwacht Twitch Channel Point Redemptions und verwaltet Votes
in einer SQLite-Datenbank mit automatischer Google Sheets Synchronisation.

Features:
- Automatische Vote-Verarbeitung (normal/super/ultra)
- SQLite Datenbank für blitzschnelle Performance
- Automatischer Sync zu Google Sheets (als View für Viewer)
- Manuelle Vote-Eingabe über CLI
- Fuzzy Matching für Spielnamen
- Automatische Rang-Berechnung
- Twitch Chat Benachrichtigungen
- Vote-History und Statistiken
"""
import asyncio
import aiohttp

from src.config.loader import load_config
from src.config.constants import CLIENT_SECRET
from src.auth.token_manager import ensure_valid_token
from src.sheets.manager import init_google_sheets
from src.twitch.redemptions import listen_to_redemptions, cache
from src.voting.processor import process_votes
from src.voting.manual_input import manual_vote_input
from src.utils.banner import banner
from src.utils.storage import load_processed_ids
from src.database.models import init_database, get_database_stats
from src.database.sync_worker import sheets_sync_worker, migrate_sheets_to_database


async def main():
    """Hauptfunktion des Vote Tracker Bots"""
    banner()
    print("🚀 Vote Tracker Bot wird gestartet...\n")

    # Konfiguration laden
    config = load_config()

    # Überprüfe Client Secrets
    if not config['streamer'].get('client_secret') or \
       not config['chat_bot'].get('client_secret'):
        print("\n" + "="*60)
        print("✗ FEHLER: Client Secrets fehlen!")
        print("  Bitte überprüfe die secrets.json Datei.")
        print("="*60 + "\n")
        return

    # ⚡ DATENBANK INITIALISIEREN
    print("→ Initialisiere Datenbank...")
    await init_database()
    
    # Verarbeitete IDs laden
    cache['processed_ids'] = load_processed_ids()
    print(f"✓ {len(cache['processed_ids'])} bereits verarbeitete Vote-IDs geladen.")

    # Google Sheets initialisieren (für Migration und Sync)
    await init_google_sheets(config)

    # Migration: Sheets → Datenbank (falls DB leer)
    if config.get('database', {}).get('enabled', True):
        await migrate_sheets_to_database(config)
        
        # Zeige Datenbank-Statistiken
        stats = await get_database_stats()
        print(f"\n{'='*60}")
        print(f"📊 Datenbank-Status:")
        print(f"{'='*60}")
        print(f"  Spiele in DB: {stats['games']}")
        print(f"  Gesamt Votes: {stats['total_votes']}")
        print(f"  Vote-History Einträge: {stats['history_entries']}")
        print(f"  Letzter Sync: {stats['last_sync'] or 'Noch nie'}")
        print(f"  Sync-Anzahl: {stats['sync_count']}")
        print(f"{'='*60}\n")

    # Token-Validierung
    print("→ Überprüfe Twitch API Tokens...")
    async with aiohttp.ClientSession() as session:
        streamer_ok = await ensure_valid_token(session, config, 'streamer')
        bot_ok = await ensure_valid_token(session, config, 'chat_bot')

    if not streamer_ok or not bot_ok:
        print("\n" + "="*60)
        print("✗ FEHLER: Konnte nicht für alle Accounts gültige Tokens sicherstellen.")
        if not streamer_ok:
            print("  - Problem mit 'streamer' Account Token.")
        if not bot_ok:
            print("  - Problem mit 'chat_bot' Account Token.")
        print("\n  Bitte überprüfe die Fehlermeldungen oben.")
        print("="*60 + "\n")
        return

    print("✓ Alle Tokens sind gültig.\n")
    
    # Bot-Konfiguration anzeigen
    print(f"{'='*60}")
    print(f"⚙️  Bot-Konfiguration:")
    print(f"{'='*60}")
    print(f"  Kanal: {config.get('twitch_username', 'Unbekannt')}")
    print(f"  Broadcaster ID: {config.get('broadcaster_id', 'Unbekannt')}")
    print(f"  Normal Vote ID: {config.get('rewards', {}).get('normal_vote', 'Nicht gesetzt')}")
    print(f"  Super Vote ID: {config.get('rewards', {}).get('super_vote', 'Nicht gesetzt')}")
    print(f"  Ultra Vote ID: {config.get('rewards', {}).get('ultra_vote', 'Nicht gesetzt')}")
    print(f"  Spreadsheet ID: {config.get('spreadsheet_id', 'Nicht gesetzt')}")
    print(f"  Datenbank: {'✓ Aktiviert' if config.get('database', {}).get('enabled') else '✗ Deaktiviert'}")
    print(f"  Sync-Intervall: {config.get('database', {}).get('sync_interval', 5)}s")
    print(f"{'='*60}\n")
    print("→ Starte Bot-Tasks...\n")

    # Tasks starten
    listener_task = asyncio.create_task(listen_to_redemptions(config))
    processor_task = asyncio.create_task(process_votes(config))
    manual_input_task = asyncio.create_task(manual_vote_input(config))
    
    # Sync-Worker starten (läuft parallel im Hintergrund)
    sync_interval = config.get('database', {}).get('sync_interval', 5)
    sync_task = asyncio.create_task(sheets_sync_worker(config, sync_interval))

    try:
        await asyncio.gather(listener_task, processor_task, manual_input_task, sync_task)
    except asyncio.CancelledError:
        print("\n→ Bot wird durch Benutzer gestoppt...")
    except Exception as e:
        print(f"\n✗ Unerwarteter Fehler: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n→ Tasks werden beendet...")
        listener_task.cancel()
        processor_task.cancel()
        manual_input_task.cancel()
        sync_task.cancel()
        
        # Warte auf sauberes Beenden
        await asyncio.gather(
            listener_task, processor_task, manual_input_task, sync_task,
            return_exceptions=True
        )
        
        print("✓ Bot wurde sauber beendet.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n→ Programm durch Strg+C beendet.")
