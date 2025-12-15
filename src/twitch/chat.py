"""
Twitch Chat Integration
"""
from src.auth.token_manager import ensure_valid_token
from src.utils.colors import success, error, warning, info

# Cache für Bot User ID (wird einmal geladen)
bot_user_id_cache = None


async def get_bot_user_id(session, config):
    """Holt die Bot User ID einmalig und cached sie"""
    global bot_user_id_cache
    
    if bot_user_id_cache:
        return bot_user_id_cache
    
    # Versuche aus Config zu laden
    if config['chat_bot'].get('user_id'):
        bot_user_id_cache = config['chat_bot']['user_id']
        return bot_user_id_cache
    
    # Hole von API
    try:
        validate_url = 'https://id.twitch.tv/oauth2/validate'
        headers_val = {'Authorization': f"Bearer {config['chat_bot']['access_token']}"}
        async with session.get(validate_url, headers=headers_val) as val_resp:
            if val_resp.status == 200:
                val_data = await val_resp.json()
                bot_user_id_cache = val_data.get('user_id')
                config['chat_bot']['user_id'] = bot_user_id_cache
                return bot_user_id_cache
    except Exception as e:
        print(f"Fehler beim Abrufen der Bot User ID: {e}")
    
    return None


async def send_chat_message(session, config, message):
    """Sendet eine Nachricht in den Twitch-Chat"""
    if not await ensure_valid_token(session, config, 'chat_bot'):
        print("Chat-Bot Token ungültig. Nachricht kann nicht gesendet werden.")
        return

    # Hole die Bot User ID (cached)
    bot_user_id = await get_bot_user_id(session, config)
    if not bot_user_id:
        print("FEHLER: Konnte die User ID des Chat-Bots nicht ermitteln.")
        return

    chat_messages_url = 'https://api.twitch.tv/helix/chat/messages'
    headers = {
        'Authorization': f"Bearer {config['chat_bot']['access_token']}",
        'Client-Id': config['chat_bot']['client_id'],
        'Content-Type': 'application/json'
    }

    data = {
        "broadcaster_id": config['broadcaster_id'],
        "sender_id": bot_user_id,
        "message": message
    }

    try:
        async with session.post(chat_messages_url, headers=headers, json=data) as response:
            if response.status == 200:
                print(success(f"Chat-Nachricht gesendet: {message}"))
            elif response.status == 403:
                resp_text = await response.text()
                print(error(f"Fehler beim Senden der Chat-Nachricht (403 Forbidden): {resp_text}"))
                if "Missing scope" in resp_text:
                    print(warning("-> Dem Bot-Token fehlt der nötige Scope ('chat:edit')."))
                elif "user does not have permission" in resp_text:
                    print(warning("-> Der Bot ist möglicherweise kein Moderator im Kanal."))
            else:
                print(error(f"Fehler beim Senden der Chat-Nachricht: {response.status} - {await response.text()}"))
    except Exception as e:
        print(error(f"Exception beim Senden der Chat-Nachricht: {str(e)}"))
