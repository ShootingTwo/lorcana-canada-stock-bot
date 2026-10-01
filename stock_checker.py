import requests
import re
import json

SEARCH_URL = "https://hobbiesville.com/search?q=lorcana&type=product"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(SEARCH_URL, headers=headers, timeout=30)
html = response.text

urls = re.findall(
    r'\\"url\\":\\"(\\/products\\/[^"]+)',
    html
)

if not urls:
    print("ERROR: No products found.")
    exit()

url = (
    urls[0]
    .replace("\\u0026", "&")
    .replace("\\/", "/")
    .split("?")[0]
)

product_url = "https://www.hobbiesville.com" + url

# Shopify stores commonly expose product information as JSON
json_url = product_url + ".js"

print("Testing product:")
print(product_url)
print()
print("JSON endpoint:")
print(json_url)
print()

response = requests.get(json_url, headers=headers, timeout=30)

print("Status code:", response.status_code)

if response.status_code != 200:
    print("ERROR: Product JSON could not be reached.")
    exit()

try:
    product = response.json()
except Exception:
    print("ERROR: Response was not valid JSON.")
    print(response.text[:1000])
    exit()

print("\n--- PRODUCT AVAILABILITY ---\n")

print("Title:", product.get("title"))

variants = product.get("variants", [])

print("Variants found:", len(variants))
print()

for variant in variants:
    print("Variant:", variant.get("title"))
    print("Available:", variant.get("available"))
    print("Price:", variant.get("price"))
    print("---")
