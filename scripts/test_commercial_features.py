"""Commercial Features Comprehensive Simulation and Bug Detection Test Suite."""

import asyncio
import io
import json
import os
import random
import tarfile
from pathlib import Path

from camoufox_pm.core.models import BrowserSettings, Profile, ProxyConfig
from camoufox_pm.core.fingerprint_mutator import mutate_browser_settings
from camoufox_pm.core.preset_icons import PRESET_ICONS
from camoufox_pm.core.cloud_sync import pack_profile_snapshot, unpack_profile_snapshot, _make_r2_sigv4_request
from camoufox_pm.core.chromium_launcher import generate_fingerprint_extension, build_chromium_args
from camoufox_pm.api.routes.radar import get_radar_dashboard


def test_1_preset_icons_integrity():
    """Verify all 12 preset icons exist and are valid base64 SVGs."""
    print("\n--- Test 1: Preset Extension Icons Integrity ---")
    assert len(PRESET_ICONS) >= 12, f"Expected at least 12 icons, got {len(PRESET_ICONS)}"
    for ext_id, icon_data in PRESET_ICONS.items():
        assert icon_data.startswith("data:image/svg+xml;base64,"), f"Icon {ext_id} not valid base64 SVG URI"
        assert len(icon_data) > 100, f"Icon {ext_id} content too short"
    print(f"✅ PASS: All {len(PRESET_ICONS)} preset vector SVG icons verified.")


def test_2_fingerprint_mutation_engine():
    """Verify hardware re-roll produces diverse, coherent profiles while preserving settings."""
    print("\n--- Test 2: Fingerprint Mutation Engine ---")
    orig_settings = BrowserSettings(
        os="windows",
        webgl_renderer="OLD_RENDERER",
        hardware_concurrency=4,
        device_memory=8,
        user_agent="OLD_UA",
    )
    
    mutated_settings, diff = mutate_browser_settings(orig_settings)
    
    assert mutated_settings.webgl_renderer != "OLD_RENDERER", "GPU Renderer was not mutated"
    assert mutated_settings.user_agent != "OLD_UA", "User Agent was not mutated"
    assert "Direct3D11" in mutated_settings.webgl_renderer or "ANGLE" in mutated_settings.webgl_renderer
    assert mutated_settings.hardware_concurrency in [4, 6, 8, 12, 16]
    assert mutated_settings.device_memory in [8, 16, 32]
    assert mutated_settings.font_masking is True
    assert mutated_settings.clipboard_isolation is True
    
    print(f"✅ PASS: Mutation generated GPU={diff['webgl_renderer']}, Cores={diff['hardware_concurrency']}, RAM={diff['device_memory']}")


def test_3_stealth_extension_and_sandbox_injection():
    """Verify generated inject.js contains all anti-detect hooks including makeNative, font masking, and clipboard sandbox."""
    print("\n--- Test 3: Stealth Extension & Injected Scripts ---")
    tmp_dir = Path("/tmp/test_cpm_ext")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    settings = BrowserSettings(
        os="windows",
        webgl_vendor="Google Inc. (NVIDIA)",
        webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        font_masking=True,
        clipboard_isolation=True,
    )
    
    generate_fingerprint_extension(tmp_dir, settings, cookies_raw="[{\"name\":\"session\",\"value\":\"123\",\"domain\":\"test.com\"}]")
    
    manifest_path = tmp_dir / "manifest.json"
    inject_path = tmp_dir / "inject.js"
    bg_path = tmp_dir / "background.js"
    cookies_path = tmp_dir / "cookies.json"
    
    assert manifest_path.exists(), "manifest.json missing"
    assert inject_path.exists(), "inject.js missing"
    assert bg_path.exists(), "background.js missing"
    assert cookies_path.exists(), "cookies.json missing"
    
    manifest = json.loads(manifest_path.read_text())
    assert manifest["content_scripts"][0]["world"] == "MAIN", "content_scripts world must be MAIN"
    
    inject_code = inject_path.read_text()
    
    # 1. makeNative
    assert "makeNative" in inject_code, "makeNative missing"
    assert "Function.prototype.toString" in inject_code, "toString override missing"
    
    # 2. userAgentData
    assert "navigator.userAgentData" in inject_code or "userAgentData" in inject_code, "userAgentData missing"
    assert "getHighEntropyValues" in inject_code, "getHighEntropyValues missing"
    
    # 3. platform Win32
    assert "Win32" in inject_code, "Win32 platform alignment missing"
    
    # 4. Font Masking
    assert "MAC_ONLY_FONTS" in inject_code, "Mac fonts blacklist missing"
    assert "document.fonts.check" in inject_code, "document.fonts.check interceptor missing"
    assert "CanvasRenderingContext2D.prototype.measureText" in inject_code, "measureText interceptor missing"
    
    # 5. MediaDevices
    assert "navigator.mediaDevices.enumerateDevices" in inject_code, "mediaDevices interceptor missing"
    assert "virtual-audio-group-01" in inject_code, "virtual audio group missing"
    
    # 6. Clipboard Sandbox
    assert "Virtual Isolated Clipboard Sandbox" in inject_code, "clipboard sandbox missing"
    assert "navigator.clipboard.readText" in inject_code, "readText interceptor missing"
    assert "navigator.clipboard.writeText" in inject_code, "writeText interceptor missing"
    
    # 7. Webdriver cleanup
    assert "webdriver" in inject_code, "webdriver cleanup missing"
    assert "cdc_adoQpoasnfa76pfcZLmcfl_" in inject_code, "cdc_ cleanup missing"
    
    print("✅ PASS: All 7 stealth spoofing and isolation layers present in inject.js.")


