"use client"

import { useEffect, useMemo, useState } from "react"

import {
  type FeedMessage,
  mockBreathability,
  mockCalendarActions,
  mockCorrelationSeries,
  mockFeed,
  mockInterventions,
  mockRewardEvents,
  mockRewards,
  mockSensorData,
} from "@/lib/mockData"
import { useDemoScenario } from "@/hooks/useDemoScenario"

const SCENARIO_COPY = {
  calm: {
    sentiment: "green",
    headline: "You are in the Green Zone",
    subcopy: "Air is manageable. Agents pre-empted a pollen spike and tightened your smart home perimeter.",
  },
  alert: {
    sentiment: "yellow",
    headline: "Pollen gust inbound – shifting to Yellow Zone",
    subcopy: "Negotiator is pausing outdoor events while Clinical prepares inhaler reminders.",
  },
  critical: {
    sentiment: "red",
    headline: "Red Zone protocol armed",
    subcopy: "Sentry detected compounding triggers. Air purifiers locked to Turbo, and caregivers are being alerted.",
  },
} as const

export function useMockAgents() {
  const { scenario } = useDemoScenario()
  const [feed, setFeed] = useState<FeedMessage[]>(mockFeed)

  useEffect(() => {
    const timer = setInterval(() => {
      setFeed((prev) => {
        const fresh = [...prev]
        const pending = fresh.find((message) => message.actionCard?.status === "pending")
        if (pending?.actionCard) {
          pending.actionCard.status = "approved"
          pending.detail = "Parents approved. Calendar + team notified."
          pending.timestamp = "just now"
        }
        return fresh
      })
    }, 25000)

    return () => clearInterval(timer)
  }, [])

  const scenarioCopy = useMemo(() => SCENARIO_COPY[scenario], [scenario])

  return {
    feed,
    sentiment: scenarioCopy.sentiment,
    headline: scenarioCopy.headline,
    subcopy: scenarioCopy.subcopy,
    breathability: { ...mockBreathability, sentiment: scenarioCopy.sentiment },
    interventions: mockInterventions,
    sensorData: mockSensorData,
    correlationSeries: mockCorrelationSeries,
    rewards: mockRewards,
    rewardEvents: mockRewardEvents,
    calendarActions: mockCalendarActions,
  }
}

