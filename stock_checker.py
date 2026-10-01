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

# Find Lorcana product titles
titles = re.findall(
    r'\\"title\\":\\"([^"]*[Ll]orcana[^"]*)\\"',
    html
)

# Find CAD prices
prices = re.findall(
    r'\\"price\\":\{\\"amount\\":([0-9.]+),'
    r'\\"currencyCode\\":\\"CAD\\"\}',
    html
)

# Find Hobbiesville product URLs
urls = re.findall(
    r'\\"url\\":\\"(\\/products\\/[^"]+)',
    html
)

print("\n--- DATA EXTRACTION TEST ---\n")

print("Lorcana titles found:", len(titles))
print("CAD prices found:", len(prices))
print("Product URLs found:", len(urls))

print("\n--- SAMPLE LORCANA TITLES ---\n")

seen = set()
count = 0

for title in titles:

    title = (
        title
        .replace("\\u0026", "&")
        .replace("\\/", "/")
    )

    if title in seen:
        continue

    seen.add(title)

    print(title)

    count += 1

    if count >= 10:
        break
