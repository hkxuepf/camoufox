# CamouHub 多内核版本库（含 CloakBrowser 架构整合）与客户端云端自动分发更新系统开发方案 (v2.0)

## 1. 战略目标与设计原则

### 1.1 核心痛点与行业背景
* **环境指纹突变导致风控封号**：真实用户的设备不会在一夜之间发生内核大版本突变。老账号（如跨境电商、海外广告、社媒长周期账号）若随着客户端升级被强制更新内核，底层 V8/Gecko 引擎特征、Canvas 渲染与音频采样曲线会发生质变，破坏风控系统建立的“设备信誉基线”。
* **伪造 UA 的穿帮风险**：仅修改 User Agent 而不替换底层真实内核，会导致 JS/CSS 新特性与声明版本产生不可调和的矛盾（Inconsistency），直接被高级指纹风控（Cloudflare/DataDome/BrowserScan）标记为欺诈伪造。
* **全量自编译历史版本的成本困局**：逐一向后编译 Chromium 146、145 等历史大版本的源码需要耗费巨大算力与维护精力，而开源界知名项目 **CloakBrowser** 已经具备成熟稳定的 C++ 源码级防检测补丁（87 项 source-level patches）以及完全开源免费、无任何云端授权并发限制的经典稳定内核（如 Chrome 146 系列）。

### 1.2 核心目标：双轨内核驱动战略 (Dual-Track Kernel Architecture)
1. **双轨演进策略（Chromium 双轨 + Camoufox Gecko）**：
   * **自研前向内核轨 (Chromium ≥ 155)**：以当前自编译纯净防关联 **Chrome 155** 为基准首发版本，后续持续向前演进（156, 157+），内置专属 C++ WebUI 补丁与底层防反编译特征；
   * **CloakBrowser 历史内核轨 (Chromium < 155)**：全面收编与兼容 **CloakBrowser** 架构中**完全免鉴权、零并发限制、纯离线运行的经典历史版本**（基准首发 **Chrome 146**，彻底剔除带第三方商业 License 鉴权及单并发限制的 154 版本），实现“零成本复用优质历史内核”；
   * **火狐内核轨 (Camoufox / Gecko)**：以当前 **Camoufox 135 (Firefox ESR / Release)** 为基线，保持与官方安全更新与指纹补丁同步。
2. **功能零破坏原则 (Zero-Breakage Guarantee)**：
   * 引入 CloakBrowser 架构时，CamouHub 原有的核心功能（**macOS 原生物理窗口锁 `libcamou_window_lock.dylib`、CDP 自动化中台、窗口同步器 Synchronizer、DNR 真实请求头重写、Cookie 动态装载、本地代理隧道**）全部无缝沿用，不受任何削弱。
3. **环境检测页 (Radar) 100% 视觉与体验一致性**：
   * 无论是唤起自研 Chrome 155 还是 CloakBrowser 历史内核，用户打开环境后均能无缝呈现商业级环境健康与指纹雷达检测页（包含出网 IP、地理位置归属、网络延迟、硬件指纹自检）。
4. **终身版本锁定（Immutable Binding）**：
   * 环境创建时选定特定内核版本（如 Chrome 146 或 155），该环境终身绑定该版本内核；无论 CamouHub 客户端升级到何种版本，启动该环境时保证 100% 调起对应的历史内核二进制，彻底杜绝指纹漂移。
5. **宿主双平台全覆盖（Windows & macOS）**：
   * 所有内核与客户端均完整适配 **Windows (x64)** 与 **macOS (Apple Silicon arm64 / Intel x86_64)**。
6. **自主 GitHub Releases 资产托管（0 存储/带宽成本）**：
   * 客户端安装包与所有 Chromium、CloakBrowser 历史内核、Camoufox 内核二进制统一托管于自主 GitHub 仓库（`hkxuepf/camoufox/releases`），支持国内高速反代加速源。
7. **全自动匹配与懒加载下载（Zero-touch UX）**：
   * 启动环境时全自动比对本地内核库；本地存在即毫秒级秒开；本地缺失时自动触发极速下载，解压校验完成后**全自动接着唤起浏览器**。

---

## 2. 系统整体分层架构

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                      CamouHub 客户端                                      │
│                                                                                           │
│  [前端 UI (Next.js)]                                                                      │
│    ├── 新建/编辑环境弹窗 ── 选择引擎 (Chrome/Firefox) & 内核版本 (155/146/135 联动 UA)        │
│    ├── 环境卡片快速启动 ── 状态自动流转 [检查本地 -> 进度下载 -> 解压校验 -> 无缝唤起]    │
│    └── 系统设置 -> [内核版本管理] & [客户端更新] 控制中心                                 │
│                                                                                           │
│  [核心调度器 (Python FastAPI / kernel_manager.py)]                                        │
│    ├── 宿主平台探测 (`sys.platform` + `platform.machine()`)                               │
│    ├── 版本路由器 (Version Router):                                                       │
│    │     ├── 若 target_version >= 155 ──> 调度 CamouChromium 原生自编译内核 (155+)         │
│    │     ├── 若 target_version < 155  ──> 调度 CloakBrowser C++ 无锁历史内核 (146)        │
│    │     └── 若 engine == "camoufox"  ──> 调度 Gecko 原生防关联内核 (135)                 │
│    │                                                                                      │
│    ├── 混合协同适配层 (Hybrid Pass-Through Adapter):                                      │
│    │     ├── 参数自适应 (--fingerprint=<seed>、--fingerprint-platform、移除自动化标签)     │
│    │     ├── 注入 cpm_anti_detect_extension (精简协同模式: Cookie/DNR 请求头/代理认证)     │
│    │     ├── 挂载 macOS libcamou_window_lock.dylib (移动端锁死 / 桌面端封顶)              │
│    │     └── 调度 CDP 遥测中台 (自动引导 Radar 环境检测页至首屏)                           │
│    │                                                                                      │
│    └── 校验本地 `~/.camoufox/kernels/{engine}/{version}/` 是否就绪 (缺失则自动下载解压)    │
└──────────────────────────────────────────┬────────────────────────────────────────────────┘
                                           │
                            (智能双通道: 官方 CDN / 国内加速镜像)
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                          云端多内核版本资产库 (GitHub Releases)                            │
│                                                                                           │
│  [自研前向轨 (≥ 155)]                                                                     │
│  - chromium-155.0.8037-mac-arm64.tar.gz  /  chromium-155.0.8037-win-x64.zip               │
│                                                                                           │
│  [CloakBrowser 兼容历史轨 (< 155 · 完全免鉴权无并发限制)]                                 │
│  - cloak-chromium-146.0.7680-mac-arm64.tar.gz  /  cloak-chromium-146.0.7680-win-x64.zip   │
│                                                                                           │
│  [Camoufox 火狐轨]                                                                        │
│  - camoufox-135.0.0-mac-arm64.tar.gz  /  camoufox-135.0.0-win-x64.zip                     │
│                                                                                           │
│  [版本清单中台]                                                                           │
│  - manifest.json (包含客户端更新元数据与多轨内核全量签名)                                  │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 云端版本清单规范 (`manifest.json`)

在 GitHub 仓库托管统一版本清单文件，全面剔除存在商业授权鉴权限制的 154 分支，保留完全开源无锁的 Chrome 146 作为历史版本基准：

```json
{
  "manifest_version": "2.1",
  "updated_at": "2026-10-16T08:00:00Z",
  "client": {
    "latest_version": "1.0.6",
    "min_required_version": "1.0.0",
    "release_date": "2026-10-16",
    "release_notes": "1. 支持整合 CloakBrowser 87 项 C++ 补丁架构作为 155 前历史版本内核\n2. 首发接入纯净无授权限制的 Chrome 146 经典长周期内核\n3. 全版本统一兼容全维雷达检测页与物理窗口边界锁定\n4. 客户端启动全自动自检与无缝自更新",
    "downloads": {
      "mac_arm64": {
        "url": "https://github.com/hkxuepf/camoufox/releases/download/v1.0.6/CamouHub-1.0.6-mac-arm64.dmg",
        "sha256": "8a31e8...",
        "size_bytes": 62914560
      },
      "mac_x64": {
        "url": "https://github.com/hkxuepf/camoufox/releases/download/v1.0.6/CamouHub-1.0.6-mac-x64.dmg",
        "sha256": "9b12d3...",
        "size_bytes": 65536000
      },
      "win_x64": {
        "url": "https://github.com/hkxuepf/camoufox/releases/download/v1.0.6/CamouHub-1.0.6-win-x64-setup.exe",
        "sha256": "7c45f1...",
        "size_bytes": 71303168
      }
    }
  },
  "kernels": {
    "chromium": [
      {
        "version": "155.0.8037",
        "flavor": "camou_native",
        "display_name": "Chrome 155 (首发基准自研防关联内核 · 原生雷达)",
        "is_recommended": true,
        "is_default": true,
        "status": "active",
        "default_ua_template": "Mozilla/5.0 ({os_token}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.8037.0 Safari/537.36",
        "platforms": {
          "mac_arm64": {
            "url": "https://github.com/hkxuepf/camoufox/releases/download/v155.0/chromium-155.0.8037-mac-arm64.tar.gz",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "size_bytes": 142605820,
            "executable_relative_path": "Chromium.app/Contents/MacOS/Chromium"
          },
          "mac_x64": {
            "url": "https://github.com/hkxuepf/camoufox/releases/download/v155.0/chromium-155.0.8037-mac-x64.tar.gz",
            "sha256": "f51b...",
            "size_bytes": 146800000,
            "executable_relative_path": "Chromium.app/Contents/MacOS/Chromium"
          },
          "win_x64": {
            "url": "https://github.com/hkxuepf/camoufox/releases/download/v155.0/chromium-155.0.8037-win-x64.zip",
            "sha256": "c8b4e289...",
            "size_bytes": 138501240,
            "executable_relative_path": "chrome.exe"
          }
        }
      },
      {
        "version": "146.0.7680",
        "flavor": "cloak_stealth",
        "display_name": "Chr* 该机制作用于 macOS Cocoa 框架层，**完全独立于具体的 Chromium 编译版本**。因此无论是自研 155 还是 CloakBrowser 146，均能实现：
  * **移动端环境**：严格锁死窗口尺寸（不可缩放、不可全屏、固定分辨率）；
  * **桌面端环境**：最大化封顶锁定（最大化只能撑大到设定的屏幕分辨率，严禁超出导致 `outerWidth > screen.width` 穿帮）。

---

## 5. 环境检测页（Radar）跨版本 100% 兼容方案

### 5.1 痛点与解决方案对比
* **自研 Chrome 155**：由于在源码中打了 `007-native-radar-newtab.patch`，默认新标签页 `chrome://newtab/` 即为雷达页；
* **CloakBrowser (< 155)**：属于官方标准 newtab 页面。

