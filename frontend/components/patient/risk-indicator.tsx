"use client"

import { getRiskLevelColor, getRiskLevelBg, type RiskLevel } from "@/lib/types"
import { AlertCircle, CheckCircle2, AlertTriangle } from "lucide-react"

interface RiskIndicatorProps {
  riskLevel: RiskLevel
  riskScore: number
  riskFactors: string[]
}

export function RiskIndicator({ riskLevel, riskScore, riskFactors }: RiskIndicatorProps) {
  const color = getRiskLevelColor(riskLevel)
  const bg = getRiskLevelBg(riskLevel)

  const getIcon = () => {
    if (riskLevel === "emergency" || riskLevel === "severe") return <AlertCircle className="h-6 w-6" />
    if (riskLevel === "high" || riskLevel === "moderate") return <AlertTriangle className="h-6 w-6" />
    return <CheckCircle2 className="h-6 w-6" />
  }

  return (
    <div className={`rounded-lg p-6 ${bg} text-white`}>
      <div className="flex items-center gap-4">
        {getIcon()}
        <div>
          <h3 className="text-2xl font-bold">{riskLevel.toUpperCase()} RISK</h3>
          <p className="text-sm opacity-90">Risk Score: {(riskScore * 100).toFixed(0)}%</p>
        </div>
      </div>
      {riskFactors.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-semibold mb-2">Risk Factors:</p>
          <ul className="list-disc list-inside space-y-1 text-sm">
            {riskFactors.map((factor, idx) => (
              <li key={idx}>{factor}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
