"use client"

import { type ClinicalRecommendation } from "@/lib/types"
import { Pill, Activity, AlertCircle } from "lucide-react"

interface RecommendationsCardProps {
  recommendations: ClinicalRecommendation
}

export function RecommendationsCard({ recommendations }: RecommendationsCardProps) {
  const zoneColors = {
    green: "bg-green-100 border-green-500",
    yellow: "bg-yellow-100 border-yellow-500",
    red: "bg-red-100 border-red-500",
  }

  return (
    <div className={`rounded-lg border-2 p-6 ${zoneColors[recommendations.zone]}`}>
      <div className="flex items-center gap-2 mb-4">
        <Activity className="h-5 w-5" />
        <h3 className="text-xl font-bold">{recommendations.zone.toUpperCase()} ZONE</h3>
      </div>
      <p className="text-sm text-gray-700 mb-4">{recommendations.zone_description}</p>

      {recommendations.actions.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold mb-2">Actions:</h4>
          <ul className="list-disc list-inside space-y-1 text-sm">
            {recommendations.actions.map((action, idx) => (
              <li key={idx}>{action}</li>
            ))}
          </ul>
        </div>
      )}

      {recommendations.medications.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold mb-2 flex items-center gap-2">
            <Pill className="h-4 w-4" />
            Medications:
          </h4>
          <ul className="space-y-2">
            {recommendations.medications.map((med, idx) => (
              <li key={idx} className="text-sm">
                <span className="font-medium">{med.type}:</span> {med.action}
                {med.frequency && <span className="text-gray-600"> - {med.frequency}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {recommendations.monitoring.length > 0 && (
        <div>
          <h4 className="font-semibold mb-2">Monitoring:</h4>
          <ul className="list-disc list-inside space-y-1 text-sm">
            {recommendations.monitoring.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {recommendations.emergency && (
        <div className="mt-4 p-4 bg-red-200 rounded border border-red-500">
          <div className="flex items-center gap-2 text-red-800">
            <AlertCircle className="h-5 w-5" />
            <p className="font-bold">EMERGENCY PROTOCOL</p>
          </div>
          {recommendations.emergency_contact && (
            <p className="mt-2 text-sm">
              {recommendations.emergency_contact.action}: {recommendations.emergency_contact.number}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
