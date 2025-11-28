"use client"

import { Terminal } from "lucide-react"

import type { AgentThoughtLog } from "@/lib/mockData"

export function AgentThought({ log }: { log: AgentThoughtLog }) {
  return (
    <div className="rounded-xl border border-amber-200/70 bg-amber-50/80 p-3 text-xs text-amber-900 dark:border-amber-400/40 dark:bg-amber-900/15 dark:text-amber-100">
      <div className="flex items-center gap-2 font-semibold">
        <Terminal className="h-3.5 w-3.5" />
        {log.agent} is thinking…
      </div>
      <div className="mt-1 font-mono text-[11px] opacity-90">{log.content}</div>
    </div>
  )
}

