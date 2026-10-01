import requests

URL = "https://hobbiesville.com/search?q=lorcana&type=product"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)

print("Status code:", response.status_code)
print("Page size:", len(response.text))

if response.status_code == 200:
    print("SUCCESS: Hobbiesville Lorcana search reached!")

    text = response.text.lower()

    print("Occurrences of 'lorcana':", text.count("lorcana"))
    print("Occurrences of 'disney':", text.count("disney"))
else:
    print("ERROR: Could not reach Hobbiesville search.")
