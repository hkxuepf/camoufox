'use client'

import { createContext, useContext, useState, ReactNode } from 'react'

export type AdminTab = 'dashboard' | 'users' | 'plans' | 'orders' | 'releases' | 'settings'

interface AdminContextType {
  activeTab: AdminTab
  setActiveTab: (tab: AdminTab) => void
}

const AdminContext = createContext<AdminContextType>({
  activeTab: 'dashboard',
  setActiveTab: () => {},
})

export function AdminProvider({ children }: { children: ReactNode }) {
  const [activeTab, setActiveTab] = useState<AdminTab>('dashboard')
  return (
    <AdminContext.Provider value={{ activeTab, setActiveTab }}>
      {children}
    </AdminContext.Provider>
  )
}

export function useAdminContext() {
  return useContext(AdminContext)
}
