import requests
from bs4 import BeautifulSoup

URL = "https://facetofacegames.com/search?keyword=lorcana"

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
    print("ERROR: Could not reach Face to Face Games.")
    exit()

soup = BeautifulSoup(response.text, "html.parser")

links = []
seen = set()

for link in soup.find_all("a", href=True):
    href = link["href"]
    text = link.get_text(" ", strip=True)

    # Look for likely product-page links containing Lorcana
    if "lorcana" in (text + " " + href).lower():
        if href not in seen:
            seen.add(href)
            links.append((text, href))

print()
print("--- POSSIBLE LORCANA LINKS ---")
print()
print("Unique links found:", len(links))
print()

for number, (text, href) in enumerate(links[:30], start=1):
    print(f"{number}.")
    print("TEXT:", repr(text))
    print("URL:", href)
    print()
