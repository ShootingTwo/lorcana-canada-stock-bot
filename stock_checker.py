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


# Start with everything we already know about.
#
# Hobbiesville's search page does not always return the exact same
# set of products on every request. Starting with the previous state
# prevents temporarily missing products from being forgotten and
# incorrectly treated as brand-new products when they reappear.
current_state = previous_state.copy()


# If the state file is empty, this is our first baseline run.
first_run = len(previous_state) == 0

if first_run:
    print("FIRST RUN: Establishing Hobbiesville baseline.")
    print("Discord alerts will be suppressed for this run.")
    print()


# Get Hobbiesville Lorcana search results
try:
    response = requests.get(
        SEARCH_URL,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        print(
            "ERROR: Could not reach Hobbiesville. "
            f"HTTP {response.status_code}"
        )
        exit(1)

except Exception as error:
    print(f"ERROR reaching Hobbiesville: {error}")
    exit(1)


html = response.text

urls = re.findall(
    r'\\"url\\":\\"(\\/products\\/[^"]+)',
    html
)

urls = list(dict.fromkeys(urls))

print(f"Lorcana products found in this search: {len(urls)}")
print(f"Products already known: {len(previous_state)}")
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

            # Because current_state began as a copy of previous_state,
            # the previous status is automatically preserved.
            continue


        product = response.json()

        title = product.get(
            "title",
            "Disney Lorcana Product"
        )


        # Find the product image
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


        variants = product.get("variants", [])

        available_variants = [
            variant
            for variant in variants
            if variant.get("available", False)
        ]

        available = len(available_variants) > 0


        # Use the lowest currently available price.
        # If nothing is available, fall back to all variants
        # for informational purposes.
        price_variants = (
            available_variants
            if available_variants
            else variants
        )

        prices = []

        for variant in price_variants:
            try:
                variant_price = variant.get("price")

                if variant_price is not None:
                    prices.append(float(variant_price))

            except (TypeError, ValueError):
                pass

        if prices:
            price = min(prices) / 100
            price_text = f"${price:.2f} CAD"
        else:
            price_text = "Price unavailable"


        # Determine preorder status from the current product title.
        #
        # We intentionally do NOT use the URL because Hobbiesville
        # may retain "-pre-order" in an old product URL even after
        # the product has become normal in-stock inventory.
        is_preorder = (
            "pre-order" in title.lower()
            or "preorder" in title.lower()
        )


        # IMPORTANT: Read the previous status BEFORE updating
        # current_state.
        was_available = previous_state.get(product_url)

        current_state[product_url] = available


        print(title)
        print("Available:", available)
        print("Previously:", was_available)


        # Alert when:
        # 1. An existing sold-out product becomes available, or
        # 2. A genuinely brand-new product appears and is available.
        #
        # The first baseline run does not send alerts.
        should_alert = (
            not first_run
            and available
            and was_available is not True
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


            # Build the Discord embed
            embed = {
                "title": title,
                "url": product_url,
                "description": (
                    f"🏪 **Hobbiesville**\n"
                    f"💰 **{price_text}**\n"
                    f"{status}\n\n"
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


            # Send Discord alert
            try:
                discord_response = requests.post(
                    DISCORD_WEBHOOK_URL,
                    json=message,
                    timeout=30
                )

                if discord_response.status_code in (200, 204):
                    print(f"Alert sent: {title}")

                else:
                    # Do NOT record the new availability if
                    # Discord failed. This allows the bot to
                    # try sending the alert again next run.
                    if was_available is None:
                        current_state.pop(product_url, None)
                    else:
                        current_state[product_url] = was_available

                    print(
                        f"Discord error "
                        f"{discord_response.status_code}: "
                        f"{title}"
                    )

                # Avoid rapid Discord webhook requests if
                # several products restock simultaneously.
                time.sleep(1)

            except Exception as error:
                # Preserve the previous state if the Discord
                # request itself fails so the bot can retry.
                if was_available is None:
                    current_state.pop(product_url, None)
                else:
                    current_state[product_url] = was_available

                print(
                    f"ERROR sending Discord alert: {error}"
                )


        print()

        # Avoid rapid requests to Hobbiesville.
        time.sleep(1)


    except Exception as error:
        print(f"ERROR checking {product_url}: {error}")

        # current_state already contains the previous value
        # for known products, so nothing needs to be removed.
        print()


# Save the accumulated availability state.
#
# Products temporarily absent from Hobbiesville's search results
# remain in this file with their last known status.
with open(STATE_FILE, "w") as file:
    json.dump(
        current_state,
        file,
        indent=2
    )


print()
print("--- HOBBIESVILLE RESULTS ---")
print(f"Products found this run: {len(urls)}")
print(f"Total products tracked: {len(current_state)}")
print("Hobbiesville stock state updated.")
