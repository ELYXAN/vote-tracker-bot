"""
Token-Verwaltung für Twitch OAuth
"""
from datetime import datetime, timedelta
from src.config.loader import save_config


def check_token_validity(config, account_type):
    """Überprüft, ob das Token noch gültig ist (rein basierend auf Ablaufdatum)"""
    if not config[account_type].get('access_token') or not config[account_type].get('token_expiry'):
        return False

    try:
        expiry_time_str = config[account_type]['token_expiry']
        if expiry_time_str.endswith('Z'):
            expiry_time_str = expiry_time_str[:-1] + '+00:00'

        expiry_time = datetime.fromisoformat(expiry_time_str)
        if expiry_time.tzinfo is None:
            pass

        now = datetime.now(expiry_time.tzinfo)
        return now < (expiry_time - timedelta(seconds=60))
    except (ValueError, TypeError) as e:
        print(f"Fehler beim Parsen des Token-Ablaufdatums für {account_type}: {e}")
        return False


async def refresh_token(session, config, account_type):
    """Token über Refresh-Token erneuern"""
    print(f"Versuche Token für {account_type} zu erneuern...")

    refresh_token_value = config[account_type].get('refresh_token')
    if not refresh_token_value:
        print(f"Kein Refresh-Token für {account_type} vorhanden. Überspringe Erneuerung.")
        return False

    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token_value,
        'client_id': config[account_type]['client_id'],
        'client_secret': config[account_type]['client_secret']
    }

    try:
        async with session.post(url, data=params) as response:
            if response.status == 200:
                data = await response.json()
                config[account_type]['access_token'] = data['access_token']
                
                if 'refresh_token' in data and data['refresh_token']:
                    config[account_type]['refresh_token'] = data['refresh_token']
                else:
                    print(f"WARNUNG: Kein neuer Refresh Token von Twitch für {account_type} erhalten.")

                expires_in = data.get('expires_in', 3600)
                config[account_type]['token_expiry'] = (
                    datetime.now() + timedelta(seconds=expires_in)
                ).isoformat()

                print(f"Token für {account_type} erfolgreich erneuert! Gültig bis: {config[account_type]['token_expiry']}")
                save_config(config)
                return True
                
            elif response.status in [400, 401]:
                response_text = await response.text()
                print(f"Fehler beim Erneuern des Tokens für {account_type}: {response.status} - {response_text}")
                
                if "Invalid refresh token" in response_text:
                    print(f"Refresh-Token für {account_type} ist ungültig geworden.")
                    config[account_type]['access_token'] = ''
                    config[account_type]['refresh_token'] = ''
                    config[account_type]['token_expiry'] = ''
                    save_config(config)
                return False
            else:
                print(f"Unerwarteter Fehler beim Erneuern des Tokens für {account_type}: {response.status}")
                return False
                
    except Exception as e:
        print(f"Exception beim Token-Refresh für {account_type}: {str(e)}")
        return False


async def ensure_valid_token(session, config, account_type):
    """Stellt sicher, dass ein gültiges Token vorhanden ist"""
    from .oauth_flow import request_initial_token
    from src.config.constants import SECRETS_FILE
    
    if check_token_validity(config, account_type):
        return True

    print(f"Token für {account_type} ist ungültig oder fehlt. Versuche Erneuerung/Neuautorisierung...")

    if config[account_type].get('refresh_token'):
        if await refresh_token(session, config, account_type):
            return True

    print(f"Token-Erneuerung für {account_type} fehlgeschlagen oder kein Refresh-Token vorhanden.")
    
    if not config[account_type].get('client_secret'):
        print(f"FEHLER: Client Secret für '{account_type}' fehlt in {SECRETS_FILE}.")
        return False

    if await request_initial_token(session, config, account_type):
        return True
    else:
        print(f"FEHLER: Konnte keinen gültigen Token für {account_type} erhalten.")
        return False
