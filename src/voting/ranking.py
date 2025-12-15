"""
Ranking-Berechnung und Chat-Benachrichtigung
Nutzt jetzt die Datenbank für blitzschnelle Rang-Berechnung!
"""
import asyncio
from src.twitch.chat import send_chat_message
from src.database.operations import get_game_rank
from src.utils.colors import success, error, warning, info


async def calculate_rank_and_notify(session, config, game_name, new_votes, user):
    """
    Berechnet den Rang eines Spiels und sendet eine Chat-Nachricht
    Jetzt VIEL schneller durch Datenbank-Abfrage!
    """
    try:
        # Hole Rang aus Datenbank (extrem schnell!)
        rank_info = await get_game_rank(game_name)
        
        if not rank_info:
            # Neues Spiel - wird automatisch auf Platz berechnet
            print(warning(f"⚠️  Spiel '{game_name}' noch nicht in DB, wird beim nächsten Update berechnet"))
            message = f"🎮 {user} hat für '{game_name}' gevotet! Neues Spiel mit {new_votes} Votes! 🎮"
        else:
            rank = rank_info['rank']
            total_games = rank_info['total_games']
            message = f"🎮 {user} hat für '{game_name}' gevotet! Rang: #{rank} von {total_games} mit {new_votes} Votes! 🎮"
        
        # Chat-Nachricht senden (await für manuelle Eingabe, damit Prompt nicht zu früh erscheint)
        await send_chat_message(session, config, message)
        
    except Exception as e:
        print(error(f"✗ Fehler bei der Rang-Berechnung: {str(e)}"))
        import traceback
        traceback.print_exc()
        
        # Fallback: Sende zumindest eine einfache Nachricht
        try:
            message = f"🎮 {user} hat für '{game_name}' gevotet! {new_votes} Votes! 🎮"
            await send_chat_message(session, config, message)
        except:
            pass
