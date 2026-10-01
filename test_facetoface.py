import requests

URL = (
    "https://facetofacegames.com/collections/"
    "lorcana/products.json?limit=250&page=1"
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
    print("ERROR: Could not reach Face to Face product feed.")
    exit()

try:
    data = response.json()
except Exception:
    print("ERROR: Response was not JSON.")
    print(response.text[:1000])
    exit()

products = data.get("products", [])

print()
print("--- FACE TO FACE LORCANA FEED ---")
print()
print("Products found:", len(products))
print()

for number, product in enumerate(products[:10], start=1):

    print(f"{number}. {product.get('title')}")
    print("   ID:", product.get("id"))
    print("   Handle:", product.get("handle"))

    variants = product.get("variants", [])

    if variants:
        available = any(
            variant.get("available", False)
            for variant in variants
        )

        prices = [
            variant.get("price")
            for variant in variants
            if variant.get("price") is not None
        ]

        print("   Available:", available)
        print("   Prices:", prices[:3])

    print()
