#!/usr/bin/env python3
"""
Script to create Channel Point Rewards via Twitch API
This ensures rewards are created with the correct Client ID
"""
import asyncio
import aiohttp
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.loader import load_config, save_config
from src.auth.token_manager import ensure_valid_token


async def create_reward(session, config, title, cost, prompt="", is_enabled=True):
    """Creates a channel point reward"""
    url = 'https://api.twitch.tv/helix/channel_points/custom_rewards'
    headers = {
        'Client-Id': config['streamer']['client_id'],
        'Authorization': f"Bearer {config['streamer']['access_token']}",
        'Content-Type': 'application/json'
    }
    
    payload = {
        'title': title,
        'cost': cost,
        'is_enabled': is_enabled,
        'is_user_input_required': True,  # Required for vote system
        'should_redemptions_skip_request_queue': False
    }
    
    if prompt:
        payload['prompt'] = prompt
    
    try:
        async with session.post(url, headers=headers, json=payload, params={'broadcaster_id': config['broadcaster_id']}) as response:
            if response.status == 200:
                data = await response.json()
                reward = data['data'][0]
                return {
                    'success': True,
                    'reward_id': reward['id'],
                    'title': reward['title'],
                    'cost': reward['cost']
                }
            else:
                error_text = await response.text()
                return {
                    'success': False,
                    'status': response.status,
                    'error': error_text
                }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


async def list_existing_rewards(session, config):
    """Lists existing rewards to check for duplicates"""
    url = 'https://api.twitch.tv/helix/channel_points/custom_rewards'
    headers = {
        'Client-Id': config['streamer']['client_id'],
        'Authorization': f"Bearer {config['streamer']['access_token']}"
    }
    params = {
        'broadcaster_id': config['broadcaster_id'],
        'only_manageable_rewards': 'false'
    }
    
    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                rewards = data.get('data', [])
                return rewards if rewards is not None else []
            else:
                print(f"⚠️  Konnte Rewards nicht abrufen: {response.status}")
                return []
    except Exception as e:
        print(f"Fehler beim Abrufen bestehender Rewards: {e}")
        import traceback
        traceback.print_exc()
        return []


async def delete_reward(session, config, reward_id):
    """Deletes a channel point reward"""
    url = 'https://api.twitch.tv/helix/channel_points/custom_rewards'
    headers = {
        'Client-Id': config['streamer']['client_id'],
        'Authorization': f"Bearer {config['streamer']['access_token']}"
    }
    params = {
        'broadcaster_id': config['broadcaster_id'],
        'id': reward_id
    }
    
    try:
        async with session.delete(url, headers=headers, params=params) as response:
            return response.status == 204
    except Exception:
        return False


async def create_vote_rewards():
    """Creates the three vote rewards"""
    print("=" * 60)
    print("🎮 Channel Point Rewards Creator")
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
        
        print("✓ Token ist gültig")
        print()
        
        # Check for existing rewards that match our names
        print("→ Prüfe bestehende Rewards...")
        existing_rewards = await list_existing_rewards(session, config)
        
        # Ensure existing_rewards is a list (defensive programming)
        if existing_rewards is None:
            existing_rewards = []
            print("⚠️  Konnte Rewards nicht abrufen, gehe von leerer Liste aus.")
        
        # Define rewards to create
        rewards_to_create = [
            {
                'title': 'Normal Vote',
                'cost': 100,
                'prompt': 'Welches Spiel möchtest du voten?',
                'config_key': 'normal_vote'
            },
            {
                'title': 'Super Vote',
                'cost': 1000,
                'prompt': 'Welches Spiel möchtest du voten?',
                'config_key': 'super_vote'
            },
            {
                'title': 'Ultra Vote',
                'cost': 2500,
                'prompt': 'Welches Spiel möchtest du voten?',
                'config_key': 'ultra_vote'
            }
        ]
        
        # Check if rewards exist and need to be deleted/recreated
        rewards_to_delete = []
        for reward_def in rewards_to_create:
            title_lower = reward_def['title'].lower()
            existing = next((r for r in existing_rewards if r['title'].lower() == title_lower), None)
            if existing:
                rewards_to_delete.append({
                    'title': existing['title'],
                    'id': existing['id'],
                    'config_key': reward_def['config_key']
                })
        
        if rewards_to_delete:
            print(f"⚠️  {len(rewards_to_delete)} Reward(s) mit gleichen Namen gefunden.")
            print("   Diese müssen gelöscht werden, um neue mit dem richtigen Client ID zu erstellen.")
            print()
            response = input("Möchtest du die bestehenden Rewards löschen und neu erstellen? (j/n): ").strip().lower()
            
            if response == 'j' or response == 'y' or response == 'ja' or response == 'yes':
                print()
                print("→ Lösche bestehende Rewards...")
                for reward in rewards_to_delete:
                    print(f"   Lösche '{reward['title']}'...")
                    if await delete_reward(session, config, reward['id']):
                        print(f"   ✓ '{reward['title']}' gelöscht")
                    else:
                        print(f"   ✗ Fehler beim Löschen von '{reward['title']}'")
                print()
            else:
                print("Abgebrochen. Bitte lösche die Rewards manuell im Twitch Dashboard.")
                return
        
        created_rewards = {}
        
        print("=" * 60)
        print("Rewards erstellen:")
        print("=" * 60)
        print()
        
        for reward_def in rewards_to_create:
            title = reward_def['title']
            
            print(f"→ Erstelle '{title}' ({reward_def['cost']} Points)...")
            result = await create_reward(
                session, 
                config, 
                title, 
                reward_def['cost'],
                reward_def['prompt']
            )
            
            if result['success']:
                print(f"✓ '{title}' erfolgreich erstellt!")
                print(f"   Reward ID: {result['reward_id']}")
                print(f"   Kosten: {result['cost']} Points")
                created_rewards[reward_def['config_key']] = result['reward_id']
            else:
                print(f"✗ Fehler beim Erstellen von '{title}':")
                print(f"   Status: {result.get('status', 'Unknown')}")
                error_msg = result.get('error', 'Unknown error')
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                print(f"   Fehler: {error_msg}")
            print()
        
        # Update config.json if rewards were created
        if created_rewards:
            print("=" * 60)
            print("📝 Aktualisiere config.json...")
            print("=" * 60)
            
            # Update config with new reward IDs
            for key, reward_id in created_rewards.items():
                config['rewards'][key] = reward_id
                print(f"✓ {key}: {reward_id}")
            
            save_config(config)
            print()
            print("✓ config.json wurde aktualisiert!")
            print()
            print("💡 Die neuen Reward IDs wurden in config.json gespeichert.")
            print("   Du kannst den Bot jetzt starten.")
        else:
            # Check if rewards were skipped (found but not deleted)
            if rewards_to_delete and not created_rewards:
                print("=" * 60)
                print("ℹ️  Alle Rewards existieren bereits.")
                print("=" * 60)
                print()
                print("Die bestehenden Reward IDs wurden verwendet.")
                print("Falls du neue Rewards erstellen möchtest, lösche die alten")
                print("zuerst im Twitch Creator Dashboard.")
            else:
                print("⚠️  Keine Rewards konnten erstellt werden.")


if __name__ == "__main__":
    try:
        asyncio.run(create_vote_rewards())
    except KeyboardInterrupt:
        print("\n→ Abgebrochen durch Benutzer.")
    except Exception as e:
        print(f"\n✗ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()