### 5.2 统一兼容实现流程
针对 `< 155` 历史版本，采用 **CDP 初始页引导 + 本地 REST 雷达端点**：

1. **统一雷达服务接入**：
   * FastAPI 后台常驻提供商业级雷达端点：`http://127.0.0.1:{api_port}/api/v1/radar?profile_id={id}`；
2. **启动时无感直投**：
   * 若环境没有配置特定的 `startup_url`，`chromium_launcher.py` 在构建启动命令行时，直接将本地雷达 URL 作为首个参数传入：
     ```bash
     /path/to/Chromium --user-data-dir=... http://127.0.0.1:41723/api/v1/radar?profile_id=prof_xxxx
     ```
3. **CDP 遥测数据动态刷新**：
   * `auto_sync_radar_tab` 通过 CDP 连接目标页面，实时下发最新的测速 Ping 值（Google、TikTok、Baidu、Iphey）、出口 IP 真实物理归属与时区校对结果；
4. **最终用户体验**：
   * 无论启动哪个内核版本，用户点击打开环境后，首屏看到的都是**同一套精致、专业、具有商业质感的深色雷达检测页**。

---

## 6. 本地多版本目录结构规范（Windows & macOS）

本地内核统一存放在用户目录下的 `.camoufox/kernels/` 路径中，按 `引擎 -> 版本` 进行两级隔离，绝不污染系统全局环境：

### 6.1 macOS 目录规范 (`~/.camoufox/kernels/`)
```text
~/.camoufox/kernels/
  ├── chromium/
  │    ├── 155.0.8037/ (自研前向基准)
  │    │     ├── .version_meta.json
  │    │     └── Chromium.app/Contents/MacOS/Chromium
  │    └── 146.0.7680/ (CloakBrowser 经典历史轨 · 纯净无锁)
  │          ├── .version_meta.json
  │          └── Chromium.app/Contents/MacOS/Chromium
  └── camoufox/
       └── 135.0-beta.36/ (火狐轨)
             ├── .version_meta.json
             └── Camoufox.app/Contents/MacOS/firefox
```

### 6.2 Windows 目录规范 (`%USERPROFILE%\.camoufox\kernels\`)
```text
C:\Users\<username>\.camoufox\kernels\
  ├── chromium\
  │    ├── 155.0.8037\ (自研前向基准)
  │    │     ├── .version_meta.json
  │    │     ├── chrome.exe
  │    │     └── ...
  │    └── 146.0.7680\ (CloakBrowser 经典历史轨 · 纯净无锁)
  │          ├── .version_meta.json
  │          ├── chrome.exe
  │          └── ...
  └── camoufox\
       └── 135.0-beta.36\
             ├── .version_meta.json
             ├── firefox.exe
             └── ...
```

### 6.3 完整性元数据规范 (`.version_meta.json`)
解压完毕后在版本目录下写入元数据，记录架构特性与可执行路径：
```json
{
  "engine": "chromium",
  "version": "146.0.7680",
  "flavor": "cloak_stealth",
  "platform": "mac_arm64",
  "installed_at": "2026-10-16T08:15:00Z",
  "sha256": "4d5e6f...",
  "size_bytes": 139800000,
  "executable_path": "Chromium.app/Contents/MacOS/Chromium",
  "is_ready": true
}
```

---

## 7. 后台核心组件改造设计

### 7.1 内核管理器 (`kernel_manager.py`)
1. **多内核分流检索**：
   * `get_executable_for_version(target_version: str) -> Optional[Path]`：根据版本号自动定位本地目录（如优先定位 `146.0.7680`）；固定随机数）；
   * 追加启动参数 `--fingerprint={seed}`，确保该环境在历史内核下每次启动的 Canvas/Audio/WebGL 扰动完全一致。
2. **宿主平台特征对齐**：
   * macOS 宿主：追加 `--fingerprint-platform=macos`，激活 CloakBrowser 原生 Metal GPU 与系统字体管线；
   * Windows 宿主：默认以 Direct3D 11 与系统原生字体透传。
3. **剔除自动化特征参数**：
   * 严格过滤 `--enable-automation` 与 `--enable-unsafe-swiftshader`，确保 `navigator.webdriver === false`。

### 4.2 扩展层精简协同模式 (Extension Cooperative Mode)
为了避免 CloakBrowser 底层 C++ 指纹与 CamouHub 的 `cpm_anti_detect_extension` 在 JavaScript 原型链上发生“二次篡改冲突”，实施如下协同策略：
* **底层让渡给 C++**：Canvas、Audio、WebGL 渲染扰动、Client Hints 基础特征完全由 CloakBrowser C++ 内核完成；
* **上层保留 CamouHub 独有能力**：
  * **Cookie 动态恢复**：通过扩展后台执行毫秒级 Cookie 会话注入；
  * **DNR 规则引擎**：精准过滤/重写 HTTP 真实请求头；
  * **本地代理认证**：无感透传代理账号密码，无需弹出系统认证窗；
  * **搜索引擎与启动页预置**：写入 `Preferences` 与 `Local State`，屏蔽 Chrome 烦人的“扩展已修改主页/默认引擎”弹窗。

### 4.3 macOS 原生物理窗口锁无缝继承 (`libcamou_window_lock.dylib`)
* `libcamou_window_lock.dylib` 基于 Objective-C Method Swizzling 拦截 `NSWindow` 的 `zoom:`、`toggleFullScreen:`、`setStyleMask:`；
* 该机制作用于 macOS Cocoa 框架层，**完全独立于具体的 Chromium 编译版本**。因此无论是自研 155 还是 CloakBrowser 154/146，均能实现：
  * **移动端环境**：严格锁死窗口尺寸（不可缩放、不可全屏、固定分辨率）；
  * **桌面端环境**：最大化封顶锁定（最大化只能撑大到设定的屏幕分辨率，严禁超出导致 `outerWidth > screen.width` 穿帮）。

---

## 5. 环境检测页（Radar）跨版本 100% 兼容方案

### 5.1 痛点与解决方案对比
* **自研 Chrome 155**：由于在源码中打了 `007-native-radar-newtab.patch`，默认新标签页 `chrome://newtab/` 即为雷达页；
* **CloakBrowser (< 155)**：属于官方标准 newtab 页面。

### 5.2 统一兼容实现流程
针对 `< 155` 历史版本，采用 **CDP 初始页引导 + 本地 REST 雷达端点**：

1. **统一雷达服务接入**：
   * FastAPI 后台常驻提供商业级雷达端点：`http://127.0.0.1:{api_port}/api/v1/radar?profile_id={id}`；
2. **启动时无感直投**：
   * 若环境没有配置特定的 `startup_url`，`chromium_launcher.py` 在构建启动命令行时，直接将本地雷达 URL 作为首个参数传入：
     ```bash
     /path/to/Chromium --user-data-dir=... http://127.0.0.1:41723/api/v1/radar?profile_id=prof_xxxx
     ```
3. **CDP 遥测数据动态刷新**：
   * `auto_sync_radar_tab` 通过 CDP 连接目标页面，实时下发最新的测速 Ping 值（Google、TikTok、Baidu、Iphey）、出口 IP 真实物理归属与时区校对结果；
4. **最终用户体验**：
   * 无论启动哪个内核版本，用户点击打开环境后，首屏看到的都是**同一套精致、专业、具有商业质感的深色雷达检测页**。

---

## 6. 本地多版本目录结构规范（Windows & macOS）

本地内核统一存放在用户目录下的 `.camoufox/kernels/` 路径中，按 `引擎 -> 版本` 进行两级隔离，绝不污染系统全局环境：

### 6.1 macOS 目录规范 (`~/.camoufox/kernels/`)
```text
~/.camoufox/kernels/
  ├── chromium/
  │    ├── 155.0.8037/ (自研基准)
  │    │     ├── .version_meta.json
  │    │     └── Chromium.app/Contents/MacOS/Chromium
  │    ├── 154.0.8037/ (CloakBrowser 历史轨)
  │    │     ├── .version_meta.json
  │    │     └── Chromium.app/Contents/MacOS/Chromium
  │    └── 146.0.7680/ (CloakBrowser 历史轨)
  │          ├── .version_meta.json
  │          └── Chromium.app/Contents/MacOS/Chromium
  └── camoufox/
       └── 135.0-beta.36/ (火狐轨)
             ├── .version_meta.json
             └── Camoufox.app/Contents/MacOS/firefox
```

