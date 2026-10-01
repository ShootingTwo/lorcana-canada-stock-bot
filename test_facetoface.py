
import requests

URL = "https://www.facetofacegames.com/search/?keyword=lorcana"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    URL,
    headers=headers,
    timeout=30
)

print("Status code:", response.status_code)
print("Final URL:", response.url)
print("Page size:", len(response.text))
print(
    "Occurrences of 'lorcana':",
    response.text.lower().count("lorcana")
)

if response.status_code == 200:
    print("SUCCESS: Face to Face Games reached!")
else:
    print("ERROR: Could not reach Face to Face Games.")
