import requests

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

html = response.text
lower_html = html.lower()

positions = []
start = 0

while True:
    position = lower_html.find("lorcana", start)

    if position == -1:
        break

    positions.append(position)
    start = position + 7

print("Total Lorcana occurrences:", len(positions))

for number, position in enumerate(positions, start=1):

    print(f"\n===== LORCANA OCCURRENCE #{number} =====\n")

    snippet_start = max(0, position - 500)
    snippet_end = min(len(html), position + 1000)

    print(html[snippet_start:snippet_end])
