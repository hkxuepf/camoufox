#!/usr/bin/env python3
"""
CamouHub Release & Kernel Automation Publisher
Automates packaging, GitHub Releases asset uploading, and metadata synchronization to CamouHub Admin Center.

Usage:
  # Publish Mac ARM64 Chrome 155 Kernel:
  python scripts/publish_release.py --type kernel --engine chromium --version 155.0.8059 --platform mac_arm64 --file path/to/archive.tar.gz

  # Publish Windows x64 Chrome 155 Kernel:
  python scripts/publish_release.py --type kernel --engine chromium --version 155.0.8059 --platform win_x64 --file path/to/archive.zip

  # Publish Desktop Client Application:
  python scripts/publish_release.py --type client --version 1.0.1 --platform mac_arm64 --file dist/CamouHub-mac-arm64.dmg
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_OWNER = "hkxuepf"
REPO_NAME = "camoufox"
ADMIN_API_BASE = os.getenv("CAMOU_API_BASE", "http://127.0.0.1:8765")


def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def github_api_request(endpoint: str, method: str = "GET", data: bytes | None = None, token: str = "", content_type: str = "application/json") -> dict:
    url = f"https://api.github.com{endpoint}" if endpoint.startswith("/") else endpoint
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "CamouHub-Release-Publisher",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    if content_type:
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_data = resp.read()
            return json.loads(resp_data.decode("utf-8")) if resp_data else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"GitHub API Error [{e.code}]: {err_msg}") from e


def get_or_create_release(tag_name: str, release_title: str, token: str) -> dict:
    try:
        return github_api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{tag_name}", token=token)
    except RuntimeError:
        print(f"[*] Release tag '{tag_name}' does not exist on GitHub. Creating new release...")
        payload = json.dumps({
            "tag_name": tag_name,
            "target_commitish": "main",
            "name": release_title,
            "body": f"Automated Release for CamouHub assets: {release_title}",
            "draft": False,
            "prerelease": False,
        }).encode("utf-8")
        return github_api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/releases", method="POST", data=payload, token=token)


def upload_asset_to_release(upload_url_template: str, filepath: Path, token: str) -> str:
    # upload_url_template looks like: https://uploads.github.com/repos/hkxuepf/camoufox/releases/123/assets{?name,label}
    base_upload_url = upload_url_template.split("{")[0]
    filename = filepath.name
    upload_url = f"{base_upload_url}?name={filename}"

    print(f"[*] Uploading binary asset '{filename}' ({filepath.stat().st_size / (1024*1024):.2f} MB)...")
    content_type = "application/gzip" if filename.endswith(".tar.gz") else "application/octet-stream"

    with open(filepath, "rb") as f:
        file_bytes = f.read()

    res = github_api_request(upload_url, method="POST", data=file_bytes, token=token, content_type=content_type)
    browser_download_url = res.get("browser_download_url")
    print(f"[✓] Asset uploaded successfully: {browser_download_url}")
    return browser_download_url


def sync_to_camou_admin(target_type: str, data: dict, token: str | None = None):
    url = f"{ADMIN_API_BASE}/api/v1/admin/releases/{target_type}"
    print(f"[*] Registering release into CamouHub Backend: {url}")
    payload = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"[✓] Successfully registered into CamouHub Admin Center: {res.get('message')}")
    except Exception as e:
        print(f"[!] Note: Could not auto-sync to local admin backend ({e}). You can copy the download URL into Admin UI manually.")


def main():
    parser = argparse.ArgumentParser(description="CamouHub Release & Kernel Publisher")
    parser.add_argument("--type", choices=["client", "kernel"], required=True, help="Release target type")
    parser.add_argument("--engine", choices=["chromium", "camoufox"], default="chromium", help="Engine type for kernels")
    parser.add_argument("--version", required=True, help="Version string (e.g. 155.0.8059 or 1.0.1)")
    parser.add_argument("--platform", choices=["mac_arm64", "mac_x64", "win_x64"], required=True, help="Operating system platform")
    parser.add_argument("--file", required=True, help="Path to asset archive (.tar.gz, .zip, .dmg, .exe)")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub Personal Access Token")
    parser.add_argument("--title", default="", help="Optional display title")

    args = parser.parse_args()
    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"[ERROR] File does not exist: {file_path}", file=sys.stderr)
        sys.exit(1)

    if not args.token:
        print("[!] GITHUB_TOKEN not provided. Please provide --token or export GITHUB_TOKEN=<pat>", file=sys.stderr)
        print(f"[i] File SHA256: {calculate_sha256(file_path)}")
        sys.exit(1)

    sha256 = calculate_sha256(file_path)
    print(f"[*] Target: {args.type} | Version: {args.version} | Platform: {args.platform}")
    print(f"[*] File: {file_path.name} | SHA256: {sha256}")

    # Tag convention: v155.0 for kernel, v1.0.1 for client
    if args.type == "kernel":
        tag = f"v{args.version.split('.')[0]}.0" if "." in args.version else f"v{args.version}"
        release_title = f"{args.engine.capitalize()} Kernel {args.version}"
    else:
        tag = f"v{args.version}"
        release_title = f"CamouHub Desktop {args.version}"

    release_info = get_or_create_release(tag, release_title, args.token)
    upload_url_template = release_info["upload_url"]
    download_url = upload_asset_to_release(upload_url_template, file_path, args.token)

    # Sync to backend
    if args.type == "kernel":
        kernel_data = {
            "engine": args.engine,
            "version": args.version,
            "display_name": args.title or f"{'Chrome' if args.engine == 'chromium' else 'Camoufox'} {args.version}",
            "is_recommended": True,
            "is_active": True,
        }
        if args.platform == "mac_arm64":
            kernel_data["mac_arm64_url"] = download_url
            kernel_data["mac_arm64_sha256"] = sha256
        elif args.platform == "mac_x64":
            kernel_data["mac_x64_url"] = download_url
            kernel_data["mac_x64_sha256"] = sha256
        elif args.platform == "win_x64":
            kernel_data["win_x64_url"] = download_url
            kernel_data["win_x64_sha256"] = sha256

        sync_to_camou_admin("kernel", kernel_data)
    else:
        client_data = {
            "version": args.version,
            "title": args.title or f"CamouHub {args.version}",
            "is_active": True,
        }
        if args.platform == "mac_arm64":
            client_data["mac_arm64_url"] = download_url
        elif args.platform == "mac_x64":
            client_data["mac_x64_url"] = download_url
        elif args.platform == "win_x64":
            client_data["win_x64_url"] = download_url

        sync_to_camou_admin("client", client_data)

    print("\n[🎉 SUCCESS] Release packaging, GitHub upload, and Admin Hub sync complete!")


if __name__ == "__main__":
    main()
