import requests
import os
import json
import time
from bs4 import BeautifulSoup

STATE_FILE = "stock_state_ebgames.json"

PRODUCTS = [
    "https://www.ebgames.ca/shop/900402-lorcana-hyperia-city-booster-box-214925?attribute_values=1",
    "https://www.ebgames.ca/shop/900404-lorcana-hyperia-city-trove-214927"
]

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-CA,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1"
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


# Preserve everything already known.
current_state = previous_state.copy()

first_run = len(previous_state) == 0

if first_run:
    print("FIRST RUN: Establishing EB Games baseline.")
    print("Discord alerts will be suppressed for this run.")
    print()


def find_product_data(html):
    soup = BeautifulSoup(html, "html.parser")

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:
        if not script.string:
            continue

        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(data, dict):
            candidates = [data]
        elif isinstance(data, list):
            candidates = data
        else:
            continue

        for item in candidates:
            if (
                isinstance(item, dict)
                and item.get("@type") == "Product"
            ):
                return item

    return None


for product_url in PRODUCTS:

    try:
        response = requests.get(
            product_url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print(
                f"Could not check {product_url}: "
                f"HTTP {response.status_code}"
            )
            continue

        product = find_product_data(response.text)

        if not product:
            print(
                "ERROR: Product structured data "
                f"not found: {product_url}"
            )
            continue


        title = product.get(
            "name",
            "Disney Lorcana Hyperia City Product"
        )

        sku = str(product.get("sku", ""))

        image_url = product.get("image")

        if isinstance(image_url, list):
            image_url = (
                image_url[0]
                if image_url
                else None
            )


        offers = product.get("offers", {})

        if isinstance(offers, list):
            offers = (
                offers[0]
                if offers
                else {}
            )

        availability_url = str(
            offers.get("availability", "")
        )

        availability = (
            availability_url
            .rstrip("/")
            .split("/")[-1]
            .lower()
        )

        available = availability in {
            "instock",
            "limitedavailability",
            "preorder"
        }


        price = offers.get("price")
        currency = offers.get(
            "priceCurrency",
            "CAD"
        )

        try:
            price_text = (
                f"${float(price):.2f} {currency}"
            )
        except (TypeError, ValueError):
            price_text = "Price unavailable"


        state_key = sku if sku else product_url

        was_available = previous_state.get(state_key)

        current_state[state_key] = available


        print(title)
        print("SKU:", sku)
        print("Availability:", availability)
        print("Available:", available)
        print("Previously:", was_available)
        print("Price:", price_text)


        should_alert = (
            not first_run
            and available
            and was_available is not True
        )

        if should_alert:

            if availability == "preorder":
                status = "🔵 PREORDER AVAILABLE"
            else:
                status = "🟢 IN STOCK"

            if was_available is False:
                heading = "♻️ Hyperia City Restock Alert"
            else:
                heading = "🚨 Hyperia City Canada Stock Alert"

            embed = {
                "title": title,
                "url": product_url,
                "description": (
                    f"🏪 **EB Games Canada**\n"
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

            try:
                discord_response = requests.post(
                    DISCORD_WEBHOOK_URL,
                    json=message,
                    timeout=30
                )

                if discord_response.status_code in (200, 204):
                    print(f"Alert sent: {title}")

                else:
                    if was_available is None:
                        current_state.pop(
                            state_key,
                            None
                        )
                    else:
                        current_state[state_key] = (
                            was_available
                        )

                    print(
                        "Discord error "
                        f"{discord_response.status_code}: "
                        f"{title}"
                    )

                time.sleep(1)

            except Exception as error:
                if was_available is None:
                    current_state.pop(
                        state_key,
                        None
                    )
                else:
                    current_state[state_key] = (
                        was_available
                    )

                print(
                    "ERROR sending Discord alert: "
                    f"{error}"
                )


        print()
        time.sleep(1)


    except Exception as error:
        print(
            f"ERROR checking {product_url}: "
            f"{error}"
        )
        print()


with open(STATE_FILE, "w") as file:
    json.dump(
        current_state,
        file,
        indent=2
    )


print()
print("--- EB GAMES RESULTS ---")
print(f"Products monitored: {len(PRODUCTS)}")
print(f"Products tracked: {len(current_state)}")
print("EB Games stock state updated.")
