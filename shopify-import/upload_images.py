#!/usr/bin/env python3
"""Upload a SKU's photos from the shared Google Drive folder to its Shopify product.

Finds the Drive subfolder named exactly <SKU> inside the shared folder
(GDRIVE_FOLDER_ID in ../gdrive/.env — the SLOY photos folder, subfoldered by
SKU), downloads its images, and attaches them to the Shopify product with
that SKU via Shopify's staged-upload flow.

Needs the Google API client, so run it with the gdrive/ venv:
  source ../gdrive/.venv/bin/activate
  python3 upload_images.py AKC-151 --dry-run   # list images, no upload
  python3 upload_images.py AKC-151             # upload to Shopify
"""
import argparse
import io
import os
import sys
import urllib.request
import uuid

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from sheet_to_shopify import Shopify, load_env as load_shopify_env

ROOT = os.path.dirname(os.path.abspath(__file__))
GDRIVE_DIR = os.path.join(ROOT, "..", "gdrive")
FOLDER_MIME = "application/vnd.google-apps.folder"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def load_gdrive_env():
    load_dotenv(os.path.join(GDRIVE_DIR, ".env"))
    key_file = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
    if not os.path.isabs(key_file):
        key_file = os.path.join(GDRIVE_DIR, key_file)
    return key_file, os.environ["GDRIVE_FOLDER_ID"]


def drive_service(key_file):
    creds = service_account.Credentials.from_service_account_file(key_file, scopes=DRIVE_SCOPES)
    return build("drive", "v3", credentials=creds)


def find_sku_folder(drive, root_folder_id, sku):
    safe_sku = sku.replace("'", "\\'")
    query = (
        f"'{root_folder_id}' in parents and trashed = false "
        f"and mimeType = '{FOLDER_MIME}' and name = '{safe_sku}'"
    )
    resp = drive.files().list(q=query, fields="files(id, name)").execute()
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def list_images(drive, folder_id):
    query = f"'{folder_id}' in parents and trashed = false and mimeType contains 'image/'"
    files = []
    page_token = None
    while True:
        resp = (
            drive.files()
            .list(q=query, fields="nextPageToken, files(id, name, mimeType)", pageToken=page_token)
            .execute()
        )
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def download_file(drive, file_id):
    request = drive.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


STAGED_UPLOADS_CREATE = """
mutation($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""

PRODUCT_CREATE_MEDIA = """
mutation($productId: ID!, $media: [CreateMediaInput!]!) {
  productCreateMedia(productId: $productId, media: $media) {
    media { alt mediaContentType status }
    mediaUserErrors { field message }
  }
}
"""


def stage_upload(shop, filename, mime_type, size):
    data = shop.gql(STAGED_UPLOADS_CREATE, {"input": [{
        "filename": filename,
        "mimeType": mime_type,
        "fileSize": str(size),
        "resource": "IMAGE",
        "httpMethod": "POST",
    }]})
    result = data["stagedUploadsCreate"]
    if result["userErrors"]:
        raise RuntimeError(str(result["userErrors"]))
    return result["stagedTargets"][0]


def post_multipart(url, fields, file_field, filename, content, content_type):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields:
        parts.append(f"--{boundary}".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        parts.append(b"")
        parts.append(str(value).encode())
    parts.append(f"--{boundary}".encode())
    parts.append(f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"'.encode())
    parts.append(f"Content-Type: {content_type}".encode())
    parts.append(b"")
    parts.append(content)
    parts.append(f"--{boundary}--".encode())
    parts.append(b"")
    body = b"\r\n".join(parts)

    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        resp.read()


def upload_to_staged_target(target, filename, content, mime_type):
    fields = [(p["name"], p["value"]) for p in target["parameters"]]
    post_multipart(target["url"], fields, "file", filename, content, mime_type)


def attach_media(shop, product_id, resource_url, alt):
    data = shop.gql(PRODUCT_CREATE_MEDIA, {
        "productId": product_id,
        "media": [{"originalSource": resource_url, "mediaContentType": "IMAGE", "alt": alt}],
    })
    result = data["productCreateMedia"]
    if result["mediaUserErrors"]:
        raise RuntimeError(str(result["mediaUserErrors"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sku")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key_file, root_folder_id = load_gdrive_env()
    drive = drive_service(key_file)

    folder_id = find_sku_folder(drive, root_folder_id, args.sku)
    if not folder_id:
        sys.exit(f"No folder named '{args.sku}' found in the Drive folder.")

    images = list_images(drive, folder_id)
    if not images:
        sys.exit(f"Folder '{args.sku}' has no images.")

    if args.dry_run:
        for img in images:
            print(f"{img['name']}  ({img['mimeType']})")
        print(f"\n{len(images)} images would be uploaded for {args.sku}.")
        return

    env = load_shopify_env()
    shop = Shopify(env)
    product_id, _ = shop.find_by_sku(args.sku)
    if not product_id:
        sys.exit(f"No Shopify product found with SKU '{args.sku}'.")

    for i, img in enumerate(images, 1):
        content = download_file(drive, img["id"])
        target = stage_upload(shop, img["name"], img["mimeType"], len(content))
        upload_to_staged_target(target, img["name"], content, img["mimeType"])
        attach_media(shop, product_id, target["resourceUrl"], f"{args.sku} {i}")
        print(f"[{i}/{len(images)}] {img['name']}: uploaded")

    print(f"\nDone. {len(images)} images attached to {args.sku}.")


if __name__ == "__main__":
    main()
