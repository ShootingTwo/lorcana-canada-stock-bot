import requests

URL = "https://hobbiesville.com/collections/lorcana"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status code:", response.status_code)
print("Page size:", len(response.text))

if response.status_code == 200:
    print("SUCCESS: Hobbiesville page reached!")
else:
    print("ERROR: Could not reach Hobbiesville.")
