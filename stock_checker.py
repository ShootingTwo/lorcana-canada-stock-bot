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

titles = re.findall(
    r'\\"title\\":\\"([^"]*[Ll]orcana[^"]*)\\"',
    html
)

prices = re.findall(
    r'\\"price\\":\{\\"amount\\":([0-9.]+),'
    r'\\"currencyCode\\":\\"CAD\\"\}',
    html
)

urls = re.findall(
    r'\\"url\\":\\"(\\/products\\/[^"]+)',
    html
)

print("\n--- HOBBIESVILLE LORCANA PRODUCTS ---\n")

for number, (title, price, url) in enumerate(
    zip(titles, prices, urls),
    start=1
):
    title = title.replace("\\u0026", "&")

    url = (
        url
        .replace("\\u0026", "&")
        .replace("\\/", "/")
        .split("?")[0]
    )

    full_url = "https://www.hobbiesville.com" + url

    print(f"{number}. {title}")
    print(f"   Price: ${float(price):.2f} CAD")
    print(f"   URL: {full_url}")
    print()
