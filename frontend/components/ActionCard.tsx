"use client"

import { useState } from "react"

import type { AgentActionCard } from "@/lib/mockData"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export function ActionCard({ card }: { card: AgentActionCard }) {
  const [status, setStatus] = useState(card.status)

  function handleAction(label: string) {
    if (label === "Approve") {
      setStatus("approved")
      return
    }
    if (label === "Ignore") {
      setStatus("ignored")
    }
  }

  return (
    <div
      className={cn(
        "rounded-2xl border p-4 shadow-lg transition-all",
        status === "pending" && "border-amber-300/60 bg-amber-50/60 dark:bg-amber-900/10",
        status === "approved" && "border-emerald-400/60 bg-emerald-50/60 dark:bg-emerald-900/10",
        status === "ignored" && "border-slate-700/60 bg-slate-900/40",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">{card.title}</p>
          <p className="text-xs text-slate-300">{card.context}</p>
        </div>
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs capitalize text-white">{status}</span>
      </div>
      <p className="mt-3 text-sm text-slate-100">{card.proposal}</p>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-xs text-slate-300">
        {Object.entries(card.metadata).map(([label, value]) => (
          <div key={label}>
            <dt className="uppercase tracking-wide text-[10px] text-slate-500">{label}</dt>
            <dd className="font-semibold text-slate-100">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-5 flex flex-wrap gap-2">
        {card.actions.map((action) => (
          <Button
            key={action.label}
            variant={action.variant === "ghost" ? "ghost" : action.variant === "destructive" ? "destructive" : "default"}
            size="sm"
            className="rounded-full"
            onClick={() => handleAction(action.label)}
          >
            {action.label}
          </Button>
        ))}
      </div>
    </div>
  )
}

