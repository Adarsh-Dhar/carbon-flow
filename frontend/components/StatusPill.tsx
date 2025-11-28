"use client"

import { cn } from "@/lib/utils"

interface StatusPillProps {
  label: string
  tone?: "green" | "yellow" | "red"
  icon?: React.ReactNode
}

const toneTokens: Record<NonNullable<StatusPillProps["tone"]>, string> = {
  green: "bg-emerald-500/20 text-emerald-200 border-emerald-400/30",
  yellow: "bg-amber-500/20 text-amber-100 border-amber-400/30",
  red: "bg-rose-500/20 text-rose-100 border-rose-400/30",
}

export function StatusPill({ label, tone = "green", icon }: StatusPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-widest",
        toneTokens[tone],
      )}
    >
      {icon}
      {label}
    </span>
  )
}

