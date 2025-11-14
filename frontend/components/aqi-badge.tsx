interface AQIBadgeProps {
  aqi: number
  category: string
  size?: 'sm' | 'md' | 'lg'
}

export default function AQIBadge({ aqi, category, size = 'md' }: AQIBadgeProps) {
  const getColorClass = () => {
    if (aqi <= 50) return 'aqi-good'
    if (aqi <= 100) return 'aqi-satisfactory'
    if (aqi <= 200) return 'aqi-moderate'
    if (aqi <= 300) return 'aqi-poor'
    if (aqi <= 400) return 'aqi-very-poor'
    return 'aqi-severe'
  }

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-lg',
  }

  return (
    <div className={`${getColorClass()} ${sizeClasses[size]} rounded-lg font-semibold inline-block`}>
      {category} ({aqi})
    </div>
  )
}
