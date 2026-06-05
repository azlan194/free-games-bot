import os
import requests
import time

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
HISTORY_FILE = "posted_games.txt"

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
    # 1. Load previously posted games from the history file
    already_posted = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            already_posted = set(line.strip() for line in f if line.strip())

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

        # Keep track of everything currently free to update our history file
        current_free_games = []
        new_deals_to_post = []

        for game in valid_deals:
            title = game.get('title')
            store_id = game.get('storeID')
            # Create a unique identifier combining platform and title
            unique_id = f"{store_id}_{title}"
            current_free_games.append(unique_id)

            # Only post if we haven't seen it recently
            if unique_id not in already_posted:
                new_deals_to_post.append(game)

        # 2. Update the history file for tomorrow's run
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for uid in current_free_games:
                f.write(f"{uid}\n")

        # 3. If there are no *new* deals, stop here
        if not new_deals_to_post:
            print("No new free games to post today. (Any active free games were already posted).")
            return

        print(f"Found {len(new_deals_to_post)} new free games. Sending to Discord...")
        
        message_chunk = "🎮 **New 100% Free Games Found!** 🎮\n" + ("=" * 45) + "\n\n"
        
        for game in new_deals_to_post:
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
