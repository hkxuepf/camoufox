import pytest
from pathlib import Path
from camoufox_pm.core.kernel_manager import kernel_manager, KernelInfo
from camoufox_pm.core.chromium_launcher import build_chromium_args
from camoufox_pm.core.models import BrowserSettings, ProxyConfig


def test_kernel_manager_defaults():
    assert kernel_manager.get_active_kernel_major() == 155
    ua = kernel_manager.generate_jittered_ua(os_name="windows", kernel_major=155)
    assert "Chrome/155.0." in ua
    assert "Windows NT 10.0" in ua


def test_build_chromium_args_cloak_146(tmp_path: Path):
    settings = BrowserSettings(
        os="windows",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.7680.177 Safari/537.36",
    )
    proxy = ProxyConfig(type="socks5", server="156.23.44.12:1080")
    
    args = build_chromium_args(
        storage_path=tmp_path,
        extension_dir=None,
        settings=settings,
        proxy=proxy,
        cdp_port=9222,
        profile_id="prof_test_123",
        kernel_version="146.0.7680",
    )
    
    # 1. Cloak fingerprint seed argument
    fp_args = [a for a in args if a.startswith("--fingerprint=")]
    assert len(fp_args) == 1
    assert (tmp_path / ".cloakbrowser-seed").exists()
    
    # 2. WebRTC exit IP injection
    webrtc_ip_args = [a for a in args if a.startswith("--fingerprint-webrtc-ip=")]
    assert len(webrtc_ip_args) == 1
    assert webrtc_ip_args[0] == "--fingerprint-webrtc-ip=156.23.44.12"
    
    # 3. Password store basic & mock keychain
    assert "--password-store=basic" in args
    assert "--use-mock-keychain" in args
    
    # 4. Local radar dashboard startup url for Cloak history kernel
    radar_args = [a for a in args if "/api/v1/radar?profile_id=prof_test_123" in a]
    assert len(radar_args) == 1
    
    # 5. Automation flags stripped
    assert not any("--enable-automation" in a for a in args)


def test_build_chromium_args_native_155(tmp_path: Path):
    settings = BrowserSettings(
        os="windows",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.8037.0 Safari/537.36",
    )
    
    args = build_chromium_args(
        storage_path=tmp_path,
        extension_dir=None,
        settings=settings,
        cdp_port=9222,
        profile_id="prof_native_155",
        kernel_version="155.0.8037",
    )
    
    # Native 155 does not pass --fingerprint seed (uses C++ patch 007 & extension instead)
    fp_args = [a for a in args if a.startswith("--fingerprint=")]
    assert len(fp_args) == 0
    assert not (tmp_path / ".cloakbrowser-seed").exists()
