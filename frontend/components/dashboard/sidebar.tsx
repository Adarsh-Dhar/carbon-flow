"use client"

import { Wind, LayoutDashboard, FileText, Settings, Activity } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/", active: true },
  { icon: FileText, label: "Reports", href: "/reports", active: false },
  { icon: Settings, label: "Settings", href: "/settings", active: false },
]

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-[72px] flex flex-col items-center py-6 bg-sidebar border-r border-sidebar-border">
      {/* Logo */}
      <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20">
        <Wind className="h-6 w-6 text-primary" />
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col items-center gap-2">
        {navItems.map((item) => (
          <button
            key={item.label}
            className={cn(
              "flex h-11 w-11 items-center justify-center rounded-xl transition-all duration-200",
              item.active
                ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground",
            )}
            title={item.label}
          >
            <item.icon className="h-5 w-5" />
          </button>
        ))}
      </nav>

      {/* Status indicator */}
      <div className="mt-auto">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-success/20">
          <Activity className="h-5 w-5 text-success" />
        </div>
      </div>
    </aside>
  )
}
