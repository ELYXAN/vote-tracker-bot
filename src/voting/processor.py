"""
Vote Processing - Hauptlogik für die Verarbeitung von Votes
Jetzt mit Datenbank für blitzschnelle Performance!
"""
import asyncio
import time
import aiohttp
from fuzzywuzzy import process
from src.twitch.redemptions import vote_queue, cache
from src.twitch.redemptions import fulfill_vote
from src.voting.ranking import calculate_rank_and_notify
from src.utils.storage import save_inaccurate_game
from src.auth.token_manager import ensure_valid_token
from src.database.operations import add_or_update_vote, get_games_list
from src.utils.colors import success, error, warning, info, highlight, dim


async def process_votes(config):
    """
    Verarbeitet Votes aus der Queue
    Nutzt jetzt Datenbank für extrem schnelle Verarbeitung!
    """
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                vote_data = await vote_queue.get()
                user = vote_data['user']
                user_input = vote_data['game']
                vote_id = vote_data['vote_id']
                reward_id = vote_data['reward_id']
                vote_type = vote_data['vote_type']

                print(f"\n{info('→ Verarbeite Vote von')} {highlight(user)} {info('für')} {highlight(user_input)} {dim(f'(Typ: {vote_type})')}")

                # Spiele-Liste aus Datenbank aktualisieren (falls Cache alt)
                if time.time() - cache['last_cache_update'] > cache['cache_validity']:
                    cache['games_list'] = await get_games_list()
                    cache['last_cache_update'] = time.time()
                    print(info(f"  Cache aktualisiert: {len(cache['games_list'])} Spiele"))

                # Fuzzy Matching (wie vorher, aber mit DB-Liste)
                match = None
                score = 0

                if cache['games_list']:
                    user_input_lower = user_input.lower()
                    games_list_lower = [game.lower() for game in cache['games_list']]
                    result = process.extractOne(
                        user_input_lower,
                        games_list_lower,
                        score_cutoff=config.get('min_match_score', 80)
                    )

                    if result:
                        match_index = games_list_lower.index(result[0])
                        match = cache['games_list'][match_index]
                        score = result[1]
                        print(success(f"  ✓ Fuzzy Match: '{match}' (Score: {score})"))
                    else:
                        print(warning(f"  ✗ Kein Match für '{user_input}' (unter Mindest-Score)."))
                else:
                    print(warning("  ⚠️  Spieleliste ist leer."))

                if match:
                    try:
                        # Bestimme Vote-Gewicht
                        if vote_type == 'ultra_vote':
                            vote_weight = config.get('ultra_vote_weight', 25)
                        elif vote_type == 'super_vote':
                            vote_weight = config.get('super_vote_weight', 10)
                        else:
                            vote_weight = config.get('normal_vote_weight', 1)

                        # ⚡ DATENBANK-UPDATE (extrem schnell!)
                        result = await add_or_update_vote(
                            game_name=match,
                            vote_weight=vote_weight,
                            user_name=user,
                            vote_type=vote_type
                        )
                        
                        new_votes = result['votes']
                        is_new = result['is_new']
                        
                        if is_new:
                            print(success(f"  ✓ Neues Spiel '{match}' mit {highlight(str(new_votes))} Votes hinzugefügt"))
                        else:
                            print(success(f"  ✓ Vote für '{match}' aktualisiert: {highlight(str(new_votes))} Votes (+{highlight(str(vote_weight))})"))

                        # ⚡ OPTIMIZATION: Fulfill vote immediately (user sees instant response)
                        # Then send chat message and calculate rank in parallel
                        fulfill_task = asyncio.create_task(fulfill_vote(session, config, reward_id, vote_id))
                        
                        # Rang berechnen und Chat-Nachricht senden (parallel zu fulfill)
                        notify_task = asyncio.create_task(calculate_rank_and_notify(session, config, match, new_votes, user))
                        
                        # Warte auf beide Tasks
                        await asyncio.gather(fulfill_task, notify_task, return_exceptions=True)
                        
                        # Cache aktualisieren wenn neues Spiel
                        if is_new:
                            cache['games_list'] = await get_games_list()
                            cache['last_cache_update'] = time.time()

                    except Exception as e:
                        print(error(f"✗ Fehler bei Vote-Verarbeitung: {str(e)}"))
                        import traceback
                        traceback.print_exc()

                else:
                    # Kein Match gefunden
                    print(warning(f"  ✗ Kein passendes Spiel für '{user_input}'."))
                    save_inaccurate_game(user_input)
                    await fulfill_vote(session, config, reward_id, vote_id)

                vote_queue.task_done()
                await asyncio.sleep(0.01)  # Minimal pause

            except Exception as e:
                print(error(f"✗ Schwerwiegender Fehler im Vote-Verarbeitungs-Loop: {str(e)}"))
                import traceback
                traceback.print_exc()
                if 'vote_data' in locals():
                    vote_queue.task_done()
                await asyncio.sleep(1)
