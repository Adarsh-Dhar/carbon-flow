import { SensorData } from '@/types/orchestrator'

const API_SERVER_URL = process.env.NEXT_PUBLIC_API_SERVER_URL || 'http://localhost:8000'

export async function GET() {
  try {
    // Try to fetch from Python API server
    const response = await fetch(`${API_SERVER_URL}/api/sensors/latest`, {
      next: { revalidate: 60 } // Revalidate every 60 seconds
    })

    if (response.ok) {
      const sensorData: SensorData = await response.json()
      
      // Calculate data quality metrics
      const cpcbCount = sensorData.cpcb_data?.length || 0
      const completeness = cpcbCount > 0 ? Math.min(1.0, cpcbCount / 10) : 0
      
      // Calculate age if timestamps are available
      let age_hours = 0
      if (sensorData.cpcb_data && sensorData.cpcb_data.length > 0) {
        const latestTimestamp = sensorData.cpcb_data
          .map(s => s.timestamp)
          .filter(Boolean)
          .sort()
          .reverse()[0]
        
        if (latestTimestamp) {
          const age_ms = Date.now() - new Date(latestTimestamp).getTime()
          age_hours = age_ms / (1000 * 60 * 60)
        }
      }

      return Response.json({
        ...sensorData,
        data_quality: {
          completeness,
          age_hours
        }
      }, {
        headers: {
          'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120'
        }
      })
    }

    // If API server returns 404, return null or fallback
    if (response.status === 404) {
      return Response.json(
        { error: 'No sensor data available' },
        { status: 404 }
      )
    }

    // For other errors, fall through to fallback
    throw new Error(`API server returned ${response.status}`)
  } catch (error) {
    console.error('Failed to fetch sensors from API server:', error)
    
    // Fallback: Return error response
    return Response.json(
      { 
        error: 'Sensor data unavailable',
        message: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 503 }
    )
  }
}
