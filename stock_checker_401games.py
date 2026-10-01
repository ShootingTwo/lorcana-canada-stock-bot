import requests
import os
import json
import time

BASE_URL = (
    "https://store.401games.ca/collections/"
    "disney-lorcana-trading-card-game/products.json"
)

STORE_URL = "https://store.401games.ca/products/"
STATE_FILE = "stock_state_401games.json"

headers = {
    "User-Agent": "Mozilla/5.0"
}

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

if not DISCORD_WEBHOOK_URL:
    print("ERROR: Discord webhook secret is missing.")
    exit(1)


# Load previous stock state
try:
    with open(STATE_FILE, "r") as file:
        previous_state = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    previous_state = {}


# Detect whether the existing state file uses the old
# product-level format:
#
# "PRODUCT_ID": true
#
# The new variant-level format is:
#
# "VARIANT_ID": {
#     "product_id": "PRODUCT_ID",
#     "available": true
# }
#
# If the old format is detected, this run becomes a migration
# baseline and Discord alerts are suppressed.
old_state_format = any(
    isinstance(value, bool)
    for value in previous_state.values()
)

first_run = len(previous_state) == 0
migration_run = old_state_format

suppress_alerts = first_run or migration_run

if first_run:
    print("FIRST RUN: Establishing 401 Games variant baseline.")
    print("Discord alerts will be suppressed for this run.")
    print()

elif migration_run:
    print("MIGRATION RUN: Converting 401 Games stock state")
    print("from product-level to variant-level tracking.")
    print("Discord alerts will be suppressed for this run.")
    print()


current_state = {}

page = 1
total_products = 0
total_variants = 0
available_variants_count = 0
sold_out_variants_count = 0
alerts_sent = 0


while True:

    url = f"{BASE_URL}?limit=250&page={page}"

    print(f"Checking page {page}...")

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print(
                f"ERROR: Page {page} returned "
                f"{response.status_code}"
            )
            exit(1)

        data = response.json()
        products = data.get("products", [])

    except Exception as error:
        print(f"ERROR loading page {page}: {error}")
        exit(1)


    if not products:
        break


    for product in products:

        product_id = str(product.get("id"))

        title = product.get(
            "title",
            "Disney Lorcana Product"
        )

        handle = product.get("handle")

        if not product_id or not handle:
            continue


        total_products += 1

        product_url = STORE_URL + handle


        # Find the product image
        image_url = None
        images = product.get("images", [])

        if images:
            first_image = images[0]

            if isinstance(first_image, dict):
                image_url = first_image.get("src")
            elif isinstance(first_image, str):
                image_url = first_image

        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url


        variants = product.get("variants", [])


        for variant in variants:

            variant_id_raw = variant.get("id")

            if variant_id_raw is None:
                continue

            variant_id = str(variant_id_raw)

            variant_title = variant.get(
                "title",
                "Default Title"
            )

            available = variant.get(
                "available",
                False
            )

            total_variants += 1

            if available:
                available_variants_count += 1
            else:
                sold_out_variants_count += 1


            # Record this specific variant's state.
            current_state[variant_id] = {
                "product_id": product_id,
                "available": available
            }


            previous_variant = previous_state.get(variant_id)

            if isinstance(previous_variant, dict):
                was_available = previous_variant.get(
                    "available"
                )
            else:
                was_available = None


            # During the migration run, every variant is being
            # seen for the first time in the new state format.
            # Alerts are therefore intentionally suppressed.
            should_alert = (
                not suppress_alerts
                and available
                and was_available is not True
            )

            if not should_alert:
                continue


            # Use this exact variant's price.
            try:
                variant_price = variant.get("price")

                if variant_price is not None:
                    price_text = (
                        f"${float(variant_price):.2f} CAD"
                    )
                else:
                    price_text = "Price unavailable"

            except (TypeError, ValueError):
                price_text = "Price unavailable"


            # If Shopify supplies a meaningful variant name,
            # display it in the Discord alert.
            show_variant_title = (
                variant_title
                and variant_title.strip().lower()
                not in ("default title", "default")
            )


            if was_available is False:
                heading = "♻️ Lorcana Restock Alert"
            else:
                heading = "🚨 Lorcana Canada Stock Alert"


            description_lines = [
                "🏪 **401 Games**"
            ]

            if show_variant_title:
                description_lines.append(
                    f"✨ **Variant:** {variant_title}"
                )

            description_lines.extend([
                f"💰 **{price_text}**",
                "🟢 IN STOCK",
                "",
                f"🔗 **[View Product]({product_url})**"
            ])

            embed = {
                "title": title,
                "url": product_url,
                "description": "\n".join(
                    description_lines
                )
            }

            if image_url:
                embed["image"] = {
                    "url": image_url
                }


            message = {
                "content": f"{heading} 🇨🇦",
                "embeds": [embed]
            }


            # Send Discord alert
            try:
                discord_response = requests.post(
                    DISCORD_WEBHOOK_URL,
                    json=message,
                    timeout=30
                )

                if discord_response.status_code in (200, 204):
                    alerts_sent += 1

                    if show_variant_title:
                        print(
                            f"Alert sent: {title} "
                            f"- {variant_title}"
                        )
                    else:
                        print(f"Alert sent: {title}")

                else:
                    # Preserve the previous variant state so
                    # the alert can be attempted again next run.
                    if previous_variant is None:
                        current_state.pop(
                            variant_id,
                            None
                        )
                    else:
                        current_state[variant_id] = (
                            previous_variant
                        )

                    print(
                        f"Discord error "
                        f"{discord_response.status_code}: "
                        f"{title}"
                    )

                # Avoid rapid Discord webhook requests if
                # several variants restock simultaneously.
                time.sleep(1)

            except Exception as error:
                # Preserve the previous variant state if the
                # Discord request itself fails.
                if previous_variant is None:
                    current_state.pop(
                        variant_id,
                        None
                    )
                else:
                    current_state[variant_id] = (
                        previous_variant
                    )

                print(
                    f"ERROR sending Discord alert: {error}"
                )


    print(
        f"Page {page}: "
        f"{len(products)} products"
    )

    if len(products) < 250:
        break

    page += 1


# Save the new variant-level stock state
with open(STATE_FILE, "w") as file:
    json.dump(
        current_state,
        file,
        indent=2
    )


print()
print("--- 401 GAMES RESULTS ---")
print(f"Products checked: {total_products}")
print(f"Variants tracked: {total_variants}")
print(
    f"Available variants: "
    f"{available_variants_count}"
)
print(
    f"Sold out variants: "
    f"{sold_out_variants_count}"
)
print(f"Discord alerts sent: {alerts_sent}")

if migration_run:
    print(
        "Variant-level migration baseline completed."
    )

print("401 Games stock state updated.")
