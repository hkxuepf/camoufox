"""Comprehensive API Diagnostics Suite for CamouHub.

Tests:
1. Standard & HubStudio dual ports (18888 & 6873)
2. HubStudio API compatibility suite (env CRUD, UA, cookies, browser lifecycle, CDP)
3. Automation & VIP credentials suite (credentials, apply, reset-secret, active)
4. CamouHub Native REST API suite (system, profiles, proxies, groups, extensions, schedules)
5. Zero lingering process verification
"""

import json
import subprocess
import time
import psutil
import requests

RESULTS = []

def report(suite: str, endpoint: str, status: bool, detail: str = ""):
    icon = "✓ PASS" if status else "✗ FAIL"
    RESULTS.append((suite, endpoint, status, detail))
    print(f"[{icon}] [{suite}] {endpoint} - {detail}")


def main():
    print("=" * 70)
    print("      CamouHub API 全功能自动化巡检与诊断测试")
    print("=" * 70)

    # 1. 终止残留后台进程
    for p in psutil.process_iter(["pid", "name"]):
        n = (p.info.get("name") or "").lower()
        if "camoufox-pm" in n or "chromium" in n:
            try:
                p.kill()
            except Exception:
                pass
    time.sleep(1)

    # 2. 注入测试会话 Token
    import hashlib
    import sqlite3
    test_token = "camouhub_test_token_9999999999"
    token_hash = hashlib.sha256(test_token.encode()).hexdigest()
    try:
        db_path = "/Users/fgwl/Library/Application Support/Camoufox Profile Manager/profiles.db"
        con = sqlite3.connect(db_path)
        u_row = con.execute("SELECT id FROM users LIMIT 1").fetchone()
        u_id = u_row[0] if u_row else "test_admin"
        con.execute("INSERT OR REPLACE INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                    (token_hash, u_id, "2099-01-01 00:00:00"))
        con.commit()
        con.close()
    except Exception as e:
        print("[WARN] Session inject error:", e)

    # 3. 启动应用
    print("\n[INIT] 正在启动 /Applications/CamouHub.app ...")
    proc = subprocess.Popen(["/Applications/CamouHub.app/Contents/MacOS/camoufox-pm"])
    time.sleep(4)

    # 端点前缀与请求头
    p_main = "http://127.0.0.1:18888"
    p_hub = "http://127.0.0.1:6873"
    auth_headers = {"X-Session-Token": test_token}

    try:
        # ====================================================
        # Suite 1: 端口连通与健康检查
        # ====================================================
        try:
            r = requests.get(f"{p_main}/health", timeout=3)
            report("Port & Health", "GET :18888/health", r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            report("Port & Health", "GET :18888/health", False, str(e))

        try:
            r = requests.get(f"{p_hub}/health", timeout=3)
            report("Port & Health", "GET :6873/health (Hub Forwarder)", r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            report("Port & Health", "GET :6873/health (Hub Forwarder)", False, str(e))

        # ====================================================
        # Suite 2: 原生系统与基础 API (携带认证)
        # ====================================================
        endpoints = [
            ("GET", "/api/v1/system/status", "系统综合监控"),
            ("GET", "/api/v1/system/config", "系统运行时配置"),
            ("GET", "/api/v1/profiles", "环境列表"),
            ("GET", "/api/v1/proxies", "代理池列表"),
            ("GET", "/api/v1/groups", "环境分组列表"),
            ("GET", "/api/v1/extensions", "应用与扩展列表"),
            ("GET", "/api/v1/schedules", "定时任务列表"),
            ("GET", "/api/v1/trash/profiles", "回收站环境查询"),
        ]
        for method, path, desc in endpoints:
            try:
                r = requests.get(f"{p_main}{path}", headers=auth_headers, timeout=3)
                ok = r.status_code in (200, 201)
                report("Native API", f"{method} {path} ({desc})", ok, f"HTTP {r.status_code}")
            except Exception as e:
                report("Native API", f"{method} {path} ({desc})", False, str(e))

        # ====================================================
        # Suite 3: 自动化与 VIP 会员 API (本期重点)
        # ====================================================
        try:
            r = requests.get(f"{p_main}/api/v1/automation/credentials", timeout=3)
            d = r.json()
            ok = r.status_code == 200 and "is_member" in d and "local_endpoint" in d
            report("Automation API", "GET /api/v1/automation/credentials", ok, f"is_member={d.get('is_member')}, status={d.get('status')}")
        except Exception as e:
            report("Automation API", "GET /api/v1/automation/credentials", False, str(e))

        try:
            r = requests.post(f"{p_main}/api/v1/automation/apply", timeout=3)
            d = r.json()
            ok = r.status_code == 200 and d.get("code") == 0 and bool(d.get("data", {}).get("app_id"))
            report("Automation API", "POST /api/v1/automation/apply", ok, f"app_id={d.get('data', {}).get('app_id')}")
        except Exception as e:
            report("Automation API", "POST /api/v1/automation/apply", False, str(e))

        try:
            r = requests.post(f"{p_main}/api/v1/automation/reset-secret", timeout=3)
            d = r.json()
            ok = r.status_code == 200 and d.get("code") == 0 and bool(d.get("data", {}).get("app_secret"))
            report("Automation API", "POST /api/v1/automation/reset-secret", ok, f"new_secret_len={len(d.get('data', {}).get('app_secret', ''))}")
        except Exception as e:
            report("Automation API", "POST /api/v1/automation/reset-secret", False, str(e))

        try:
            r = requests.get(f"{p_main}/api/v1/automation/active", timeout=3)
            ok = r.status_code == 200 and "active_sessions" in r.json()
            report("Automation API", "GET /api/v1/automation/active", ok, f"active_sessions={len(r.json().get('active_sessions', []))}")
        except Exception as e:
            report("Automation API", "GET /api/v1/automation/active", False, str(e))

        # ====================================================
        # Suite 4: HubStudio 兼容规范 API 全功能检测 (CamouHub 核心端点)
        # ====================================================
        # 1. POST /login
        try:
            r = requests.post(f"{p_main}/login", json={}, timeout=3)
            report("HubStudio API", "POST /login", r.status_code == 200 and r.json().get("code") == 0, "成功返回 code:0")
        except Exception as e:
            report("HubStudio API", "POST /login", False, str(e))

        # 2. POST /api/v1/env/random-ua
        try:
            r = requests.post(f"{p_main}/api/v1/env/random-ua", json={"type": "windows"}, timeout=3)
            ua = r.json().get("data", "")
            ok = r.status_code == 200 and "Mozilla" in ua
            report("HubStudio API", "POST /api/v1/env/random-ua", ok, f"生成 UA: {ua[:35]}...")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/env/random-ua", False, str(e))

        # 3. POST /api/v1/env/create
        created_code = None
        try:
            r = requests.post(f"{p_main}/api/v1/env/create", json={
                "containerName": "API_Auto_Check_Profile",
                "remark": "自动化测试专用环境",
                "tagName": "测试分组",
                "proxyTypeName": "不使用代理"
            }, timeout=5)
            d = r.json()
            created_code = d.get("data", {}).get("containerCode")
            ok = r.status_code == 200 and d.get("code") == 0 and bool(created_code)
            report("HubStudio API", "POST /api/v1/env/create", ok, f"新环境 containerCode={created_code}")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/env/create", False, str(e))

        # 4. POST /api/v1/env/list
        try:
            r = requests.post(f"{p_main}/api/v1/env/list", json={"current": 1, "size": 10}, timeout=3)
            d = r.json()
            env_list = d.get("data", {}).get("list", [])
            ok = r.status_code == 200 and d.get("code") == 0 and len(env_list) > 0
            report("HubStudio API", "POST /api/v1/env/list", ok, f"返回环境数量={len(env_list)}, total={d.get('data', {}).get('total')}")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/env/list", False, str(e))

        # 5. Cookie 导入与导出
        test_env_id = created_code or "enhwzvfw"
        try:
            r = requests.post(f"{p_main}/api/v1/env/import-cookie", json={
                "containerCode": test_env_id,
                "cookie": json.dumps([{"name": "test_token", "value": "123456", "domain": ".example.com"}])
            }, timeout=3)
            ok = r.status_code == 200 and r.json().get("data") == True
            report("HubStudio API", "POST /api/v1/env/import-cookie", ok, "导入成功")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/env/import-cookie", False, str(e))

        try:
            r = requests.post(f"{p_main}/api/v1/env/export-cookie", json={
                "containerCode": test_env_id
            }, timeout=3)
            ok = r.status_code == 200 and "test_token" in str(r.json().get("data"))
            report("HubStudio API", "POST /api/v1/env/export-cookie", ok, "导出成功并验证包含数据")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/env/export-cookie", False, str(e))

        # 6. POST /api/v1/browser/start (启动环境)
        debug_port = None
        try:
            r = requests.post(f"{p_main}/api/v1/browser/start", json={
                "containerCode": test_env_id,
                "isHeadless": False
            }, timeout=15)
            d = r.json()
            debug_port = d.get("data", {}).get("debuggingPort")
            ok = r.status_code == 200 and d.get("code") == 0 and bool(debug_port) and debug_port > 0
            report("HubStudio API", "POST /api/v1/browser/start", ok, f"debuggingPort={debug_port}")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/browser/start", False, str(e))

        # 等待内核端口就绪
        time.sleep(2.5)

        # 7. CDP 端口握手检查
        if debug_port:
            try:
                r = requests.get(f"http://127.0.0.1:{debug_port}/json/version", timeout=5)
                ok = r.status_code == 200 and "webSocketDebuggerUrl" in r.json()
                report("CDP Verification", f"GET http://127.0.0.1:{debug_port}/json/version", ok, f"Browser={r.json().get('Browser')}")
            except Exception as e:
                report("CDP Verification", f"GET http://127.0.0.1:{debug_port}/json/version", False, str(e))

        # 8. POST /api/v1/browser/all-browser-status (状态查询)
        try:
            r = requests.post(f"{p_main}/api/v1/browser/all-browser-status", json={
                "containerCodes": [test_env_id]
            }, timeout=3)
            st = r.json().get("data", {}).get(test_env_id)
            ok = r.status_code == 200 and st == 0
            report("HubStudio API", "POST /api/v1/browser/all-browser-status", ok, f"状态值={st} (0=已开启)")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/browser/all-browser-status", False, str(e))

        # 9. POST /api/v1/browser/foreground & POST /api/v1/browser/arrange
        try:
            r = requests.post(f"{p_main}/api/v1/browser/foreground", json={"containerCode": test_env_id}, timeout=3)
            report("HubStudio API", "POST /api/v1/browser/foreground", r.status_code == 200 and r.json().get("code") == 0, "窗口置顶激活成功")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/browser/foreground", False, str(e))

        try:
            r = requests.post(f"{p_main}/api/v1/browser/arrange", json={"colNum": 2, "gapX": 10, "gapY": 10}, timeout=3)
            report("HubStudio API", "POST /api/v1/browser/arrange", r.status_code == 200 and r.json().get("code") == 0, "窗口平铺排版成功")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/browser/arrange", False, str(e))

        # 10. POST /api/v1/browser/stop (关闭指定环境)
        try:
            r = requests.post(f"{p_main}/api/v1/browser/stop", json={"containerCode": test_env_id}, timeout=5)
            report("HubStudio API", "POST /api/v1/browser/stop", r.status_code == 200 and r.json().get("code") == 0, "成功关闭")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/browser/stop", False, str(e))

        time.sleep(2)

        # 11. POST /api/v1/browser/stop-all (停止所有)
        try:
            r = requests.post(f"{p_main}/api/v1/browser/stop-all", json={}, timeout=5)
            report("HubStudio API", "POST /api/v1/browser/stop-all", r.status_code == 200 and r.json().get("code") == 0, "停止所有环境成功")
        except Exception as e:
            report("HubStudio API", "POST /api/v1/browser/stop-all", False, str(e))

        time.sleep(1)

        # 12. POST /api/v1/env/del (删除测试环境)
        if created_code:
            try:
                r = requests.post(f"{p_main}/api/v1/env/del", json={"containerCodes": [created_code]}, timeout=3)
                report("HubStudio API", "POST /api/v1/env/del", r.status_code == 200 and r.json().get("data") == True, f"删除测试环境 {created_code}")
            except Exception as e:
                report("HubStudio API", "POST /api/v1/env/del", False, str(e))

        # ====================================================
        # Suite 5: 孤儿进程清理与安全退出检查
        # ====================================================
        time.sleep(2)
        alive_chromes = [p.pid for p in psutil.process_iter(["pid", "name"]) if "chromium" in (p.info.get("name") or "").lower()]
        report("Process Lifecycle", "Chromium 孤儿进程检测", len(alive_chromes) == 0, f"关闭后存活 Chromium 数量: {len(alive_chromes)}")

    finally:
        proc.kill()

    # 统计总结
    print("\n" + "=" * 70)
    passed = sum(1 for r in RESULTS if r[2])
    failed = sum(1 for r in RESULTS if not r[2])
    total = len(RESULTS)
    print(f" 巡检总结: 共测试 {total} 个接口与功能项 | 通过: {passed} | 失败: {failed} | 通过率: {passed/total*100:.1f}%")
    print("=" * 70)
    return failed == 0

if __name__ == "__main__":
    exit(0 if main() else 1)
