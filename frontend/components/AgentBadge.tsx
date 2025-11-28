"use client"

import { Brain, Diamond, ShieldCheck, Sparkles } from "lucide-react"

import type { AgentName } from "@/lib/mockData"
import { cn } from "@/lib/utils"

const ICONS: Record<AgentName, React.ComponentType<{ className?: string }>> = {
  Sentry: ShieldCheck,
  Negotiator: Sparkles,
  Clinical: Brain,
  Rewards: Diamond,
}

const COLORS: Record<AgentName, string> = {
  Sentry: "from-sky-500/70 to-cyan-400/50 shadow-sky-900/40",
  Negotiator: "from-violet-500/70 to-pink-400/50 shadow-violet-900/40",
  Clinical: "from-emerald-500/70 to-lime-400/50 shadow-emerald-900/40",
  Rewards: "from-amber-500/70 to-orange-400/50 shadow-amber-900/40",
}

export function AgentBadge({ agent, subtle = false }: { agent: AgentName; subtle?: boolean }) {
  const Icon = ICONS[agent]

  if (subtle) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-slate-900/40 px-2 py-1 text-xs font-medium text-slate-200">
        <Icon className="h-3.5 w-3.5" />
        {agent}
      </span>
    )
  }

  return (
    <div
      className={cn(
        "flex w-fit items-center gap-3 rounded-full px-4 py-2 text-sm font-semibold text-white shadow-xl transition-all",
        "bg-gradient-to-r",
        COLORS[agent],
      )}
    >
      <Icon className="h-4 w-4" />
      {agent} Agent
    </div>
  )
}

