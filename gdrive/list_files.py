#!/usr/bin/env python3
"""List files in the shared Google Drive folder using a service account,
recursing into subfolders.

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
FOLDER_MIME = "application/vnd.google-apps.folder"


def drive_service():
    key_file = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
    if not os.path.isabs(key_file):
        key_file = os.path.join(ROOT, key_file)
    creds = service_account.Credentials.from_service_account_file(
        key_file, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def list_children(service, folder_id):
    files = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed = false"
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
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def walk(service, folder_id, path, count):
    for f in list_children(service, folder_id):
        item_path = f"{path}/{f['name']}"
        if f["mimeType"] == FOLDER_MIME:
            count = walk(service, f["id"], item_path, count)
        else:
            count += 1
            print(f"{f['id']}  {f.get('mimeType')}  {item_path}")
    return count


def main():
    folder_id = os.environ["GDRIVE_FOLDER_ID"]
    service = drive_service()
    count = walk(service, folder_id, "", 0)
    print(f"\n{count} files.")


if __name__ == "__main__":
    main()
