import os
import requests
import time

# Secure variables pulled from GitHub environments
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
ITAD_API_KEY = os.environ.get("ITAD_API_KEY")
HISTORY_FILE = "posted_games.txt"

def send_to_discord(content):
    """Sends a formatted text payload to the Discord Webhook."""
    if not DISCORD_WEBHOOK:
        print("Error: DISCORD_WEBHOOK environment variable is missing.")
        return
    data = {"content": content}
    try:
        response = requests.post(DISCORD_WEBHOOK, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message to Discord: {e}")

def get_all_free_games():
    if not ITAD_API_KEY:
        print("Error: ITAD_API_KEY environment variable is missing.")
        return

    # 1. Load previously posted history
    already_posted = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            already_posted = set(line.strip() for line in f if line.strip())

    # 🔑 FIXED: Exact endpoint path from the documentation
    deals_url = "https://api.isthereanydeal.com/deals/v2"
    
    # 🔑 FIXED: Filter parameters to narrow down only to 100% off deals across up to 200 listings
    query_params = {
        "key": ITAD_API_KEY,
        "country": "US",
        "limit": 200,
        "filter": '{"cut":{"min":100,"max":100}}'
    }
    
    try:
        response = requests.get(deals_url, params=query_params)
        response.raise_for_status()
        
        # 🔑 FIXED: ITAD v2 returns a flat list of game objects
        games = response.json()
        
        current_free_games = []
        new_deals_to_post = []

        for game in games:
            title = game.get("title")
            game_id = game.get("id")
            game_deals = game.get("deals", [])
            
            # Iterate through the specific store deals for this game
            for deal in game_deals:
                price_info = deal.get("price", {})
                regular_info = deal.get("regular", {})
                
                current_price = price_info.get("amount", 1.0)
                regular_price = regular_info.get("amount", 0.0)
                
                # Double-check that it is free and normally costs money
                if current_price == 0.0 and regular_price > 0.0:
                    shop = deal.get("shop", {})
                    store_name = shop.get("name", "Unknown Store")
                    shop_id = shop.get("id", "unknown")
                    deal_url = deal.get("url") 
                    
                    # Create a unique identifier combining store ID and unique game uuid
                    unique_id = f"{shop_id}_{game_id}"
                    current_free_games.append(unique_id)

                    if unique_id not in already_posted:
                        new_deals_to_post.append({
                            "title": title,
                            "store": store_name,
                            "original": regular_price,
                            "url": deal_url
                        })

        # 3. Save current free list into state history
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for uid in current_free_games:
                f.write(f"{uid}\n")

        # 4. If nothing is new, shut down gracefully
        if not new_deals_to_post:
            print("No brand new free games to post today via IsThereAnyDeal.")
            return

        print(f"Found {len(new_deals_to_post)} new free deals on ITAD! Sending...")
        
        message_chunk = "🎮 **New 100% Free Games Found (via IsThereAnyDeal)!** 🎮\n" + ("=" * 45) + "\n\n"
        
        for game in new_deals_to_post:
            game_text = (
                f"**{game['title']}**\n"
                f"🏬 **Platform:** {game['store']}\n"
                f"💰 **Price:** ~~${game['original']:.2f}~~ -> **FREE!**\n"
                f"🔗 [Claim Game Here]({game['url']})\n"
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
        # Safe error handling: strips out the API key from the log string if it prints out
        error_msg = str(e)
        if ITAD_API_KEY and ITAD_API_KEY in error_msg:
            error_msg = error_msg.replace(ITAD_API_KEY, "[REDACTED_API_KEY]")
            
        send_to_discord(f"⚠️ **Error fetching data from IsThereAnyDeal:** {error_msg}")

if __name__ == "__main__":
    get_all_free_games()
