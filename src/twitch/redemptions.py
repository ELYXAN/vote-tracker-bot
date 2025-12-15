"""
Twitch Channel Points Redemptions Handling
"""
import asyncio
import aiohttp
from src.auth.token_manager import ensure_valid_token
from src.utils.storage import save_processed_id
from src.utils.colors import success, error, warning, info, highlight


# Globale Queue für Vote-Verarbeitung
vote_queue = asyncio.Queue()

# Globaler Cache
cache = {
    'games_list': [],
    'processed_ids': set(),
    'last_cache_update': 0,
    'cache_validity': 300,
    'worksheet': None,
    'spreadsheet': None,
    'invalid_reward_ids': set()  # Reward IDs die 403 Fehler verursachen
}


async def listen_to_redemptions(config):
    """Überwacht Channel Point Redemptions"""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                if not await ensure_valid_token(session, config, 'streamer'):
                    print("Streamer Token ungültig. Warte 30 Sekunden...")
                    await asyncio.sleep(30)
                    continue

                url = 'https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions'
                headers = {
                    'Client-Id': config['streamer']['client_id'],
                    'Authorization': f"Bearer {config['streamer']['access_token']}"
                }

                rewards_to_check = []
                if config['rewards'].get('normal_vote'):
                    rewards_to_check.append(('normal_vote', config['rewards']['normal_vote']))
                if config['rewards'].get('super_vote'):
                    rewards_to_check.append(('super_vote', config['rewards']['super_vote']))
                if config['rewards'].get('ultra_vote'):
                    rewards_to_check.append(('ultra_vote', config['rewards']['ultra_vote']))

                # Check all rewards in parallel for faster detection
                async def check_reward(vote_type, reward_id):
                    if reward_id in cache['invalid_reward_ids']:
                        return []
                    
                    params = {
                        'broadcaster_id': config['broadcaster_id'],
                        'reward_id': reward_id,
                        'status': 'UNFULFILLED',
                        'first': 20
                    }
                    
                    try:
                        async with session.get(url, headers=headers, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                redemptions = data.get('data', [])
                                result = []
                                for redemption in redemptions:
                                    vote_id = redemption['id']
                                    if vote_id not in cache['processed_ids']:
                                        user = redemption['user_name']
                                        user_input = redemption.get('user_input', '').strip()
                                        if user_input:
                                            result.append({
                                                'user': user,
                                                'game': user_input,
                                                'vote_id': vote_id,
                                                'reward_id': reward_id,
                                                'vote_type': vote_type
                                            })
                                return result
                            elif response.status == 403:
                                cache['invalid_reward_ids'].add(reward_id)
                            return []
                    except Exception as e:
                        print(f"✗ Fehler beim Prüfen von {vote_type}: {str(e)}")
                        return []
                
                # Check all rewards in parallel
                tasks = [check_reward(vt, rid) for vt, rid in rewards_to_check]
                results = await asyncio.gather(*tasks)
                
                # Process all found redemptions
                for redemptions in results:
                    for redemption_data in redemptions:
                        vote_type_upper = redemption_data['vote_type'].upper()
                        user = redemption_data['user']
                        game = redemption_data['game']
                        print(info(f"[{vote_type_upper}] Neuer Vote von") + f" {highlight(user)}: {highlight(game)}")
                        await vote_queue.put(redemption_data)

                await asyncio.sleep(1)  # Reduced from 5s to 1s for faster response

            except Exception as e:
                print(f"Schwerwiegender Fehler im Redemption-Listener: {str(e)}")
                await asyncio.sleep(10)


async def fulfill_vote(session, config, reward_id, vote_id):
    """Markiert einen Vote als erfüllt"""
    redeem_url = 'https://api.twitch.tv/helix/channel_points/custom_rewards/redemptions'
    headers = {
        'Client-Id': config['streamer']['client_id'],
        'Authorization': f"Bearer {config['streamer']['access_token']}",
        'Content-Type': 'application/json'
    }

    params = {
        'broadcaster_id': config['broadcaster_id'],
        'reward_id': reward_id,
        'id': vote_id
    }

    payload = {'status': 'FULFILLED'}

    try:
        async with session.patch(redeem_url, headers=headers, json=payload, params=params) as response:
            if response.status == 200:
                print(success(f"Vote {vote_id} erfolgreich als FULFILLED markiert."))
                cache['processed_ids'] = save_processed_id(cache['processed_ids'], vote_id)
            elif response.status == 400 and "redemption is already" in await response.text():
                print(info(f"Vote {vote_id} war bereits als FULFILLED/CANCELED markiert."))
                cache['processed_ids'] = save_processed_id(cache['processed_ids'], vote_id)
            elif response.status == 403:
                print(error(f"Fehler beim Erfüllen von Vote {vote_id} (403 Forbidden)."))
            else:
                print(error(f"Fehler beim Erfüllen des Votes {vote_id}: {response.status}"))
    except Exception as e:
        print(f"Exception beim Erfüllen des Votes {vote_id}: {str(e)}")
