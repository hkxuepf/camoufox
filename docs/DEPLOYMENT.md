# CamouHub 线上服务器配置与运维部署文档

## 一、服务器节点信息

* **服务器内网/公网 IP**: `10.10.10.5`
* **SSH 端口**: `22`
* **SSH 用户名**: `root`
* **SSH 密码**: `Xw112112!@#`
* **部署绝对路径**: `/www/wwwroot/docker/camoufox`
* **线上生产域名**: `https://camoufox.usrde.com`
* **Cloudflare Tunnel 隧道容器**: `camoufox-tunnel`
* **核心业务容器**: `camoufox-app` 
* **持久化卷**: `cpm-data:/data` (存储云端 `profiles.db` 及用户配置)

---

## 二、架构拓扑

```
[用户浏览器/客户端]
       │
       ▼ (HTTPS 443)
Cloudflare Edge CDN (camoufox.usrde.com)
       │
       ▼ (Cloudflare Tunnel: eyJhIjoiYTQ...)
camoufox-tunnel (Docker 容器)
       │
       ▼ (内网桥接 camoufox-net:8000)
camoufox-app (FastAPI + Next.js Static Export 容器)
       │
       ▼
数据卷 (/data/profiles.db)
```

---

## 三、一键自动化更新与部署流程

本地代码更新后（例如前端新增路由 `/5DRnDsWW` 管理员后台、后端新增接口、指纹内核逻辑变更），通过以下步骤同步到服务器并重新热部署：

### 1. 本地生成全量静态资源与代码归档
```bash
# 1. 导出最新静态前端
export PATH=$PATH:/Users/fgwl/.nvm/versions/node/v22.22.2/bin
python3 scripts/build_webui.py

# 2. 打包同步归档 (排除 node_modules 与虚拟环境)
tar --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='.git' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='data' \
    --exclude='.next' \
    -czf dist_sync.tar.gz .
```

### 2. 推送至服务器并解压重构
```bash
# 上传归档至目标路径
scp -P 22 dist_sync.tar.gz root@10.10.10.5:/www/wwwroot/docker/camoufox/

# SSH 登录并重新构建运行
ssh -p 22 root@10.10.10.5 "cd /www/wwwroot/docker/camoufox && tar -xzf dist_sync.tar.gz && docker compose build app && docker compose up -d"
```

---

## 四、服务健康检查与排错

1. **查看业务容器日志**：
   ```bash
   docker logs -f --tail 100 camoufox-app
   ```
2. **查看隧道容器日志**：
   ```bash
   docker logs -f --tail 100 camoufox-tunnel
   ```
3. **重启云端服务**：
   ```bash
   cd /www/wwwroot/docker/camoufox && docker compose restart
   ```

---

## 五、Windows C++ 内核专用编译机信息

* **服务器内网 IP**: `192.168.101.107`
* **SSH 端口**: `22`
* **SSH 用户名**: `Administrator`
* **SSH 密码**: `112112`
* **编译工作区目录**: `C:\Users\Administrator\Documents\camoufox`
* **常用检查命令**:
  - 查看编译进程: `powershell -Command "Get-Process -Name ninja, clang-cl"`
  - 查看编译日志: `powershell -Command "Get-Content build_ninja.log -Tail 30"`
  - 查看定时构建任务: `schtasks /query /tn ChromeBuild /v /fo list`

