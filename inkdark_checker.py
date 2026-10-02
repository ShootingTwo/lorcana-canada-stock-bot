import json
import os
import time

import requests


DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
STATE_FILE = "inkdark_state.json"

SET_NAME = "into the inkdark"

STORES = [
    {
        "name": "Kanzen",
        "base_url": "https://kanzengames.com",
        "feed": "/collections/disney-lorcana/products.json",
    },
    {
        "name": "Amazing Stories",
        "base_url": "https://amazingstoriesgames.ca",
        "feed": "/products.json",
    },
    {
        "name": "Wizard's Tower",
        "base_url": "https://store.wizardtower.com",
        "feed": "/products.json",
    },
    {
        "name": "Board Game Bliss",
        "base_url": "https://www.boardgamebliss.com",
        "feed": "/products.json",
    },
    {
        "name": "Manta Trading",
        "base_url": "https://mantatrading.com",
        "feed": "/products.json",
    },
    {
        "name": "Heroes World",
        "base_url": "https://heroesworld.ca",
        "feed": "/collections/disney-lorcana/products.json",
    },
    {
        "name": "Claw Me Baby",
        "base_url": "https://www.clawmebaby.ca",
        "feed": "/collections/disney-lorcana/products.json",
    },
    {
        "name": "Fantasy Forged",
        "base_url": "https://www.fantasyforged.ca",
        "feed": "/products.json",
    },
    {
        "name": "Enter the Battlefield",
        "base_url": "https://enterthebattlefield.ca",
        "feed": "/products.json",
    },
    {
        "name": "Game Shack",
        "base_url": "https://www.gameshack.ca",
        "feed": "/collections/disney-lorcana/products.json",
    },
    {
        "name": "Gotham Central Comics",
        "base_url": "https://www.gothamcentralcomics.com",
        "feed": "/products.json",
    },
    {
        "name": "Hope Club",
        "base_url": "https://hopeclubshop.ca",
        "feed": "/products.json",
    },
    {
        "name": "Le Coin du Jeu",
        "base_url": "https://www.lecoindujeu.ca",
        "feed": "/collections/disney-lorcana/products.json",
    },
    {
        "name": "The Mythic Store",
        "base_url": "https://themythicstore.com",
        "feed": "/collections/disney-lorcana/products.json",
    },
]


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, sort_keys=True)


def normalize_text(text):
    return (
        str(text or "")
        .lower()
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )


def is_target_product(title):
    title_lower = normalize_text(title)

    if SET_NAME not in title_lower:
        return False

    booster_box_terms = [
        "booster box",
        "booster display",
    ]

    trove_terms = [
        "illumineer's trove",
        "illumineers trove",
        "illumineer trove",
    ]

    return (
        any(term in title_lower for term in booster_box_terms)
        or any(term in title_lower for term in trove_terms)
    )


def product_is_available(product):
    variants = product.get("variants", [])
    return any(bool(variant.get("available")) for variant in variants)


def get_lowest_available_price(product):
    prices = []

    for variant in product.get("variants", []):
        if not variant.get("available"):
            continue

        try:
            prices.append(float(variant.get("price")))
        except (TypeError, ValueError):
            pass

    if not prices:
        return None

    return min(prices)


def get_display_price(product):
    available_price = get_lowest_available_price(product)

    if available_price is not None:
        return available_price

    prices = []

    for variant in product.get("variants", []):
        try:
            prices.append(float(variant.get("price")))
        except (TypeError, ValueError):
            pass

    if not prices:
        return None

    return min(prices)


def get_image(product):
    image = product.get("image")

    if isinstance(image, dict):
        src = image.get("src")
        if src:
            if src.startswith("//"):
                return "https:" + src
            return src

    images = product.get("images", [])

    if images:
        first_image = images[0]

        if isinstance(first_image, dict):
            src = first_image.get("src")
            if src:
                if src.startswith("//"):
                    return "https:" + src
                return src

    return None


def is_preorder(title):
    title_lower = normalize_text(title)

    return (
        "pre-order" in title_lower
        or "preorder" in title_lower
        or "pre order" in title_lower
    )


