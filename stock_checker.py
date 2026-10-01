import requests
import re
import os

SEARCH_URL = "https://hobbiesville.com/search?q=lorcana&type=product"

headers = {
    "User-Agent": "Mozilla/5.0"
}

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

if not DISCORD_WEBHOOK_URL:
    print("ERROR: Discord webhook secret is missing.")
    exit(1)

# Get Lorcana search results
response = requests.get(SEARCH_URL, headers=headers, timeout=30)

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

# Find the first available product
for url in urls:

    url = (
        url
        .replace("\\u0026", "&")
        .replace("\\/", "/")
        .split("?")[0]
    )

    product_url = "https://www.hobbiesville.com" + url
    json_url = product_url + ".js"

    response = requests.get(
        json_url,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        continue

    product = response.json()

    variants = product.get("variants", [])

    available = any(
        variant.get("available", False)
        for variant in variants
    )

    if not available:
        continue

    title = product.get("title", "Disney Lorcana Product")

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

    if "pre-order" in product_url.lower():
        status = "🔵 PREORDER AVAILABLE"
    else:
        status = "🟢 IN STOCK"

    message = {
        "content": (
            "🚨 **Lorcana Canada Stock Alert** 🇨🇦\n\n"
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

    print("Discord response:", discord_response.status_code)

    if discord_response.status_code in (200, 204):
        print("SUCCESS: Test alert sent to Discord!")
    else:
        print("ERROR sending Discord alert:")
        print(discord_response.text)

    # TEST ONLY: send one product
    break
