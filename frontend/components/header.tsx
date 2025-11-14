'use client'

import { usePathname } from 'next/navigation'
import { Cloud, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function Header() {
  const pathname = usePathname()
  
  const getTitle = () => {
    const path = pathname.split('/').pop() || 'overview'
    return path.charAt(0).toUpperCase() + path.slice(1).replace('-', ' ')
  }

  return (
    <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
      <div className="flex items-center justify-between px-8 py-4">
        <div className="flex items-center gap-3">
          <Cloud className="w-6 h-6 text-blue-400" />
          <h1 className="text-2xl font-bold text-slate-50">{getTitle()}</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-slate-400">
            Last updated: <span className="text-slate-300">now</span>
          </div>
          <Button variant="outline" size="icon" className="border-slate-700">
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </header>
  )
}
