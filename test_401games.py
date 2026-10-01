import requests

URL = (
    "https://store.401games.ca/collections/"
    "disney-lorcana-trading-card-game/products.json?limit=250"
)

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    URL,
    headers=headers,
    timeout=30
)

print("Status code:", response.status_code)
print("Content type:", response.headers.get("content-type"))
print("Page size:", len(response.text))

if response.status_code != 200:
    print("ERROR: Could not reach 401 Games product feed.")
    exit()

try:
    data = response.json()
except Exception:
    print("ERROR: Response was not JSON.")
    print(response.text[:1000])
    exit()

products = data.get("products", [])

print("\n--- 401 GAMES LORCANA FEED ---\n")
print("Products found:", len(products))
print()

for number, product in enumerate(products[:10], start=1):

    print(f"{number}. {product.get('title')}")

    variants = product.get("variants", [])

    if variants:
        variant = variants[0]

        print("   Price:", variant.get("price"))
        print("   Available:", variant.get("available"))

    print("   Handle:", product.get("handle"))
    print()