### 6.2 Windows 目录规范 (`%USERPROFILE%\.camoufox\kernels\`)
```text
C:\Users\<username>\.camoufox\kernels\
  ├── chromium\
  │    ├── 155.0.8037\
  │    │     ├── .version_meta.json
  │    │     ├── chrome.exe
  │    │     └── ...
  │    ├── 154.0.8037\ (CloakBrowser)
  │    │     ├── .version_meta.json
  │    │     ├── chrome.exe
  │    │     └── ...
  │    └── 146.0.7680\ (CloakBrowser)
  │          ├── .version_meta.json
  │          ├── chrome.exe
  │          └── ...
  └── camoufox\
       └── 135.0-beta.36\
             ├── .version_meta.json
             ├── firefox.exe
             └── ...
```

### 6.3 完整性元数据规范 (`.version_meta.json`)
解压完毕后在版本目录下写入元数据，记录架构特性与可执行路径：
```json
{
  "engine": "chromium",
  "version": "154.0.8037",
  "flavor": "cloak_stealth",
  "platform": "mac_arm64",
  "installed_at": "2026-10-16T08:15:00Z",
  "sha256": "7a8b9c...",
  "size_bytes": 141200000,
  "executable_path": "Chromium.app/Contents/MacOS/Chromium",
  "is_ready": true
}
```

---

## 7. 后台核心组件改造设计

### 7.1 内核管理器 (`kernel_manager.py`)
1. **多内核分流检索**：
   * `get_executable_for_version(target_version: str) -> Optional[Path]`：根据版本号自动定位本地目录（如优先定位 `154.0.8037`）；
   * 读取 `.version_meta.json` 判断 `flavor`（`camou_native` 或 `cloak_stealth`）。
2. **下载与解压安全加固**：
   * 支持从 GitHub Releases 官方源或国内反代源拉取对应的 `.tar.gz` / `.zip`；
   * 下载过程进行 SHA-256 校验；
   * macOS 下自动执行 `chmod +x` 并剥离隔离标志：`xattr -rd com.apple.quarantine`。

### 7.2 启动器适配 (`chromium_launcher.py`)
1. **参数自适应装配**：
   * 判断目标内核是否属于 `cloak_stealth`：
     * 若是：自动读取/写入 `.cloakbrowser-seed`，注入 `--fingerprint=` 与 `--fingerprint-platform=`；
     * 若未设自定义启动页：自动将启动页指向本地雷达仪表盘。
2. **窗口锁与 CDP 统一管线**：
   * 无论内核来源，统一注入 `libcamou_window_lock.dylib` 环境变量（`CAMOU_LOCK_MODE`、`CAMOU_LOCK_WINDOW_SIZE`）；
   * 统一分配 `cdp_port`，挂接后台进程与窗口监控。

### 7.3 客户端自动更新调度器 (`client_updater.py`)
1. **启动自检核心方法**：
   * `check_for_update() -> Optional[ClientUpdateInfo]`：
     * 读取当前客户端运行版本（如 `1.0.5`）；
     * 向云端请求 `manifest.json` 或 `/api/v1/releases/client`；
     * 采用标准 SemVer 语义化版本算法比较（`cloud_version > current_version`）；
     * 返回更新元数据（版本号、更新日志、各平台安装包直链、`is_force_update` 标记）；
2. **多平台全自动静默下载与安装接管**：
   * `download_and_apply_update(progress_callback=None)`：
     * 根据当前宿主环境拉取目标安装包（macOS 为 `.dmg`，Windows 为 `.exe` 安装程序）；
     * **macOS 自动更新实现**：
       * 后台挂载下载好的 `.dmg`（`hdiutil attach -nobrowse`）；
       * 将卷宗内的 `CamouHub.app` 复制覆盖至 `/Applications/CamouHub.app`；
       * 剥离隔离标志：`xattr -rd com.apple.quarantine /Applications/CamouHub.app`；
       * 弹出重启通知，用户点击后执行重启：`open -n /Applications/CamouHub.app` 并退出旧进程；
     * **Windows 自动更新实现**：
       * 下载新版安装程序至临时目录（如 `CamouHub-Setup-1.0.6.exe`）；
       * 启动时执行静默覆盖安装参数（`CamouHub-Setup.exe /SILENT /NORESTART`）；
       * 自动拉起新客户端并退出当前实例。

---

## 8. 管理控制台设计：核心版本库与软件版本管理中台

在管理员控制台（`/5DRnDsWW` 路径下的 **「版本与内核」** 模块）中，系统完整包含并严格划分两个平行的核心业务子板块：**「软件版本管理」** 与 **「核心版本库」**：

```
                              ┌──────────────────────────────────────────────┐
                              │     管理控制台 -> 版本与内核中台 (`releases`)   │
                              └──────────────────────┬───────────────────────┘
                                                     │
                         ┌───────────────────────────┴───────────────────────────┐
                         ▼                                                       ▼
            【子板块 A: 软件版本管理】                              【子板块 B: 核心版本库】
         (Desktop App / Client Releases)                        (Multi-Kernel Version Hub)
  ┌──────────────────────────────────────────────┐       ┌──────────────────────────────────────────────┐
  │ 1. 客户端本体全平台发布 (macOS DMG / Win EXE)  │       │ 1. 双轨防关联内核资产管理                     │
  │ 2. 版本号 (SemVer) 与强制更新策略配置          │       │    - ≥155 自研纯净内核 (Chrome 155+)         │
  │ 3. 更新日志 (Changelog) 富文本发布            │       │    - <155 CloakBrowser 历史内核 (154/146)    │
  │ 4. 客户端自检更新 API 响应与在线分发引导       │       │    - Camoufox 火狐内核 (Firefox 135+)        │
  │ 5. 最低兼容版本与灰度发布控制                 │       │ 2. 跨平台二进制包配置 (Win zip / Mac tar.gz)   │
  └──────────────────────────────────────────────┘       │ 3. 推荐版本/默认内核标记 (Recommended/Default)│
                                                         │ 4. GitHub CDN / 加速镜像分发状态监控         │
                                                         │ 5. 一键热下架、版本废弃与环境降级防护         │
                                                         └──────────────────────────────────────────────┘
```

### 8.1 板块 A：软件版本管理（客户端应用本体更新）
* **定位**：负责 CamouHub 桌面客户端应用本体（UI 交互壳体、本地调度服务程序）的发版、升级检测与更新分发。
* **核心配置项与能力**：
  * **版本号与标题**：记录桌面端 SemVer 版本（如 `v1.0.6`）与发版主题；
  * **跨平台安装包托管**：配置 `mac_arm64.dmg`、`mac_x64.dmg` 与 `win_x64-setup.exe` 的 GitHub Releases 直链；
  * **更新策略与约束**：
    * `min_version`（最低要求版本）：若用户当前客户端低于此版本，强制阻断并提示升级；
    * `is_force_update`（强制更新开关）：开启后登录时强弹窗拦截，避免旧版协议不兼容风险；
  * **客户端自检闭环**：客户端启动或在「系统设置」中点击“检查更新”时，后台直连 `/api/v1/releases/client` 接口，无缝获取最新版本并提示一键下载。

### 8.2 板块 B：核心版本库（多引擎多轨内核库）
* **定位**：负责环境实例运行时所需的**底层浏览器内核二进制资产**，与客户端应用安装包彻底解耦，按需下载复用。
* **核心配置项与能力**：
  * **双轨多引擎版本归档**：
    * **自研前向轨 (≥ 155)**：管理 Chrome 155、156 等自编译内核包；
    * **Cloak 历史轨 (< 155)**：管理 Chrome 154、146、145 等 CloakBrowser 架构的 C++ 补丁二进制；
    * **Camoufox 火狐轨**：管理 Firefox 135 ESR / Release 资产；
  * **跨平台切片就绪监控**：实时检查每个内核的 macOS arm64/x64 与 Windows x64 下载包是否存在，计算 SHA256 完整性签名；
  * **生命周期策略**：
    * **默认推荐（Recommended）**：控制新建环境时的首选默认内核；
    * **活跃（Active）**：开放供用户在下拉菜单自由选用；
    * **已归档（Archived / Deprecated）**：隐藏不再对新建环境开放，但已绑定的存量历史环境依然保证 100% 正常启动，确保环境终身锁定。

### 8.3 后台管理接口与 CLI 自动化流水线
支持管理后台页面可视化操作，同时提供 CLI 自动化脚本供编译后一键同步：

