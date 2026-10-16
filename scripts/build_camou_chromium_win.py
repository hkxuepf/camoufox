#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CamouChromium Windows x64 Native Automated Build Script
Specially customized for Windows 10/11 / Windows Server
Target Directory: Documents/camoufox or specified working directory
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

VERSION_TAG = "155.0.8059.39"
REPO_ROOT = Path(__file__).resolve().parent.parent

# 默认构建工作区路径在当前运行目录或用户文档目录下
DOCUMENTS_DIR = Path(os.environ.get("USERPROFILE", "C:\\Users\\Administrator")) / "Documents" / "camoufox"
BUILD_ROOT = DOCUMENTS_DIR / "chromium_build"
SRC_DIR = BUILD_ROOT / "src"
DEPOT_TOOLS_DIR = BUILD_ROOT / "depot_tools"

def log(msg):
    print(f"\n[CamouChromium-Win] >>> {msg}", flush=True)

def run_cmd(cmd, cwd=None, env=None, check=True):
    log(f"Running: {cmd} in {cwd or os.getcwd()}")
    p = subprocess.run(cmd, shell=True, cwd=cwd, env=env)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed with code {p.returncode}: {cmd}")
    return p.returncode

def ensure_env_vars():
    """配置 Windows 编译所需的环境变量"""
    log("Configuring Windows environment variables...")
    env = os.environ.copy()
    
    # 代理检测（如果本地有科学上网代理如 Clash/V2ray 7890 端口，自动注入）
    import socket
    proxy_ports = [7890, 10809, 10808, 1080]
    for port in proxy_ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", port)) == 0:
            log(f"Detected active local proxy on port {port}. Injecting HTTP_PROXY / HTTPS_PROXY...")
            env["HTTP_PROXY"] = f"http://127.0.0.1:{port}"
            env["HTTPS_PROXY"] = f"http://127.0.0.1:{port}"
            env["ALL_PROXY"] = f"socks5://127.0.0.1:{port}"
            s.close()
            break
        s.close()

    # 将 depot_tools 放在 PATH 环境变量最前列（Windows 下编译 Chromium 强制要求）
    path_val = env.get("PATH", "")
    if str(DEPOT_TOOLS_DIR) not in path_val:
        env["PATH"] = f"{DEPOT_TOOLS_DIR};{path_val}"

    # 声明使用本地安装的 Visual Studio 工具链
    env["DEPOT_TOOLS_WIN_TOOLCHAIN"] = "0"
    # 防止 Python 字符集编码报错
    env["PYTHONIOENCODING"] = "utf-8"
    env["GIT_REDIRECT_STDERR"] = "2>&1"

    return env

def step1_prepare_dirs():
    log("Step 1: Preparing build workspace...")
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    log(f"Build Root directory: {BUILD_ROOT}")

