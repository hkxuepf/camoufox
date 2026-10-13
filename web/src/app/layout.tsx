import type { Metadata } from 'next'

import { AdminProvider } from '@/components/admin-context'
import { AppShell } from '@/components/app-shell'
import { LoginGate } from '@/components/login-gate'
import { ToastProvider } from '@/components/toast'
import { I18nProvider } from '@/lib/i18n'
import './fonts.css'
import './globals.css'

export const metadata: Metadata = {
  title: 'CamouHub',
  description: 'CamouHub Antidetect Browser Management',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <I18nProvider>
          <ToastProvider>
            <LoginGate>
              <AdminProvider>
                <AppShell>{children}</AppShell>
              </AdminProvider>
            </LoginGate>
          </ToastProvider>
        </I18nProvider>
      </body>
    </html>
  )
}
