'use client'

import { useEffect, useState } from 'react'
import {
  BookOpen,
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  Eye,
  EyeOff,
  KeyRound,
  Laptop,
  Lock,
  Network,
  RefreshCw,
  RotateCw,
  Shield,
  Sparkles,
  Terminal,
  User,
  Zap,
} from 'lucide-react'

import { BillingModal } from '@/components/billing-modal'
import { Modal } from '@/components/modal'
import { useAuth } from '@/components/login-gate'
import { automationAPI } from '@/lib/api'

export default function ApiServicePage() {
  const { planId, role } = useAuth()
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [billingOpen, setBillingOpen] = useState(false)
  const [docModalOpen, setDocModalOpen] = useState(false)
  const [showSecret, setShowSecret] = useState(false)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [codeTab, setCodeTab] = useState<'playwright' | 'selenium' | 'puppeteer' | 'curl'>('playwright')

  const [data, setData] = useState<{
    username: string
    is_member: boolean
    role: string
    plan_id: string
    plan_name: string
    has_applied: boolean
    status: string
    local_endpoint: string
    app_id: string
    app_secret: string
    rate_limit: string
    max_devices: number
    documentation_url: string
  }>({
    username: '',
    is_member: false,
    role: 'user',
    plan_id: 'free',
    plan_name: '免费版',
    has_applied: false,
    status: 'unapplied',
    local_endpoint: 'http://127.0.0.1:6873',
    app_id: '',
    app_secret: '',
    rate_limit: '100 次/分钟',
    max_devices: 200,
    documentation_url: '/api-service/',
  })

  const loadData = async () => {
    try {
      setLoading(true)
      const res = await automationAPI.credentials()
      setData(res)
    } catch (err) {
      console.error('Failed to load api credentials:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const copyToClipboard = (text: string, key: string) => {
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const handleApply = async () => {
    if (!data.is_member) {
      setBillingOpen(true)
      return
    }
    try {
      setApplying(true)
      await automationAPI.apply()
      await loadData()
    } catch (err: any) {
      alert(err?.message || '申请失败，请稍后重试')
    } finally {
      setApplying(false)
    }
  }

  const handleResetSecret = async () => {
    if (!confirm('重置 APP Secret 后旧密钥将立即失效，是否确认重新生成？')) {
      return
    }
    try {
      setResetting(true)
      await automationAPI.resetSecret()
      await loadData()
    } catch (err: any) {
      alert(err?.message || '重置密钥失败')
    } finally {
      setResetting(false)
    }
  }

  const isMember = data.is_member || role === 'admin' || (planId && planId !== 'free')

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12 select-text">
      {/* ================= 1. 顶部标头与文档直达 ================= */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <span className="h-6 w-1 rounded-full bg-[#1664ff]" />
            <h1 className="text-xl font-bold tracking-tight text-[#0f172a]">
              开发者中心 (API)
            </h1>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-[#64748b]">
            CamouHub 开发者中心提供完整的 Local HTTP API，支持批量创建及管理浏览器环境、打开指定环境并获取 CDP 调试端口。可与
            Selenium、Puppeteer、Playwright 等主流自动化框架对接，实现脚本化批量控制与自动化任务运营。
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => setDocModalOpen(true)}
            className="flex items-center gap-1.5 rounded-lg bg-[#1664ff] px-4 py-2 text-xs font-semibold text-white shadow-sm transition-all hover:bg-[#0e52d6] active:scale-95 cursor-pointer"
          >
            <BookOpen size={14} />
            <span>API接口文档</span>
            <span className="text-[11px] opacity-80">&gt;</span>
          </button>
        </div>
      </div>

      {/* ================= 2. 状态与配额药丸指标栏 ================= */}
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="flex items-center gap-2 rounded-full bg-[#f0f5ff] px-3.5 py-1.5 text-xs text-[#1664ff] border border-[#d6e4ff]">
          <User size={13} className="text-[#1664ff]" />
          <span>API 权限范围随团队角色</span>
        </div>

        <div className="flex items-center gap-2 rounded-full bg-[#f6ffed] px-3.5 py-1.5 text-xs text-[#389e0d] border border-[#b7eb8f]">
          <Network size={13} className="text-[#52c41a]" />
          <span>单个接口请求限制 100 次/分钟</span>
        </div>

        <div className="flex items-center gap-2 rounded-full bg-[#f0f5ff] px-3.5 py-1.5 text-xs text-[#1664ff] border border-[#d6e4ff]">
          <Laptop size={13} className="text-[#1664ff]" />
          <span>团队下 API 可开发设备数 200</span>
        </div>
      </div>

      {/* ================= 3. 主卡片：Local API 配置面板 ================= */}
      <div className="rounded-xl border border-[#eaedf1] bg-white p-6 shadow-sm">
        {/* 卡片头部 */}
        <div className="flex items-center justify-between border-b border-[#f1f5f9] pb-4">
          <div>
            <h2 className="text-base font-bold text-[#0f172a]">Local API</h2>
            <p className="mt-1 text-xs text-[#64748b]">
              通过开启本地客户端调用接口，支持浏览器 &amp; 云手机，如需API与客户端同时运行使用，只需通过命令行调用接口中的IP+端口即可。
            </p>
          </div>

          <div>
            {data.has_applied ? (
              <span className="flex items-center gap-1.5 rounded-full bg-[#e6f9ed] px-3 py-1 text-xs font-semibold text-[#10b981] border border-[#bbf7d0]">
                <Check size={13} strokeWidth={2.5} />
                <span>正常</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5 rounded-full bg-[#fef2f2] px-3 py-1 text-xs font-medium text-[#ef4444] border border-[#fecaca]">
                <span>未激活</span>
              </span>
            )}
          </div>
        </div>

        {/* 卡片主体内容 */}
        {loading ? (
          <div className="py-16 text-center text-xs text-[#94a3b8]">
            <RotateCw size={18} className="mx-auto mb-2 animate-spin text-[#1664ff]" />
            加载 API 配置中...
          </div>
        ) : !isMember ? (
          /* Case 1: 非会员限制 */
          <div className="py-10 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#fef2f2] text-[#ef4444] mb-3 border border-[#fee2e2]">
              <Lock size={26} />
            </div>
            <h3 className="text-base font-bold text-[#0f172a]">开发者 API 为会员专享功能</h3>
            <p className="mx-auto mt-2 max-w-md text-xs text-[#64748b] leading-relaxed">
              您当前为免费版用户。CamouHub Local REST API 及 CDP
              批量自动化控制仅对 VIP 会员开放。升级套餐后即可立即生成专属 APP ID 与 Secret 凭据。
            </p>
            <div className="mt-5 flex justify-center gap-3">
              <button
                type="button"
                onClick={() => setBillingOpen(true)}
                className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-[#1664ff] to-[#4080ff] px-5 py-2.5 text-xs font-semibold text-white shadow-md hover:opacity-95 cursor-pointer"
              >
                <Zap size={14} />
                <span>立即升级会员解锁 API</span>
              </button>
            </div>
          </div>
        ) : !data.has_applied ? (
          /* Case 2: 会员未申请 */
          <div className="py-10 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#f0fdf4] text-[#16a34a] mb-3 border border-[#dcfce7]">
              <Sparkles size={26} />
            </div>
            <h3 className="text-base font-bold text-[#0f172a]">
              尊贵的【{data.plan_name}】会员，点击即可申请开通
            </h3>
            <p className="mx-auto mt-2 max-w-md text-xs text-[#64748b] leading-relaxed">
              您的会员权益已包含完整的 Local 自动化 API 权限与 200 台设备并发接管。点击下方申请按钮，系统将立即为您分配独立的
              APP ID 与 Secret 访问凭据。
            </p>
            <div className="mt-5 flex justify-center gap-3">
              <button
                type="button"
                disabled={applying}
                onClick={handleApply}
                className="flex items-center gap-2 rounded-lg bg-[#1664ff] px-6 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-[#0e52d6] disabled:opacity-50 cursor-pointer"
              >
                {applying ? (
                  <>
                    <RotateCw size={14} className="animate-spin" />
                    <span>正在申请开通中...</span>
                  </>
                ) : (
                  <>
                    <KeyRound size={14} />
                    <span>立即申请开通 API</span>
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          /* Case 3: 凭据已激活展示 */
          <div className="mt-6 space-y-5">
            {/* 1. 接口地址 */}
            <div>
              <label className="block text-xs font-medium text-[#475569] mb-1.5">
                接口地址
              </label>
              <div className="relative flex items-center">
                <input
                  type="text"
                  readOnly
                  value={data.local_endpoint}
                  className="w-full rounded-lg border border-[#e2e8f0] bg-[#f8fafc] px-3.5 py-2.5 font-mono text-xs text-[#0f172a] pr-10 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(data.local_endpoint, 'endpoint')}
                  title="复制接口地址"
                  className="absolute right-3 flex h-7 w-7 items-center justify-center rounded text-[#64748b] hover:bg-[#e2e8f0] hover:text-[#0f172a] transition-colors cursor-pointer"
                >
                  {copiedKey === 'endpoint' ? (
                    <Check size={14} className="text-[#10b981]" />
                  ) : (
                    <Copy size={14} />
                  )}
                </button>
              </div>
            </div>

            {/* 2. APP ID */}
            <div>
              <label className="block text-xs font-medium text-[#475569] mb-1.5">
                APP ID
              </label>
              <div className="relative flex items-center">
                <input
                  type="text"
                  readOnly
                  value={data.app_id}
                  className="w-full rounded-lg border border-[#e2e8f0] bg-[#f8fafc] px-3.5 py-2.5 font-mono text-xs text-[#0f172a] pr-10 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(data.app_id, 'app_id')}
                  title="复制 APP ID"
                  className="absolute right-3 flex h-7 w-7 items-center justify-center rounded text-[#64748b] hover:bg-[#e2e8f0] hover:text-[#0f172a] transition-colors cursor-pointer"
                >
                  {copiedKey === 'app_id' ? (
                    <Check size={14} className="text-[#10b981]" />
                  ) : (
                    <Copy size={14} />
                  )}
                </button>
              </div>
            </div>

            {/* 3. APP Secret */}
            <div>
              <label className="block text-xs font-medium text-[#475569] mb-1.5">
                APP Secret
              </label>
              <div className="relative flex items-center">
                <input
                  type={showSecret ? 'text' : 'password'}
                  readOnly
                  value={data.app_secret}
                  className="w-full rounded-lg border border-[#e2e8f0] bg-[#f8fafc] px-3.5 py-2.5 font-mono text-xs text-[#0f172a] pr-28 focus:outline-none"
                />
                <div className="absolute right-2.5 flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setShowSecret(!showSecret)}
                    title={showSecret ? '隐藏密钥' : '显示明文密钥'}
                    className="flex h-7 w-7 items-center justify-center rounded text-[#64748b] hover:bg-[#e2e8f0] hover:text-[#0f172a] transition-colors cursor-pointer"
                  >
                    {showSecret ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                  <button
                    type="button"
                    disabled={resetting}
                    onClick={handleResetSecret}
                    title="重置 APP Secret"
                    className="flex h-7 w-7 items-center justify-center rounded text-[#64748b] hover:bg-[#e2e8f0] hover:text-[#0f172a] transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <RotateCw size={14} className={resetting ? 'animate-spin' : ''} />
                  </button>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(data.app_secret, 'secret')}
                    title="复制 APP Secret"
                    className="flex h-7 w-7 items-center justify-center rounded text-[#64748b] hover:bg-[#e2e8f0] hover:text-[#0f172a] transition-colors cursor-pointer"
                  >
                    {copiedKey === 'secret' ? (
                      <Check size={14} className="text-[#10b981]" />
                    ) : (
                      <Copy size={14} />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ================= 4. 快速接入与示例代码 Tab ================= */}
      <div className="rounded-xl border border-[#eaedf1] bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-[#f1f5f9] pb-3">
          <div className="flex items-center gap-2">
            <Terminal size={16} className="text-[#1664ff]" />
            <h3 className="text-sm font-bold text-[#0f172a]">自动化对接代码示例</h3>
          </div>

          <div className="flex rounded-lg bg-[#f1f5f9] p-0.5 text-[11px] font-medium text-[#64748b]">
            <button
              onClick={() => setCodeTab('playwright')}
              className={`rounded-md px-2.5 py-1 cursor-pointer transition-colors ${
                codeTab === 'playwright' ? 'bg-white font-semibold text-[#1664ff] shadow-xs' : 'hover:text-[#0f172a]'
              }`}
            >
              Playwright
            </button>
            <button
              onClick={() => setCodeTab('puppeteer')}
              className={`rounded-md px-2.5 py-1 cursor-pointer transition-colors ${
                codeTab === 'puppeteer' ? 'bg-white font-semibold text-[#1664ff] shadow-xs' : 'hover:text-[#0f172a]'
              }`}
            >
              Puppeteer
            </button>
            <button
              onClick={() => setCodeTab('selenium')}
              className={`rounded-md px-2.5 py-1 cursor-pointer transition-colors ${
                codeTab === 'selenium' ? 'bg-white font-semibold text-[#1664ff] shadow-xs' : 'hover:text-[#0f172a]'
              }`}
            >
              Selenium
            </button>
            <button
              onClick={() => setCodeTab('curl')}
              className={`rounded-md px-2.5 py-1 cursor-pointer transition-colors ${
                codeTab === 'curl' ? 'bg-white font-semibold text-[#1664ff] shadow-xs' : 'hover:text-[#0f172a]'
              }`}
            >
              cURL
            </button>
          </div>
        </div>

        <div className="mt-4">
          <div className="relative">
            <pre className="rounded-lg bg-[#0f172a] p-4 font-mono text-[11px] text-[#e2e8f0] overflow-x-auto leading-relaxed">
              {codeTab === 'playwright' &&
`import requests
from playwright.sync_api import sync_playwright

# 1. 启动指定环境
res = requests.post("${data.local_endpoint}/api/v1/browser/start", json={
    "containerCode": "YOUR_PROFILE_ID", # 环境 ID 或编号
    "isHeadless": False
}).json()

# 2. 获取 CDP 调试端口并接管浏览器
debugging_port = res["data"]["debuggingPort"]
ws_url = f"http://127.0.0.1:{debugging_port}"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(ws_url)
    page = browser.contexts[0].pages[0] if browser.contexts[0].pages else browser.contexts[0].new_page()
    page.goto("https://www.google.com")
    print("Page Title:", page.title())

# 3. 操作完毕后关闭环境
requests.post("${data.local_endpoint}/api/v1/browser/stop", json={"containerCode": "YOUR_PROFILE_ID"})`}

              {codeTab === 'puppeteer' &&
`const axios = require('axios');
const puppeteer = require('puppeteer-core');

async function run() {
    // 1. 启动环境
    const startRes = await axios.post('${data.local_endpoint}/api/v1/browser/start', {
        containerCode: 'YOUR_PROFILE_ID',
        isHeadless: false
    });
    const port = startRes.data.data.debuggingPort;

    // 2. 连接 CDP
    const browser = await puppeteer.connect({
        browserURL: \`http://127.0.0.1:\${port}\`
    });
    const page = (await browser.pages())[0] || await browser.newPage();
    await page.goto('https://www.google.com');
    console.log(await page.title());

    // 3. 关闭环境
    await axios.post('${data.local_endpoint}/api/v1/browser/stop', {
        containerCode: 'YOUR_PROFILE_ID'
    });
}
run();`}

              {codeTab === 'selenium' &&
`import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 1. 打开环境
res = requests.post("${data.local_endpoint}/api/v1/browser/start", json={
    "containerCode": "YOUR_PROFILE_ID",
    "isHeadless": False
}).json()
debug_port = res["data"]["debuggingPort"]

# 2. 通过 ChromeOptions 接管
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
driver = webdriver.Chrome(options=chrome_options)
driver.get("https://www.google.com")
print(driver.title)

# 3. 关闭环境
requests.post("${data.local_endpoint}/api/v1/browser/stop", json={"containerCode": "YOUR_PROFILE_ID"})`}

              {codeTab === 'curl' &&
`# 1. 查询环境列表
curl -X POST "${data.local_endpoint}/api/v1/env/list" \\
     -H "Content-Type: application/json" \\
     -d '{"current": 1, "size": 10}'

# 2. 打开指定环境并获取 debuggingPort
curl -X POST "${data.local_endpoint}/api/v1/browser/start" \\
     -H "Content-Type: application/json" \\
     -d '{"containerCode": "YOUR_PROFILE_ID", "isHeadless": false}'

# 3. 关闭环境
curl -X POST "${data.local_endpoint}/api/v1/browser/stop" \\
     -H "Content-Type: application/json" \\
     -d '{"containerCode": "YOUR_PROFILE_ID"}'`}
            </pre>
            <button
              onClick={() => {
                const codeSnippets: Record<string, string> = {
                  playwright: `import requests\nfrom playwright.sync_api import sync_playwright\n\nres = requests.post("${data.local_endpoint}/api/v1/browser/start", json={"containerCode": "YOUR_PROFILE_ID"}).json()\nport = res["data"]["debuggingPort"]\n\nwith sync_playwright() as p:\n    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")\n    page = browser.contexts[0].new_page()\n    page.goto("https://www.google.com")\n`,
                  puppeteer: `const axios = require('axios');\nconst puppeteer = require('puppeteer-core');\n\nasync function run() {\n  const res = await axios.post('${data.local_endpoint}/api/v1/browser/start', { containerCode: 'YOUR_PROFILE_ID' });\n  const browser = await puppeteer.connect({ browserURL: \`http://127.0.0.1:\${res.data.data.debuggingPort}\` });\n}\nrun();`,
                  selenium: `import requests\nfrom selenium import webdriver\nfrom selenium.webdriver.chrome.options import Options\n\nres = requests.post("${data.local_endpoint}/api/v1/browser/start", json={"containerCode": "YOUR_PROFILE_ID"}).json()\nopt = Options()\nopt.add_experimental_option("debuggerAddress", f"127.0.0.1:{res['data']['debuggingPort']}")\ndriver = webdriver.Chrome(options=opt)\n`,
                  curl: `curl -X POST "${data.local_endpoint}/api/v1/browser/start" -H "Content-Type: application/json" -d '{"containerCode": "YOUR_PROFILE_ID"}'`,
                }
                copyToClipboard(codeSnippets[codeTab], 'codeSnippet')
              }}
              className="absolute top-3 right-3 flex items-center gap-1 rounded bg-slate-800 px-2.5 py-1 text-[10px] text-slate-300 hover:bg-slate-700 hover:text-white transition-colors cursor-pointer"
            >
              {copiedKey === 'codeSnippet' ? (
                <>
                  <Check size={12} className="text-[#10b981]" />
                  <span>已复制</span>
                </>
              ) : (
                <>
                  <Copy size={12} />
                  <span>复制代码</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ================= 5. API 接口文档抽屉/弹窗 ================= */}
      <Modal
        open={docModalOpen}
        title="CamouHub 开发者 API 接口文档规范"
        onClose={() => setDocModalOpen(false)}
        width={760}
        footer={
          <div className="flex items-center justify-between w-full">
            <span className="flex items-center gap-1.5 text-xs text-[#64748b] font-mono">
              <span className="h-1.5 w-1.5 rounded-full bg-[#10b981]" />
              CamouHub Local REST API v1.0 · 本地端口: 6873 / 18888
            </span>
            <button
              onClick={() => setDocModalOpen(false)}
              className="rounded-md bg-[#1664ff] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#0e52d6] transition-colors cursor-pointer"
            >
              确定
            </button>
          </div>
        }
      >
        <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1 text-xs text-[#334155]">
          <div className="rounded-lg bg-[#f0f5ff] border border-[#d6e4ff] p-3">
            <p className="text-[11px] text-[#1664ff] leading-relaxed">
              <strong>接口规范说明：</strong>本系统提供全套标准 Local REST API 规范，纯本地运行，免外网通讯依赖。所有接口统一采用
              JSON 交互，返回结构均为 <code className="font-mono bg-white px-1 py-0.5 rounded border border-[#d6e4ff]">&#123;code: 0, msg: &quot;Success&quot;, data: ...&#125;</code>。本地默认服务监听端口为{' '}
              <code className="font-mono bg-white px-1 py-0.5 rounded border border-[#d6e4ff]">6873</code> /{' '}
              <code className="font-mono bg-white px-1 py-0.5 rounded border border-[#d6e4ff]">18888</code>。
            </p>
          </div>

          <div className="space-y-3">
            <h4 className="font-bold text-[#0f172a] text-xs">核心支持的接口列表：</h4>

            <div className="rounded border border-[#e2e8f0] p-2.5 bg-[#f8fafc]">
              <div className="flex items-center justify-between font-mono text-xs font-bold text-[#0f172a]">
                <span className="text-[#10b981]">POST</span>
                <span>/api/v1/browser/start</span>
              </div>
              <p className="mt-1 text-[11px] text-[#64748b]">
                打开指定环境。参数：<code className="font-mono text-[#0f172a]">containerCode</code> (环境ID),{' '}
                <code className="font-mono text-[#0f172a]">isHeadless</code> (是否无头模式),{' '}
                <code className="font-mono text-[#0f172a]">args</code> (扩展启动参数)。返回值包含{' '}
                <code className="font-mono text-[#1664ff]">debuggingPort</code> (CDP 调试端口)。
              </p>
            </div>

            <div className="rounded border border-[#e2e8f0] p-2.5 bg-[#f8fafc]">
              <div className="flex items-center justify-between font-mono text-xs font-bold text-[#0f172a]">
                <span className="text-[#ef4444]">POST</span>
                <span>/api/v1/browser/stop</span>
              </div>
              <p className="mt-1 text-[11px] text-[#64748b]">
                关闭指定环境。参数：<code className="font-mono text-[#0f172a]">containerCode</code>。同时支持 GET /api/v1/browser/stop?containerCode=xxx。
              </p>
            </div>

            <div className="rounded border border-[#e2e8f0] p-2.5 bg-[#f8fafc]">
              <div className="flex items-center justify-between font-mono text-xs font-bold text-[#0f172a]">
                <span className="text-[#3b82f6]">POST</span>
                <span>/api/v1/browser/all-browser-status</span>
              </div>
              <p className="mt-1 text-[11px] text-[#64748b]">
                批量查询环境运行状态。参数：<code className="font-mono text-[#0f172a]">&#123;&quot;containerCodes&quot;: [&quot;id1&quot;, &quot;id2&quot;]&#125;</code>。返回值：0 代表已开启，3 代表已关闭。
              </p>
            </div>

            <div className="rounded border border-[#e2e8f0] p-2.5 bg-[#f8fafc]">
              <div className="flex items-center justify-between font-mono text-xs font-bold text-[#0f172a]">
                <span className="text-[#8b5cf6]">POST</span>
                <span>/api/v1/env/list</span>
              </div>
              <p className="mt-1 text-[11px] text-[#64748b]">
                环境列表查询。参数：<code className="font-mono text-[#0f172a]">&#123;&quot;current&quot;: 1, &quot;size&quot;: 20&#125;</code>。返回所有环境的 containerCode、名称、代理、指纹、标签等完整结构。
              </p>
            </div>

            <div className="rounded border border-[#e2e8f0] p-2.5 bg-[#f8fafc]">
              <div className="flex items-center justify-between font-mono text-xs font-bold text-[#0f172a]">
                <span className="text-[#8b5cf6]">POST</span>
                <span>/api/v1/env/create</span>
              </div>
              <p className="mt-1 text-[11px] text-[#64748b]">
                创建环境。参数支持 containerName、proxyServer、proxyTypeName、remark 等，自动返回生成的 containerCode。
              </p>
            </div>

            <div className="rounded border border-[#e2e8f0] p-2.5 bg-[#f8fafc]">
              <div className="flex items-center justify-between font-mono text-xs font-bold text-[#0f172a]">
                <span className="text-[#f59e0b]">POST</span>
                <span>/api/v1/browser/arrange</span>
              </div>
              <p className="mt-1 text-[11px] text-[#64748b]">
                一键自动将当前打开的所有浏览器窗口进行多屏/单屏网格平铺排版。
              </p>
            </div>
          </div>
        </div>
      </Modal>

      {/* 会员升级模态框 */}
      <BillingModal open={billingOpen} onClose={() => setBillingOpen(false)} />
    </div>
  )
}
