import json
import os
import time
import xml.etree.ElementTree as ET

import requests


DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
STATE_FILE = "inkdark_state.json"

SET_NAME = "into the inkdark"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0 Safari/537.36"
    )
}

STORES = [
    {
        "name": "Hobbiesville",
        "base_url": "https://www.hobbiesville.com",
        "feed": "/sitemap.xml",
        "special_handler": "hobbiesville",
    },
    {
        "name": "401 Games",
        "base_url": "https://store.401games.ca",
        "feed": "/collections/disney-lorcana-trading-card-game/products.json",
    },
    {
        "name": "Face to Face Games",
        "base_url": "https://facetofacegames.com",
        "feed": "/collections/lorcana/products.json",
    },
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

    elif isinstance(image, str):
        if image.startswith("//"):
            return "https:" + image
        return image

    images = product.get("images", [])

    if images:
        first_image = images[0]

        if isinstance(first_image, dict):
            src = first_image.get("src")
            if src:
                if src.startswith("//"):
                    return "https:" + src
                return src

        elif isinstance(first_image, str):
            if first_image.startswith("//"):
                return "https:" + first_image
            return first_image

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


def get_xml_locations(xml_text):
    """
    Return every <loc> value from a Shopify sitemap XML document.
    """
    locations = []

    try:
        root = ET.fromstring(xml_text)

        for element in root.iter():
            if element.tag.endswith("loc") and element.text:
                locations.append(element.text.strip())

    except ET.ParseError as error:
        print(f"Could not parse Hobbiesville sitemap XML: {error}")

    return locations


def fetch_hobbiesville_products(store):
    """
    Discover Hobbiesville Lorcana products through its Shopify
    product sitemaps instead of the site's search results.

    Hobbiesville search can omit valid product pages, so the
    sitemap provides more reliable discovery.
    """
    products = []

    sitemap_index_url = store["base_url"] + store["feed"]

    try:
        response = requests.get(
            sitemap_index_url,
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()

    except requests.RequestException as error:
        print(f"Could not fetch Hobbiesville sitemap index: {error}")
        return products

    sitemap_urls = get_xml_locations(response.text)

    product_sitemaps = [
        url
        for url in sitemap_urls
        if "sitemap_products_" in url
    ]

    print(
        f"Hobbiesville product sitemaps found: "
        f"{len(product_sitemaps)}"
    )

    product_urls = set()

    for sitemap_url in product_sitemaps:
        try:
            sitemap_response = requests.get(
                sitemap_url,
                headers=HEADERS,
                timeout=30,
            )
            sitemap_response.raise_for_status()

        except requests.RequestException as error:
            print(
                f"Could not fetch Hobbiesville product sitemap "
                f"{sitemap_url}: {error}"
            )
            continue

        locations = get_xml_locations(sitemap_response.text)

        for product_url in locations:
            normalized_url = product_url.lower()

            if (
                "/products/" in normalized_url
                and "lorcana" in normalized_url
            ):
                product_urls.add(
                    product_url.split("?")[0]
                )

        time.sleep(0.2)

    print(
        f"Hobbiesville Lorcana product URLs found: "
        f"{len(product_urls)}"
    )

    for product_url in sorted(product_urls):
        try:
            product_response = requests.get(
                product_url + ".js",
                headers=HEADERS,
                timeout=30,
            )
            product_response.raise_for_status()
            product = product_response.json()

        except (requests.RequestException, ValueError) as error:
            print(f"Could not fetch {product_url}: {error}")
            continue

        title = product.get("title", "")

        # Extra safeguard so a misleading URL does not result
        # in an unrelated product entering the monitor.
        if "lorcana" not in normalize_text(title):
            continue

        if not product.get("handle"):
            product["handle"] = (
                product_url.rstrip("/").split("/")[-1]
            )

        products.append(product)

        time.sleep(0.2)

    return products


def fetch_store_products(store):
    if store.get("special_handler") == "hobbiesville":
        return fetch_hobbiesville_products(store)

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
                headers=HEADERS,
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

        except (requests.RequestException, ValueError) as error:
            print(
                f"Could not fetch {store['name']} "
                f"page {page}: {error}"
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
