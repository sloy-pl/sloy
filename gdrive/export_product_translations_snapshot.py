#!/usr/bin/env python3
"""Snapshot all product-related EN->PL Shopify translations into a Google Sheet.

Reuses shopify-import/export_translations.py's collect() to pull every
translated PRODUCT / PRODUCT_OPTION / PRODUCT_OPTION_VALUE string from the
store (title, body_html, handle, seo, options, translatable metafields...),
then creates a new Google Sheet inside a shared Drive folder and writes the
rows to it. The sheet's name is the run timestamp in Europe/Berlin time.

Auth: OAuth as your own Google user, not a service account. A service
account has 0 bytes of its own Drive storage, so file-creation calls fail
with storageQuotaExceeded even when your personal Drive has plenty of
space (see git log / PR discussion). Authenticating as you means new files
are owned by your account and count against your normal quota.

One-time setup:
1. In the Google Cloud project that has the Drive API + Sheets API enabled
   (Google Cloud Console -> APIs & Services -> Library, enable both),
   go to APIs & Services -> Credentials -> Create Credentials ->
   OAuth client ID -> Application type "Desktop app". Download the JSON
   and save it as gdrive/client_secret.json (or point
   GOOGLE_OAUTH_CLIENT_FILE at it in gdrive/.env).
2. Make sure the OAuth consent screen is in "Testing" mode with your own
   Google account added as a test user (no Google verification needed for
   personal use).
3. Run this script. The first run opens a browser for you to sign in and
   consent; the resulting token is cached in gdrive/token.json (gitignored)
   and auto-refreshed after that, so later runs don't prompt again.

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
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = os.path.dirname(os.path.abspath(__file__))
SHOPIFY_IMPORT_DIR = os.path.join(os.path.dirname(ROOT), "shopify-import")
sys.path.insert(0, SHOPIFY_IMPORT_DIR)

from export_translations import collect  # noqa: E402
from sheet_to_shopify import Shopify, load_env as load_shopify_env  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))

# drive.file: only files this app creates/opens, not full Drive read/write.
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]
TOKEN_FILE = os.path.join(ROOT, "token.json")
# https://drive.google.com/drive/folders/1AOyI9fKLObpb4LTUp-4wa5RtdO_6dg7b
DEFAULT_FOLDER_ID = "1AOyI9fKLObpb4LTUp-4wa5RtdO_6dg7b"
HEADER = ["resource_type", "resource_id", "key", "source_locale", "en", "pl"]


def google_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        client_file = os.environ.get("GOOGLE_OAUTH_CLIENT_FILE", "./client_secret.json")
        if not os.path.isabs(client_file):
            client_file = os.path.join(ROOT, client_file)
        if not os.path.exists(client_file):
            sys.exit(
                f"Missing OAuth client file at {client_file}. Download it from "
                "Cloud Console (Credentials -> OAuth client ID -> Desktop app) "
                "and save it there, or set GOOGLE_OAUTH_CLIENT_FILE in gdrive/.env."
            )
        flow = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    return creds


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
