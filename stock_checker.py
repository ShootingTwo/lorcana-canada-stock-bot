import requests
import re

URL = "https://hobbiesville.com/search?q=lorcana&type=product"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status code:", response.status_code)

if response.status_code != 200:
    print("ERROR: Could not reach Hobbiesville.")
    exit()

html = response.text

# Hobbiesville embeds product information with escaped JSON.
pattern = re.compile(
    r'\\"price\\":\{\\"amount\\":\\"?([0-9.]+)\\"?,'
    r'\\"currencyCode\\":\\"CAD\\"\},'
    r'\\"product\\":\{\\"title\\":\\"(.*?)\\",'
    r'\\"vendor\\":\\"(.*?)\\",'
    r'\\"id\\":\\"(.*?)\\",'
    r'\\"untranslatedTitle\\":\\".*?\\",'
    r'\\"url\\":\\"(.*?)\\"'
)

matches = pattern.findall(html)

products = {}

for price, title, vendor, product_id, url in matches:

    title = title.replace("\\u0026", "&")
    url = url.replace("\\u0026", "&").replace("\\/", "/")

    # Remove Shopify search tracking from the URL
    url = url.split("?")[0]

    if url.startswith("/"):
        url = "https://www.hobbiesville.com" + url

    # Only keep Lorcana products
    if "lorcana" not in title.lower():
        continue

    products[product_id] = {
        "title": title,
        "price": price,
        "vendor": vendor,
        "url": url
    }

print("\n--- LORCANA PRODUCTS ---\n")
print("Unique Lorcana products found:", len(products))
print()

for number, product in enumerate(products.values(), start=1):

    print(f"{number}. {product['title']}")
    print(f"   Price: ${product['price']} CAD")
    print(f"   Vendor: {product['vendor']}")
    print(f"   URL: {product['url']}")
    print()
