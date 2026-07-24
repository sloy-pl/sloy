#!/usr/bin/env python3
"""Create Shopify shipping (delivery) profiles for the SKUs with known
InPost/courier costs (the same SHIPPING_DATA table used by
update_shipping_pickup.py for the product-page text).

Scope: Poland only. One profile per (label, price) tier, each with a single
zone covering PL and a flat-rate method. No other country/zone is added —
shipping abroad stays off these profiles and is handled case-by-case
outside Shopify. Products not in SHIPPING_DATA are left on the store's
existing default/general profile.

Requires the Dev Dashboard app to have the `read_shipping` and
`write_shipping` scopes (same gap as `read_translations` for the
translation scripts — add the scopes, then re-run; the client_credentials
exchange picks them up automatically). Also needs `read_locations` to look
up the fulfillment location to attach the zones to.

Usage:
  python3 create_shipping_profiles.py --dry-run     # show groups + skus, no calls
  python3 create_shipping_profiles.py               # create the profiles
"""
import argparse, sys

from sheet_to_shopify import Shopify, load_env
from update_shipping_pickup import SHIPPING_DATA

CURRENCY = "PLN"


def group_skus():
    """(label, price) -> [sku, ...], in first-seen order."""
    groups = {}
    for sku, (label_en, _label_pl, price) in SHIPPING_DATA.items():
        key = (label_en, price)
        groups.setdefault(key, []).append(sku)
    return groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    groups = group_skus()

    if args.dry_run:
        for (label, price), skus in groups.items():
            print(f"{label} ({price} zł) — {len(skus)} SKUs: {', '.join(skus)}")
        print(f"\n{len(groups)} profiles would be created.")
        return

    env = load_env()
    shop = Shopify(env)

    locations_data = shop.gql("{ locations(first: 10) { edges { node { id name } } } }")
    locations = locations_data["locations"]["edges"]
    if not locations:
        sys.exit("No locations found on the store.")
    if len(locations) > 1:
        print("Multiple locations found, using the first one:")
        for edge in locations:
            print(f"  {edge['node']['id']}  {edge['node']['name']}")
    location_id = locations[0]["node"]["id"]
    print(f"Using location: {locations[0]['node']['name']} ({location_id})")

    not_found = []
    for (label, price), skus in groups.items():
        variant_ids = []
        for sku in skus:
            _product_id, variant_id = shop.find_by_sku(sku)
            if not variant_id:
                not_found.append(sku)
                continue
            variant_ids.append(variant_id)

        if not variant_ids:
            print(f"{label} ({price} zł): no variants found, skipping profile")
            continue

        amount = price.replace(",", ".")
        profile_input = {
            "name": f"PL Shipping – {label} ({price} zł)",
            "locationGroupsToCreate": [{
                "locationsToAdd": [location_id],
                "zonesToCreate": [{
                    "name": "Poland",
                    "countries": [{"code": "PL"}],
                    "methodDefinitionsToCreate": [{
                        "name": label,
                        "active": True,
                        "rateDefinition": {
                            "price": {"amount": amount, "currencyCode": CURRENCY},
                        },
                    }],
                }],
            }],
            "variantsToAssociate": variant_ids,
        }

        mutation = """
        mutation($profile: DeliveryProfileInput!) {
          deliveryProfileCreate(profile: $profile) {
            profile { id name }
            userErrors { field message }
          }
        }
        """
        data = shop.gql(mutation, {"profile": profile_input})
        result = data["deliveryProfileCreate"]
        if result["userErrors"]:
            print(f"{label} ({price} zł): ERROR {result['userErrors']}")
            continue
        profile = result["profile"]
        print(f"{label} ({price} zł): created {profile['name']} ({profile['id']}) — {len(variant_ids)} variants")

    if not_found:
        print(f"\nSKUs not found in Shopify, skipped: {not_found}", file=sys.stderr)


if __name__ == "__main__":
    main()
