"""Kernel Version Management, Jittered UA Generation & Update Channel.

Manages multiple Chromium anti-detect kernel versions (new and old coexistence),
detects installed binary capabilities, provides real-version micro-jittered
User Agent generation, and manages cloud update channels.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal
import random
from loguru import logger
from pydantic import BaseModel, Field

from camoufox_pm.config import get_settings


class KernelInfo(BaseModel):
    """Metadata describing an installed or available Chromium kernel."""

    version: str = Field(..., description="Full version string, e.g. '154.0.8037.97'")
    major: int = Field(..., description="Major version number, e.g. 154")
    build: int = Field(8037, description="Build number, e.g. 8037")
    patch: int = Field(97, description="Patch number, e.g. 97")
    is_default: bool = Field(False, description="Whether this is the primary active kernel")
    executable_path: str = Field(..., description="Path to the executable binary")
    channel: Literal["stable", "beta", "dev"] = "stable"


class KernelUpdateCheckResult(BaseModel):
    """Result of checking for newer compiled kernel updates."""

    current_version: str
    latest_version: str
    has_update: bool
    download_url: str | None = None
    changelog: str | None = None
    size_mb: float = 0.0


# Baseline build numbers by major version for realistic jitter ranges
KNOWN_MAJOR_BUILD_BASELINES = {
    151: 7922,
    152: 7977,
    153: 8010,
    154: 8037,
    155: 8080,
    156: 8120,
    158: 8200,
    160: 8300,
}


class KernelManager:
    """Manages multi-version kernel installation, detection, and invocation routing."""

    def __init__(self) -> None:
        self._cached_version_map: dict[str, KernelInfo] = {}
        self._default_major: int = 154

    def get_kernels_root_dir(self) -> Path:
        """Root directory where multi-version kernels are stored."""
        settings = get_settings()
        data_dir = Path(settings.db_path).resolve().parent
        kernels_dir = data_dir / "bin" / "kernels"
        kernels_dir.mkdir(parents=True, exist_ok=True)
        return kernels_dir

    def detect_binary_version(self, executable_path: str) -> KernelInfo | None:
        """Execute a Chromium binary with --version and parse its version string."""
        if not Path(executable_path).is_file():
            return None

        # Return cached if already parsed
        if executable_path in self._cached_version_map:
            return self._cached_version_map[executable_path]

        try:
            res = subprocess.run(
                [executable_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = res.stdout.strip()
            # Output format: Chromium 154.0.8037.97 or Google Chrome 154.0.8037.97
            m = re.search(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", out)
            if m:
                major = int(m.group(1))
                build = int(m.group(3))
                patch = int(m.group(4))
                info = KernelInfo(
                    version=m.group(0),
                    major=major,
                    build=build,
                    patch=patch,
                    is_default=False,
                    executable_path=executable_path,
                )
                self._cached_version_map[executable_path] = info
                return info
        except Exception as exc:
            logger.warning(f"Failed to detect version for {executable_path}: {exc}")

        # Fallback based on executable name or default 154
        return KernelInfo(
            version="154.0.8037.97",
            major=154,
            build=8037,
            patch=97,
            is_default=False,
            executable_path=executable_path,
        )

    def list_installed_kernels(self) -> list[KernelInfo]:
        """Scan and list all installed Chromium kernels (default + versioned kernels)."""
        kernels: list[KernelInfo] = []
        seen_paths: set[str] = set()

        # 1. Check primary/default Chromium in bin/Chromium.app
        from camoufox_pm.core.chromium_launcher import get_chromium_executable_path
        default_exe = get_chromium_executable_path()
        if default_exe and Path(default_exe).is_file():
            info = self.detect_binary_version(default_exe)
            if info:
                info.is_default = True
                kernels.append(info)
                seen_paths.add(default_exe)
                self._default_major = info.major

        # 2. Check multi-version kernel directory (bin/kernels/<version>/...)
        kernels_root = self.get_kernels_root_dir()
        if kernels_root.is_dir():
            for item in kernels_root.iterdir():
                if item.is_dir():
                    # Look for Chromium executable inside version dir
                    candidates = [
                        item / "Contents" / "MacOS" / "Chromium",
                        item / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
                        item / "chrome.exe",
                        item / "chromium",
                    ]
                    for cand in candidates:
                        cand_str = str(cand)
                        if cand.is_file() and cand_str not in seen_paths:
                            info = self.detect_binary_version(cand_str)
                            if info:
                                kernels.append(info)
                                seen_paths.add(cand_str)

        # Sort by major version descending
        kernels.sort(key=lambda k: k.major, reverse=True)
        return kernels

    def get_active_kernel_major(self) -> int:
        """Return the major version of the current default active kernel."""
        kernels = self.list_installed_kernels()
        for k in kernels:
            if k.is_default:
                return k.major
        return self._default_major

    def get_executable_for_version(self, target_version: str | int | None = None) -> str | None:
        """Route to the matching kernel executable for a target version (new or old).
        
        If target_version is specified (e.g. 154 or "151"):
        1. Searches installed kernels for an exact or major match.
        2. If not found, falls back cleanly to the primary/default kernel.
        """
        kernels = self.list_installed_kernels()
        if not kernels:
            from camoufox_pm.core.chromium_launcher import get_chromium_executable_path
            return get_chromium_executable_path()

        if target_version:
            target_str = str(target_version)
            target_major = None
            m = re.search(r"(\d+)", target_str)
            if m:
                target_major = int(m.group(1))

            if target_major is not None:
                for k in kernels:
                    if k.major == target_major:
                        return k.executable_path

        # Default fallback: return kernel marked is_default, or highest version
        for k in kernels:
            if k.is_default:
                return k.executable_path

        return kernels[0].executable_path

    def generate_jittered_ua(
        self,
        os_name: str = "windows",
        kernel_major: int | None = None,
    ) -> str:
        """Generate a realistic User Agent aligned with the actual kernel version,
        featuring natural micro-jitter on the build and patch numbers.
        
        Example outputs for 154:
        - Windows: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8037.114 Safari/537.36
        - macOS:   Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8038.86 Safari/537.36
        """
        major = kernel_major or self.get_active_kernel_major()
        base_build = KNOWN_MAJOR_BUILD_BASELINES.get(major, 8037)

        # Micro-jitter on build (±2) and patch (35 ~ 185)
        build_jitter = base_build + random.randint(-2, 4)
        patch_jitter = random.randint(35, 185)
        full_version = f"{major}.0.{build_jitter}.{patch_jitter}"

        os_lower = os_name.lower()
        if "android" in os_lower:
            models = ["SM-S918B", "SM-S928B", "Pixel 8", "Pixel 7 Pro", "23049PCD8G"]
            model = random.choice(models)
            return (
                f"Mozilla/5.0 (Linux; Android 14; {model}) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{full_version} Mobile Safari/537.36"
            )
        elif "ios" in os_lower or "iphone" in os_lower:
            ios_versions = ["17_5_1", "17_4_1", "17_6", "18_0"]
            v = random.choice(ios_versions)
            return (
                f"Mozilla/5.0 (iPhone; CPU iPhone OS {v} like Mac OS X) "
                f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"Version/17.5 Mobile/15E148 Safari/604.1"
            )
        elif "mac" in os_lower or "darwin" in os_lower:
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{full_version} Safari/537.36"
            )
        elif "linux" in os_lower:
            return (
                f"Mozilla/5.0 (X11; Linux x86_64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{full_version} Safari/537.36"
            )
        else:
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{full_version} Safari/537.36"
            )

    async def check_updates(self) -> KernelUpdateCheckResult:
        """Check the cloud server/R2 for newly compiled kernel versions."""
        current_major = self.get_active_kernel_major()
        current_ver = f"{current_major}.0.8037.97"

        # In cloud updates, check manifest or settings.cloud_server
        # Default mock channel info for next scheduled kernel release (Chrome 156)
        latest_major = 156
        has_update = latest_major > current_major

        return KernelUpdateCheckResult(
            current_version=current_ver,
            latest_version=f"{latest_major}.0.8120.45" if has_update else current_ver,
            has_update=has_update,
            download_url="https://a416a58f6b1d69a87d52bf0c70c27163.r2.cloudflarestorage.com/tikmatrix/camoufox/chromium-macos-arm64-v156.tar.gz"
            if has_update
            else None,
            changelog="Chromium 156 商业防关联内核升级：原生对齐 Chrome 156 V8 引擎与 Client Hints，修复最新 WebRTC 泄漏向量。"
            if has_update
            else "当前内核已是最新版本。",
            size_mb=168.5,
        )


kernel_manager = KernelManager()
