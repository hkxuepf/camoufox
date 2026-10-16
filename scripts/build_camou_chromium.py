#!/usr/bin/env python3
"""Automated pipeline to fetch, patch, and build CamouChromium C++ Kernel locally on macOS (Apple Silicon M-series).

Features:
- Downloads Google depot_tools if not present.
- Shallow syncs Chromium 155.0.8059.39 source tree (--no-history, shallow DEPS).
- Applies all 5 platform & stealth C++ patches from patches/chromium/.
- Configures GN args optimized for Apple Silicon (arm64, Release, fast link).
- Compiles Chromium.app via Ninja utilizing all CPU cores (M4 10-core).
- Installs compiled CamouChromium-155.app directly into local CamouHub kernels directory.
"""

import os
import shutil
import subprocess
import sys
import multiprocessing
from pathlib import Path

# Working paths
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
PATCHES_DIR = WORKSPACE_DIR / "patches" / "chromium"
BUILD_ROOT = Path.home() / ".camoufox_build"
DEPOT_TOOLS = BUILD_ROOT / "depot_tools"
CHROMIUM_DIR = BUILD_ROOT / "chromium"
SRC_DIR = CHROMIUM_DIR / "src"

VERSION_TAG = "155.0.8059.39"


def run_cmd(cmd, cwd=None, env=None, check=True):
    """Run command with live logging and check code."""
    cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
    print(f"\n[RUN] {cmd_str} (in {cwd or os.getcwd()})", flush=True)
    res = subprocess.run(cmd, cwd=cwd, env=env, shell=isinstance(cmd, str))
    sys.stdout.flush()
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {res.returncode}: {cmd_str}")
    return res.returncode



def get_build_env():
    """Environment variables including depot_tools in PATH."""
    import socket
    env = os.environ.copy()
    env["PATH"] = f"{DEPOT_TOOLS}:/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"
    env["DEPOT_TOOLS_UPDATE"] = "0"
    
    # Auto-detect local proxy
    for port in [7890, 1087, 10808]:
        s = socket.socket()
        s.settimeout(0.5)
        try:
            if s.connect_ex(('127.0.0.1', port)) == 0:
                print(f"--> Detected active local proxy on port {port}, injecting proxy env...")
                env["http_proxy"] = f"http://127.0.0.1:{port}"
                env["https_proxy"] = f"http://127.0.0.1:{port}"
                env["all_proxy"] = f"socks5://127.0.0.1:{port}"
                break
        except Exception:
            pass
    # Auto-detect Xcode for build
    for xcode_cand in [
        "/Applications/Xcode-beta.app/Contents/Developer",
        "/Applications/Xcode.app/Contents/Developer",
    ]:
        if os.path.exists(xcode_cand):
            print(f"--> Using Xcode Developer Directory: {xcode_cand}")
            env["DEVELOPER_DIR"] = xcode_cand
            break

    return env




def ensure_depot_tools():
    """Download Google depot_tools if missing."""
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    if not (DEPOT_TOOLS / "gclient").exists():
        print("--> Cloning Google depot_tools...")
        cloned = False
        for url in [
            "https://chromium.googlesource.com/chromium/tools/depot_tools.git",
            "https://github.com/chromium/tools-depot_tools.git",
        ]:
            try:
                run_cmd(["git", "clone", "--depth", "1", url, str(DEPOT_TOOLS)])
                cloned = True
                break
            except Exception as e:
                print(f"Failed to clone from {url}: {e}")
        if not cloned:
            raise RuntimeError("Failed to clone depot_tools from all sources.")
    else:
        print("--> depot_tools already installed.")


