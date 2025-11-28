"use client"

import { useState, useEffect, Suspense } from "react"
import { useQuery } from "@tanstack/react-query"
import { Sidebar } from "@/components/dashboard/sidebar"
import { RiskIndicator } from "@/components/patient/risk-indicator"
import { RecommendationsCard } from "@/components/patient/recommendations-card"
import {
  getPatientStatus,
  getRecommendations,
  getRewards,
  getCalendar,
  createSession,
  executeSession,
} from "@/lib/api"
import type { PatientState, Recommendations, RewardsStatus } from "@/lib/types"

const PATIENT_ID = "patient-001" // In production, would come from auth

function DashboardContent() {
  const [sessionId, setSessionId] = useState<string | null>(null)

  // Create session on mount
  useEffect(() => {
    createSession(PATIENT_ID).then((result) => {
      setSessionId(result.session_id)
      executeSession(result.session_id)
    })
  }, [])

  const statusQuery = useQuery({
    queryKey: ["patient-status", PATIENT_ID],
    queryFn: () => getPatientStatus(PATIENT_ID),
    retry: 1,
    enabled: !!sessionId,
  })

  const recommendationsQuery = useQuery({
    queryKey: ["recommendations", PATIENT_ID],
    queryFn: () => getRecommendations(PATIENT_ID),
    retry: 1,
    enabled: !!sessionId,
  })

  const rewardsQuery = useQuery({
    queryKey: ["rewards", PATIENT_ID],
    queryFn: () => getRewards(PATIENT_ID),
    retry: 1,
    enabled: !!sessionId,
  })

  const calendarQuery = useQuery({
    queryKey: ["calendar", PATIENT_ID],
    queryFn: () => getCalendar(PATIENT_ID),
    retry: 1,
    enabled: !!sessionId,
  })

  const isLoading =
    statusQuery.isLoading || recommendationsQuery.isLoading || rewardsQuery.isLoading

  const patientState = statusQuery.data
  const recommendations = recommendationsQuery.data

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="flex-1 ml-[72px] p-6">
        <div className="max-w-[1400px] mx-auto space-y-6">
          <h1 className="text-3xl font-bold">Respiro Asthma Management</h1>

          {isLoading && <div className="text-center py-8">Loading...</div>}

          {patientState && (
            <RiskIndicator
              riskLevel={patientState.current_risk_level}
              riskScore={patientState.risk_score}
              riskFactors={patientState.risk_factors}
            />
          )}

          {recommendations && (
            <RecommendationsCard recommendations={recommendations.recommendations} />
          )}

          {rewardsQuery.data && (
            <div className="rounded-lg border p-6">
              <h3 className="text-xl font-bold mb-4">Rewards & Points</h3>
              <p>Adherence Score: {(rewardsQuery.data.adherence_score * 100).toFixed(0)}%</p>
              <p>Points: {rewardsQuery.data.points}</p>
              {rewardsQuery.data.rewards.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-semibold">Unlocked Rewards:</h4>
                  <ul className="list-disc list-inside">
                    {rewardsQuery.data.rewards.map((reward, idx) => (
                      <li key={idx}>
                        {reward.type}: {reward.value}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Loading...</div>}>
      <DashboardContent />
    </Suspense>
  )
}