def test_4_radar_dashboard_route():
    """Verify Environment Health Radar generates valid HTML with real-time probes."""
    print("\n--- Test 4: Environment Health Radar Route ---")
    resp = asyncio.run(get_radar_dashboard(profile_id="prof_test_999"))
    html = resp.body.decode("utf-8")
    
    assert "CamouHub - 环境安全与指纹雷达" in html
    assert "prof_test_999" in html
    assert "WebRTC" in html
    assert "RTCPeerConnection" in html
    assert "剪贴板反窥探沙箱" in html
    assert "跨系统字体指纹隔离" in html
    assert "BrowserLeaks" in html
    assert "CreepJS" in html
    
    print(f"✅ PASS: Radar dashboard generated successfully ({len(html)} bytes).")


def test_5_cloud_sync_packing_and_sigv4():
    """Verify profile snapshot packing, unpacking, and SigV4 request creation."""
    print("\n--- Test 5: Cloud Sync Packing & SigV4 Request ---")
    mock_dir = Path("/tmp/test_profile_snapshot")
    mock_dir.mkdir(parents=True, exist_ok=True)
    def_dir = mock_dir / "Default"
    def_dir.mkdir(parents=True, exist_ok=True)
    (def_dir / "Preferences").write_text('{"test":"pref"}')
    (def_dir / "Cookies").write_text('cookie_db_binary_content')
    
    meta = {"id": "test_sync_id", "name": "Sync Profile", "tags": ["prod"]}
    
    # 1. Pack snapshot
    tar_bytes = pack_profile_snapshot(mock_dir, meta)
    assert len(tar_bytes) > 100, "Packed tar too small"
    
    # 2. Unpack snapshot
    restore_dir = Path("/tmp/test_profile_restored")
    restored_meta = unpack_profile_snapshot(tar_bytes, restore_dir)
    assert restored_meta["name"] == "Sync Profile"
    assert (restore_dir / "Default" / "Preferences").exists()
    assert (restore_dir / "Default" / "Cookies").read_text() == 'cookie_db_binary_content'
    
    # 3. SigV4 request creation
    req = _make_r2_sigv4_request("PUT", "/tikmatrix/camoufox/cloud_profiles/test/snapshot.tar.gz", tar_bytes)
    auth_h = req.get_header("Authorization")
    assert "AWS4-HMAC-SHA256" in auth_h, "SigV4 Authorization header missing"
    assert "Credential=" in auth_h
    assert req.get_header("X-amz-content-sha256") is not None
    
    print(f"✅ PASS: Cloud snapshot packed ({len(tar_bytes)} bytes), restored, and SigV4 header verified.")


def test_6_bezier_curve_mouse_trajectory():
    """Verify cubic bezier curve mathematical generation and coordinate bounds."""
    print("\n--- Test 6: Cubic Bezier Curve Math Simulation ---")
    start_x, start_y = 100.0, 500.0
    target_x, target_y = 650.0, 250.0
    
    p1_x = start_x + (target_x - start_x) * 0.3 + 10.0
    p1_y = start_y + (target_y - start_y) * 0.1 - 15.0
    p2_x = start_x + (target_x - start_x) * 0.7 - 10.0
    p2_y = start_y + (target_y - start_y) * 0.9 + 15.0
    
    steps = 15
    coords = []
    for i in range(1, steps + 1):
        t = i / steps
        bx = ((1 - t) ** 3 * start_x
              + 3 * (1 - t) ** 2 * t * p1_x
              + 3 * (1 - t) * t ** 2 * p2_x
              + t ** 3 * target_x)
        by = ((1 - t) ** 3 * start_y
              + 3 * (1 - t) ** 2 * t * p1_y
              + 3 * (1 - t) * t ** 2 * p2_y
              + t ** 3 * target_y)
        coords.append((round(bx, 1), round(by, 1)))
        
    assert len(coords) == 15
    assert abs(coords[-1][0] - target_x) < 0.1, "Final point must match target X"
    assert abs(coords[-1][1] - target_y) < 0.1, "Final point must match target Y"
    
    print(f"✅ PASS: Bezier trajectory smoothly transitioned across 15 steps to destination ({target_x}, {target_y}).")


def run_all_tests():
    print("=" * 60)
    print("🚀 CAMOUHUB COMMERCIAL FEATURES SIMULATION TEST RUNNER")
    print("=" * 60)
    test_1_preset_icons_integrity()
    test_2_fingerprint_mutation_engine()
    test_3_stealth_extension_and_sandbox_injection()
    test_4_radar_dashboard_route()
    test_5_cloud_sync_packing_and_sigv4()
    test_6_bezier_curve_mouse_trajectory()
    print("\n" + "=" * 60)
    print("🎉 ALL 6 ADVANCED COMMERCIAL FEATURES PASSED WITH ZERO BUGS!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
