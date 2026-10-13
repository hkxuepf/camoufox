#!/usr/bin/env python3
"""Upload compiled Chromium binaries to Cloudflare R2 bucket."""

import hashlib
import json
import os
import sys
from pathlib import Path
import boto3
from botocore.config import Config

R2_ACCESS_KEY_ID = "9f12c91813dddea0d5fe6c63963dadf5"
R2_SECRET_ACCESS_KEY = "6ae268a165e49f6c05de633b037177606bef740ff991ab7db9c29f9254d2f4a1"
R2_ENDPOINT = "https://a416a58f6b1d69a87d52bf0c70c27163.r2.cloudflarestorage.com"
R2_BUCKET = "tikmatrix"
R2_PREFIX = "camoufox"

TAR_PATH = Path("/tmp/chromium-macos-arm64.tar.gz")
DMG_PATH = Path("/Users/fgwl/docker/ungoogled-chromium-macos/build/ungoogled-chromium_154.0.8037.97-1.1_macos.dmg")

def get_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    return h.hexdigest()

def upload():
    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )

    if TAR_PATH.exists():
        print(f"Calculating SHA-256 for {TAR_PATH} ({TAR_PATH.stat().st_size / 1024 / 1024:.1f} MB)...")
        tar_sha256 = get_sha256(TAR_PATH)
        key = f"{R2_PREFIX}/chromium-macos-arm64.tar.gz"
        print(f"Uploading {TAR_PATH} -> s3://{R2_BUCKET}/{key}...")
        s3.upload_file(str(TAR_PATH), R2_BUCKET, key)
        print(f"Uploaded {key} successfully!")

        meta = {
            "version": "154.0.8037.97",
            "os": "darwin",
            "arch": "arm64",
            "filename": "chromium-macos-arm64.tar.gz",
            "size": TAR_PATH.stat().st_size,
            "sha256": tar_sha256,
        }
        meta_key = f"{R2_PREFIX}/chromium_version.json"
        print(f"Uploading metadata -> s3://{R2_BUCKET}/{meta_key}...")
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=meta_key,
            Body=json.dumps(meta, indent=2).encode(),
            ContentType="application/json",
        )
        print("Metadata uploaded!")

    if DMG_PATH.exists():
        dmg_key = f"{R2_PREFIX}/{DMG_PATH.name}"
        print(f"Uploading {DMG_PATH} -> s3://{R2_BUCKET}/{dmg_key} ({DMG_PATH.stat().st_size / 1024 / 1024:.1f} MB)...")
        s3.upload_file(str(DMG_PATH), R2_BUCKET, dmg_key)
        print(f"Uploaded {dmg_key} successfully!")

    print("\nAll files uploaded to Cloudflare R2 successfully!")

if __name__ == "__main__":
    upload()
