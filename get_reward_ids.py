#!/usr/bin/env python3
"""
Helper script to list all Channel Point Rewards for your Twitch channel
This helps you find the correct Reward IDs for config.json
"""
import asyncio
import aiohttp
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.loader import load_config
from src.auth.token_manager import ensure_valid_token


async def list_rewards():
    """Lists all channel point rewards for the broadcaster"""
    print("=" * 60)
    print("🔍 Channel Point Rewards Finder")
    print("=" * 60)
    print()
    
    # Load config
    try:
        config = load_config()
    except Exception as e:
        print(f"✗ Fehler beim Laden der Konfiguration: {e}")
        print("Bitte stelle sicher, dass secrets.json korrekt ausgefüllt ist.")
        return
    
    async with aiohttp.ClientSession() as session:
        # Ensure valid token
        if not await ensure_valid_token(session, config, 'streamer'):
            print("✗ Konnte kein gültiges Token für den Streamer-Account erhalten.")
            return
        
        # Get all custom rewards
        url = 'https://api.twitch.tv/helix/channel_points/custom_rewards'
        headers = {
            'Client-Id': config['streamer']['client_id'],
            'Authorization': f"Bearer {config['streamer']['access_token']}"
        }
        params = {
            'broadcaster_id': config['broadcaster_id'],
            'only_manageable_rewards': 'false'  # Get all rewards
        }
        
        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    rewards = data.get('data', [])
                    
                    if not rewards:
                        print("⚠️  Keine Channel Point Rewards gefunden!")
                        print("   Stelle sicher, dass du Rewards in deinem Twitch-Kanal erstellt hast.")
                        return
                    
                    print(f"✓ {len(rewards)} Reward(s) gefunden:\n")
                    print("=" * 60)
                    
                    for i, reward in enumerate(rewards, 1):
                        reward_id = reward['id']
                        title = reward['title']
                        cost = reward['cost']
                        is_enabled = reward['is_enabled']
                        is_user_input_required = reward.get('is_user_input_required', False)
                        
                        status = "✓ Aktiv" if is_enabled else "✗ Deaktiviert"
                        input_req = "✓ Benötigt Eingabe" if is_user_input_required else "✗ Keine Eingabe"
                        
                        print(f"\n[{i}] {title}")
                        print(f"    Reward ID: {reward_id}")
                        print(f"    Kosten: {cost} Channel Points")
                        print(f"    Status: {status}")
                        print(f"    Eingabe erforderlich: {input_req}")
                    
                    print("\n" + "=" * 60)
                    print("\n💡 Tipp: Kopiere die Reward IDs für deine Vote-Rewards")
                    print("   und füge sie in config.json ein:\n")
                    print("   \"rewards\": {")
                    print("     \"normal_vote\": \"<REWARD_ID_HIER>\",")
                    print("     \"super_vote\": \"<REWARD_ID_HIER>\",")
                    print("     \"ultra_vote\": \"<REWARD_ID_HIER>\"")
                    print("   }")
                    print()
                    
                elif response.status == 401:
                    print("✗ Token ungültig. Bitte autorisiere die Anwendung erneut.")
                elif response.status == 403:
                    print("✗ Keine Berechtigung. Stelle sicher, dass:")
                    print("  - Der Streamer-Account der Besitzer des Kanals ist")
                    print("  - Das Token die Scope 'channel:read:redemptions' hat")
                else:
                    error_text = await response.text()
                    print(f"✗ Fehler: {response.status}")
                    print(f"   {error_text}")
                    
        except Exception as e:
            print(f"✗ Fehler beim Abrufen der Rewards: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(list_rewards())
    except KeyboardInterrupt:
        print("\n→ Abgebrochen durch Benutzer.")
    except Exception as e:
        print(f"\n✗ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()

