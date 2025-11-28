"use client"

import type { BiometricMetric } from "@/lib/mockData"
import { cn } from "@/lib/utils"

export function BiometricTicker({ metrics }: { metrics: BiometricMetric[] }) {
  return (
    <div className="flex flex-wrap gap-3 rounded-2xl border border-white/5 bg-white/5 p-4 text-white shadow-inner backdrop-blur">
      {metrics.map((metric) => (
        <div key={metric.id} className="flex items-center gap-3 rounded-2xl bg-white/5 px-3 py-2">
          <span className="text-lg">{metric.icon}</span>
          <div>
            <div className="text-xs uppercase tracking-widest text-slate-300">{metric.label}</div>
            <div className="flex items-baseline gap-2 text-sm font-semibold text-white">
              <span className="text-lg">{metric.value}</span>
              <span className="text-xs text-slate-300">{metric.unit}</span>
              <span
                className={cn(
                  "text-[10px] font-medium",
                  metric.trend >= 0 ? "text-emerald-300" : "text-sky-300",
                  metric.trend === 0 && "text-slate-400",
                )}
              >
                {metric.trend >= 0 ? "+" : ""}
                {metric.trend}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

