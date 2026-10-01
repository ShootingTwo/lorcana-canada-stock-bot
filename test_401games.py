import requests
import re

URL = "https://store.401games.ca/pages/search-results?q=lorcana"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status code:", response.status_code)

if response.status_code != 200:
    print("ERROR: Could not reach 401 Games.")
    exit()

html = response.text

# Find every collection URL containing "lorcana"
matches = re.findall(
    r'href=["\']([^"\']*\/collections\/[^"\']*lorcana[^"\']*)["\']',
    html,
    flags=re.IGNORECASE
)

# Remove duplicates while preserving order
matches = list(dict.fromkeys(matches))

print("\n--- LORCANA COLLECTION LINKS ---\n")
print("Unique collection links found:", len(matches))
print()

for number, url in enumerate(matches, start=1):
    print(f"{number}. {url}")