def fetch_chromium_source(env):
    """Fetch Chromium source tree with shallow clone."""
    CHROMIUM_DIR.mkdir(parents=True, exist_ok=True)
    gclient_file = CHROMIUM_DIR / ".gclient"
    if not gclient_file.exists():
        print("--> Generating .gclient configuration...")
        gclient_content = (
            'solutions = [{"name": "src", "url": "https://chromium.googlesource.com/chromium/src.git", '
            '"deps_file": ".DEPS.git", "managed": False, "custom_deps": {}}]\n'
            'target_os = ["mac"]\n'
        )
        gclient_file.write_text(gclient_content, encoding="utf-8")

    if not (SRC_DIR / ".git").exists():
        print(f"--> Cloning Chromium src (tag {VERSION_TAG}, shallow)...")
        for i in range(1, 4):
            try:
                run_cmd(
                    ["git", "clone", "--depth", "1", "--branch", VERSION_TAG,
                     "https://chromium.googlesource.com/chromium/src.git", "src"],
                    cwd=str(CHROMIUM_DIR),
                )
                break
            except Exception as e:
                print(f"Attempt {i} failed: {e}")
                if i == 3:
                    raise

    print("--> Synchronizing DEPS submodules (shallow, fast)...")
    run_cmd(["gclient", "sync", "--no-history", "--shallow", "--nohooks", f"-j{multiprocessing.cpu_count()}"], cwd=str(SRC_DIR), env=env)
    print("--> Running essential gclient hooks...")
    run_cmd(["gclient", "runhooks"], cwd=str(SRC_DIR), env=env, check=False)



def apply_patches():
    """Apply all 5 platform & stealth C++ patches."""
    print("--> Applying CamouChromium C++ stealth patches...")
    if PATCHES_DIR.exists():
        for patch in sorted(PATCHES_DIR.glob("*.patch")):
            print(f"Applying patch: {patch.name}")
            ret = run_cmd(["git", "apply", str(patch)], cwd=str(SRC_DIR), check=False)
            if ret != 0:
                print(f"Note: git apply returned {ret}, attempting reject apply or check if already applied...")
                run_cmd(["git", "apply", "--reject", str(patch)], cwd=str(SRC_DIR), check=False)

    # Manual compatibility fix for posix_spawn
    launch_mac = SRC_DIR / "base" / "process" / "launch_mac.cc"
    if launch_mac.exists():
        content = launch_mac.read_text(encoding="utf-8")
        if "posix_spawn_file_actions_addchdir(&" in content:
            print("Fixing launch_mac.cc posix_spawn symbol...")
            content = content.replace("posix_spawn_file_actions_addchdir(&", "posix_spawn_file_actions_addchdir_np(&")
            launch_mac.write_text(content, encoding="utf-8")

    # Manual compatibility fix for skia_utils_mac
    skia_mac = SRC_DIR / "skia" / "ext" / "skia_utils_mac.mm"
    if skia_mac.exists():
        content = skia_mac.read_text(encoding="utf-8")
        if "kCGImageByteOrder32Host" in content:
            print("Fixing skia_utils_mac.mm kCGImageByteOrder32Host...")
            content = content.replace("kCGImageByteOrder32Host", "kCGImageByteOrder32Little")
            skia_mac.write_text(content, encoding="utf-8")

    # Manual compatibility fix for screen_utils_mac
    screen_mac = SRC_DIR / "ui" / "display" / "mac" / "screen_utils_mac.mm"
    if screen_mac.exists():
        content = screen_mac.read_text(encoding="utf-8")
        if "screen.CGDirectDisplayID" in content:
            print("Fixing screen_utils_mac.mm CGDirectDisplayID...")
            content = content.replace(
                "screen_display_id = screen.CGDirectDisplayID;",
                'screen_display_id = [screen.deviceDescription[@"NSScreenNumber"] unsignedIntValue];'
            )
            screen_mac.write_text(content, encoding="utf-8")

    # Manual compatibility fix for ca_renderer_layer_tree
    ca_layer_mac = SRC_DIR / "ui" / "accelerated_widget_mac" / "ca_renderer_layer_tree.mm"
    if ca_layer_mac.exists():
        content = ca_layer_mac.read_text(encoding="utf-8")
        if "contentsHeadroom" in content:
            print("Fixing ca_renderer_layer_tree.mm contentsHeadroom & preferredDynamicRange...")
            import re
            content = re.sub(
                r"bool UseCALayerContentsHeadroom\(\)\s*\{[\s\S]*?return false;\s*\}",
                "bool UseCALayerContentsHeadroom() {\n  (void)kUseCALayerContentsHeadroom;\n  return false;\n}",
                content,
                count=1
            )
            content = content.replace("ca_layer_.contentsHeadroom = 16.f;", "// ca_layer_.contentsHeadroom = 16.f;")
            content = content.replace("ca_layer_.preferredDynamicRange = CADynamicRangeHigh;", "// ca_layer_.preferredDynamicRange = CADynamicRangeHigh;")
            content = content.replace("ca_layer_.contentsHeadroom = 0.f;", "// ca_layer_.contentsHeadroom = 0.f;")
            content = content.replace("ca_layer_.preferredDynamicRange = CADynamicRangeStandard;", "// ca_layer_.preferredDynamicRange = CADynamicRangeStandard;")
            ca_layer_mac.write_text(content, encoding="utf-8")



