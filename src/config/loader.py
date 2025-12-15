"""
Konfigurationsverwaltung für den Vote Tracker Bot
"""
import json
import os
from .constants import CONFIG_FILE, SECRETS_FILE, DEFAULT_CONFIG


def load_secrets():
    """Lädt sensible Daten wie Tokens und Client-Secrets."""
    if not os.path.exists(SECRETS_FILE):
        raise FileNotFoundError(
            f"Datei '{SECRETS_FILE}' fehlt. Bitte lege sie an und trage Client IDs/Secrets dort ein."
        )

    with open(SECRETS_FILE, 'r') as f:
        secrets_data = json.load(f)

    required_sections = ['streamer', 'chat_bot']
    for section in required_sections:
        if section not in secrets_data:
            raise KeyError(f"'{section}' fehlt in {SECRETS_FILE}.")

        for key in ['client_id', 'client_secret']:
            if not secrets_data[section].get(key):
                raise ValueError(f"'{key}' fehlt für '{section}' in {SECRETS_FILE}.")

    if not secrets_data.get('broadcaster_id'):
        raise ValueError("'broadcaster_id' fehlt in secrets.json")

    return secrets_data


def merge_config_with_secrets(base_config, secrets_data):
    """Fügt sensible Werte aus secrets.json zur Laufzeit in die Config ein."""
    merged = json.loads(json.dumps(base_config))  # tiefe Kopie
    merged['broadcaster_id'] = secrets_data.get('broadcaster_id')

    for account in ['streamer', 'chat_bot']:
        merged[account]['client_id'] = secrets_data[account]['client_id']
        merged[account]['client_secret'] = secrets_data[account]['client_secret']
        merged[account]['access_token'] = secrets_data[account].get('access_token', '')
        merged[account]['refresh_token'] = secrets_data[account].get('refresh_token', '')
        merged[account]['token_expiry'] = secrets_data[account].get('token_expiry', '')
        if secrets_data[account].get('user_id'):
            merged[account]['user_id'] = secrets_data[account]['user_id']

    return merged


def persist_secrets(config):
    """Speichert aktualisierte Token zurück in secrets.json."""
    secrets_payload = {
        'streamer': {
            'client_id': config['streamer']['client_id'],
            'client_secret': config['streamer']['client_secret'],
            'access_token': config['streamer'].get('access_token', ''),
            'refresh_token': config['streamer'].get('refresh_token', ''),
            'token_expiry': config['streamer'].get('token_expiry', ''),
            'user_id': config['streamer'].get('user_id', '')
        },
        'chat_bot': {
            'client_id': config['chat_bot']['client_id'],
            'client_secret': config['chat_bot']['client_secret'],
            'access_token': config['chat_bot'].get('access_token', ''),
            'refresh_token': config['chat_bot'].get('refresh_token', ''),
            'token_expiry': config['chat_bot'].get('token_expiry', ''),
            'user_id': config['chat_bot'].get('user_id', '')
        },
        'broadcaster_id': config.get('broadcaster_id')
    }

    with open(SECRETS_FILE, 'w') as f:
        json.dump(secrets_payload, f, indent=4)


def load_config():
    """Lädt die Konfiguration, ergänzt Defaults und sensitive Daten."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            loaded_config = json.load(f)
    else:
        print(f"Konfigurationsdatei {CONFIG_FILE} nicht gefunden. Erstelle neue.")
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        loaded_config = json.loads(json.dumps(DEFAULT_CONFIG))

    # Merge Defaults für neue Keys
    for key, value in DEFAULT_CONFIG.items():
        if key not in loaded_config:
            loaded_config[key] = value
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if sub_key not in loaded_config[key]:
                    loaded_config[key][sub_key] = sub_value

    secrets_data = load_secrets()
    merged_config = merge_config_with_secrets(loaded_config, secrets_data)
    
    # Setze globale Variablen
    from . import constants
    constants.BROADCASTER_ID = merged_config.get('broadcaster_id')
    constants.CLIENT_SECRET = merged_config['streamer']['client_secret']
    
    return merged_config


def save_config(config):
    """Speichert die aktualisierte Konfiguration"""
    # Speichere nicht-sensitive Teile weiterhin in config.json
    safe_config = json.loads(json.dumps(config))
    for account in ['streamer', 'chat_bot']:
        for key in ['client_id', 'client_secret', 'access_token', 'refresh_token', 'token_expiry', 'user_id']:
            safe_config[account].pop(key, None)

    with open(CONFIG_FILE, 'w') as f:
        json.dump(safe_config, f, indent=4)

    # Sensible Teile separat persistieren
    persist_secrets(config)
