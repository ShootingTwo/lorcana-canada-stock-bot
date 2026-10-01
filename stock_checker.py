import requests

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

position = html.lower().find("lorcana")

print("\n--- DATA AROUND FIRST LORCANA MATCH ---\n")

if position == -1:
    print("No Lorcana text found.")
else:
    start = max(0, position - 1000)
    end = min(len(html), position + 2000)

    print(html[start:end])
