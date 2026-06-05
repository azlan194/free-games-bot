import os
import requests
import time

# This pulls the secret URL safely from the cloud environment
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

def send_to_discord(content):
    """Sends a formatted text payload to the Discord Webhook."""
    if not WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK environment variable is missing.")
        return
    data = {"content": content}
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message to Discord: {e}")

def get_all_free_games():
    stores_url = "https://www.cheapshark.com/api/1.0/stores"
    deals_url = "https://www.cheapshark.com/api/1.0/deals?upperPrice=0"
    
    try:
        store_response = requests.get(stores_url)
        store_response.raise_for_status()
        stores_data = store_response.json()
        store_map = {store['storeID']: store['storeName'] for store in stores_data}
        
        deals_response = requests.get(deals_url)
        deals_response.raise_for_status()
        deals = deals_response.json()
        
        valid_deals = [game for game in deals if float(game.get('normalPrice', 0)) > 0.00]

        if not valid_deals:
            send_to_discord("😭 No 100% free games found across any platforms right now.")
            return

        print(f"Found {len(valid_deals)} free games. Sending to Discord...")
        
        message_chunk = "🎮 **Currently 100% Free Games Across All Platforms** 🎮\n" + ("=" * 45) + "\n\n"
        
        for game in valid_deals:
            title = game.get('title')
            normal_price = float(game.get('normalPrice', 0))
            store_name = store_map.get(game.get('storeID'), "Unknown Store")
            link = f"https://www.cheapshark.com/redirect?dealID={game.get('dealID')}"
            
            game_text = (
                f"**{title}**\n"
                f"🏬 **Platform:** {store_name}\n"
                f"💰 **Price:** ~~${normal_price:.2f}~~ -> **FREE!**\n"
                f"🔗 [Claim Game Here]({link})\n"
                f"---------------------------------------------\n"
            )
            
            if len(message_chunk) + len(game_text) > 1900:
                send_to_discord(message_chunk)
                message_chunk = ""
                time.sleep(1) 
                
            message_chunk += game_text
            
        if message_chunk:
            send_to_discord(message_chunk)
            
    except requests.exceptions.RequestException as e:
        send_to_discord(f"⚠️ **Error fetching data from CheapShark:** {e}")

if __name__ == "__main__":
    get_all_free_games()