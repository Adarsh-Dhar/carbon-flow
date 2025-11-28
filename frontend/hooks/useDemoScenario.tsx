"use client"

import { createContext, useContext, useMemo, useState } from "react"

type Scenario = "calm" | "alert" | "critical"

interface DemoScenarioContextValue {
  scenario: Scenario
  setScenario: (scenario: Scenario) => void
  cycleScenario: () => void
}

const DemoScenarioContext = createContext<DemoScenarioContextValue | null>(null)

export function DemoScenarioProvider({ children }: { children: React.ReactNode }) {
  const [scenario, setScenario] = useState<Scenario>("calm")

  const value = useMemo(
    () => ({
      scenario,
      setScenario,
      cycleScenario: () => {
        setScenario((current) => {
          if (current === "calm") return "alert"
          if (current === "alert") return "critical"
          return "calm"
        })
      },
    }),
    [scenario],
  )

  return <DemoScenarioContext.Provider value={value}>{children}</DemoScenarioContext.Provider>
}

export function useDemoScenario() {
  const ctx = useContext(DemoScenarioContext)
  if (!ctx) {
    throw new Error("useDemoScenario must be used within DemoScenarioProvider")
  }
  return ctx
}

