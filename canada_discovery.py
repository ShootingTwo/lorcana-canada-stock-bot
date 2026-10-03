import json
import os
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests


DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

STATE_FILE = "canada_discovery_state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0 Safari/537.36"
    )
}

# Number of sitemap files we may fetch simultaneously.
# Kept deliberately moderate so we do not hammer retailers.
MAX_SITEMAP_WORKERS = 8


SEED_STORES = [
    {
        "name": "Hobbiesville",
        "base_url": "https://www.hobbiesville.com",
    },
    {
        "name": "401 Games",
        "base_url": "https://store.401games.ca",
    },
    {
        "name": "Face to Face Games",
        "base_url": "https://facetofacegames.com",
    },
    {
        "name": "Kanzen Games",
        "base_url": "https://kanzengames.com",
    },
    {
        "name": "Amazing Stories",
        "base_url": "https://amazingstoriesgames.ca",
    },
    {
        "name": "Wizard's Tower",
        "base_url": "https://store.wizardtower.com",
    },
    {
        "name": "Board Game Bliss",
        "base_url": "https://www.boardgamebliss.com",
    },
    {
        "name": "Manta Trading",
        "base_url": "https://mantatrading.com",
    },
    {
        "name": "Heroes World",
        "base_url": "https://heroesworld.ca",
    },
    {
        "name": "Claw Me Baby",
        "base_url": "https://www.clawmebaby.ca",
    },
    {
        "name": "Fantasy Forged",
        "base_url": "https://www.fantasyforged.ca",
    },
    {
        "name": "Enter the Battlefield",
        "base_url": "https://enterthebattlefield.ca",
    },
    {
        "name": "Game Shack",
        "base_url": "https://www.gameshack.ca",
    },
    {
        "name": "Gotham Central Comics",
        "base_url": "https://www.gothamcentralcomics.com",
    },
    {
        "name": "Hope Club",
        "base_url": "https://hopeclubshop.ca",
    },
    {
        "name": "Le Coin du Jeu",
        "base_url": "https://www.lecoindujeu.ca",
    },
    {
        "name": "The Mythic Store",
        "base_url": "https://themythicstore.com",
    },
]


SET_TERMS = [
    "into the inkdark",
    "hyperia city",
]


PRODUCT_TERMS = [
    "booster box",
    "booster display",
    "trove",
]


def load_state():
    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

            if isinstance(data, dict):
                return data

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        OSError,
    ):
        pass

    return {}


def save_state(state):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            state,
            file,
            indent=2,
            sort_keys=True,
        )


def normalize_text(text):
    text = str(text or "").lower()

    text = text.replace("’", "'")
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def is_target_text(text):
    text = normalize_text(text)

    set_match = any(
        term in text
        for term in SET_TERMS
    )

    product_match = any(
        term in text
        for term in PRODUCT_TERMS
    )

    return set_match and product_match


def clean_product_url(url):
    if not url:
        return None

    url = url.strip()
    url = url.split("#")[0]
    url = url.split("?")[0]

    return url.rstrip("/")


def get_domain(url):
    try:
        return (
            urlparse(url)
            .netloc
            .lower()
            .replace(":443", "")
        )
    except Exception:
        return ""


def get_xml_locations(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    locations = []

    for element in root.iter():
        if element.tag.endswith("loc"):
            if element.text:
                locations.append(
                    element.text.strip()
                )

    return locations


def fetch_url(url, timeout=30):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
        )

        response.raise_for_status()

        return response.text

    except requests.RequestException:
        return None


def fetch_product_sitemap(sitemap_url):
    xml_text = fetch_url(
        sitemap_url,
        timeout=30,
    )

    if not xml_text:
        return []

    locations = get_xml_locations(
        xml_text
    )

    return [
        location
        for location in locations
        if "/products/" in location.lower()
    ]


