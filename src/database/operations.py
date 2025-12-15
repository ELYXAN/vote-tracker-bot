"""
Datenbank-Operationen für Vote Tracking
"""
import aiosqlite
from datetime import datetime
from .models import DB_FILE


async def add_or_update_vote(game_name: str, vote_weight: int, user_name: str = None, vote_type: str = 'normal'):
    """
    Fügt einen Vote hinzu oder aktualisiert die Vote-Anzahl für ein Spiel
    
    Args:
        game_name: Name des Spiels
        vote_weight: Gewicht des Votes (1, 10, 25)
        user_name: Name des Users (für History)
        vote_type: Typ des Votes (normal, super, ultra)
    
    Returns:
        dict mit neuer Vote-Anzahl und ob Spiel neu erstellt wurde
    """
    async with aiosqlite.connect(DB_FILE) as db:
        # Prüfe ob Spiel existiert
        cursor = await db.execute("SELECT votes FROM games WHERE name = ?", (game_name,))
        result = await cursor.fetchone()
        
        if result:
            # Spiel existiert - Update
            old_votes = result[0]
            new_votes = old_votes + vote_weight
            await db.execute("""
                UPDATE games 
                SET votes = ?, last_updated = CURRENT_TIMESTAMP 
                WHERE name = ?
            """, (new_votes, game_name))
            is_new = False
        else:
            # Neues Spiel - Insert
            new_votes = vote_weight
            await db.execute("""
                INSERT INTO games (name, votes, last_updated, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (game_name, new_votes))
            is_new = True
        
        # Vote History eintragen
        if user_name:
            await db.execute("""
                INSERT INTO vote_history (game_name, user_name, vote_type, vote_weight, timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (game_name, user_name, vote_type, vote_weight))
        
        # Pending changes erhöhen
        await db.execute("""
            UPDATE sync_status 
            SET pending_changes = pending_changes + 1 
            WHERE id = 1
        """)
        
        await db.commit()
        
        return {
            'game_name': game_name,
            'votes': new_votes,
            'is_new': is_new,
            'vote_weight': vote_weight
        }


async def get_game_votes(game_name: str):
    """Gibt die aktuelle Vote-Anzahl für ein Spiel zurück"""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT votes FROM games WHERE name = ?", (game_name,))
        result = await cursor.fetchone()
        return result[0] if result else 0


async def get_all_games_sorted():
    """
    Gibt alle Spiele sortiert nach Votes zurück (schnell!)
    
    Returns:
        List von dicts mit game_name, votes, rank
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
            SELECT name, votes 
            FROM games 
            ORDER BY votes DESC, name ASC
        """)
        results = await cursor.fetchall()
        
        # Ränge hinzufügen
        games = []
        for rank, (name, votes) in enumerate(results, start=1):
            games.append({
                'rank': rank,
                'name': name,
                'votes': votes
            })
        
        return games


async def get_game_rank(game_name: str):
    """
    Berechnet den aktuellen Rang eines Spiels (sehr schnell!)
    
    Returns:
        dict mit rank, votes, total_games
    """
    async with aiosqlite.connect(DB_FILE) as db:
        # Hole Vote-Anzahl des Spiels
        cursor = await db.execute("SELECT votes FROM games WHERE name = ?", (game_name,))
        result = await cursor.fetchone()
        
        if not result:
            return None
        
        votes = result[0]
        
        # Berechne Rang (wie viele Spiele haben mehr Votes?)
        cursor = await db.execute("""
            SELECT COUNT(*) + 1 FROM games 
            WHERE votes > ? OR (votes = ? AND name < ?)
        """, (votes, votes, game_name))
        rank = (await cursor.fetchone())[0]
        
        # Gesamtanzahl Spiele
        cursor = await db.execute("SELECT COUNT(*) FROM games")
        total = (await cursor.fetchone())[0]
        
        return {
            'rank': rank,
            'votes': votes,
            'total_games': total
        }


async def search_game_fuzzy(search_term: str, limit: int = 10):
    """
    Sucht Spiele ähnlich zum Suchbegriff (für Fuzzy Matching)
    
    Returns:
        Liste von Spielnamen
    """
    async with aiosqlite.connect(DB_FILE) as db:
        # SQLite LIKE für einfache Suche
        cursor = await db.execute("""
            SELECT name FROM games 
            WHERE name LIKE ? 
            ORDER BY votes DESC 
            LIMIT ?
        """, (f"%{search_term}%", limit))
        results = await cursor.fetchall()
        return [row[0] for row in results]


async def get_games_list():
    """Gibt einfache Liste aller Spielnamen zurück (für Fuzzy Matching Cache)"""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT name FROM games ORDER BY votes DESC")
        results = await cursor.fetchall()
        return [row[0] for row in results]


async def get_pending_changes():
    """Gibt die Anzahl der ausstehenden Sync-Changes zurück"""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT pending_changes FROM sync_status WHERE id = 1")
        result = await cursor.fetchone()
        return result[0] if result else 0


async def mark_synced():
    """Markiert, dass ein Sync durchgeführt wurde"""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            UPDATE sync_status 
            SET last_sync = CURRENT_TIMESTAMP,
                sync_count = sync_count + 1,
                pending_changes = 0
            WHERE id = 1
        """)
        await db.commit()


async def get_vote_statistics(game_name: str = None):
    """
    Gibt detaillierte Statistiken zurück
    
    Args:
        game_name: Optional - Statistiken für ein bestimmtes Spiel
    
    Returns:
        dict mit Statistiken
    """
    async with aiosqlite.connect(DB_FILE) as db:
        if game_name:
            # Statistiken für ein Spiel
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as vote_count,
                    SUM(vote_weight) as total_votes,
                    COUNT(DISTINCT user_name) as unique_voters,
                    MIN(timestamp) as first_vote,
                    MAX(timestamp) as last_vote
                FROM vote_history
                WHERE game_name = ?
            """, (game_name,))
            result = await cursor.fetchone()
            
            return {
                'game_name': game_name,
                'vote_count': result[0],
                'total_votes': result[1],
                'unique_voters': result[2],
                'first_vote': result[3],
                'last_vote': result[4]
            }
        else:
            # Globale Statistiken
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_votes,
                    COUNT(DISTINCT game_name) as unique_games,
                    COUNT(DISTINCT user_name) as unique_voters
                FROM vote_history
            """)
            result = await cursor.fetchone()
            
            return {
                'total_votes': result[0],
                'unique_games': result[1],
                'unique_voters': result[2]
            }
