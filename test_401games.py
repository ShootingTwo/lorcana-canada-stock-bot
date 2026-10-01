import requests

BASE_URL = (
    "https://store.401games.ca/collections/"
    "disney-lorcana-trading-card-game/products.json"
)

headers = {
    "User-Agent": "Mozilla/5.0"
}

all_products = []

for page in range(1, 11):

    url = f"{BASE_URL}?limit=250&page={page}"

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        print(f"ERROR loading page {page}")
        break

    data = response.json()
    products = data.get("products", [])

    print(
        f"Page {page}: "
        f"{len(products)} products"
    )

    if not products:
        break

    all_products.extend(products)

    # Fewer than 250 means this was the last page
    if len(products) < 250:
        break

print()
print("--- RESULTS ---")
print("Total Lorcana products found:", len(all_products))

available = 0
sold_out = 0

for product in all_products:

    variants = product.get("variants", [])

    is_available = any(
        variant.get("available", False)
        for variant in variants
    )

    if is_available:
        available += 1
    else:
        sold_out += 1

print("Currently available:", available)
print("Currently sold out:", sold_out)
