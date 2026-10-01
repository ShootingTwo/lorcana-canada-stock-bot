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

print("\n--- PRODUCT LINKS FOUND ---\n")

links_found = 0

for link in soup.find_all("a", href=True):
    href = link["href"]

    if "/products/" in href:
        text = link.get_text(" ", strip=True)

        print("TEXT:", repr(text))
        print("URL:", href)
        print("---")

        links_found += 1

        # We only need a sample
        if links_found >= 15:
            break

print("\nProduct links sampled:", links_found)
