import requests
from bs4 import BeautifulSoup

URL = "https://store.401games.ca/pages/search-results?q=lorcana"

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
    print("ERROR: Could not reach 401 Games.")
    exit()

soup = BeautifulSoup(response.text, "html.parser")

print("\n--- 401 GAMES PRODUCT LINKS ---\n")

links = []

for link in soup.find_all("a", href=True):
    href = link["href"]
    text = link.get_text(" ", strip=True)

    if "/products/" in href:
        links.append((text, href))

print("Product links found:", len(links))
print()

for number, (text, href) in enumerate(links[:20], start=1):
    print(f"{number}.")
    print("TEXT:", repr(text))
    print("URL:", href)
    print()
