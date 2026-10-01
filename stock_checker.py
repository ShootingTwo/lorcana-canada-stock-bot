import requests
import re
import os
import json
import time

SEARCH_URL = "https://hobbiesville.com/search?q=lorcana&type=product"
STATE_FILE = "stock_state.json"

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

current_state = {}
# If the state file is empty, this is our first baseline run.
first_run = len(previous_state) == 0

if first_run:
    print("FIRST RUN: Establishing stock baseline.")
    print("Discord alerts will be suppressed for this run.")
    print()

# Get Hobbiesville Lorcana search results
response = requests.get(
    SEARCH_URL,
    headers=headers,
    timeout=30
)

if response.status_code != 200:
    print("ERROR: Could not reach Hobbiesville.")
    exit(1)

html = response.text

urls = re.findall(
    r'\\"url\\":\\"(\\/products\\/[^"]+)',
    html
)

urls = list(dict.fromkeys(urls))

print(f"Lorcana products found: {len(urls)}")
print()

for url in urls:

    url = (
        url
        .replace("\\u0026", "&")
        .replace("\\/", "/")
        .split("?")[0]
    )

    product_url = "https://www.hobbiesville.com" + url
    json_url = product_url + ".js"

    try:
        response = requests.get(
            json_url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print("Could not check:", product_url)
            continue

        product = response.json()

        title = product.get(
            "title",
            "Disney Lorcana Product"
        )

        variants = product.get("variants", [])

        available = any(
            variant.get("available", False)
            for variant in variants
        )

        prices = [
            variant.get("price")
            for variant in variants
            if variant.get("price") is not None
        ]

        if prices:
            price = min(prices) / 100
            price_text = f"${price:.2f} CAD"
        else:
            price_text = "Price unavailable"

        is_preorder = "pre-order" in product_url.lower()

        current_state[product_url] = available

        was_available = previous_state.get(product_url)

        print(title)
        print("Available:", available)
        print("Previously:", was_available)

        # Alert only when:
        # 1. Product is new and available
        # 2. Product was sold out and becomes available
        should_alert = (
            not first_run
            and available
            and was_available is not True
    )
        )

        if should_alert:

            if is_preorder:
                status = "🔵 PREORDER AVAILABLE"
            else:
                status = "🟢 IN STOCK"

            if was_available is False:
                heading = "♻️ Lorcana Restock Alert"
            else:
                heading = "🚨 Lorcana Canada Stock Alert"

            message = {
                "content": (
                    f"{heading} 🇨🇦\n\n"
                    f"**{title}**\n"
                    f"🏪 Hobbiesville\n"
                    f"💰 {price_text}\n"
                    f"{status}\n"
                    f"🔗 {product_url}"
                )
            }

            discord_response = requests.post(
                DISCORD_WEBHOOK_URL,
                json=message,
                timeout=30
            )

            print(
                "Discord response:",
                discord_response.status_code
            )

        print()

        # Avoid rapid requests to Hobbiesville
        time.sleep(1)

    except Exception as error:
        print("ERROR:", error)
        print()

# Save current availability
with open(STATE_FILE, "w") as file:
    json.dump(
        current_state,
        file,
        indent=2
    )

print("Stock state updated.")
