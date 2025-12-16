"""
Manuelle Vote-Eingabe über die Kommandozeile
Jetzt mit Datenbank für sofortige Updates!
"""
import asyncio
import time
import aiohttp
from fuzzywuzzy import process
from src.twitch.redemptions import cache
from src.voting.ranking import calculate_rank_and_notify
from src.database.operations import add_or_update_vote, get_games_list
from src.utils.colors import success, error, warning, info, highlight, prompt, dim
import sys


async def manual_vote_input(config):
    """
    Ermöglicht manuelle Eingabe von Votes über die Kommandozeile
    Nutzt Datenbank für sofortige Verarbeitung!
    """
    print("\n" + "="*60)
    print(info("⌨️  MANUELLE VOTE-EINGABE GESTARTET", bold=True))
    print(info("   Du kannst jederzeit Votes manuell hinzufügen."))
    print(dim("   (Datenbank-Modus - Sofortige Updates!)"))
    print("="*60 + "\n")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # Warte kurz und flush stdout um sicherzustellen dass alle async Nachrichten
                # (z.B. von automatischer Vote-Verarbeitung) fertig sind
                await asyncio.sleep(0.2)
                sys.stdout.flush()
                
                # Spielname eingeben
                print()  # Leerzeile für bessere Trennung
                print(dim("-"*60))
                sys.stdout.flush()  # Flush vor input() damit Prompt sauber erscheint
                game_input = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    input, 
                    prompt("Gib den Spielnamen ein (oder 'exit' zum Beenden): ")
                )
                game_input = game_input.strip()
                
                if game_input.lower() == 'exit':
                    print(info("→ Manuelle Eingabe wird beendet..."))
                    break
                
                if not game_input:
                    print(warning("⚠️  Eingabe ungültig. Bitte einen Spielnamen eingeben."))
                    continue
                
                # Vote-Anzahl eingeben
                votes_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    input,
                    prompt("Gib die Anzahl der Votes ein: ")
                )
                votes_input = votes_input.strip()
                
                try:
                    vote_count = int(votes_input)
                    if vote_count <= 0:
                        print(warning("⚠️  Vote-Anzahl muss größer als 0 sein."))
                        continue
                except ValueError:
                    print(warning("⚠️  Ungültige Eingabe. Bitte eine Zahl eingeben."))
                    continue
                
                # Spiele-Liste aus Datenbank holen (für Fuzzy Matching)
                if time.time() - cache['last_cache_update'] > cache['cache_validity']:
                    cache['games_list'] = await get_games_list()
                    cache['last_cache_update'] = time.time()
                
                # Fuzzy Matching durchführen
                match = None
                score = 0
                
                if cache['games_list']:
                    game_input_lower = game_input.lower()
                    games_list_lower = [game.lower() for game in cache['games_list']]
                    result = process.extractOne(
                        game_input_lower, 
                        games_list_lower, 
                        score_cutoff=config.get('min_match_score', 80)
                    )
                    
                    if result:
                        match_index = games_list_lower.index(result[0])
                        match = cache['games_list'][match_index]
                        score = result[1]
                        print(success(f"  ✓ Match gefunden: '{match}' (Score: {score})"))
                    else:
                        print(info(f"  ℹ️  Kein Match gefunden - Spiel wird neu hinzugefügt: '{game_input}'"))
                        match = game_input
                else:
                    print(info(f"  ℹ️  Spieleliste leer - Spiel wird neu hinzugefügt: '{game_input}'"))
                    match = game_input
                
                if not match:
                    print(error("✗ Fehler beim Verarbeiten des Spielnamens."))
                    continue
                
                # ⚡ DATENBANK-UPDATE (sofort!)
                print(f"\n{info('→ Verarbeite manuellen Vote:')} {highlight(str(vote_count))} Votes für {highlight(match)}...")
                
                result = await add_or_update_vote(
                    game_name=match,
                    vote_weight=vote_count,
                    user_name=config.get('twitch_username', 'Streamer'),
                    vote_type='manual'
                )
                
                new_votes = result['votes']
                is_new = result['is_new']
                
                if is_new:
                    print(success(f"  ✓ Neues Spiel '{match}' mit {highlight(str(new_votes))} Votes hinzugefügt"))
                else:
                    print(success(f"  ✓ Vote aktualisiert: {highlight(str(new_votes))} Votes (+{highlight(str(vote_count))})"))
                
                # Rang berechnen und Nachricht senden
                streamer_name = config.get('twitch_username', 'Streamer')
                await calculate_rank_and_notify(session, config, match, new_votes, streamer_name)
                
                # Cache aktualisieren wenn neues Spiel
                if is_new:
                    cache['games_list'] = await get_games_list()
                    cache['last_cache_update'] = time.time()
                
                # Warte kurz damit Chat-Nachricht und andere async Operationen abgeschlossen sind
                await asyncio.sleep(0.3)
                
                print(f"\n{'='*60}")
                print(success("✓ Manueller Vote erfolgreich verarbeitet!", bold=True))
                print(f"  Spiel: {highlight(match)}")
                print(f"  Neue Gesamt-Votes: {highlight(str(new_votes))}")
                print(dim(f"  (Wird in {config.get('database', {}).get('sync_interval', 5)}s mit Google Sheets synchronisiert)"))
                print(f"{'='*60}")
                
                # Warte länger damit alle async Ausgaben (Sync-Messages, Chat-Nachricht, etc.) sichtbar sind
                # bevor der nächste Prompt erscheint
                await asyncio.sleep(0.8)
                
                # Flush stdout um sicherzustellen dass alle Ausgaben geschrieben sind
                sys.stdout.flush()
                
                # Explizit neue Zeile und Separator für nächsten Prompt
                print()  # Leerzeile nach Erfolgsmeldung
                
            except KeyboardInterrupt:
                print(f"\n\n{info('→ Manuelle Eingabe durch Benutzer abgebrochen.')}")
                break
            except Exception as e:
                print(error(f"\n✗ Fehler bei der manuellen Vote-Eingabe: {str(e)}"))
                import traceback
                traceback.print_exc()
                await asyncio.sleep(1)
