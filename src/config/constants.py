"""
Konfigurationskonstanten für den Vote Tracker Bot
"""

# Dateinamen
CONFIG_FILE = 'config.json'
SECRETS_FILE = 'secrets.json'

# OAuth Einstellungen
REDIRECT_URI = 'http://localhost'

# Twitch API Scopes
STREAMER_SCOPES = 'channel:read:redemptions channel:manage:redemptions'
CHAT_BOT_SCOPES = 'chat:read chat:edit user:write:chat'

# Standardkonfiguration
DEFAULT_CONFIG = {
    'streamer': {
        'client_id': '',
        'client_secret': '',
        'access_token': '',
        'refresh_token': '',
        'token_expiry': '',
        'scopes': STREAMER_SCOPES
    },
    'chat_bot': {
        'client_id': '',
        'client_secret': '',
        'access_token': '',
        'refresh_token': '',
        'token_expiry': '',
        'scopes': CHAT_BOT_SCOPES
    },
    'twitch_username': 'eilyxan',
    'rewards': {
        'normal_vote': 'dca20e2b-e6a9-424f-83f2-f77eb91d5a89', #dca20e2b-e6a9-424f-83f2-f77eb91d5a89
        'super_vote': '2d8c35aa-31d0-4d24-aaea-9c12afe35129',
        'ultra_vote': 'b22f5783-02fc-41f1-b917-d9c9530b5297'
    },
    'spreadsheet_id': '1rIVCDXx5KwqF42F2Yq11k5UQeF_cfNY3KVcFSmZxw80',
    'min_match_score': 80,
    'normal_vote_weight': 1,
    'super_vote_weight': 10,
    'ultra_vote_weight': 25,
    'broadcaster_id': '',
    'database': {
        'enabled': True,
        'sync_interval': 5,  # Sekunden zwischen Syncs zu Google Sheets
        'use_sheets_as_view': True  # Sheets als View für Viewer behalten
    }
}

# Globale Variablen (werden zur Laufzeit gesetzt)
BROADCASTER_ID = None
CLIENT_SECRET = None