| 方法 | 路由 | 归属子板块 | 说明 |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/releases/client` | 软件版本管理 | 客户端调用的检查更新端点（返回最新安装包与升级策略） |
| `GET` | `/api/v1/admin/releases/client` | 软件版本管理 | 后台管理列表：列出历史所有客户端发版记录 |
| `POST` | `/api/v1/admin/releases/client` | 软件版本管理 | 发布新的客户端版本（写入版本、平台包 URL、强制更新标记） |
| `DELETE` | `/api/v1/admin/releases/client/{id}` | 软件版本管理 | 撤回/下架特定的客户端发布包 |
| `GET` | `/api/v1/admin/releases/kernels` | 核心版本库 | 后台管理列表：列出多内核库全量资产及平台切片状态 |
| `POST` | `/api/v1/admin/releases/kernels` | 核心版本库 | 上架新内核（支持注册 Chrome 154/146 Cloak 架构包及 155 自研包） |
| `PUT` | `/api/v1/admin/releases/kernels/{id}` | 核心版本库 | 编辑内核元数据（更新推荐状态、修改 UA 模板、调整下载源） |
| `DELETE` | `/api/v1/admin/releases/kernels/{id}` | 核心版本库 | 下架内核版本 |
| `POST` | `/api/v1/admin/releases/sync-github` | 自动化同步 | 触发后台从 GitHub Releases 与 `manifest.json` 自动同步资产 |

* **CLI 命令行一键打包发布工具 (`scripts/publish_release.py`)**：
  ```bash
  # 1. 注册发布 CloakBrowser 历史内核
  python scripts/publish_release.py --type kernel --engine chromium --flavor cloak_stealth --version 154.0.8037 --platform mac_arm64 --file dist/cloak-chromium-154-mac.tar.gz

  # 2. 注册发布新版本桌面端软件
  python scripts/publish_release.py --type client --version 1.0.6 --platform mac_arm64 --file dist/CamouHub-1.0.6-arm64.dmg
  ```

---

## 9. 商业级特性强化与企业风控防御规范 (Enterprise & Commercial Standards)

为了使 CamouHub 在生产环境中达到与顶级商业指纹浏览器（AdsPower、Multilogin、HubStudio）同等甚至超越的稳定性与抗风控水准，在多内核系统中固化以下六大商业级规范：

### 9.1 Client Hints (`Sec-CH-UA`) 严格自洽矩阵 (Inconsistency Defense)
* **核心风控痛点**：在 Chrome 107+ 中，高级反爬（Cloudflare、Akamai、DataDome）不再仅看 `navigator.userAgent`，而是重点校验 HTTP 请求头中的 `Sec-CH-UA`、`Sec-CH-UA-Full-Version-List` 与 JavaScript 端的 `navigator.userAgentData.getHighEntropyValues()`。
* **自洽联动规则**：
  * 当内核为 Chrome 155 时，`Sec-CH-UA` 品牌主版本固定为 `"155"`，全量版本号严格为 `155.0.8037.x`；
  * 当内核为 Chrome 154 (Cloak) 时，动态重写为 `"Not_A Brand";v="8", "Chromium";v="154", "Google Chrome";v="154"`，全量版本严格对齐 `154.0.8037.57`；
  * 当内核为 Chrome 146 (Cloak) 时，全量版本严格对齐 `146.0.7680.177`；
  * **严禁**出现“UA 声明为 Chrome 154，但 Client Hints 泄露出 155”或“CSS/API 特性与声明版本倒挂”的致命矛盾。
* **命令行开关向后兼容白名单**：针对 `< 155` 版本，启动器在组装 CLI 参数时自动过滤高版本专有参数（如高版本新增的实验性 `--enable-features`），防止因参数不兼容导致内核崩溃。

### 9.2 WebRTC 出口 IP 智能绑定策略 (WebRTC IP Defense)
为商业跨境电商与海外多账号运营提供四种工业级 WebRTC 防护模式：
1. **替换为代理出口 IP (Altered / Exit IP Match，商业首选)**：
   * 自动探测当前代理的真实出口公共 IP（如 `156.23.44.12`）；
   * 将该 IP 显式注入到 WebRTC ICE Candidate 中（Cloak 历史内核传递 `--fingerprint-webrtc-ip={exit_ip}`，Camoufox 通过扩展拦截），彻底消除内网真实 IP 泄露，同时保证 WebRTC 处于可用状态，避免被检测为“机器完全禁用 WebRTC”；
2. **局域网假 IP 扰动 (Fake LAN IP)**：
   * 注入伪造的内网私有地址（如 `192.168.1.188`），符合真实家宽环境特征；
3. **彻底禁用 (Disabled)**：
   * 启动参数追加 `--disable-webrtc`，彻底关闭任何媒体流通道；
4. **原生透传 (Pass-through)**：
   * 保持宿主机真实网络状态。

### 9.3 内核引用计数与存储安全清理 (Reference Counting & Storage GC)
商业用户常有成百上千个历史环境，多内核解压后（单版本 300MB~600MB）需严格管控磁盘开销：
1. **多环境只读共享 (Immutable Binary Sharing)**：
   * 所有环境无论启动多少开，**100% 共享同一份不可变的本地内核二进制目录**；
   * 各环境仅在自身的 `user_data_dir` 下写入独立的 Session、Cache、Cookie 与偏好设置，实现物理级存储解耦；
2. **引用计数安全删除机制 (Reference Counter)**：
   * 管理后台或客户端删除内核时，核心调度器首先执行：
     ```python
     bound_count = await storage.count_profiles_by_kernel(engine, version)
     if bound_count > 0:
         raise KernelInUseError(f"当前仍有 {bound_count} 个环境绑定此内核，禁止卸载！")
     ```
   * 严防误删导致绑定的历史账号环境无法启动；
3. **无引用废弃内核垃圾回收 (Storage GC)**：
   * 在「系统设置 -> 内核管理」面板提供「一键扫描无用内核」，统计未被任何活跃环境引用的历史内核，支持一键释放数 GB 磁盘空间。

### 9.4 团队多设备跨平台自愈流转 (Cross-Host Auto-Healing)
针对企业团队在 Windows 与 macOS（Apple Silicon / Intel）混合办公的复杂场景：
* **业务场景**：员工 A（Windows 电脑）创建了环境并选定 Chrome 154 内核；该环境通过云端同步到员工 B（macOS M3 芯片）的工作台；
* **自愈机制**：
  * 环境数据中仅记录**逻辑内核标识**（`browser_engine: "chromium"`, `kernel_version: "154.0.8037"`），不硬编码宿主机操作系统路径；
  * 员工 B 点击「启动」时，本地 `kernel_manager` 自动探测宿主为 `mac_arm64`；
  * 若本地缺少该切片，系统静默从 GitHub Release CDN 拉取 `cloak-chromium-154.0.8037-mac-arm64.tar.gz`，解压自愈后自动唤起；
  * **全程无需员工重新配置环境，彻底打破 Windows 与 macOS 设备间的协作壁垒**；
* **离线内网环境侧载支持 (Air-Gapped Sideloading)**：
  * 针对受限局域网/军工专网客户，支持在客户端界面点击「离线导入内核」，直接拖拽 `.zip` 或 `.tar.gz` 完成离线验证与注册。

### 9.5 开放本地 RPA 自动化中台 (AdsPower / HubStudio CDP 规范)
现代指纹浏览器的大客户高度依赖自动化脚本。系统提供标准化本地自动化调度端点：
* **启动接口 (`POST /api/v1/browser/start`)**：
  ```json
  {
    "code": 0,
    "message": "success",
    "data": {
      "profile_id": "prof_789456",
      "ws_endpoint": "ws://127.0.0.1:41723/devtools/browser/abc-123-def",
      "http_endpoint": "http://127.0.0.1:41723",
      "kernel_version": "154.0.8037",
      "engine": "chromium",
      "pid": 68241
    }
  }
  ```
* **第三方框架零修改直连**：
  * Playwright、Puppeteer、Selenium 自动化脚本只需通过 `chromium.connectOverCDP(data.ws_endpoint)` 即可秒级接管，无论是 Chrome 155 还是 Cloak 154，自动化交互逻辑完全一致；
  * 支持一键挂接 CamouHub 内部开发的**多窗口平铺同步器 (Synchronizer)**。

### 9.6 下载双通道容灾与解压原子性防护 (Failover & Atomic Installation)
针对国内网络访问 GitHub CDN 偶发波动的问题：
1. **智能测速与双源无感回退**：
   * 下载内核或更新包时，并发探测：
     * **通道 A（国内加速镜像源）**：通过高性能反向代理 CDN 直连；
     * **通道 B（官方 GitHub Releases 官方源）**：直连全球 CDN；
   * 自动选取最低延迟通道，若通道 A 出现 HTTP 5xx 或超时，100ms 内无缝回退至通道 B，杜绝下载中断；
2. **解压原子性与断点防损坏 (Atomic Rename)**：
   * 下载时采用临时文件 `.tmp`，下载完毕先比对 SHA-256 摘要；
   * 解压时释放到临时目录 `~/.camoufox/kernels/chromium/154.0.8037.unpacking/`；
   * 全部解压完成、权限修补完毕且通过执行测试后，通过操作系统原子重命名（`os.rename`）生效为目标目录；
   * 彻底避免因网络中断、误关机或强制杀进程造成“半残留损坏内核”，保证本地资产库 100% 健壮。

---

## 10. 客户端 UI / UX 规范：HubStudio 级顶部「更新中心」与交互设计

为了让 CamouHub 达到与 Hubstudio 一致的商业化桌面端交互体验，在客户端主界面顶部导航栏及交互流中实现 **HubStudio 级「更新中心 (Update Center)」**。

```
CamouHub 顶部导航栏右侧布局结构示意:
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] CamouHub v1.0                                [同步器] [通知] [更新中心] │ [头像] [企业版] [退出] │
└────────────────────────────────────────────────────────────────────────────┬─────────────────────┘
                                                                             │ 点击展开
                                                                             ▼
                                                  ┌──────────────────────────────────────────────┐
                                                  │ 更新中心                            检查更新 │
                                                  ├──────────────────────────────────────────────┤
                                                  │                                              │
                                                  │             [状态 A: 无新版本]                │
                                                  │               当前没有更新内容               │
                                                  │         当前客户端: CamouHub v1.0.5          │
                                                  │         当前内核: Chromium 155 / Firefox 135 │
                                                  │                                              │
                                                  │         ───────────────────────────          │
                                                  │             [状态 B: 发现新版本]              │
                                                  │  [新版] CamouHub v1.0.6 (2026-10-16)         │
                                                  │  • 全新支持 CloakBrowser 历史内核 (154/146)  │
                                                  │  • 移动端物理窗口硬核锁定特性增强            │
                                                  │  [ 立即升级下载 (62MB) ]  [ 查看完整日志 ]   │
                                                  │                                              │
                                                  │         ───────────────────────────          │
                                                  │             [状态 C: 内核资产更新]            │
                                                  │  [内核] Chrome 154 (Cloak C++ 补丁版)        │
                                                  │  [ 一键预缓存到本地 ]                        │
                                                  │                                              │
                                                  └──────────────────────────────────────────────┘
