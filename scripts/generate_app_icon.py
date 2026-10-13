#!/usr/bin/env python3
"""Generate a pristine macOS .icns app icon for CamouHub matching its brand identity."""

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"
ICONSET_DIR = PACKAGING / "CamouHub.iconset"
ICNS_FILE = PACKAGING / "CamouHub.icns"
MASTER_PNG = PACKAGING / "master_1024.png"

HTML_CONTENT = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1024px;
    height: 1024px;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .icon-canvas {
    position: relative;
    width: 824px;
    height: 824px;
    border-radius: 185px;
    background: linear-gradient(135deg, #1664ff 0%, #3882ff 45%, #7928ca 100%);
    box-shadow:
      0 40px 80px rgba(22, 100, 255, 0.35),
      0 16px 32px rgba(15, 23, 42, 0.25),
      inset 0 1px 2px rgba(255, 255, 255, 0.6),
      inset 0 -2px 4px rgba(0, 0, 0, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  /* Subtle glass sheen across top half */
  .sheen {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 50%;
    background: linear-gradient(180deg, rgba(255,255,255,0.22) 0%, rgba(255,255,255,0) 100%);
    pointer-events: none;
  }
  /* Subtle inner tech grid pattern */
  .grid-pattern {
    position: absolute;
    inset: 0;
    background-image: 
      radial-gradient(circle at 50% 30%, rgba(255, 255, 255, 0.15) 0%, transparent 60%),
      radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
    background-size: 100% 100%, 36px 36px;
    pointer-events: none;
  }
  .shield-svg {
    width: 480px;
    height: 480px;
    filter: drop-shadow(0 14px 28px rgba(0, 0, 0, 0.25));
  }
</style>
</head>
<body>
  <div class="icon-canvas">
    <div class="sheen"></div>
    <div class="grid-pattern"></div>
    <svg class="shield-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <defs>
        <linearGradient id="shieldFill" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#ffffff" stop-opacity="0.98"/>
          <stop offset="100%" stop-color="#edf2f7" stop-opacity="0.90"/>
        </linearGradient>
        <linearGradient id="accentStroke" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#1664ff"/>
          <stop offset="100%" stop-color="#7928ca"/>
        </linearGradient>
      </defs>
      <!-- Shield Outer Contour -->
      <path
        d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"
        fill="url(#shieldFill)"
        stroke="rgba(255,255,255,0.9)"
        stroke-width="0.8"
      />
      <!-- Futuristic Inner Biometric & Circuit Core -->
      <path
        d="M12 8v4"
        stroke="url(#accentStroke)"
        stroke-width="1.8"
        stroke-linecap="round"
      />
      <circle
        cx="12"
        cy="15"
        r="1.2"
        fill="url(#accentStroke)"
      />
      <path
        d="M9 11.5a4.2 4.2 0 0 1 6 0"
        stroke="url(#accentStroke)"
        stroke-width="1.6"
        stroke-linecap="round"
      />
      <path
        d="M7.5 9a6.2 6.2 0 0 1 9 0"
        stroke="url(#accentStroke)"
        stroke-width="1.4"
        stroke-linecap="round"
      />
    </svg>
  </div>
</body>
</html>
"""

async def generate():
    async with async_playwright() as p:
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        browser = await p.chromium.launch(executable_path=chrome_path)
        page = await browser.new_page(viewport={"width": 1024, "height": 1024}, device_scale_factor=1)
        await page.set_content(HTML_CONTENT)
        await page.screenshot(path=str(MASTER_PNG), omit_background=True)
        await browser.close()
    print(f"Generated master 1024x1024 PNG at {MASTER_PNG}")

    # Build iconset
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)

    sizes = [
        ("16x16", 16),
        ("16x16@2x", 32),
        ("32x32", 32),
        ("32x32@2x", 64),
        ("128x128", 128),
        ("128x128@2x", 256),
        ("256x256", 256),
        ("256x256@2x", 512),
        ("512x512", 512),
        ("512x512@2x", 1024),
    ]

    for name, sz in sizes:
        dest = ICONSET_DIR / f"icon_{name}.png"
        subprocess.run(["sips", "-z", str(sz), str(sz), str(MASTER_PNG), "--out", str(dest)], check=True, capture_output=True)

    # Convert iconset to .icns
    subprocess.run(["iconutil", "-c", "icns", str(ICONSET_DIR), "-o", str(ICNS_FILE)], check=True)
    print(f"Successfully generated macOS icon at {ICNS_FILE}")

if __name__ == "__main__":
    asyncio.run(generate())
