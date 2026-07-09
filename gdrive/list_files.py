#!/usr/bin/env python3
"""List files in the shared Google Drive folder using a service account.

Requires GOOGLE_SERVICE_ACCOUNT_FILE and GDRIVE_FOLDER_ID in .env (see
.env.example). The folder must be shared with the service account's email.
"""
import os

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def drive_service():
    key_file = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
    if not os.path.isabs(key_file):
        key_file = os.path.join(ROOT, key_file)
    creds = service_account.Credentials.from_service_account_file(
        key_file, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def main():
    folder_id = os.environ["GDRIVE_FOLDER_ID"]
    service = drive_service()
    query = f"'{folder_id}' in parents and trashed = false"
    page_token = None
    count = 0
    while True:
        resp = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size)",
                pageToken=page_token,
            )
            .execute()
        )
        for f in resp.get("files", []):
            count += 1
            print(f"{f['id']}  {f.get('mimeType')}  {f['name']}")
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    print(f"\n{count} files.")


if __name__ == "__main__":
    main()
