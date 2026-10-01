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
print()

# Show samples from farther into the page,
# rather than the first occurrence in the URL.
for number, position in enumerate(positions[20:25], start=21):

    print(f"\n===== LORCANA OCCURRENCE #{number} =====\n")

    snippet_start = max(0, position - 500)
    snippet_end = min(len(html), position + 1000)

    print(html[snippet_start:snippet_end])
