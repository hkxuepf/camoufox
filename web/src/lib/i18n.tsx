'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'

export type Language = 'zh' | 'en'

const translations: Record<Language, Record<string, string>> = {
  zh: {
    // 导航
    'nav.profiles': '环境列表',
    'nav.groups': '分组管理',
    'nav.schedules': '任务调度',
    'nav.trash': '回收站',
    'nav.settings': '系统设置',
    'nav.logout': '退出登录',

    // 常用按钮/操作
    'action.new_profile': '新建环境',
    'action.edit': '编辑',
    'action.delete': '删除',
    'action.restore': '恢复',
    'action.duplicate': '克隆环境',
    'action.launch': '启动环境',
    'action.stop': '停止',
    'action.stopping': '正在停止...',
    'action.starting': '正在启动...',
    'action.check_proxy': '测试代理',
    'action.checking': '检测中...',
    'action.import': '导入环境',
    'action.export': '导出环境',
    'action.cancel': '取消',
    'action.save': '保存',
    'action.saving': '保存中...',
    'action.confirm': '确认',
    'action.close': '关闭',
    'action.search_placeholder': '搜索环境名称或 ID...',
    'action.all_statuses': '全部状态',
    'action.status_running': '运行中',
    'action.status_stopped': '已停止',
    'action.status_error': '异常',
    'action.select_all': '全选',
    'action.batch_actions': '批量操作',
    'action.batch_start': '批量启动',
    'action.batch_stop': '批量停止',
    'action.batch_delete': '批量删除',
    'action.batch_check_proxy': '批量测速',

    // 表格列
    'col.name': '环境名称',
    'col.id': '环境 ID',
    'col.group': '分组',
    'col.os': '操作系统',
    'col.status': '状态',
    'col.proxy': '代理信息',
    'col.last_used': '上次使用',
    'col.actions': '操作',

    // 空状态
    'empty.profiles_title': '暂无浏览器环境',
    'empty.profiles_desc': '每个环境都是一个独立的指纹身份（包含独立的指纹特征、代理、Cookie 与本地缓存）。',
    'empty.create_first': '创建您的第一个环境',

    // 内核安装横幅
    'setup.title': '配置浏览器内核',
    'setup.desc': '首次启动环境前需下载一次浏览器内核。仅创建配置无需下载。',
    'setup.install': '安装浏览器内核',
    'setup.installing': '正在下载安装...',
    'setup.create_first': '先创建环境',
    'setup.installed': '内核已就绪',

    // 登录界面
    'login.title': '账号登录',
    'login.subtitle': '连接云端服务平台，管理您的指纹环境与套餐',
    'login.cloud_server': '云端认证中心',
    'login.cloud_badge': '云端同步模式',
    'login.username': '用户名',
    'login.password': '登录密码',
    'login.signin': '立即登录',
    'login.signing_in': '正在连接云端验证…',
    'login.register_link': '注册账号',
    'login.register_btn': '立即注册',
    'login.registering': '正在注册…',
    'login.has_account': '已有账号？立即登录',
    'login.confirm_password': '确认密码',
    'login.password_mismatch': '两次输入的密码不一致',
    'login.password_min_len': '密码长度至少需 6 位',
    'login.footer': 'CamouHub • 商业多开防关联指纹管理系统',

    // 表单
    'form.title_new': '新建浏览器环境',
    'form.title_edit': '编辑环境',
    'form.tab_general': '基本信息',
    'form.tab_fingerprint': '指纹参数',
    'form.tab_proxy': '代理设置',
    'form.tab_storage': '缓存与数据',
    'form.name_label': '环境名称',
    'form.name_placeholder': '例如：Google-01 / TikTok-US',
    'form.group_label': '选择分组',
    'form.no_group': '未分组',
    'form.notes_label': '备注说明',
    'form.notes_placeholder': '可记录账号、密码或用途备注',
    'form.tags_label': '标签',
    'form.tags_placeholder': '以逗号分隔标签',

    // 代理
    'proxy.title': '代理网络配置',
    'proxy.none': '直连（不使用代理）',
    'proxy.type': '协议类型',
    'proxy.host': '代理主机 (IP / 域名)',
    'proxy.port': '端口',
    'proxy.user': '用户名',
    'proxy.pass': '密码',
    'proxy.test_btn': '测试连接',
    'proxy.test_success': '代理连接成功',
    'proxy.test_failed': '代理连接失败',

    // 指纹
    'fp.title': '防关联指纹伪装',
    'fp.os': '操作系统',
    'fp.screen': '屏幕分辨率',
    'fp.cores': 'CPU 核心数',
    'fp.memory': '内存容量 (GB)',
    'fp.canvas': 'Canvas 指纹保护',
    'fp.audio': '音频上下文保护',
    'fp.webgl': 'WebGL 图像渲染伪装',
    'fp.webrtc': 'WebRTC 策略',
    'fp.webrtc_disabled': '完全禁用 (最高隐私)',
    'fp.webrtc_proxy': '通过代理转发 (推荐)',
    'fp.webrtc_real': '真实 IP',
    'fp.fonts': '字体库伪装',
    'fp.lang': '系统语言与地区',
    'fp.timezone': '时区伪装 (可跟随代理 IP)',
    'fp.randomize': '重新随机生成指纹',

    // 分组页
    'groups.title': '环境分组管理',
    'groups.new': '新建分组',
    'groups.name': '分组名称',
    'groups.desc': '描述',
    'groups.count': '环境数量',
    'groups.empty': '暂无分组，点击上方新建',

    // 调度页
    'schedules.title': '定时任务与自动化',
    'schedules.new': '新建任务',
    'schedules.warming': '环境自动预热 (Warming)',
    'schedules.empty': '暂无自动化任务',

    // 设置页
    'settings.title': '系统设置',
    'settings.security': '安全与访问控制',
    'settings.lang': '界面语言 / Language',
    'settings.lang_desc': '切换控制台显示语言（简体中文 / English）',
    'settings.encryption': '代理密码加密存储',
    'settings.user_auth': '多用户访问鉴权',
    'settings.api_key': 'API 访问密钥',
    'settings.backup': '数据备份与迁移',
    'settings.export_all': '备份全部配置',
    'settings.import_all': '恢复备份数据',

    // 回收站
    'trash.title': '环境回收站',
    'trash.empty': '回收站为空',
    'trash.clear': '清空回收站',
    'trash.restore_all': '全部恢复',

    // 语言提示
    'lang.zh': '简体中文',
    'lang.en': 'English',
  },
  en: {
    // Navigation
    'nav.profiles': 'Profiles',
    'nav.groups': 'Groups',
    'nav.schedules': 'Schedules',
    'nav.trash': 'Trash',
    'nav.settings': 'Settings',
    'nav.logout': 'Log out',

    // Common Actions
    'action.new_profile': 'New profile',
    'action.edit': 'Edit',
    'action.delete': 'Delete',
    'action.restore': 'Restore',
    'action.duplicate': 'Duplicate',
    'action.launch': 'Launch',
    'action.stop': 'Stop',
    'action.stopping': 'Stopping...',
    'action.starting': 'Starting...',
    'action.check_proxy': 'Check proxy',
    'action.checking': 'Checking...',
    'action.import': 'Import',
    'action.export': 'Export',
    'action.cancel': 'Cancel',
    'action.save': 'Save',
    'action.saving': 'Saving...',
    'action.confirm': 'Confirm',
    'action.close': 'Close',
    'action.search_placeholder': 'Search name or ID...',
    'action.all_statuses': 'All statuses',
    'action.status_running': 'Running',
    'action.status_stopped': 'Stopped',
    'action.status_error': 'Error',
    'action.select_all': 'Select all',
    'action.batch_actions': 'Batch actions',
    'action.batch_start': 'Batch start',
    'action.batch_stop': 'Batch stop',
    'action.batch_delete': 'Batch delete',
    'action.batch_check_proxy': 'Check proxies',

    // Columns
    'col.name': 'Name',
    'col.id': 'ID',
    'col.group': 'Group',
    'col.os': 'OS',
    'col.status': 'Status',
    'col.proxy': 'Proxy',
    'col.last_used': 'Last used',
    'col.actions': 'Actions',

    // Empty state
    'empty.profiles_title': 'No profiles yet',
    'empty.profiles_desc': 'A profile is one isolated browser identity — its own fingerprint, proxy, cookies and storage. Create one to get started.',
    'empty.create_first': 'Create your first profile',

    // Setup banner
    'setup.title': 'Set up your browser',
    'setup.desc': 'Download the browser once to launch profiles. Creating a profile does not require a download. Download the browser to open your first profile.',
    'setup.install': 'Install browser',
    'setup.installing': 'Installing browser...',
    'setup.create_first': 'Create a profile first',
    'setup.installed': 'Browser ready',

    // Login
    'login.title': 'Sign In',
    'login.subtitle': 'Connect to Camoufox Cloud to manage profiles and subscription',
    'login.cloud_server': 'Cloud Auth Server',
    'login.cloud_badge': 'Cloud Sync Mode',
    'login.username': 'Username',
    'login.password': 'Password',
    'login.signin': 'Sign In',
    'login.signing_in': 'Connecting to Cloud…',
    'login.register_link': 'Register Account',
    'login.register_btn': 'Sign Up',
    'login.registering': 'Creating account…',
    'login.has_account': 'Already have an account? Sign in',
    'login.confirm_password': 'Confirm Password',
    'login.password_mismatch': 'Passwords do not match',
    'login.password_min_len': 'Password must be at least 6 characters',
    'login.footer': 'CamouHub • Antidetect Fingerprint Browser',

    // Forms
    'form.title_new': 'New Profile',
    'form.title_edit': 'Edit Profile',
    'form.tab_general': 'General',
    'form.tab_fingerprint': 'Fingerprint',
    'form.tab_proxy': 'Proxy',
    'form.tab_storage': 'Storage',
    'form.name_label': 'Profile Name',
    'form.name_placeholder': 'e.g., Google-01 / TikTok-US',
    'form.group_label': 'Group',
    'form.no_group': 'No group',
    'form.notes_label': 'Notes',
    'form.notes_placeholder': 'Store credentials or use case details',
    'form.tags_label': 'Tags',
    'form.tags_placeholder': 'Comma-separated tags',

    // Proxy
    'proxy.title': 'Proxy Configuration',
    'proxy.none': 'Direct connection (No proxy)',
    'proxy.type': 'Protocol',
    'proxy.host': 'Host (IP / Domain)',
    'proxy.port': 'Port',
    'proxy.user': 'Username',
    'proxy.pass': 'Password',
    'proxy.test_btn': 'Test connection',
    'proxy.test_success': 'Proxy connection succeeded',
    'proxy.test_failed': 'Proxy connection failed',

    // Fingerprint
    'fp.title': 'Fingerprint Protection',
    'fp.os': 'Operating System',
    'fp.screen': 'Screen Resolution',
    'fp.cores': 'CPU Cores',
    'fp.memory': 'Memory (GB)',
    'fp.canvas': 'Canvas Noise',
    'fp.audio': 'Audio Noise',
    'fp.webgl': 'WebGL Vendor & Renderer',
    'fp.webrtc': 'WebRTC Policy',
    'fp.webrtc_disabled': 'Disabled (Highest privacy)',
    'fp.webrtc_proxy': 'Route through proxy (Recommended)',
    'fp.webrtc_real': 'Real IP',
    'fp.fonts': 'Fonts Spoofing',
    'fp.lang': 'Language & Locale',
    'fp.timezone': 'Timezone (Match proxy IP)',
    'fp.randomize': 'Randomize Fingerprint',

    // Groups
    'groups.title': 'Group Management',
    'groups.new': 'New Group',
    'groups.name': 'Group Name',
    'groups.desc': 'Description',
    'groups.count': 'Profiles',
    'groups.empty': 'No groups created yet',

    // Schedules
    'schedules.title': 'Schedules & Automation',
    'schedules.new': 'New Schedule',
    'schedules.warming': 'Profile Warming',
    'schedules.empty': 'No schedules configured',

    // Settings
    'settings.title': 'Settings',
    'settings.security': 'Security & Access',
    'settings.lang': 'Language / 语言',
    'settings.lang_desc': 'Switch console display language (简体中文 / English)',
    'settings.encryption': 'Proxy Password Encryption',
    'settings.user_auth': 'User Authentication',
    'settings.api_key': 'API Key',
    'settings.backup': 'Backup & Migration',
    'settings.export_all': 'Backup All Data',
    'settings.import_all': 'Restore Backup',

    // Trash
    'trash.title': 'Trash',
    'trash.empty': 'Trash is empty',
    'trash.clear': 'Empty Trash',
    'trash.restore_all': 'Restore All',

    // Language
    'lang.zh': '简体中文',
    'lang.en': 'English',
  },
}

