import { ReactNode } from 'react'
import { Card } from '@/components/ui/card'

interface MetricCardProps {
  title: string
  value: string | number
  unit?: string
  icon?: ReactNode
  trend?: 'up' | 'down' | 'stable'
  trendValue?: string
  description?: string
}

export default function MetricCard({ 
  title, 
  value, 
  unit,
  icon,
  trend,
  trendValue,
  description 
}: MetricCardProps) {
  return (
    <Card className="bg-slate-800/50 border-slate-700 p-6">
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-slate-300 text-sm font-medium">{title}</h3>
        {icon && <div className="text-blue-400">{icon}</div>}
      </div>
      <div className="flex items-baseline gap-2">
        <div className="text-3xl font-bold text-slate-50">{value}</div>
        {unit && <span className="text-slate-400 text-sm">{unit}</span>}
      </div>
      {trend && (
        <div className="mt-3 flex items-center gap-2 text-xs">
          <span className={trend === 'up' ? 'text-red-400' : trend === 'down' ? 'text-green-400' : 'text-slate-400'}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trendValue}
          </span>
        </div>
      )}
      {description && <p className="mt-2 text-xs text-slate-400">{description}</p>}
    </Card>
  )
}
