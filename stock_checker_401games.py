import requests
import os
import json
import time

BASE_URL = (
    "https://store.401games.ca/collections/"
    "disney-lorcana-trading-card-game/products.json"
)

STORE_URL = "https://store.401games.ca/products/"
STATE_FILE = "stock_state_401games.json"

headers = {
    "User-Agent": "Mozilla/5.0"
}

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

if not DISCORD_WEBHOOK_URL:
    print("ERROR: Discord webhook secret is missing.")
    exit(1)

# Load previous stock state
try:
    with open(STATE_FILE, "r") as file:
        previous_state = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    previous_state = {}

first_run = len(previous_state) == 0

if first_run:
    print("FIRST RUN: Establishing 401 Games baseline.")
    print("Discord alerts will be suppressed for this run.")
    print()

current_state = {}

page = 1
total_products = 0
available_products = 0
sold_out_products = 0
alerts_sent = 0

while True:

    url = f"{BASE_URL}?limit=250&page={page}"

    print(f"Checking page {page}...")

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print(
                f"ERROR: Page {page} returned "
                f"{response.status_code}"
            )
            exit(1)

        data = response.json()
        products = data.get("products", [])

    except Exception as error:
        print(f"ERROR loading page {page}: {error}")
        exit(1)

    if not products:
        break

    for product in products:

        product_id = str(product.get("id"))
        title = product.get("title", "Disney Lorcana Product")
        handle = product.get("handle")
        image_url = None

        images = product.get("images", [])

        if images:
            first_image = images[0]

            if isinstance(first_image, dict):
                image_url = first_image.get("src")
            elif isinstance(first_image, str):
                image_url = first_image

    if image_url and image_url.startswith("//"):
        image_url = "https:" + image_url
        if not product_id or not handle:
            continue

        variants = product.get("variants", [])

        available_variants = [
            variant
            for variant in variants
            if variant.get("available", False)
        ]

        available = len(available_variants) > 0

        product_url = STORE_URL + handle

        # Save current state using Shopify product ID
        current_state[product_id] = available

        was_available = previous_state.get(product_id)

        total_products += 1

        if available:
            available_products += 1
        else:
            sold_out_products += 1

        # First baseline run sends no alerts.
        # Afterwards alert if:
        # 1. A brand-new product appears available, or
        # 2. A sold-out product becomes available.
        should_alert = (
            not first_run
            and available
            and was_available is not True
        )

        if not should_alert:
            continue

        # Get the lowest currently available variant price
        prices = []

        for variant in available_variants:
            try:
                prices.append(float(variant.get("price")))
            except (TypeError, ValueError):
                pass

        if prices:
            price_text = f"${min(prices):.2f} CAD"
        else:
            price_text = "Price unavailable"

        if was_available is False:
            heading = "♻️ Lorcana Restock Alert"
        else:
            heading = "🚨 Lorcana Canada Stock Alert"

        embed = {
    "title": title,
    "url": product_url,
    "description": (
        f"🏪 **401 Games**\n"
        f"💰 **{price_text}**\n"
        f"🟢 IN STOCK\n\n"
        f"🔗 **[View Product]({product_url})**"
    )
}

if image_url:
    embed["image"] = {
        "url": image_url
    }

message = {
    "content": f"{heading} 🇨🇦",
    "embeds": [embed]
}

discord_response = requests.post(
    DISCORD_WEBHOOK_URL,
    json=message,
    timeout=30
)

if discord_response.status_code in (200, 204):
    alerts_sent += 1
    print(f"Alert sent: {title}")
else:
    print(
        f"Discord error "
        f"{discord_response.status_code}: {title}"
    )

# Avoid rapid Discord webhook requests if
# several products restock simultaneously.
time.sleep(1)
print(f"Page {page}: {len(products)} products")

    if len(products) < 250:
        break

    page += 1

# Save current stock state
with open(STATE_FILE, "w") as file:
    json.dump(
        current_state,
        file,
        indent=2
    )

print()
print("--- 401 GAMES RESULTS ---")
print(f"Total products: {total_products}")
print(f"Available: {available_products}")
print(f"Sold out: {sold_out_products}")
print(f"Discord alerts sent: {alerts_sent}")
print("401 Games stock state updated.")
