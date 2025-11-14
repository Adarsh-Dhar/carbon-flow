interface ConfidenceMeterProps {
  value: number
  label?: string
}

export default function ConfidenceMeter({ value, label }: ConfidenceMeterProps) {
  const getColor = () => {
    if (value >= 80) return 'text-green-400'
    if (value >= 60) return 'text-yellow-400'
    return 'text-orange-400'
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-32 h-32">
        <svg className="transform -rotate-90" width="128" height="128">
          <circle
            cx="64"
            cy="64"
            r="56"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-slate-700"
          />
          <circle
            cx="64"
            cy="64"
            r="56"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeDasharray={`${(value / 100) * 351.68} 351.68`}
            className={`transition-all duration-500 ${getColor()}`}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className={`text-3xl font-bold ${getColor()}`}>{value}%</div>
            {label && <div className="text-xs text-slate-400 mt-1">{label}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
