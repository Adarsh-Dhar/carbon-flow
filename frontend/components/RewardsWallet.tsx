"use client"

import type { RewardsStatus } from "@/lib/types"

export function RewardsWallet({ rewards }: { rewards: RewardsStatus }) {
  return (
    <div className="rounded-3xl border border-white/5 bg-gradient-to-br from-emerald-500/20 to-cyan-500/10 p-6 text-white shadow-2xl">
      <div className="text-xs uppercase tracking-[0.4em] text-emerald-200">BreathPoints Wallet</div>
      <div className="mt-2 text-4xl font-black">{rewards.points.toLocaleString()}</div>
      <p className="mt-1 text-sm text-emerald-100">Adherence {Math.round(rewards.adherence_score * 100)}%</p>
      <div className="mt-4 space-y-3">
        {rewards.rewards.map((reward) => (
          <div key={reward.type} className="rounded-2xl bg-white/10 px-3 py-2 text-sm">
            <div className="text-xs uppercase tracking-widest text-emerald-200">{reward.type}</div>
            <div className="font-semibold">{reward.value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