def get_sitemap_urls(base_url):
    sitemap_url = (
        base_url.rstrip("/")
        + "/sitemap.xml"
    )

    xml_text = fetch_url(
        sitemap_url,
        timeout=30,
    )

    if not xml_text:
        print("Sitemap unavailable.")
        return []

    locations = get_xml_locations(
        xml_text
    )

    if not locations:
        return []

    sitemap_urls = []
    direct_product_urls = []

    for location in locations:
        lower = location.lower()

        if "/products/" in lower:
            direct_product_urls.append(
                location
            )

        if (
            "sitemap_products_" in lower
            or (
                "sitemap" in lower
                and "product" in lower
            )
        ):
            sitemap_urls.append(
                location
            )

    sitemap_urls = list(
        dict.fromkeys(
            sitemap_urls
        )
    )

    direct_product_urls = list(
        dict.fromkeys(
            direct_product_urls
        )
    )

    if not sitemap_urls:
        return direct_product_urls

    print(
        f"Product sitemap files: "
        f"{len(sitemap_urls)}"
    )

    product_urls = list(
        direct_product_urls
    )

    # Fetch independent product sitemap files
    # concurrently rather than sequentially.
    with ThreadPoolExecutor(
        max_workers=MAX_SITEMAP_WORKERS
    ) as executor:

        futures = {
            executor.submit(
                fetch_product_sitemap,
                sitemap,
            ): sitemap
            for sitemap in sitemap_urls
        }

        for future in as_completed(
            futures
        ):
            try:
                urls = future.result()
                product_urls.extend(urls)
            except Exception as error:
                sitemap = futures[future]

                print(
                    "Sitemap fetch failed: "
                    f"{sitemap} - {error}"
                )

    return list(
        dict.fromkeys(
            product_urls
        )
    )


def find_target_urls(store):
    name = store["name"]
    base_url = store["base_url"]

    print()
    print(f"Checking {name}...")

    start_time = time.time()

    urls = get_sitemap_urls(
        base_url
    )

    elapsed = (
        time.time()
        - start_time
    )

    print(
        f"Product URLs discovered: "
        f"{len(urls)}"
    )

    print(
        f"Sitemap scan time: "
        f"{elapsed:.1f} seconds"
    )

    matches = []

    for url in urls:
        cleaned_url = clean_product_url(
            url
        )

        if not cleaned_url:
            continue

        url_text = (
            cleaned_url
            .replace("-", " ")
            .replace("_", " ")
        )

        if is_target_text(
            url_text
        ):
            matches.append(
                cleaned_url
            )

    matches = list(
        dict.fromkeys(
            matches
        )
    )

    print(
        f"Target URLs found: "
        f"{len(matches)}"
    )

    return matches