interface I18nContextType {
  lang: Language
  language: Language
  setLang: (lang: Language) => void
  t: (key: string, fallback?: string) => string
  isZh: boolean
}

const I18nContext = createContext<I18nContextType>({
  lang: 'zh',
  language: 'zh',
  setLang: () => { },
  t: (key: string, fallback?: string) => fallback ?? key,
  isZh: true,
})

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Language>('zh')

  useEffect(() => {
    try {
      const saved = localStorage.getItem('cpm_lang') as Language | null
      if (saved && (saved === 'zh' || saved === 'en')) {
        setLangState(saved)
      } else {
        // Detect browser default
        const browserLang = navigator.language.toLowerCase()
        if (browserLang.startsWith('zh')) {
          setLangState('zh')
        } else {
          setLangState('en')
        }
      }
    } catch {
      // fallback
    }
  }, [])

  const setLang = (next: Language) => {
    setLangState(next)
    try {
      localStorage.setItem('cpm_lang', next)
    } catch {
      // ignored
    }
  }

  const t = (key: string, fallback?: string): string => {
    return translations[lang]?.[key] ?? fallback ?? translations['en']?.[key] ?? key
  }

  return (
    <I18nContext.Provider value={{ lang, language: lang, setLang, t, isZh: lang === 'zh' }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  return useContext(I18nContext)
}

export function LanguageToggle({ className = '' }: { className?: string }) {
  const { lang, setLang } = useI18n()

  return (
    <button
      type="button"
      onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium transition-colors hover:bg-raised text-ink-dim hover:text-ink ${className}`}
      title={lang === 'zh' ? 'Switch to English' : '切换到中文'}
    >
      <span className="opacity-70">🌐</span>
      <span>{lang === 'zh' ? '中 / EN' : 'EN / 中'}</span>
    </button>
  )
}