```

### 10.1 顶部 Header 按钮布局与角标联动
* **位置对齐**：位于客户端 Header 右侧、用户账号信息（头像/企业版标签）左侧；
* **图标形态**：采用商业标准的环形旋转下载/刷新图标（`RotateCcw` / `DownloadCloud`）；
* **红点徽标 (Badge)**：
  * 当客户端启动检测到云端存在高于本地的客户端安装包，或有新上架的推荐内核时，图标右上角高亮小红点（`1` 或呼吸微动圆点）；
  * 当用户点击查看或系统更新完毕后，徽标自动消解。

### 10.2 「更新中心」浮层窗口 (Popover) 交互规范
点击更新中心图标，在下方弹出轻量精致的 Popover 窗口（宽约 `340px`，带平滑动画与阴影）：
1. **浮层 Header**：
   * 左侧：显示加粗标题 **「更新中心」**；
   * 右侧：**「检查更新」** 交互按钮。点击后图标执行平滑旋转动画，向后端 `/api/v1/releases/client` 及 `manifest.json` 发起静默校验；
2. **状态 A（已是最新，对标 Hubstudio 默认状态）**：
   * 居中展示灰度文案：`当前没有更新内容`；
   * 底部轻量展示当前运行的宿主环境版本：
     * 客户端版本：`CamouHub v1.0.5 (macOS arm64)`
     * 默认内核版本：`Chrome 155.0.8037 (自研原生)` / `Firefox 135`；
3. **状态 B（发现客户端新版本）**：
   * 显示高亮版本胶囊：`CamouHub v1.0.6 (最新)`；
   * 提取展示富文本更新日志简报（Changelog 前 3 条重点特性）；
   * 操作按钮：
     * **「立即升级」**：点击后直接在卡片内就地切换为下载进度条；
     * 下载完成后，macOS 自动调出挂载好的 `.dmg` 安装向导，Windows 自动启动 `.exe` 安装程序；
4. **状态 C（发现内核版本库更新）**：
   * 若云端上架了新的历史内核（如 `Chrome 154.0.8037 (Cloak 87 项 C++ 补丁)` 或 `Chrome 146`），卡片提示用户：
     * “发现可用新内核：Chrome 154”；
     * 用户可点击「预缓存下载」，提前将 140MB 的内核包拉取到本地，避免日后首次启动该环境时产生等待；
5. **状态 D（下载中进度实时反馈）**：
   * 无论是在更新中心点击下载，还是在主列表点击环境触发下载内核，更新中心内均能同步回显全局下载任务条（如 `下载 Chromium 154: 45MB/141MB (32%)`），支持随时暂停或取消。

### 10.3 新建/编辑环境表单：基于 User Agent 智能匹配内核机制 (100% 对标 HubStudio 图 1)
根据商业标杆 Hubstudio 的产品设计规范，在新建与编辑环境表单中，彻底取消让普通用户困惑的手动选内核繁琐步骤，实现 **“基于 User Agent 智能推导内核版本，本地缺失自动懒加载极速下载”**：

```
Hubstudio 标准新建环境 UI 联动机制 (图 1):
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 浏览器:   [ ChroBrowser ▾ ]    [ FireBrowser ▾ ]                                                  │
│          基于 User Agent 匹配 Chrome 内核版本                                                      │
│                                                                                                    │
│ 操作系统: [ Windows ]  [ Android ]  [ iOS ]  [ macOS ]  [ Linux ]                                  │
│                                                                                                    │
│ User Agent:                                                                                        │
│   [ 随机 ]   [ 自定义 (高亮选中) ]                                                                 │
│   [ 全部 ▾ ] [ Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ... Chrome/154.0.8037.57 ... 🔀 ]  │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                    │ 实时解析 Chrome/(\d+)
                                                    ▼
                             ┌──────────────────────────────────────────────┐
                             │ 右侧【环境预览】实时联动状态:                  │
                             │   浏览器: ChroBrowser (智能匹配)             │
                             │   指纹ID: LDOhQ0j5AWaYnUA7JwB3 (全球唯一)    │
                             │   操作系统: macOS                            │
                             │   User Agent: Chrome/154.0.8037.57 ...       │
                             │   内核状态: ⚡️ 启动时自动下载 Chrome 154      │
                             └──────────────────────────────────────────────┘
```

1. **浏览器组件与提示语规范**：
   * 在浏览器选项（`ChroBrowser` / `FireBrowser`）下方，明确展示提示文本：
     `基于 User Agent 匹配 Chrome 内核版本`；
2. **User Agent 模式切换与实时解析推导算法**：
   * **「随机」模式**：系统在当前受支持的真实版本库池（如 Chrome 155、154、146）中随机抽取，生成符合所选操作系统的真实原生 UA；
   * **「自定义」模式**：
     * 提供版本快速筛选下拉框（`全部`、`155`、`154`、`146` 等）；
     * 提供 UA 完整编辑框，右侧附带 `🔀 随机置换` 按钮；
     * **实时正则智能推导引擎**：
       ```typescript
       // 前端与后端统一推导算法
       function inferKernelFromUA(ua: string, engine: 'chromium' | 'camoufox'): string {
         if (engine === 'camoufox') return '135.0';
         // 匹配 Chrome/xxx 或 CriOS/xxx
         const match = ua.match(/(?:Chrome|CriOS)\/(\d+)/i);
         if (!match) return '155.0.8037'; // 默认基准自研内核
         const major = parseInt(match[1], 10);
         if (major >= 155) return '155.0.8037';     // 自研前向轨 (≥155)
         if (major >= 150) return '154.0.8037';     // Cloak 历史轨 (150-154)
         if (major >= 140) return '146.0.7680';     // Cloak 经典长周期轨 (140-149)
         return '146.0.7680';                       // 兜底稳定历史轨
       }
       ```
3. **右侧「环境预览 (Profile Preview)」实时动态回显**：
   * 当用户键入或置换 UA 时，右侧面板即时呈现：
     * `浏览器: ChroBrowser (智能匹配 Chrome 154 内核)`；
     * 若检测到该内核本地尚未下载，右侧状态标签微动提示：`⚡️ 云端就绪 · 启动时全自动秒级下载`；
   * 提交保存时，环境数据自动将推导出的 `kernel_version` 固化绑定（终身不可变）。

### 10.4 启动环境零感静默下载流转 (Zero-touch Auto-Download on Launch)
当用户在环境列表或分组卡片点击「打开」时，全流程实现 **零弹窗中断、零二次点击** 的极速自愈体验：
1. **第一步（本地检索）**：
   * 调度器检查本地 `~/.camoufox/kernels/chromium/{kernel_version}/` 是否就绪；
   * 若就绪：按钮变为 `正在启动`，1 秒内直接唤起浏览器窗口；
2. **第二步（本地缺失时自动静默下载）**：
   * 列表行内按钮状态自动平滑流转为：
     `下载 Chrome 154 内核 35% (50MB/141MB)`（带波纹进度条动画）；
   * 通过国内加速通道 / GitHub Releases 并发拉取分片；
3. **第三步（原子解压与权限自动修补）**：
   * 下载完成后后台自动进行 SHA-256 签名比对；
   * 临时解压并原子生效，macOS 自动剥离 `com.apple.quarantine` 隔离标志；
4. **第四步（自动无缝开窗并直达雷达页）**：
   * 解压完成瞬间，系统**无需用户再次点击「打开」**，直接调起浏览器，挂接 `libcamou_window_lock.dylib` 物理窗口锁，首屏自动呈现全维雷达环境检测页；
   * 单一内核在本地仅下载一次，后续所有绑定该内核的历史环境均实现毫秒级秒开复用。

### 10.5 客户端程序启动全自动检测与自动更新流程 (Auto-Update on Startup Lifecycle)
为了保障全体客户环境协议与核心防关联逻辑的最新状态，客户端在冷启动时实现 **工业级自检与全自动升级闭环**：

```
                             [用户双击打开 CamouHub 客户端]
                                           │
                                           ▼
                       [应用启动生命周期钩子 (App Launch Hook)]
                                           │
                                           ▼
                   向云端请求最新 manifest.json /api/v1/releases/client
                                           │
                                           ▼
                      云端版本 latest_version > 本地当前版本 current_version ?
                                ├── 否 ──> [秒级进入主界面] 顶部更新中心显示“已是最新”
                                └── 是 ──> 命中更新策略分支:
                                           ├── [分支 A: 强制更新 (is_force_update = true 或 < min_version)]
                                           │     1. 首屏全屏模态拦截: “检测到重要客户端更新，正在自动升级...”
                                           │     2. 全自动极速多线程下载最新分发包 (带真实进度百分比)
                                           │     3. 下载校验通过后，自动调用底层脚本覆盖替换并重启
                                           │
                                           └── [分支 B: 常规更新 (平滑自更新)]
                                                 1. 顶部 Header「更新中心」即刻点亮红点徽标 (Badge)
                                                 2. 后台并发静默下载最新客户端安装包至临时缓存
                                                 3. 下载完成后弹出轻量提示卡: “新版 v1.0.6 已就绪，点击立即重启完成更新”
                                                 4. 若用户暂不重启，在下次正常退出客户端时完成自更新