def get_product_details(url):
    details = {
        "url": url,
        "title": "",
        "price": None,
        "available": None,
        "image": None,
    }

    js_url = url + ".js"

    try:
        response = requests.get(
            js_url,
            headers=HEADERS,
            timeout=30,
        )

        if response.ok:
            product = response.json()

            title = product.get(
                "title",
                "",
            )

            if title:
                details["title"] = title

            variants = product.get(
                "variants",
                [],
            )

            if variants:
                available_variants = [
                    variant
                    for variant in variants
                    if variant.get(
                        "available"
                    )
                ]

                details["available"] = bool(
                    available_variants
                )

                price_variants = (
                    available_variants
                    if available_variants
                    else variants
                )

                prices = []

                for variant in price_variants:
                    price = variant.get(
                        "price"
                    )

                    if price is None:
                        continue

                    try:
                        prices.append(
                            float(price)
                            / 100
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        pass

                if prices:
                    details["price"] = min(
                        prices
                    )

            images = product.get(
                "images",
                [],
            )

            if images:
                image = images[0]

                if isinstance(image, str):
                    if image.startswith("//"):
                        image = (
                            "https:"
                            + image
                        )

                    details["image"] = image

            return details

    except (
        requests.RequestException,
        ValueError,
    ):
        pass

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

    except requests.RequestException:
        return details

    html = response.text

    title_match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    if title_match:
        title = re.sub(
            r"<[^>]+>",
            " ",
            title_match.group(1),
        )

        title = re.sub(
            r"\s+",
            " ",
            title,
        ).strip()

        details["title"] = title

    return details


def send_discord_alert(
    store,
    details,
):
    if not DISCORD_WEBHOOK_URL:
        print(
            "ERROR: DISCORD_WEBHOOK_URL "
            "is missing."
        )
        return False

    title = (
        details.get("title")
        or "Lorcana Product"
    )

    url = details["url"]

    price = details.get("price")
    available = details.get(
        "available"
    )

    if price is None:
        price_text = "Unknown"
    else:
        price_text = (
            f"${price:.2f} CAD"
        )

    if available is True:
        availability_text = (
            "Available"
        )
    elif available is False:
        availability_text = (
            "Unavailable"
        )
    else:
        availability_text = (
            "Unknown"
        )

    embed = {
        "title": title,
        "url": url,
        "description": (
            "A qualifying Lorcana listing "
            "was discovered by the "
            "Canada-wide monitor."
        ),
        "fields": [
            {
                "name": "Retailer",
                "value": store["name"],
                "inline": True,
            },
            {
                "name": "Availability",
                "value": availability_text,
                "inline": True,
            },
            {
                "name": "Price",
                "value": price_text,
                "inline": True,
            },
            {
                "name": "Website",
                "value": get_domain(url),
                "inline": False,
            },
        ],
    }

    image = details.get(
        "image"
    )

    if image:
        embed["thumbnail"] = {
            "url": image
        }

    payload = {
        "content": (
            "🔎 CANADA-WIDE "
            "LORCANA DISCOVERY"
        ),
        "embeds": [embed],
    }

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        print(
            f"Discord alert sent: "
            f"{store['name']} - "
            f"{title}"
        )

        return True

    except requests.RequestException as error:
        print(
            f"Discord alert failed: "
            f"{error}"
        )

        return False


def main():
    run_start = time.time()

    previous_state = load_state()
    current_state = (
        previous_state.copy()
    )

    total_urls = 0
    total_targets = 0
    alerts_sent = 0

    for store in SEED_STORES:
        target_urls = (
            find_target_urls(
                store
            )
        )

        total_urls += len(
            target_urls
        )

        for url in target_urls:
            total_targets += 1

            state_key = (
                get_domain(url)
                + "::"
                + url
            )

            if (
                state_key
                in previous_state
            ):
                continue

            details = (
                get_product_details(
                    url
                )
            )

            verification_text = (
                details.get(
                    "title",
                    "",
                )
                + " "
                + url.replace(
                    "-",
                    " ",
                )
            )

            if not is_target_text(
                verification_text
            ):
                continue

            print()
            print("New discovery:")
            print(
                details.get(
                    "title"
                )
                or url
            )
            print(url)

            alert_sent = (
                send_discord_alert(
                    store,
                    details,
                )
            )

            if alert_sent:
                current_state[
                    state_key
                ] = {
                    "store": (
                        store["name"]
                    ),
                    "domain": (
                        get_domain(
                            url
                        )
                    ),
                    "title": (
                        details.get(
                            "title"
                        )
                        or ""
                    ),
                    "url": url,
                }

                alerts_sent += 1

            time.sleep(0.5)

    save_state(
        current_state
    )

    total_runtime = (
        time.time()
        - run_start
    )

    print()
    print(
        "--- CANADA DISCOVERY SUMMARY ---"
    )
    print(
        f"Stores checked: "
        f"{len(SEED_STORES)}"
    )
    print(
        f"Target URLs found: "
        f"{total_urls}"
    )
    print(
        f"Qualifying products processed: "
        f"{total_targets}"
    )
    print(
        f"New Discord alerts: "
        f"{alerts_sent}"
    )
    print(
        f"Total discoveries tracked: "
        f"{len(current_state)}"
    )
    print(
        f"Total runtime: "
        f"{total_runtime:.1f} seconds"
    )


if __name__ == "__main__":
    main()
