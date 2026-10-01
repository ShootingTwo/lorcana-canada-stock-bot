import requests
import re
import time

SEARCH_URL = "https://hobbiesville.com/search?q=lorcana&type=product"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(SEARCH_URL, headers=headers, timeout=30)

if response.status_code != 200:
    print("ERROR: Could not reach Hobbiesville.")
    exit()

html = response.text

urls = re.findall(
    r'\\"url\\":\\"(\\/products\\/[^"]+)',
    html
)

# Remove duplicate URLs while preserving order
urls = list(dict.fromkeys(urls))

print(f"Lorcana products found: {len(urls)}")
print()

for number, url in enumerate(urls, start=1):

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
            print(f"{number}. ERROR loading {product_url}")
            continue

        product = response.json()

        title = product.get("title", "Unknown Product")
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

        if "pre-order" in product_url.lower():
            product_type = "PREORDER"
        else:
            product_type = "IN STOCK"

        if available:
            status = f"✅ AVAILABLE ({product_type})"
        else:
            status = "❌ SOLD OUT"

        print(f"{number}. {title}")
        print(f"   {status}")
        print(f"   {price_text}")
        print(f"   {product_url}")
        print()

        # Be polite to the store's server
        time.sleep(1)

    except Exception as error:
        print(f"{number}. ERROR: {error}")
        print()
