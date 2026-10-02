import requests
import re
import os
import json
import time
import xml.etree.ElementTree as ET

SITEMAP_URL = "https://www.hobbiesville.com/sitemap.xml"
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
# This prevents temporarily missing products from being forgotten and
# incorrectly treated as brand-new products when they reappear.
current_state = previous_state.copy()


# If the state file is empty, this is our first baseline run.
first_run = len(previous_state) == 0

if first_run:
    print("FIRST RUN: Establishing Hobbiesville baseline.")
    print("Discord alerts will be suppressed for this run.")
    print()


def get_xml_locations(xml_text):
    """
    Return every <loc> value from a Shopify sitemap XML document.
    Namespace handling is intentionally flexible.
    """
    locations = []

    try:
        root = ET.fromstring(xml_text)

        for element in root.iter():
            if element.tag.endswith("loc") and element.text:
                locations.append(element.text.strip())

    except ET.ParseError as error:
        print(f"ERROR parsing sitemap XML: {error}")

    return locations


# ---------------------------------------------------------
# STEP 1: Get Hobbiesville's sitemap index
# ---------------------------------------------------------

try:
    response = requests.get(
        SITEMAP_URL,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        print(
            "ERROR: Could not reach Hobbiesville sitemap. "
            f"HTTP {response.status_code}"
        )
        exit(1)

except Exception as error:
    print(f"ERROR reaching Hobbiesville sitemap: {error}")
    exit(1)


sitemap_urls = get_xml_locations(response.text)

product_sitemaps = [
    url
    for url in sitemap_urls
    if "sitemap_products_" in url
]

print(f"Hobbiesville product sitemaps found: {len(product_sitemaps)}")


# ---------------------------------------------------------
# STEP 2: Read every product sitemap and collect Lorcana URLs
# ---------------------------------------------------------

product_urls = set()

for sitemap_url in product_sitemaps:

    try:
        response = requests.get(
            sitemap_url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print(
                f"Could not read product sitemap: {sitemap_url} "
                f"(HTTP {response.status_code})"
            )
            continue

        sitemap_product_urls = get_xml_locations(response.text)

        for product_url in sitemap_product_urls:

            normalized_url = product_url.lower()

            if (
                "/products/" in normalized_url
                and "lorcana" in normalized_url
            ):
                product_urls.add(product_url.split("?")[0])

    except Exception as error:
        print(
            f"ERROR reading product sitemap "
            f"{sitemap_url}: {error}"
        )

    # Be polite to Hobbiesville.
    time.sleep(0.2)


product_urls = sorted(product_urls)

print(f"Lorcana product URLs discovered: {len(product_urls)}")
print(f"Products already known: {len(previous_state)}")
print()


# ---------------------------------------------------------
# STEP 3: Check each discovered Lorcana product
# ---------------------------------------------------------

for product_url in product_urls:

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


        # Safety check:
        # The URL contained "lorcana", but confirm the current product
        # information is actually Lorcana-related as well.
        if "lorcana" not in title.lower():
            continue


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
        time.sleep(0.5)


    except Exception as error:
        print(f"ERROR checking {product_url}: {error}")

        # current_state already contains the previous value
        # for known products, so nothing needs to be removed.
        print()


# Save the accumulated availability state.
#
# Products temporarily absent from discovery remain in this file
# with their last known status.
with open(STATE_FILE, "w") as file:
    json.dump(
        current_state,
        file,
        indent=2
    )


print()
print("--- HOBBIESVILLE RESULTS ---")
print(f"Product sitemaps checked: {len(product_sitemaps)}")
print(f"Lorcana products discovered: {len(product_urls)}")
print(f"Total products tracked: {len(current_state)}")
print("Hobbiesville stock state updated.")