def step2_install_depot_tools(env):
    log("Step 2: Checking Google depot_tools for Windows...")
    if not (DEPOT_TOOLS_DIR / "gclient.bat").exists():
        log("Downloading depot_tools bundle for Windows...")
        # Windows 版 depot_tools 通常推荐解压 zip 包以保证全部 git 钩子和 python 运行时完整
        zip_url = "https://storage.googleapis.com/chrome-infra/depot_tools.zip"
        zip_path = BUILD_ROOT / "depot_tools.zip"
        import urllib.request
        import zipfile
        
        # 尝试下载
        try:
            log(f"Fetching {zip_url}...")
            urllib.request.urlretrieve(zip_url, zip_path)
            log("Extracting depot_tools.zip...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(DEPOT_TOOLS_DIR)
            if zip_path.exists():
                zip_path.unlink()
        except Exception as e:
            log(f"Download zip failed ({e}), fallback to git clone...")
            if DEPOT_TOOLS_DIR.exists():
                shutil.rmtree(DEPOT_TOOLS_DIR, ignore_errors=True)
            run_cmd(f"git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git \"{DEPOT_TOOLS_DIR}\"", env=env)
        
        # Windows 下首次运行 gclient 自动引导环境
        log("Bootstrapping depot_tools on Windows (running gclient once)...")
        run_cmd(f"cmd.exe /c \"{DEPOT_TOOLS_DIR}\\gclient.bat\"", cwd=BUILD_ROOT, env=env, check=False)
    else:
        log("depot_tools already present.")

def step3_fetch_chromium_source(env):
    log("Step 3: Fetching Chromium 155 source tree...")
    if not (SRC_DIR / ".git").exists():
        log(f"Cloning Chromium repository (shallow tag {VERSION_TAG})...")
        run_cmd(
            f"git clone --depth 1 --branch {VERSION_TAG} "
            f"https://chromium.googlesource.com/chromium/src.git \"{SRC_DIR}\"",
            cwd=BUILD_ROOT,
            env=env
        )
    else:
        log("Chromium source repository already exists.")

    # 保证 .gclient 文件存在
    gclient_file = BUILD_ROOT / ".gclient"
    if not gclient_file.exists():
        log("Generating .gclient configuration...")
        gclient_content = """solutions = [
  {
    "name": "src",
    "url": "https://chromium.googlesource.com/chromium/src.git",
    "managed": False,
    "custom_deps": {},
    "custom_vars": {},
  },
]
target_os = ["win"]
"""
        gclient_file.write_text(gclient_content, encoding="utf-8")

    # 同步依赖 (third_party 等)
    log("Synchronizing submodules & DEPS via gclient sync...")
    run_cmd(
        f"cmd.exe /c \"{DEPOT_TOOLS_DIR}\\gclient.bat\" sync -D --no-history --shallow",
        cwd=BUILD_ROOT,
        env=env
    )

    # 关键：Windows 编译 Chromium 必须使用 clang-cl，执行官方脚本拉取 LLVM/Clang 工具链
    log("Ensuring Chromium LLVM/Clang toolchain is installed for Windows...")
    update_clang_py = SRC_DIR / "tools" / "clang" / "scripts" / "update.py"
    if update_clang_py.exists():
        run_cmd(f"python \"{update_clang_py}\"", cwd=SRC_DIR, env=env, check=False)


def step4_apply_stealth_patches():
    log("Step 4: Applying CamouChromium C++ stealth patches...")
    patches_dir = REPO_ROOT / "patches" / "chromium"
    # Windows 平台核心补丁：Intl 语言区域和时区防穿透补丁
    intl_patch = patches_dir / "001-camou-intl-stealth.patch"
    if intl_patch.exists():
        log(f"Applying patch: {intl_patch.name}...")
        p = subprocess.run(f"git apply --check --ignore-space-change --ignore-whitespace \"{intl_patch}\"", shell=True, cwd=SRC_DIR)
        if p.returncode == 0:
            run_cmd(f"git apply --ignore-space-change --ignore-whitespace \"{intl_patch}\"", cwd=SRC_DIR)
            log("Stealth patch applied successfully.")
        else:
            log("Patch already applied or conflict detected, skipping.")


def step5_gn_and_ninja(env):
    log("Step 5: Generating Windows GN configuration & compiling via Ninja...")
    out_dir = SRC_DIR / "out" / "Release"
    out_dir.mkdir(parents=True, exist_ok=True)

    args_gn_file = out_dir / "args.gn"
    args_content = """is_debug = false
is_component_build = false
symbol_level = 0
blink_symbol_level = 0
target_cpu = "x64"
target_os = "win"
is_official_build = false
chrome_pgo_phase = 0
enable_nacl = false
is_clang = true
clang_use_chrome_plugins = false
treat_warnings_as_errors = false
"""
    args_gn_file.write_text(args_content, encoding="utf-8")

    # 执行 gn gen
    gn_bat = DEPOT_TOOLS_DIR / "gn.bat"
    if not gn_bat.exists():
        gn_bat = "gn"
    run_cmd(f"cmd.exe /c \"{gn_bat}\" gen out/Release", cwd=SRC_DIR, env=env)

    # 统计核心数
    cpu_count = os.cpu_count() or 8
    ninja_bat = DEPOT_TOOLS_DIR / "ninja.bat"
    if not ninja_bat.exists():
        ninja_bat = "ninja"

    log(f"Starting Ninja build for chrome.exe with -j{cpu_count}...")
    run_cmd(f"cmd.exe /c \"{ninja_bat}\" -C out/Release chrome -j{cpu_count}", cwd=SRC_DIR, env=env)


def step6_install_kernel():
    log("Step 6: Installing CamouChromium Windows Kernel...")
    src_exe = SRC_DIR / "out" / "Release" / "chrome.exe"
    if not src_exe.exists():
        raise FileNotFoundError(f"Compiled binary not found: {src_exe}")

    dest_dir = Path(os.environ.get("LOCALAPPDATA", "C:\\Users\\Administrator\\AppData\\Local")) / "Camoufox Profile Manager" / "bin" / "kernels" / "CamouChromium-155"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    log(f"Copying build release artifacts to: {dest_dir}...")
    # 拷贝可执行文件及关联 dll/pak 资源
    for item in (SRC_DIR / "out" / "Release").glob("*"):
        if item.is_file() and item.suffix in [".exe", ".dll", ".pak", ".bin", ".dat"]:
            shutil.copy2(item, dest_dir / item.name)

    log("Verifying compiled kernel version:")
    installed_exe = dest_dir / "chrome.exe"
    if installed_exe.exists():
        run_cmd(f"\"{installed_exe}\" --version", check=False)
        log("🎉 CamouChromium Windows Native Kernel built and installed successfully!")

def main():
    log("=== CamouChromium Windows Native Automated Build Pipeline ===")
    env = ensure_env_vars()
    step1_prepare_dirs()
    step2_install_depot_tools(env)
    step3_fetch_chromium_source(env)
    step4_apply_stealth_patches()
    step5_gn_and_ninja(env)
    step6_install_kernel()

if __name__ == "__main__":
    main()
