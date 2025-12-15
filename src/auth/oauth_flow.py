"""
OAuth2 Authentifizierungsflow für Twitch
"""
import secrets
import webbrowser
from datetime import datetime, timedelta
from src.config.constants import REDIRECT_URI
from src.config.loader import save_config


async def request_initial_token(session, config, account_type):
    """Fordert den Benutzer auf, die Anwendung zu autorisieren"""
    print("-" * 50)
    print(f"INITIIERE AUTORISIERUNG für Account: {account_type}")
    print("-" * 50)

    client_id = config[account_type]['client_id']
    scopes = config[account_type]['scopes']
    state = secrets.token_urlsafe(16)

    auth_url = (
        f"https://id.twitch.tv/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scopes.replace(' ', '+')}"
        f"&state={state}"
    )

    print(f"\nBitte öffne die folgende URL in deinem Browser:")
    print(auth_url)
    print(f"\nNachdem du die Anwendung autorisiert hast, wirst du zu '{REDIRECT_URI}?code=...' weitergeleitet.")
    print("Die Seite wird wahrscheinlich einen Fehler anzeigen (das ist normal!).")
    print("Kopiere den kompletten Wert des 'code'-Parameters aus der Adressleiste deines Browsers.")
    print("Der Code ist der Teil nach 'code=' und vor '&scope=...' (falls vorhanden).")

    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"(Konnte den Browser nicht automatisch öffnen: {e})")

    while True:
        authorization_code = input("\nFüge den kopierten 'code' hier ein und drücke Enter: ").strip()
        if authorization_code:
            break
        else:
            print("Eingabe ungültig, bitte versuche es erneut.")

    token_url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': config[account_type]['client_secret'],
        'code': authorization_code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }

    try:
        async with session.post(token_url, data=params) as response:
            if response.status == 200:
                data = await response.json()
                config[account_type]['access_token'] = data['access_token']
                config[account_type]['refresh_token'] = data['refresh_token']
                expires_in = data.get('expires_in', 3600)
                config[account_type]['token_expiry'] = (
                    datetime.now() + timedelta(seconds=expires_in)
                ).isoformat()

                print(f"Token für {account_type} erfolgreich erhalten und gespeichert!")
                save_config(config)
                print("-" * 50)
                return True
            else:
                print(f"Fehler beim Austauschen des Codes gegen Tokens für {account_type}: {response.status}")
                print(await response.text())
                print("Mögliche Ursachen: Falscher Code, Client Secret falsch, Redirect URI stimmt nicht überein.")
                print("-" * 50)
                return False
    except Exception as e:
        print(f"Exception beim Token-Austausch für {account_type}: {str(e)}")
        print("-" * 50)
        return False
