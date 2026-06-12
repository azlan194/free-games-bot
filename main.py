import json
import os
import requests
import time
# from dotenv import load_dotenv

# --- INITIALIZE ENVIRONMENT VARIABLES ---
# load_dotenv()  # This looks for a local .env file and l>

# Secure variables pulled from GitHub environments
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
ITAD_API_KEY = os.environ.get("ITAD_API_KEY")
HISTORY_FILE = "posted_games.txt"

def send_to_discord(content, embeds=None):
    """Sends a formatted text payload and optional embeds to the Discord Webhook."""
    if not DISCORD_WEBHOOK:
        print("Error: DISCORD_WEBHOOK environment variable is missing.")
        return

    data = {"content": content}
    if embeds:
        data["embeds"] = embeds

    try:
        response = requests.post(DISCORD_WEBHOOK, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message to Discord: {e}")

def get_all_free_games():
    if not ITAD_API_KEY:
        print("Error: ITAD_API_KEY environment variable is missing.")
        return

    already_posted = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            already_posted = set(line.strip() for line in f if line.strip())

    deals_url = "https://api.isthereanydeal.com/deals/v2"
    
    # Ensure the API key is stripped of any accidental newlines/spaces from the GitHub Secret
    headers = {
        "ITAD-API-Key": ITAD_API_KEY.strip(),
        "Content-Type": "application/json",
        "User-Agent": "FreeGameDiscordBot/1.0"
    }
    
    # Using the verified stable filter to grab 100% price cuts
    payload = {
        "limit": 200,
        "filter": {
            "cut": {"min": 99, "max": 100},
            "price": {"min": 0, "max": 0}
        }
    }
    
    try:
        response = requests.get(deals_url, headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()
        games = response_json.get("list", [])
        current_free_games = []
        new_deals_to_post = []

        for game in games:
            title = game.get("title")
            game_id = game.get("id")

            # Extract the thumbnail asset
            assets = game.get("assets", {})
            thumbnail_url = assets.get("banner600")

            game_deals = [game.get("deal")]

            for deal in game_deals:
                price_info = deal.get("price", {})
                regular_info = deal.get("regular", {})

                current_price = price_info.get("amount", 1.0)
                regular_price = regular_info.get("amount", 0.0)

                # Double-check logic: Current price is $0, but it normally costs money
                if current_price == 0.0 and regular_price > 0.0:
                    shop = deal.get("shop", {})
                    store_name = shop.get("name", "Unknown Store")
                    shop_id = shop.get("id", "unknown")
                    deal_url = deal.get("url")

                    unique_id = f"{shop_id}_{game_id}"
                    current_free_games.append(unique_id)

                    if unique_id not in already_posted:
                        new_deals_to_post.append({
                            "title": title,
                            "store": store_name,
                            "original": regular_price,
                            "url": deal_url,
                            "thumbnail": thumbnail_url # Save the thumbnail to our list
                        })

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for uid in current_free_games:
                f.write(f"{uid}\n")

        if not new_deals_to_post:
            print("No brand new free games to post today via IsThereAnyDeal.")
            return

        print(f"Found {len(new_deals_to_post)} new free deals! Bundling for Discord...")

       # Dictionary mapping storefront names to high-quality public icon URLs
        STORE_ICONS = {
            "steam": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/500px-Steam_icon_logo.svg.png",
            "epic game store": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Epic_Games_logo.svg/500px-Epic_Games_logo.svg.png",
            "gog": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/GOG.com_logo.svg/500px-GOG.com_logo.svg.png",
            "microsoft store": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Microsoft_logo.svg/500px-Microsoft_logo.svg.png",
            "humble store": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Humble_Bundle_H_logo_red.svg/500px-Humble_Bundle_H_logo_red.svg.png"
        }
 
        # 1. Group the games into chunks of 8 to respect Discord's strict 10-embed limit per message
        embed_chunks = []
        current_chunk = []

        for game in new_deals_to_post:
            # Build the base structured embed card
            embed = {
                "title": game['title'],
                "description": (
                    f"🏬 **Platform:** {game['store']}\n"
                    f"💰 **Price:** ~~${game['original']:.2f}~~ -> **FREE!**\n"
                    f"🔗 [Claim Game Here]({game['url']})"
                )
            }
            
            # 1. Attach the large game banner to the bottom
            if game['thumbnail']:
                embed["image"] = {"url": game['thumbnail']}
                
            # 2. Attach the small store logo to the top right
            store_key = game['store'].lower()
            if store_key in STORE_ICONS:
                embed["thumbnail"] = {"url": STORE_ICONS[store_key]}
                
            current_chunk.append(embed)

            # If we reach our bundle limit, save this batch and start a new one
            if len(current_chunk) == 10:
                embed_chunks.append(current_chunk)
                current_chunk = []

            # Catch any remaining games left over
        if current_chunk:
            embed_chunks.append(current_chunk)

            # 3. Transmit the bundles to your Discord server
        for i, chunk in enumerate(embed_chunks):
            # Include the main alert banner only on the very first notification bundle
            content = f"🎮 **New {len(new_deals_to_post)} Free Games Found (via IsThereAnyDeal)!** 🎮\n" + ("=" * 45) if i == 0 else ""

            # This sends all games in the chunk inside a single webhook request payload
            send_to_discord(content, embeds=chunk)

            # Anti-rate-limit safety pause between distinct batch messages
            time.sleep(2)

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if ITAD_API_KEY and ITAD_API_KEY in error_msg:
            error_msg = error_msg.replace(ITAD_API_KEY, "[REDACTED_API_KEY]")

        send_to_discord(f"⚠️ **Error fetching data from IsThereAnyDeal:** {error_msg}")

if __name__ == "__main__":
    get_all_free_games()


