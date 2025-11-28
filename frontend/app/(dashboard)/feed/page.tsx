"use client"

import { useMemo, useState } from "react"
import type { UIMessage } from "ai"
import { useChat } from "@ai-sdk/react"
import { AlertTriangle, Loader2, Shield } from "lucide-react"

import { ActionCard } from "@/components/ActionCard"
import { AgentBadge } from "@/components/AgentBadge"
import { AgentThought } from "@/components/AgentThought"
import { StatusPill } from "@/components/StatusPill"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import type { AgentThoughtLog, FeedMessage } from "@/lib/mockData"
import { useMockAgents } from "@/hooks/useMockAgents"

type EnrichedMessage = UIMessage & {
  meta?: {
    agent?: FeedMessage["agent"]
    summary?: string
    timestamp?: string
    thoughts?: AgentThoughtLog[]
    actionCard?: FeedMessage["actionCard"]
  }
}

const toolStateToStatus = (state?: string): "pending" | "approved" | "ignored" => {
  if (state === "result" || state === "output-available") return "approved"
  return "pending"
}

export default function NegotiatorFeedPage() {
  const { feed, calendarActions } = useMockAgents()
  const [note, setNote] = useState("")

  const history = useMemo<EnrichedMessage[]>(() => {
    return feed.map((event) => ({
      id: event.id,
      role: "assistant",
      parts: [{ type: "text", text: `${event.summary} — ${event.detail}` }],
      meta: {
        agent: event.agent,
        summary: event.summary,
        timestamp: event.timestamp,
        thoughts: event.thoughts,
        actionCard: event.actionCard,
      },
    }))
  }, [])

  const { messages, sendMessage, status, stop, error } = useChat({
    api: "/api/respiro/chat",
    id: "respiro-negotiator",
  })

  const liveAssistantMessages = messages.filter((message) => message.role === "assistant") as EnrichedMessage[]

  const combinedTimeline = [...history, ...liveAssistantMessages]

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = note.trim() || "Agent, continue monitoring schedules against AQI spikes."
    await sendMessage({ text: payload })
    setNote("")
  }

  return (
    <div className="min-h-screen bg-[#030712] text-white">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-10">
        <header className="space-y-4">
          <AgentBadge agent="Negotiator" />
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-semibold">Action Feed</h1>
              <p className="text-sm text-slate-300">
                Multi-agent orchestrator posts autonomous proposals. Review the reasoning before approving.
              </p>
            </div>
            <StatusPill label="Auto-monitoring" tone="green" icon={<Shield className="h-3.5 w-3.5" />} />
          </div>
        </header>

        <section className="space-y-6">
          {combinedTimeline.map((message) => (
            <article key={message.id} className="rounded-3xl border border-white/5 bg-slate-950/70 p-6 shadow-2xl">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <AgentBadge agent={message.meta?.agent ?? "Negotiator"} subtle />
                <span className="text-xs uppercase tracking-[0.4em] text-slate-500">{message.meta?.timestamp ?? "Live"}</span>
              </div>
              <h3 className="mt-3 text-xl font-semibold">{message.meta?.summary ?? "Agent update"}</h3>
              <div className="mt-2 text-sm text-slate-200">
                {message.parts?.map((part, index) => {
                  if (part.type === "text") {
                    return <p key={`${message.id}-${index}`}>{part.text}</p>
                  }
                  if (part.type === "tool-call") {
                    return (
                      <p key={`${message.id}-${index}`} className="text-amber-200">
                        Tool call invoked: {part.toolName}
                      </p>
                    )
                  }
                  return null
                })}
              </div>

              {message.meta?.thoughts?.length ? (
                <details className="mt-4 rounded-2xl border border-amber-200/40 bg-amber-50/10 p-4 text-slate-100">
                  <summary className="cursor-pointer text-sm font-semibold">
                    ✨ Agent Reasoning <span className="text-xs text-amber-200">(tap to inspect)</span>
                  </summary>
                  <div className="mt-3 space-y-2">
                    {message.meta.thoughts.map((thought) => (
                      <AgentThought key={thought.id} log={thought} />
                    ))}
                  </div>
                </details>
              ) : null}

              {message.meta?.actionCard && <ActionCard card={message.meta.actionCard} />}
            </article>
          ))}
        </section>

        <section className="rounded-3xl border border-white/5 bg-slate-950/80 p-6 shadow-2xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">Live Negotiation Stream</h2>
              <p className="text-sm text-slate-400">Streaming via Vercel AI SDK. Approve or override proposals.</p>
            </div>
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.4em] text-slate-400">
              {status === "streaming" ? <Loader2 className="h-4 w-4 animate-spin" /> : <AlertTriangle className="h-4 w-4 text-amber-300" />}
              {status}
            </div>
          </div>

          <div className="mt-5 space-y-4">
            {liveAssistantMessages.length === 0 && (
              <p className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-slate-400">
                Awaiting the next agent broadcast…
              </p>
            )}
            {liveAssistantMessages.map((message) => (
              <div key={message.id} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
                {message.parts?.map((part, index) => (part.type === "text" ? <p key={index}>{part.text}</p> : null))}
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Textarea
              placeholder="Optional note for the agents (they already have context)…"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              className="min-h-[96px] rounded-2xl border-white/10 bg-slate-900/60 text-white placeholder:text-slate-500"
            />
            <div className="flex flex-wrap gap-3">
              <Button type="submit" size="lg" className="rounded-full px-8" disabled={status === "streaming"}>
                {status === "streaming" ? "Streaming…" : "Approve & Stream"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                className="rounded-full border border-white/10 bg-transparent px-6 text-white"
                onClick={() => stop()}
              >
                Pause Stream
              </Button>
            </div>
          </form>
          {error && <p className="mt-3 text-sm text-rose-400">Streaming error: {error.message}</p>}
          <p className="mt-3 text-xs text-slate-500">
            Tip: set <code className="text-emerald-300">OPENAI_API_KEY</code> to let agents stream from a live model.
          </p>

          {calendarActions.length > 0 && (
            <div className="mt-6 rounded-2xl border border-white/5 bg-white/5 p-4 text-xs text-slate-200">
              <p className="mb-2 font-semibold uppercase tracking-[0.3em] text-slate-400">Latest tool outputs</p>
              <ul className="space-y-2">
                {calendarActions.map((action) => (
                  <li key={action.event_id} className="flex justify-between text-sm text-white">
                    <span>{action.action}</span>
                    <span className="text-slate-400">{action.new_time}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