```

1. **多操作系统全自动覆盖热升级实现**：
   * **macOS 平台全自动静默升级**：
     ```bash
     # 1. 后台无感挂载 DMG
     hdiutil attach -nobrowse -quiet /path/to/CamouHub-1.0.6-mac-arm64.dmg -mountpoint /Volumes/CamouHubUpdate
     # 2. 覆盖替换应用程序目录
     rm -rf /Applications/CamouHub.app
     cp -R /Volumes/CamouHubUpdate/CamouHub.app /Applications/
     # 3. 剥离 Gatekeeper 隔离属性并卸载卷宗
     xattr -rd com.apple.quarantine /Applications/CamouHub.app
     hdiutil detach /Volumes/CamouHubUpdate -quiet
     # 4. 重新拉起全新进程并退出老实例
     open -n /Applications/CamouHub.app && exit 0
     ```
   * **Windows 平台全自动静默升级**：
     ```cmd
     :: 下载最新安装程序后，后台静默执行覆盖安装
     CamouHub-1.0.6-win-x64-setup.exe /SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
     ```
2. **系统设置项与权限容灾**：
   * 在「系统设置 -> 偏好设置」中默认勾选：`☑️ 启动时自动检查并静默更新客户端`；
   * 若遇到无管理员写权限（如受限 Windows 普通用户或企业管控域），系统优雅降级为弹出标准下载指引并直链打开安装包。

---

## 11. 自动化云漫游与全生命周期无感同步设计 (Automated Cloud Roaming & Lifecycle Sync)

### 11.1 业务背景与标准指纹浏览器体验重塑
在商业级指纹浏览器（如 AdsPower、Hubstudio、BitBrowser、Multilogin）的工业标准中，**云端漫游对用户必须是透明、全自动且无感的**。
- **现状痛点**：目前 CamouHub 将云漫游功能放在环境右键菜单的「备份至云漫游」与「从云漫游恢复」按钮上，属于反直觉的手动操作设计。用户在关闭浏览器或跨设备切换时，一旦遗漏手动点击，就会造成账号登录凭证（Cookies）、本地缓存与操作记录丢失。
- **设计目标**：取消强制手动操作，建立**开窗前自动拉取（Auto-Pull）**与**关窗后自动备份（Auto-Push）**的生命周期闭环，保障用户随时随地换机无缝续开，同时在列表以状态徽标清晰反馈同步状态。

---

### 11.2 全生命周期时序闭环与状态机设计

```
[用户点击「打开」]
       │
       ▼
 [检查本地 Profile 是否存在 或 云端是否有更新 Snapshot]
       ├── (需更新/初次在新机器打开) ──> [后台静默拉取 R2 快照 (Auto-Pull)] ──> [解压覆写本地目录]
       └── (本地已是最新) ───────────────> [跳过拉取]
                                                │
                                                ▼
                                    [启动内核进程 (带入完整会话)]
                                                │
                                                ▼
                                    [运行中：用户正常浏览操作]
                                                │
                                                ▼
                        [用户关闭浏览器 或 后台 API 触发 close_browser]
                                                │
                                                ▼
                                  [捕获进程退出事件 (_on_browser_exit)]
                                                │
                                                ▼
                                  [UI 即刻显示「🔄 正在同步云端...」]
                                                │
                                                ▼
                        [后台异步打包 Cookies/Storage 并上传至 R2 (Auto-Push)]
                                                │
                                                ▼
                                   [上传完成，释放租约锁 (Lease)]
                                                │
                                                ▼
                                  [UI 状态变更为「☁️ 已同步就绪」]
```

#### 时序流程图 (Sequence Diagram)
```mermaid
sequenceDiagram
    autonumber
    actor User as 用户 (Web UI / 客户端)
    participant Core as ProfileManager 后端调度器
    participant Storage as Cloudflare R2 云存储
    participant Browser as 浏览器内核进程 (Camoufox/Chromium)

    Note over User, Storage: 阶段 1：启动环节 (Auto-Pull)
    User->>Core: 点击「打开环境」 (launch_browser)
    Core->>Core: 检查本地缓存与云端版本校验 (ETag/Timestamp)
    alt 本地无数据 或 云端快照版本更新
        Core->>Storage: GET /camoufox/cloud_profiles/{id}/snapshot.tar.gz
        Storage-->>Core: 返回快照数据流
        Core->>Core: 解压并还原 Cookies/LocalStorage/IndexedDB
    end
    Core->>Browser: 调起浏览器进程，装配指纹与会话
    Core-->>User: 状态更新为「运行中」

    Note over User, Storage: 阶段 2：退出环节 (Auto-Push)
    User->>Browser: 用户关闭浏览器窗口
    Browser-->>Core: 进程退出信号 (_on_browser_exit)
    Core->>User: UI 状态更新为「🔄 同步中...」(短暂保护防连点)
    Core->>Core: 打包过滤关键会话数据 (pack_profile_snapshot)
    Core->>Storage: PUT /camoufox/cloud_profiles/{id}/snapshot.tar.gz
    Storage-->>Core: 上传成功响应 (200 OK)
    Core->>Core: 安全释放租约锁 (release_lease)
    Core-->>User: 状态更新为「☁️ 已同步」
