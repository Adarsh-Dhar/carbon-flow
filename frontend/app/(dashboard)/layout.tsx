"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Activity, Gauge, LineChart as LineChartIcon, MessagesSquare, Zap } from "lucide-react"

import { DemoScenarioProvider, useDemoScenario } from "@/hooks/useDemoScenario"
import { cn } from "@/lib/utils"

const navItems = [
  { href: "/", label: "Now", icon: Gauge },
  { href: "/feed", label: "Negotiator Feed", icon: MessagesSquare },
  { href: "/insights", label: "Clinical Insights", icon: LineChartIcon },
]

const scenarioButtons = [
  { value: "calm", label: "Calm" },
  { value: "alert", label: "Alert" },
  { value: "critical", label: "Critical" },
] as const

function ScenarioControls() {
  const { scenario, setScenario, cycleScenario } = useDemoScenario()

  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-lg">
      <div className="flex items-center gap-2 text-xs uppercase tracking-[0.4em] text-slate-400">
        <Activity className="h-3.5 w-3.5 text-emerald-300" />
        Demo Mode
      </div>
      <div className="mt-4 flex gap-2">
        {scenarioButtons.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setScenario(option.value)}
            className={cn(
              "flex-1 rounded-2xl border px-3 py-2 text-sm font-semibold transition-colors",
              scenario === option.value
                ? "border-emerald-400/60 bg-emerald-500/20 text-white"
                : "border-white/10 text-slate-300 hover:border-white/30",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={cycleScenario}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl border border-white/10 px-3 py-2 text-sm text-slate-200 hover:border-white/40"
      >
        Pulse Spike <Zap className="h-3.5 w-3.5 text-amber-300" />
      </button>
    </div>
  )
}

function DesktopSidebar() {
  const pathname = usePathname()

  return (
    <aside className="hidden w-64 flex-col border-r border-white/5 bg-[#020615] px-6 py-10 lg:flex">
      <div className="space-y-8">
        <div>
          <p className="text-xs uppercase tracking-[0.5em] text-slate-500">Respiro</p>
          <h2 className="text-2xl font-semibold text-white">Guardian</h2>
        </div>
        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-colors",
                  active ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>
        <ScenarioControls />
      </div>
    </aside>
  )
}

function MobileNav() {
  const pathname = usePathname()

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-white/10 bg-black/50 backdrop-blur lg:hidden">
      <div className="flex justify-around px-2 py-3">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
          return (
            <Link key={item.href} href={item.href} className="flex flex-col items-center text-xs text-white">
              <Icon className={cn("h-5 w-5", active ? "text-white" : "text-slate-400")} />
              <span className={cn("mt-1", active ? "text-white" : "text-slate-400")}>{item.label.split(" ")[0]}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <DemoScenarioProvider>
      <div className="min-h-screen bg-[#01030b] text-white lg:flex">
        <DesktopSidebar />
        <div className="flex-1 pb-24 lg:pb-0">{children}</div>
        <MobileNav />
      </div>
    </DemoScenarioProvider>
  )
}

