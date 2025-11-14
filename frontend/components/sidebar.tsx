'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart3, Cloud, Map, Settings, Wind } from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: BarChart3 },
  { name: 'Forecast', href: '/forecast', icon: Cloud },
  { name: 'Sensors', href: '/sensors', icon: Map },
  { name: 'Sources', href: '/sources', icon: Wind },
  { name: 'System Status', href: '/status', icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900 p-6 hidden md:block">
      <div className="mb-12">
        <h2 className="text-xl font-bold text-slate-50 flex items-center gap-2">
          <Cloud className="w-6 h-6 text-blue-400" />
          CarbonFlow
        </h2>
      </div>
      <nav className="space-y-2">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                isActive
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
