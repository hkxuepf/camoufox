"""Fingerprint Mutation Engine (Re-Roll).

Generates a fresh, realistic, and coherent hardware fingerprint tuple (GPU, CPU, RAM, Screen, UA)
to mutate a profile's identity without losing cookies, saved credentials, or session storage.
"""

import random
from typing import Any

from camoufox_pm.core.models import BrowserSettings

# Windows Hardware Profiles
WIN_GPUS = [
    {
        "vendor": "Google Inc. (NVIDIA)",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (NVIDIA)",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (NVIDIA)",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (NVIDIA)",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (AMD)",
        "renderer": "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (AMD)",
        "renderer": "ANGLE (AMD, AMD Radeon RX 7600 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (Intel)",
        "renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (Intel)",
        "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
]

WIN_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
]

# macOS Hardware Profiles
MAC_GPUS = [
    {
        "vendor": "Google Inc. (Apple)",
        "renderer": "ANGLE (Apple, Apple M1, OpenGL 4.1)",
    },
    {
        "vendor": "Google Inc. (Apple)",
        "renderer": "ANGLE (Apple, Apple M2, OpenGL 4.1)",
    },
    {
        "vendor": "Google Inc. (Apple)",
        "renderer": "ANGLE (Apple, Apple M3, OpenGL 4.1)",
    },
    {
        "vendor": "Google Inc. (Apple)",
        "renderer": "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)",
    },
    {
        "vendor": "Google Inc. (Apple)",
        "renderer": "ANGLE (Apple, Apple M2 Max, OpenGL 4.1)",
    },
]

MAC_UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]

SCREENS_COMMON = [
    ("1920x1080", 1280, 720),
    ("1920x1080", 1366, 768),
    ("2560x1440", 1440, 900),
    ("1920x1200", 1400, 850),
    ("1680x1050", 1200, 750),
]


def mutate_browser_settings(settings: BrowserSettings) -> tuple[BrowserSettings, dict[str, Any]]:
    """Mutate and re-roll the hardware fingerprint components of a BrowserSettings instance."""
    target_os = (settings.os or "windows").lower()
    is_mac = "mac" in target_os

    # 1. Pick fresh GPU
    gpu_pool = MAC_GPUS if is_mac else WIN_GPUS
    # Avoid picking the exact same renderer if possible
    available_gpus = [g for g in gpu_pool if g["renderer"] != settings.webgl_renderer]
    new_gpu = random.choice(available_gpus if available_gpus else gpu_pool)

    # 2. Pick fresh CPU & Memory
    if is_mac:
        new_cpu = random.choice([8, 10, 12])
        new_ram = random.choice([8, 16, 24, 32])
    else:
        new_cpu = random.choice([4, 6, 8, 12, 16])
        new_ram = random.choice([8, 16, 32])

    # 3. Pick fresh Screen & Window Size
    screen_tuple = random.choice(SCREENS_COMMON)
    new_screen, new_w, new_h = screen_tuple

    # 4. Pick fresh User-Agent dynamically jittered from real active kernel
    from camoufox_pm.core.kernel_manager import kernel_manager
    new_ua = kernel_manager.generate_jittered_ua(os_name="macos" if is_mac else "windows")

    # Clone settings and update fields
    updated_dict = settings.model_dump()
    updated_dict.update({
        "webgl_vendor": new_gpu["vendor"],
        "webgl_renderer": new_gpu["renderer"],
        "hardware_concurrency": new_cpu,
        "device_memory": new_ram,
        "screen": new_screen,
        "window_width": new_w,
        "window_height": new_h,
        "user_agent": new_ua,
        "canvas_noise": True,
        "audio_noise": True,
        "client_rects_noise": True,
        "font_masking": True,
        "clipboard_isolation": True,
    })

    new_settings = BrowserSettings(**updated_dict)

    mutated_diff = {
        "webgl_renderer": new_gpu["renderer"],
        "hardware_concurrency": f"{new_cpu} Cores",
        "device_memory": f"{new_ram} GB",
        "screen": new_screen,
        "window_size": f"{new_w}x{new_h}",
        "user_agent": new_ua,
    }

    return new_settings, mutated_diff
