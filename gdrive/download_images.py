#!/usr/bin/env python3
"""Recurse into each product subfolder of GDRIVE_FOLDER_ID and download its
images to images/<subfolder name>/<file name>.

Requires GOOGLE_SERVICE_ACCOUNT_FILE and GDRIVE_FOLDER_ID in .env (see
.env.example). The folder must be shared with the service account's email.
"""
import io
import os
import re

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(ROOT, "images")
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


def safe_dirname(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def download_file(service, file_id, dest):
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    with open(dest, "wb") as f:
        f.write(buf.getvalue())


def main():
    root_folder_id = os.environ["GDRIVE_FOLDER_ID"]
    service = drive_service()
    subfolders = [
        f for f in list_children(service, root_folder_id) if f["mimeType"] == FOLDER_MIME
    ]
    print(f"{len(subfolders)} product folders")

    total_ok = 0
    total_fail = 0
    for sf in subfolders:
        dest_dir = os.path.join(IMG, safe_dirname(sf["name"]))
        os.makedirs(dest_dir, exist_ok=True)
        children = list_children(service, sf["id"])
        images = [c for c in children if c["mimeType"] != FOLDER_MIME]
        for img in images:
            dest = os.path.join(dest_dir, img["name"])
            try:
                download_file(service, img["id"], dest)
                total_ok += 1
                print(f"[{sf['name']}] {img['name']} -> ok")
            except Exception as e:
                total_fail += 1
                print(f"[{sf['name']}] {img['name']} -> FAIL {type(e).__name__}: {e}")

    print(f"\nDone. {total_ok} ok, {total_fail} failed.")


if __name__ == "__main__":
    main()
