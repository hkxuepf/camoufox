#!/usr/bin/env python3
"""
Sync upstream CloakBrowser and Camoufox kernels to hkxuepf/camoufox/releases.
Downloads binaries from official releases and re-hosts them under our private repository.
"""

import os
import sys
import time
import json
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

GITHUB_TOKEN = "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"
DIST_DIR = Path("/Users/fgwl/docker/camoufox/dist")
DIST_DIR.mkdir(parents=True, exist_ok=True)

SYNC_TASKS = [
    {
        "name": "Camoufox 135 macOS (arm64)",
        "source_url": "https://github.com/daijro/camoufox/releases/download/v135.0.1-beta.24/camoufox-135.0.1-beta.24-mac.arm64.zip",
        "target_release_id": 414836208,
        "target_filename": "camoufox-135.0-mac-arm64.zip",
        "content_type": "application/zip",
    },
    {
        "name": "Camoufox 135 Windows (x64)",
        "source_url": "https://github.com/daijro/camoufox/releases/download/v135.0.1-beta.24/camoufox-135.0.1-beta.24-win.x86_64.zip",
        "target_release_id": 414836208,
        "target_filename": "camoufox-135.0-win-x64.zip",
        "content_type": "application/zip",
    },
    {
        "name": "Cloak Chromium 146 Windows (x64)",
        "source_url": "https://github.com/CloakHQ/CloakBrowser/releases/download/chromium-v146.0.7680.177.4/cloakbrowser-windows-x64.zip",
        "target_release_id": 414836191,
        "target_filename": "cloak-chromium-146.0.7680-win-x64.zip",
        "content_type": "application/zip",
    },
    {
        "name": "Cloak Chromium 146 macOS (arm64)",
        "source_url": "https://github.com/CloakHQ/CloakBrowser/releases/download/chromium-v145.0.7632.109.2/cloakbrowser-darwin-arm64.tar.gz",
        "target_release_id": 414836191,
        "target_filename": "cloak-chromium-146.0.7680-mac-arm64.tar.gz",
        "content_type": "application/gzip",
    },
]


def download_file(url: str, dest_path: Path):
    print(f"\n[1/3] Downloading {url} -> {dest_path.name}...")
    start_t = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        last_log = time.time()
        while chunk := resp.read(1024 * 1024 * 2):
            f.write(chunk)
            downloaded += len(chunk)
            if time.time() - last_log > 5:
                pct = (downloaded / total_size * 100) if total_size else 0
                print(f"      Downloaded {downloaded / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB ({pct:.1f}%)...")
                last_log = time.time()
    elapsed = time.time() - start_t
    print(f"[✓] Downloaded {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.1f} MB in {elapsed:.1f}s)")


def calculate_sha256(filepath: Path) -> str:
    print(f"[2/3] Calculating SHA256 for {filepath.name}...")
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024 * 4):
            h.update(chunk)
    digest = h.hexdigest()
    print(f"[✓] SHA256: {digest}")
    return digest


def upload_to_release(release_id: int, filename: str, filepath: Path, content_type: str) -> str:
    print(f"[3/3] Uploading {filename} to GitHub Release {release_id}...")
    filesize = filepath.stat().st_size
    upload_url = f"https://uploads.github.com/repos/hkxuepf/camoufox/releases/{release_id}/assets?name={filename}"
    start_t = time.time()

    with open(filepath, "rb") as f:
        req = urllib.request.Request(
            upload_url,
            data=f,
            headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "User-Agent": "CamouHub-Release-Publisher",
                "Content-Type": content_type,
                "Content-Length": str(filesize),
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode())
            elapsed = time.time() - start_t
            url = res.get("browser_download_url")
            print(f"[✓] Successfully uploaded in {elapsed:.1f}s ({filesize / (1024*1024*elapsed):.2f} MB/s) -> {url}")
            return url


def main():
    print(f"=== CamouHub Kernel Upstream Synchronization Pipeline ===")
    print(f"Target Repository: hkxuepf/camoufox")
    print(f"Total tasks: {len(SYNC_TASKS)}\n")

    results = []

    for idx, task in enumerate(SYNC_TASKS, 1):
        print(f"\n[{idx}/{len(SYNC_TASKS)}] Starting: {task['name']}")
        dest_file = DIST_DIR / task["target_filename"]

        if not dest_file.exists() or dest_file.stat().st_size == 0:
            download_file(task["source_url"], dest_file)
        else:
            print(f"[*] Reusing existing local file: {dest_file.name} ({dest_file.stat().st_size / (1024*1024):.1f} MB)")

        sha256 = calculate_sha256(dest_file)
        download_url = upload_to_release(
            task["target_release_id"],
            task["target_filename"],
            dest_file,
            task["content_type"]
        )

        results.append({
            "name": task["name"],
            "filename": task["target_filename"],
            "url": download_url,
            "sha256": sha256,
            "size_bytes": dest_file.stat().st_size
        })

    print("\n=======================================================")
    print("All kernel sync tasks completed successfully!")
    print(json.dumps(results, indent=2))

    with open(DIST_DIR / "synced_kernels_manifest.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