```

---

### 11.3 核心资产归档范围与瘦身过滤策略
指纹浏览器如果将整个数十 GB 的浏览器缓存直接上传，会导致流量爆炸和同步延迟。系统必须采取**白名单精细化归档**：

| 分类 | 路径/数据对象 | 是否同步 | 说明 |
| :--- | :--- | :---: | :--- |
| **登录态凭证** | `Default/Network/Cookies`, `Default/Cookies` | **是** | 确保账号登录状态不失效（核心资产） |
| **前端持久化** | `Default/Local Storage/`, `Default/IndexedDB/` | **是** | 电商/社交平台 Token 与前端状态 |
| **会话状态** | `Default/Session Storage/` | **是** | 页面临时状态保持 |
| **偏好设置** | `Default/Preferences`, `Default/Web Data` | **是** | 浏览器内置表单、账号自动填充记录 |
| **元数据快照** | `profile_meta.json` | **是** | 环境基础信息、指纹种子与代理绑定配置 |
| **多媒体与网页缓存** | `Default/Cache/*`, `Default/Code Cache/*` | **否** | 极度臃肿无用数据，全量过滤，节省 90% 流量 |
| **崩溃日志/GPU缓存** | `Crashpad/*`, `GPUCache/*` | **否** | 宿主机本地硬件相关临时文件，杜绝跨机污染 |

---

### 11.4 分布式租约锁（Lease）与跨端并发写冲突防御 (Split-Brain 防护)
为杜绝多台设备或多名团队成员在同一时刻打开同一环境导致数据互相覆盖踩踏：
1. **分布式租约锁绑定**：启动时调用 `storage.acquire_lease(profile_id, lease_holder, ttl)`。
2. **同步期间锁延长**：在浏览器关闭后、数据上传 R2 期间，后台保持锁占用，直到 `upload_profile_to_r2` 返回成功后才正式调用 `release_lease`。
3. **防踩踏拦截**：若另一台电脑或同一终端在同步未完成时试图打开该环境，系统拦截并提示：`「该环境正在同步至云端，请稍候 2 秒后重试」`。

---

### 11.5 弱网容错与离线待传队列机制 (Offline Pending Queue)
1. **网络超时重试**：上传 R2 配置 30 秒超时，发生网络闪断时后台自动按指数退避重试 3 次。
2. **离线待传标记**：若彻底断网（如关机或移动网络中断），本地标记状态为 `sync_status = "pending_push"`。在客户端下次联网或下次启动 CamouHub 时，后台自动守护线程扫描并补传未完成的云备份。

---

### 11.6 前端 UI / UX 规范重构
1. **移除二级菜单强制操作**：
   * 移除环境列表中突兀的「备份至云漫游」与「从云漫游恢复」主操作；
   * 仅在环境编辑页的「高级设置」中保留一个应急按钮：`「从云端重置覆盖本地数据 (应急兜底)」`。
2. **列表原生云同步状态徽标**：
   * **静默态（已同步）**：展示轻量图标 `☁️`（或鼠标悬停显示 `上次云同步于 14:32:05 (1.8 MB)`）；
   * **同步中**：展示动画图标 `🔄 同步中...`，此时该环境的「打开」按钮暂时禁用，避免写冲突；
   * **异常态**：展示 `⚠️ 待同步`，点击可触发立即重传并查看错误日志。
3. **全局/独立同步开关**：
   * 「系统设置 -> 偏好设置」提供全局开关：`☑️ 开启全自动云端漫游 (跨设备同步)`；
   * 环境配置允许单独覆盖：如针对爬虫大数据量测试环境，可单独标记 `关闭云同步`。

---

### 11.7 商业级核心防御 A：Chromium 跨机 OSCrypt / DPAPI 密钥解耦机制
* **核心隐患与机理**：
  * 原生 Chromium 在保存 Cookie、密码和 LocalStorage 时，默认调用操作系统的硬件级加密接口：
    * **Windows**：调用 Windows DPAPI (`CryptProtectData`)，使用当前登录 Windows 用户的密码哈希作为密钥；
    * **macOS**：调用系统 Keychain（钥匙串访问）生成加密密钥存储在系统钥匙串中；
    * **Linux**：调用 Gnome Keyring 或 KWallet。
  * **跨设备灾难**：如果电脑 A（如 Windows 机器）将包含 DPAPI 加密的 `Default/Network/Cookies` 同步到 R2，电脑 B（无论是另一台 Windows 还是 macOS）拉取该快照并启动 Chromium 时，Chromium 将**因私钥不匹配导致解密失败，并强制清空所有 Cookies**，表现为“所有账号跨机全部退出登录”。
* **内核级解耦规范**：
  1. **启动参数解耦注入**：
     * Chromium 启动时统一追加 `--password-store=basic`、`--use-mock-keychain`；
  2. **内核源码级 Patch 约束**：
     * 在 CloakBrowser 与自研 Chrome 155+ 内核中，强制 Patch `components/os_crypt/` 模块，将 `OSCrypt::EncryptString` 和 `OSCrypt::DecryptString` 替换为固定的应用级软加密（如 AES-256-GCM 固定盐值），彻底剥离操作系统私钥依赖；
  3. **Camoufox (Firefox) 适配**：
     * Firefox 本身默认采用 profile 目录下的 `key4.db` 与 `logins.json` 本地密码库，不强依赖系统 DPAPI，只要随 profile 目录完整打包即可天然支持跨机器无缝解密。

---

### 11.8 商业级核心防御 B：进程退出 SQLite WAL 日志合并与文件锁安全合流
* **核心隐患与机理**：
  * Chromium 与 Firefox 在运行过程中对 `Cookies`、`Web Data`、`History` 等数据库均开启了 SQLite WAL（Write-Ahead Logging）预写日志模式；
  * 当用户点击关闭浏览器时，主进程（Browser Process）虽然退出了，但 GPU 进程、网络服务进程（Network Service）或 CrashpadHandler 往往存在 300ms ~ 1000ms 的 I/O 滞后延迟；
  * 若后台在收到主进程退出信号瞬间立刻执行打包，会遭遇两大灾难：
    1. **文件锁冲突**：操作系统抛出 `PermissionError: [Errno 13] Permission denied: .../Default/Network/Cookies`；
    2. **数据损坏/未刷盘**：`Cookies-wal` 临时日志尚未 Checkpoint 合并入主文件，导致打包上去的数据缺少最新的会话与 Cookie。
* **安全合流与打包规范**：
  1. **Graceful Teardown 静默期**：捕获退出信号后，后台异步任务先进行 500ms 的 I/O 静默等待；
  2. **SQLite Checkpoint 校验与临时 Staging**：
     * 复制打包前，检查目标目录是否仍被未退出的僵尸进程占用；
     * 采用 **Copy-on-Staging 模式**：先将所需同步的白名单文件原子复制到临时工作区（`scratch/sync_staging/{profile_id}`），若存在 `-wal` 和 `-shm`，一并复制；
     * 在临时工作区完成压缩归档后，立即释放清理临时 staging 目录，确保 100% 避免因文件锁定引发同步失败。

---

### 11.9 商业级核心防御 C：云端全局租约协调器 (Global Session Coordinator，跨电脑防双开)
* **核心隐患与机理**：
  * 单机版租约（Lease）仅存在于本机 SQLite 或单个客户端的内存中；
  * 如果操作员在办公室电脑 A 正在运行环境 A，另一位操作员（或该用户回家后）在电脑 B 同时也点击了打开环境 A；
  * **后果**：双端同时写入同一个账号，不仅会引发平台极度敏感的“异地高频并发操作”风控封号，关窗时还会发生两端数据互相覆盖（Split-Brain 脑裂）。
* **全局分布式锁架构**：
  1. **云端中心租约表（Central Lease Registry）**：
     * 打开环境前，客户端必须向云端 API 发送租约申领请求（带有 `client_id`、`hostname`、`user_id`、`expires_at`）；
     * 云端中心判断该环境当前是否已被其他终端持有且仍在心跳保活期（TTL 默认 60 秒，每 20 秒心跳续约）；
  2. **异地冲突阻断响应**：
     * 若已被电脑 A 持有，电脑 B 启动时强拦截，弹窗明确提示：
       > ⚠️ **环境冲突警告**  
       > 该环境当前正在设备 **[PC-Office-03 (张三)]** 运行中（心跳时间: 10 秒前）。  
       > 为保障账号安全，禁止多端同时打开！  
       > [确定]  [申请强制接管(需管理员权限)]
  3. **关窗释放与数据落盘确认**：
     * 关窗后，电脑 A 必须等待 Auto-Push 将最新快照成功上传至 R2，再向云端注销租约锁，彻底杜绝数据版本踩踏。

---

### 11.10 商业级高价值功能：多版本快照时光机与一键回滚 (Snapshot History & Rollback)
* **商业溢价痛点**：
  * 跨境电商或社媒运营中，用户极易因误触封禁策略、自动化脚本误操作或密码被改，导致当前会话被毁；
  * 若云漫游只保留单版本覆盖，坏数据一旦被 Auto-Push 同步上去，原始完好的登录态将万劫不复；
  * 商业指纹浏览器（如 Multilogin、AdsPower 企业版）的核心卖点之一就是**快照时光机**。
* **架构设计与生命周期管理**：
  1. **分级快照存储拓扑**：
     ```
     /{R2_BUCKET}/tenants/{tenant_id}/profiles/{profile_id}/
         ├── latest.tar.gz                     # 最新热快照 (开窗默认秒级拉取)
         ├── latest.meta.json                  # 元数据 (时间戳, 大小, 操作人, 设备名)
         └── history/                          # 历史版本库 (时光机)
             ├── 20261015_093012_v1.tar.gz
             ├── 20261015_184500_v2.tar.gz
             └── 20261016_072011_v3.tar.gz
     ```
  2. **滚动淘汰策略（Rolling Retention）**：
     * 默认保留最近 **5 个有效版本**（或最近 7 天的版本快照），超期版本后台基于 R2 Lifecycle Rules 自动清理，平衡存储成本与历史安全性；
  3. **前端 UI：一键回滚时光机**：
     * 在环境详情页或操作菜单增加「快照历史时光机」弹窗，列表清晰呈现历史备份的时间、文件大小、操作设备及备注；
     * 用户点击「回滚到该版本」时，系统拉取该历史归档并替换本地环境，实现“会话级一键复活”。

---

### 11.11 企业级多租户隔离与 R2 数据安全架构 (Tenant Namespacing & Access Control)
* **安全漏洞防御**：
  * 严禁在存储桶根目录下扁平存放快照文件（如 `R2_PREFIX/{profile_id}/...`），否则存在被遍历或横向越权拉取的重大合规漏洞；
* **企业级隔离规范**：
  1. **层级化存储路径**：
     `/{R2_BUCKET}/tenants/{tenant_id}/workspaces/{workspace_id}/profiles/{profile_id}/`；
  2. **API 权限鉴权链**：
     * 每次 `Auto-Pull` 与 `Auto-Push` 均需经过服务端 JWT 验证；
     * 校验当前请求的用户是否对该 `tenant_id` 和环境具有 `VIEW / LAUNCH / EDIT` 权限；
  3. **数据静态加密 (Encryption at Rest)**：
     * 快照数据在上传前由客户端使用团队派生密钥（Team Key）进行端到端加密（AES-GCM），即使云存储 Bucket 遭到未授权嗅探，也无法被任何第三方反解。

---

### 11.12 客户端磁盘 LRU 智能冷热淘汰机制 (Storage Eviction & Cloud-Only Mode)
* **痛点**：
  * 重度用户单台电脑管理上千个环境，随着使用时间累积，本地磁盘空间迅速被消耗数百 GB；
* **机制设计**：
  1. **云端全量，本地轻量（Cloud-First Architecture）**：
     * 云端永远保留最新快照；本地环境标记为两种物理状态：
       * `HOT (本地已缓存)`：直接秒开；
       * `COLD (仅云端保留 / Cloud-Only)`：本地不占用物理磁盘，仅存元数据；点击打开时自动触发拉取转换为 `HOT`；
  2. **LRU 自动归档休眠**：
     * 当本地检测到可用磁盘空间不足（如低于 15%）或环境连续超过 14 天未在当前设备启动，且已确认云端存在完好快照；
     * 系统自动释放本地 `Default/` 缓存目录，将状态更新为 `☁️ 仅云端归档`，为用户节省上百 GB 宝贵的本地 SSD 空间。

---

## 12. 商业级服务端架构演进与资产流量分流规范 (Server Architecture Evolution & Traffic Decoupling)

### 12.1 动静资产绝对解耦与流量双轨制
为确保支撑千级团队客户并发使用，系统确立严格的**动静资产分离原则**，严禁使用业务服务器本身的公网带宽承载大文件吞吐：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CamouHub 资产与流量分流体系                        │
├────────────────────────────────┬────────────────────────────────────────────┤
│ 1. 静态公开大资产 (Static Public Assets)│ 2. 动态私密用户资产 (Dynamic Private Assets) │
│ (多内核 155/154/146, 客户端 DMG/EXE)   │ (环境 Session, Cookies, LocalStorage 快照)  │
├────────────────────────────────┼────────────────────────────────────────────┤
│ 托管位置：GitHub Releases 官方仓       │ 托管位置：Cloudflare R2 (私有加密 Bucket)    │
│ 存储/带宽成本：0 成本 (GitHub 承载)    │ 传输机制：客户端 S3 预签名直传 (0 服务器中转)│
│ 分发通道：全球 Fastly CDN + 国内镜像加速│ 鉴权安全：JWT 租户命名空间 + AES-GCM 端到端加密│
└────────────────────────────────┴────────────────────────────────────────────┘
```

1. **静态大资产（严格走 GitHub Releases）**：
   * 所有历史内核包（`155.0.zip`、`146.0.tar.gz` 等）与桌面客户端安装包（`CamouHub.dmg`、`Setup.exe`）全量托管于 GitHub 官方 Releases 资产库；
   * 客户端在启动自检或缺少内核时，直连 GitHub Releases 全球 CDN 或系统内置的国内反代加速节点，**业务应用服务器不发生 1 字节大文件流量**。
2. **动态私密漫游快照（严格走私有 R2 预签名直传）**：
   * 用户环境的真实登录态（Cookies、LocalStorage）具有极高商业机密性，绝不能公开；
   * 快照存储于 Cloudflare R2 私有桶，采用预签名授权让客户端与 R2 直接通信。

---

### 12.2 核心机制：S3 预签名直传 (Presigned Upload/Download Architecture)
* **传统模式缺陷**：客户端把 50MB 快照传给业务服务器，服务器再转存云存储。当多操作员集中关窗时，业务服务器网卡瞬时打满瘫痪；
* **预签名直传时序闭环**：

```mermaid
sequenceDiagram
    autonumber
    actor Client as 桌面客户端 (Desktop Client)
    participant Server as CamouHub 业务服务器 (FastAPI)
    participant R2 as Cloudflare R2 对象存储

    Note over Client, R2: 场景 A：关窗自动备份 (Auto-Push 直传)
    Client->>Server: POST /api/v1/sync/presigned-upload (携带环境 ID 与 JWT)
    Server->>Server: 校验租户权限与环境归属
    Server->>Server: 生成带 5 分钟有效期的 R2 PUT 预签名授权 URL
    Server-->>Client: 返回 { upload_url: "https://r2.../snapshot.tar.gz?sig=...", expires_in: 300 }
    Client->>R2: HTTP PUT [快照数据流] (直推 R2，绕过业务服务器)
    R2-->>Client: 200 OK (上传成功)
    Client->>Server: POST /api/v1/sync/confirm-upload (上报大小、ETag，释放租约)

    Note over Client, R2: 场景 B：开窗自动恢复 (Auto-Pull 直拉)
    Client->>Server: GET /api/v1/sync/presigned-download (请求拉取凭证)
    Server-->>Client: 返回带有 SigV4 的临时 GET 预签名直链
    Client->>R2: HTTP GET [数据流] (极速拉取并本地解压)
```

* **收益**：业务服务器实现 **“零大文件流量中转”**，服务器仅处理几百字节的 JSON 元数据鉴权，CPU 与网络负载降低 99%。

---

### 12.3 数据库引擎双轨制演进 (Dual-Engine Storage Architecture)
为兼顾“个人单机轻量开箱即用”与“企业级多端高并发协作”，数据持久层必须完成存储适配器解耦：

1. **单机轻量模式 (Lite Mode - 默认保留)**：
   * **引擎**：内置 SQLite 3（开启 WAL 模式）；
   * **适用场景**：单人单机桌面自用、无需配置外部服务，零依赖秒起。
2. **企业生产模式 (Enterprise Production Mode - 商业推荐)**：
   * **引擎**：PostgreSQL 15+ / MySQL 8.0；
   * **适用场景**：工作室、团队多人协作、自动化多任务并发；
   * **核心优势**：行级锁（Row-Level Locking）、真正的高并发读写、彻底根绝 `database is locked` 报错；
   * **切换方式**：仅需在服务端环境变量中配置 `DATABASE_URL=postgresql://user:pass@pg-host:5432/camouhub` 即可自动生效，底层数据模型统一使用 SQLAlchemy / 抽象 Storage 适配器。

---

### 12.4 分布式状态中枢：Redis 全局锁与 WebSocket 实时总线
1. **Redis 毫秒级全局分布式锁 (Redlock & Heartbeat)**：
   * Key 设计：`camouhub:lease:{tenant_id}:{profile_id}`；
   * 跨电脑防双开：打开环境时以原子操作获取 Redis 锁（设置 TTL 60 秒，客户端后台每 20 秒发送一次保活心跳）；
   * 关窗或异常掉线时，锁自动超时释放或由客户端确认同步后主动 `DEL`。
2. **WebSocket 实时状态流广播 (Real-time Event Bus)**：
   * 淘汰前端每 3 秒全量调用列表接口的高频轮询机制；
   * 当电脑 A 上传完成或电脑 B 打开环境时，服务端通过 WebSocket 向所有在线客户端广播轻量事件：
     ```json
     {
       "event": "PROFILE_SYNC_COMPLETED",
       "tenant_id": "team_001",
       "profile_id": "ha6e9wwj",
       "sync_status": "synced",
       "size_kb": 1840,
       "timestamp": "2026-10-16T07:40:00Z"
     }
     ```
   * 前端列表接收事件后局部刷新徽标，状态切换实时且零延迟。

---

### 12.5 生产部署容器拓扑升级 (Production Docker Topology)
商业化环境下的 `docker-compose.yml` 推荐架构拓扑：

```yaml
services:
  # 核心业务 API 与前端 UI (轻量无状态应用)
  camouhub-server:
    image: camouhub/server:latest
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://cpm_user:cpm_pass@postgres:5432/camouhub
      - REDIS_URL=redis://redis:6379/0
      - R2_ACCESS_KEY_ID=${R2_ACCESS_KEY_ID}
      - R2_SECRET_ACCESS_KEY=${R2_SECRET_ACCESS_KEY}
      - R2_HOST=a416a58f6b1d69a87d52bf0c70c27163.r2.cloudflarestorage.com
      - R2_BUCKET=tikmatrix
    depends_on:
      - postgres
      - redis

  # 企业级关系型数据库
  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    volumes:
      - pg-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=camouhub
      - POSTGRES_USER=cpm_user
      - POSTGRES_PASSWORD=cpm_pass

  # 高速分布式锁与消息中枢
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data

volumes:
  pg-data:
  redis-data:
```

---

## 13. 分步开发实施计划

### 第一阶段：适配器实现与内核参数对齐（核心准备）
1. 扩展 `kernel_manager.py`，支持识别 `flavor: "cloak_stealth"` 与相关元数据；
2. 改造 `chromium_launcher.py`，实现 CloakBrowser 的启动参数装配、指纹种子固化与扩展精简协同模式；
3. 完成本地雷达检测页对 `< 155` 内核的自动导向与联动显示。

### 第二阶段：云端多内核库归档与自动下载
1. 在自主 GitHub Release 库归档打包好的 Windows x64 与 macOS arm64/x64 的 CloakBrowser 历史内核（154.0 / 146.0）；
2. 更新云端 `manifest.json`，配置对应版本的下载 URL、SHA256 与文件大小；
3. 测试启动环境时本地缺失历史内核的自动静默下载与秒开调起。

### 第三阶段：管理后台双中台与客户端「更新中心」UI 落地
1. 完善管理后台 `/5DRnDsWW` 的 **「版本与内核中台」**，确保「软件版本管理」和「核心版本库」两大板块均能完整支持可视化录入与热更新；
2. 在客户端 `AppShell` 顶部 Header 右侧按照 Hubstudio 标准增加 **「更新中心」Popover 组件**，实现检查更新、无更新空状态、新版推送与下载进度回显；
3. 升级创建/编辑环境界面的内核版本下拉框，清晰展示 `Chrome 155 (首发推荐)`、`Chrome 154 (Cloak 87 项 C++ 补丁)`、`Chrome 146 (经典长周期)`。

### 第四阶段：全维风控测试与验证
1. 在 BrowserScan、Iphey、Pixelscan、Cloudflare Turnstile 测试站分别对 155 原生内核与 154/146 历史内核进行跑分测试；
2. 确保得分均为 100% / Normal，无任何自动化信号泄漏。

### 第五阶段：全自动云端漫游生命周期闭环与商业防御落地
1. **启动/退出生命周期挂接**：在 `ProfileManager.launch_browser` 挂接 `Auto-Pull`，在 `_on_browser_exit` 与 `close_browser` 挂接 `Auto-Push` 异步任务；
2. **OSCrypt 跨机解密与 SQLite WAL 保护**：实现 Chromium 跨机 DPAPI 软解耦参数注入，并在归档前增加 500ms 静默合流与 Staging 临时隔离；
3. **全局租约协调与防双开**：接入全局会话锁与异地并发打开拦截提示；
4. **多版本时光机与租户隔离**：重构 R2 路径规范（`tenants/{id}/...`），实现滚动保留 5 个历史版本；
5. **UI 重构与磁盘 LRU 清理**：移除右键菜单中的手动上传/下载按钮，落地列表实时云同步状态徽标（已同步/同步中/冷归档）及快照时光机弹窗。

### 第六阶段：服务端架构现代化与 R2 预签名直传升级
1. **预签名直传改造**：在后端提供 `/api/v1/sync/presigned-upload` 与 `presigned-download`，客户端直连 R2，实现服务端 0 带宽消耗；
2. **数据库驱动适配**：完成 Storage 存储层对 PostgreSQL 的兼容抽象；
3. **Redis 分布式锁与 WebSocket 接入**：建立毫秒级并发租约控制与前端实时状态推送总线。
