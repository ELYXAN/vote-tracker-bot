"""
Datenbank-Schema für Vote Tracker
"""
import sqlite3
import aiosqlite
from datetime import datetime


DB_FILE = 'votes.db'


async def init_database():
    """Initialisiert die Datenbank mit allen benötigten Tabellen"""
    async with aiosqlite.connect(DB_FILE) as db:
        # Haupttabelle: Spiele und ihre Votes
        await db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                votes INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Vote-History: Jeder einzelne Vote wird protokolliert
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vote_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_name TEXT NOT NULL,
                user_name TEXT NOT NULL,
                vote_type TEXT NOT NULL,
                vote_weight INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_name) REFERENCES games(name)
            )
        """)
        
        # Sync-Status: Verfolgt, wann zuletzt mit Sheets synchronisiert wurde
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_sync TIMESTAMP,
                sync_count INTEGER DEFAULT 0,
                pending_changes INTEGER DEFAULT 0
            )
        """)
        
        # Initialen Sync-Status einfügen falls nicht vorhanden
        await db.execute("""
            INSERT OR IGNORE INTO sync_status (id, last_sync, sync_count, pending_changes)
            VALUES (1, NULL, 0, 0)
        """)
        
        # Indizes für Performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_games_votes ON games(votes DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_games_name ON games(name)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON vote_history(timestamp DESC)")
        
        await db.commit()
        print("✓ Datenbank initialisiert")


async def get_database_stats():
    """Gibt Statistiken über die Datenbank zurück"""
    async with aiosqlite.connect(DB_FILE) as db:
        # Anzahl Spiele
        cursor = await db.execute("SELECT COUNT(*) FROM games")
        game_count = (await cursor.fetchone())[0]
        
        # Gesamte Votes
        cursor = await db.execute("SELECT SUM(votes) FROM games")
        total_votes = (await cursor.fetchone())[0] or 0
        
        # Vote History Einträge
        cursor = await db.execute("SELECT COUNT(*) FROM vote_history")
        history_count = (await cursor.fetchone())[0]
        
        # Letzter Sync
        cursor = await db.execute("SELECT last_sync, sync_count FROM sync_status WHERE id = 1")
        sync_info = await cursor.fetchone()
        
        return {
            'games': game_count,
            'total_votes': total_votes,
            'history_entries': history_count,
            'last_sync': sync_info[0] if sync_info else None,
            'sync_count': sync_info[1] if sync_info else 0
        }