def send_discord_alert(
    store_name,
    title,
    product_url,
    image_url,
    price,
    available,
    event_type,
):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL is not configured.")
        return False

    if event_type == "new":
        heading = "🆕 NEW INTO THE INKDARK LISTING"
        description = "A new qualifying product listing has appeared."

    elif available and is_preorder(title):
        heading = "🔵 INTO THE INKDARK PREORDER AVAILABLE"
        description = "This product is now available to preorder."

    else:
        heading = "🟢 INTO THE INKDARK AVAILABLE"
        description = "This product is now available to order."

    fields = [
        {
            "name": "Store",
            "value": store_name,
            "inline": True,
        },
        {
            "name": "Status",
            "value": "Available" if available else "Not currently available",
            "inline": True,
        },
    ]

    if price is not None:
        fields.append(
            {
                "name": "Price",
                "value": f"${price:.2f} CAD",
                "inline": True,
            }
        )

    embed = {
        "title": title,
        "url": product_url,
        "description": description,
        "fields": fields,
    }

    if image_url:
        embed["thumbnail"] = {"url": image_url}

    payload = {
        "content": heading,
        "embeds": [embed],
    }

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        print(f"Discord alert sent: {store_name} - {title}")
        return True

    except requests.RequestException as error:
        print(f"Discord alert failed: {error}")
        return False


def fetch_store_products(store):
    products = []
    page = 1

    while True:
        url = store["base_url"] + store["feed"]

        try:
            response = requests.get(
                url,
                params={
                    "limit": 250,
                    "page": page,
                },
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/154.0 Safari/537.36"
                    )
                },
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

        except (requests.RequestException, ValueError) as error:
            print(
                f"Could not fetch {store['name']} page {page}: {error}"
            )
            break

        page_products = data.get("products", [])

        if not page_products:
            break

        products.extend(page_products)

        if len(page_products) < 250:
            break

        page += 1
        time.sleep(0.5)

    return products


def main():
    previous_state = load_state()
    current_state = previous_state.copy()

    products_checked = 0
    matches_found = 0
    alerts_sent = 0

    for store in STORES:
        print(f"\nChecking {store['name']}...")

        products = fetch_store_products(store)
        products_checked += len(products)

        print(f"Products retrieved: {len(products)}")

        for product in products:
            title = product.get("title", "")

            if not is_target_product(title):
                continue

            matches_found += 1

            product_id = str(product.get("id", ""))
            handle = product.get("handle", "")

            if not product_id or not handle:
                continue

            state_key = f"{store['name']}::{product_id}"
            product_url = (
                store["base_url"].rstrip("/")
                + "/products/"
                + handle
            )

            available = product_is_available(product)               
            price = get_display_price(product)
            image_url = get_image(product)

            old_entry = previous_state.get(state_key)

            new_entry = {
                "store": store["name"],
                "product_id": product_id,
                "title": title,
                "url": product_url,
                "available": available,
            }

            if price is not None:
                new_entry["price"] = price

            current_state[state_key] = new_entry

            if old_entry is None:
                alert_sent = send_discord_alert(
                    store["name"],
                    title,
                    product_url,
                    image_url,
                    price,
                    available,
                    "new",
                )

                if alert_sent:
                    alerts_sent += 1
                else:
                    current_state.pop(state_key, None)

                continue

            was_available = bool(old_entry.get("available"))

            if available and not was_available:
                alert_sent = send_discord_alert(
                    store["name"],
                    title,
                    product_url,
                    image_url,
                    price,
                    available,
                    "available",
                )

                if alert_sent:
                    alerts_sent += 1
                else:
                    current_state[state_key]["available"] = False

    save_state(current_state)

    print("\n--- Into the Inkdark Monitor Summary ---")
    print(f"Stores checked: {len(STORES)}")
    print(f"Products checked: {products_checked}")
    print(f"Target products found: {matches_found}")
    print(f"Discord alerts sent: {alerts_sent}")
    print(f"Products tracked: {len(current_state)}")


if __name__ == "__main__":
    main()