def configure_gn(env):
    """Generate GN build configuration for Release arm64."""
    print("--> Configuring GN args for Release build...")
    out_dir = SRC_DIR / "out" / "Release"
    out_dir.mkdir(parents=True, exist_ok=True)

    gn_bin = None
    for cand in [
        SRC_DIR / "buildtools" / "mac" / "gn",
        Path("/opt/homebrew/bin/gn"),
    ]:
        if Path(cand).exists():
            gn_bin = str(cand)
            break
    if not gn_bin:
        gn_bin = shutil.which("gn", path=env["PATH"]) or "gn"

    args = """
is_debug = false
is_component_build = false
symbol_level = 0
blink_symbol_level = 0
target_cpu = "arm64"
is_official_build = false
chrome_pgo_phase = 0
use_system_xcode = true
use_clang_modules = false
use_unified_system_module = false
"""
    (out_dir / "args.gn").write_text(args.strip() + "\n", encoding="utf-8")
    run_cmd([gn_bin, "gen", "out/Release"], cwd=str(SRC_DIR), env=env)


def compile_chromium(env):
    """Compile Chromium.app using Ninja with all CPU cores."""
    ncpu = multiprocessing.cpu_count()
    print(f"--> Compiling Chromium with Ninja using {ncpu} CPU cores...")
    ninja_bin = None
    for cand in [
        Path("/opt/homebrew/bin/ninja"),
        SRC_DIR / "third_party" / "ninja" / "ninja",
    ]:
        if Path(cand).exists():
            ninja_bin = str(cand)
            break
    if not ninja_bin:
        ninja_bin = shutil.which("ninja", path=env["PATH"]) or "ninja"
    run_cmd([ninja_bin, "-C", "out/Release", "chrome", f"-j{ncpu}"], cwd=str(SRC_DIR), env=env)



def install_kernel():
    """Install compiled Chromium.app into local Camoufox profile manager directories."""
    app_src = SRC_DIR / "out" / "Release" / "Chromium.app"
    if not app_src.exists():
        raise RuntimeError(f"Expected build output not found: {app_src}")

    target_dirs = [
        Path.home() / "Library" / "Application Support" / "Camoufox Profile Manager" / "bin" / "kernels",
        Path.home() / ".camoufox" / "bin" / "kernels",
    ]

    for d in target_dirs:
        d.mkdir(parents=True, exist_ok=True)
        dest_app = d / "CamouChromium-155.app"
        if dest_app.exists():
            shutil.rmtree(dest_app)
        print(f"--> Installing kernel to: {dest_app}")
        shutil.copytree(app_src, dest_app, symlinks=True)

    print("\n✅ CamouChromium C++ Kernel successfully built and installed!")


def main():
    print("=" * 60)
    print("   CamouChromium C++ Native Kernel Local Build Pipeline   ")
    print("=" * 60)
    ncpu = multiprocessing.cpu_count()
    stat = shutil.disk_usage(Path.home())
    avail_gb = stat.free / (1024 ** 3)
    print(f"Host System:     macOS Apple Silicon ({ncpu} Cores)")
    print(f"Available Disk:  {avail_gb:.1f} GB")
    print(f"Build Root:      {BUILD_ROOT}")
    print(f"Target Version:  Chromium {VERSION_TAG}")
    print("=" * 60)

    # 1. depot_tools
    ensure_depot_tools()
    env = get_build_env()

    # 2. Source tree
    if not (SRC_DIR / "third_party" / "zstd").exists():
        fetch_chromium_source(env)
    else:
        print("--> Chromium source tree and third_party DEPS already complete. Skipping sync.")


    # 3. Apply patches
    apply_patches()

    # 4. GN args
    configure_gn(env)

    # 5. Compile with Ninja
    compile_chromium(env)

    # 6. Install to kernel directory
    install_kernel()


if __name__ == "__main__":
    main()
