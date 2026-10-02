import json
import os
import re
import time
from urllib.parse import (
    parse_qs,
    quote_plus,
    unquote,
    urlparse,
)

import requests


DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

STATE_FILE = "canada_discovery_state.json"

SEARCH_URL = "https://www.bing.com/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0 Safari/537.36"
    )
}


SEARCH_QUERIES = [
    '"Into the Inkdark" "Booster Box" Canada',
    '"Into the Inkdark" "Booster Display" Canada',
    '"Into the Inkdark" "Illumineer\'s Trove" Canada',
    '"Into the Inkdark" "Illumineers Trove" Canada',

    '"Hyperia City" "Booster Box" Canada',
    '"Hyperia City" "Booster Display" Canada',
    '"Hyperia City" "Illumineer\'s Trove" Canada',
    '"Hyperia City" "Illumineers Trove" Canada',
]


EXCLUDED_DOMAINS = {
    "bing.com",
    "www.bing.com",
    "google.com",
    "www.google.com",
    "youtube.com",
    "www.youtube.com",
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "reddit.com",
    "www.reddit.com",
    "x.com",
    "twitter.com",
    "www.twitter.com",
    "tiktok.com",
    "www.tiktok.com",
    "ebay.com",
    "www.ebay.com",
    "amazon.com",
    "www.amazon.com",
    "amazon.ca",
    "www.amazon.ca",
}


def load_state():
    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

            if isinstance(data, dict):
                return data

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        OSError,
    ):
        pass

    return {}


def save_state(state):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            state,
            file,
            indent=2,
            sort_keys=True,
        )


def normalize_text(text):
    return (
        str(text or "")
        .lower()
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )


def clean_url(url):
    if not url:
        return None

    url = unquote(url).strip()

    # Bing occasionally wraps destination URLs.
    parsed = urlparse(url)

    if "bing.com" in parsed.netloc:
        query = parse_qs(parsed.query)

        for key in ("url", "u", "r"):
            values = query.get(key)

            if values:
                candidate = unquote(values[0])

                if candidate.startswith("http"):
                    url = candidate
                    break

    url = url.split("#")[0]

    return url


def get_domain(url):
    try:
        return (
            urlparse(url)
            .netloc
            .lower()
            .replace(":443", "")
        )
    except Exception:
        return ""


def is_excluded_url(url):
    domain = get_domain(url)

    if not domain:
        return True

    if domain in EXCLUDED_DOMAINS:
        return True

    return False


def looks_like_target(text):
    text = normalize_text(text)

    set_match = (
        "into the inkdark" in text
        or "hyperia city" in text
    )

    booster_match = (
        "booster box" in text
        or "booster display" in text
    )

    trove_match = (
        "illumineer's trove" in text
        or "illumineers trove" in text
        or "illumineer trove" in text
    )

    return (
        set_match
        and (
            booster_match
            or trove_match
        )
    )


def search_bing(query):
    print()
    print(f"Searching: {query}")

    try:
        response = requests.get(
            SEARCH_URL,
            params={
                "q": query,
                "count": 50,
            },
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        print(
            f"Search request failed: {error}"
        )
        return []

    html = response.text

    results = []

    # Bing organic result blocks normally use b_algo.
    blocks = re.findall(
        r'<li class="b_algo".*?</li>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for block in blocks:
        link_match = re.search(
            r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if not link_match:
            continue

        url = clean_url(
            link_match.group(1)
        )

        title_html = link_match.group(2)

        title = re.sub(
            r"<[^>]+>",
            " ",
            title_html,
        )

        title = re.sub(
            r"\s+",
            " ",
            title,
        ).strip()

        snippet_match = re.search(
            r'<p>(.*?)</p>',
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )

        snippet = ""

        if snippet_match:
            snippet = re.sub(
                r"<[^>]+>",
                " ",
                snippet_match.group(1),
            )

            snippet = re.sub(
                r"\s+",
                " ",
                snippet,
            ).strip()

        if not url:
            continue

        if is_excluded_url(url):
            continue

        combined_text = (
            title
            + " "
            + snippet
            + " "
            + url
        )

        if not looks_like_target(
            combined_text
        ):
            continue

        results.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "domain": get_domain(url),
            }
        )

    print(
        f"Qualifying search results: "
        f"{len(results)}"
    )

    return results


def send_discord_alert(result):
    if not DISCORD_WEBHOOK_URL:
        print(
            "ERROR: DISCORD_WEBHOOK_URL "
            "is missing."
        )
        return False

    title = result.get(
        "title",
        "Lorcana Product",
    )

    url = result["url"]
    domain = result["domain"]

    embed = {
        "title": title,
        "url": url,
        "description": (
            "A new Canadian search result "
            "matching the Lorcana discovery "
            "monitor was found."
        ),
        "fields": [
            {
                "name": "Website",
                "value": domain,
                "inline": True,
            },
            {
                "name": "Discovery",
                "value": "New listing",
                "inline": True,
            },
        ],
    }

    payload = {
        "content": (
            "🔎 NEW CANADIAN "
            "LORCANA LISTING"
        ),
        "embeds": [embed],
    }

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        print(
            f"Discord alert sent: "
            f"{title}"
        )

        return True

    except requests.RequestException as error:
        print(
            f"Discord alert failed: {error}"
        )

        return False


def main():
    previous_state = load_state()
    current_state = previous_state.copy()

    discoveries = {}

    for query in SEARCH_QUERIES:
        results = search_bing(query)

        for result in results:
            url = result["url"]

            discoveries[url] = result

        time.sleep(2)

    print()
    print(
        f"Unique qualifying URLs found: "
        f"{len(discoveries)}"
    )

    alerts_sent = 0

    for url, result in discoveries.items():

        if url in previous_state:
            continue

        print()
        print("New discovery:")
        print(result["title"])
        print(url)

        alert_sent = send_discord_alert(
            result
        )

        if alert_sent:
            current_state[url] = {
                "title": result["title"],
                "domain": result["domain"],
            }

            alerts_sent += 1

            time.sleep(1)

    save_state(current_state)

    print()
    print(
        "--- CANADA DISCOVERY SUMMARY ---"
    )
    print(
        f"Unique results found: "
        f"{len(discoveries)}"
    )
    print(
        f"New Discord alerts: "
        f"{alerts_sent}"
    )
    print(
        f"Total URLs tracked: "
        f"{len(current_state)}"
    )


if __name__ == "__main__":
    main()
