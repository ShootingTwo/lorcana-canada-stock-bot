import requests
from bs4 import BeautifulSoup

URL = "https://hobbiesville.com/search?q=lorcana&type=product"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status code:", response.status_code)

if response.status_code != 200:
    print("ERROR: Could not reach Hobbiesville.")
    exit()

soup = BeautifulSoup(response.text, "html.parser")

print("\n--- LORCANA PRODUCT LINKS FOUND ---\n")

products = {}

for link in soup.find_all("a", href=True):
    href = link["href"]

    if "/products/" not in href:
        continue

    name = link.get_text(" ", strip=True)

    if not name:
        continue

    if "lorcana" not in name.lower():
        continue

    if href.startswith("/"):
        href = "https://hobbiesville.com" + href

    products[href] = name

print("Unique products found:", len(products))
print()

for number, (url, name) in enumerate(products.items(), start=1):
    print(f"{number}. {name}")
    print(f"   {url}")
    print()
