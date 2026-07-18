#!/usr/bin/env python3
"""Snapshot all product-related EN->PL Shopify translations into a Google Sheet.

Reuses shopify-import/export_translations.py's collect() to pull every
translated PRODUCT / PRODUCT_OPTION / PRODUCT_OPTION_VALUE string from the
store (title, body_html, handle, seo, options, translatable metafields...),
then creates a new Google Sheet inside a shared Drive folder and writes the
rows to it. The sheet's name is the run timestamp in Europe/Berlin time.

Setup:
- gdrive/.env: GOOGLE_SERVICE_ACCOUNT_FILE (see gdrive/.env.example).
- shopify-import/.env: Shopify Admin API credentials (SHOPIFY_STORE,
  SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET), same as export_translations.py.
- The target Drive folder must be shared as Editor (not just Viewer) with
  the service account's email — creating a file needs write access, unlike
  list_files.py's read-only listing.

Usage:
  python3 export_product_translations_snapshot.py
  python3 export_product_translations_snapshot.py --locale pl
  python3 export_product_translations_snapshot.py --folder-id <drive-folder-id>
"""
import argparse
import datetime
import os
import sys
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

ROOT = os.path.dirname(os.path.abspath(__file__))
SHOPIFY_IMPORT_DIR = os.path.join(os.path.dirname(ROOT), "shopify-import")
sys.path.insert(0, SHOPIFY_IMPORT_DIR)

from export_translations import collect  # noqa: E402
from sheet_to_shopify import Shopify, load_env as load_shopify_env  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
# https://drive.google.com/drive/folders/1AOyI9fKLObpb4LTUp-4wa5RtdO_6dg7b
DEFAULT_FOLDER_ID = "1AOyI9fKLObpb4LTUp-4wa5RtdO_6dg7b"
HEADER = ["resource_type", "resource_id", "key", "source_locale", "en", "pl"]


def google_credentials():
    key_file = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
    if not os.path.isabs(key_file):
        key_file = os.path.join(ROOT, key_file)
    return service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)


def berlin_timestamp():
    now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
    return now.strftime("%Y-%m-%d %H-%M-%S")


def create_sheet(drive, sheets, folder_id, title, rows):
    file = drive.files().create(
        body={
            "name": title,
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [folder_id],
        },
        fields="id, webViewLink",
    ).execute()
    spreadsheet_id = file["id"]

    values = [HEADER] + [[row.get(col, "") for col in HEADER] for row in rows]
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()

    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
                {
                    "repeatCell": {
                        "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold",
                    }
                },
            ]
        },
    ).execute()
    return file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--locale", default="pl")
    parser.add_argument("--folder-id", default=os.environ.get("GDRIVE_TRANSLATIONS_FOLDER_ID", DEFAULT_FOLDER_ID))
    args = parser.parse_args()

    shopify_env = load_shopify_env()
    shop = Shopify(shopify_env)
    rows = collect(shop, args.locale)
    print(f"{len(rows)} translated strings collected from Shopify", file=sys.stderr)

    creds = google_credentials()
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)

    title = berlin_timestamp()
    file = create_sheet(drive, sheets, args.folder_id, title, rows)
    print(f"Created \"{title}\" -> {file.get('webViewLink')}", file=sys.stderr)


if __name__ == "__main__":
    main()
