import requests

HANDLE = "disney-lorcana-the-first-chapter-starter-decks"

URL = (
    "https://store.401games.ca/products/"
    f"{HANDLE}.js"
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

if response.status_code != 200:
    print("ERROR: Could not retrieve product.")
    exit(1)

product = response.json()

print()
print("--- TEST PRODUCT ---")
print("Title:", product.get("title"))
print("Product ID:", product.get("id"))

variants = product.get("variants", [])

available = any(
    variant.get("available", False)
    for variant in variants
)

print("Available:", available)
print(
    "URL:",
    f"https://store.401games.ca/products/{HANDLE}"
)
