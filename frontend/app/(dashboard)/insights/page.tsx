"use client"

import { useMemo } from "react"
import { LineChart, Card, Flex, Metric, Text, Divider } from "@tremor/react"
import { Award, Sparkles } from "lucide-react"

import { AgentBadge } from "@/components/AgentBadge"
import { RewardsWallet } from "@/components/RewardsWallet"
import { StatusPill } from "@/components/StatusPill"
import { useMockAgents } from "@/hooks/useMockAgents"

export default function ClinicalInsightsPage() {
  const { correlationSeries, rewards, rewardEvents, breathability } = useMockAgents()

  const highlights = useMemo(
    () => [
      {
        label: "Trigger confidence",
        value: "0.82",
        detail: "PM2.5 ↔ symptoms last 48h",
      },
      {
        label: "Rescue inhaler usage",
        value: "1",
        detail: "in the past week",
      },
    ],
    [],
  )

  return (
    <div className="min-h-screen bg-[#01030b] text-white">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-10">
        <header className="space-y-3">
          <AgentBadge agent="Clinical" />
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-semibold">Clinical & Rewards Intelligence</h1>
              <p className="text-sm text-slate-400">
                Clinical agent correlates biometrics with environmental triggers while the Rewards agent keeps compliance fun.
              </p>
            </div>
            <StatusPill label={`Zone ${breathability.recommendations.zone.toUpperCase()}`} tone={breathability.sentiment} />
          </div>
        </header>

        <section className="rounded-3xl border border-white/5 bg-slate-950/70 p-6 shadow-2xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">Trigger Correlation</h2>
              <p className="text-sm text-slate-400">Overlay shows symptom trend alongside PM2.5 concentrations.</p>
            </div>
            <div className="rounded-2xl border border-white/10 px-4 py-2 text-sm text-slate-200">
              Last sync: {new Date().toLocaleTimeString()}
            </div>
          </div>
          <div className="mt-6 rounded-3xl border border-white/5 bg-slate-900/60 p-4">
            <LineChart
              data={correlationSeries}
              index="timestamp"
              categories={["symptom", "pm25"]}
              colors={["rose", "cyan"]}
              valueFormatter={(value) => `${value}`}
              curveType="monotone"
              allowDecimals={false}
              showYAxis={false}
            />
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {highlights.map((highlight) => (
              <Card key={highlight.label} className="bg-slate-900/60 text-left text-white">
                <Text className="text-xs uppercase tracking-[0.4em] text-slate-500">{highlight.label}</Text>
                <Metric className="mt-2">{highlight.value}</Metric>
                <Text className="mt-1 text-sm text-slate-300">{highlight.detail}</Text>
              </Card>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="rounded-3xl border border-white/5 bg-slate-950/80 p-6 shadow-2xl">
            <div className="flex items-center gap-2 text-sm text-slate-300">
              <Award className="h-4 w-4 text-amber-300" />
              Rewards & Adherence
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <Card className="bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 text-left text-white">
                <Text className="text-xs uppercase tracking-[0.4em] text-emerald-100">Adherence Score</Text>
                <Metric className="mt-2 text-4xl">{Math.round(rewards.adherence_score * 100)}%</Metric>
                <Text className="mt-1 text-sm text-emerald-100">Clinical agent verified logs & smart home compliance</Text>
              </Card>
              <Card className="bg-slate-900/80 text-left text-white">
                <Text className="text-xs uppercase tracking-[0.4em] text-slate-400">Rewards unlocked</Text>
                <Metric className="mt-2">{rewards.rewards.length}</Metric>
                <Text className="mt-1 text-sm text-slate-300">{rewards.rewards.map((reward) => reward.type).join(", ")}</Text>
              </Card>
            </div>

            <Divider className="my-6 border-slate-800" />
            <div className="space-y-4">
              {rewardEvents.map((event) => (
                <Flex key={event.id} justifyContent="between" className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{event.label}</p>
                    <p className="text-xs text-slate-400">{event.timestamp}</p>
                  </div>
                  <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-200">
                    {event.delta}
                  </span>
                </Flex>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <RewardsWallet rewards={rewards} />
            <Card className="rounded-3xl border-white/5 bg-slate-950/70 text-left text-white">
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Sparkles className="h-4 w-4 text-cyan-300" />
                Upcoming upgrades
              </div>
              <ul className="mt-4 space-y-3 text-sm text-slate-200">
                <li>• +150 pts when windows remain sealed through Red zone.</li>
                <li>• Insurance agent auto-submits premium adjustment at 95% adherence.</li>
                <li>• Pharmacy coupon unlock after next medication log.</li>
              </ul>
            </Card>
          </div>
        </section>
      </div>
    </div>
  )
}

