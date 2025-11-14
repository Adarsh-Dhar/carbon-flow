import { ForecastData } from '@/types/orchestrator'

const API_SERVER_URL = process.env.NEXT_PUBLIC_API_SERVER_URL || 'http://localhost:8000'

export async function GET() {
  try {
    // Try to fetch from Python API server
    const response = await fetch(`${API_SERVER_URL}/api/forecast/latest`, {
      next: { revalidate: 60 } // Revalidate every 60 seconds
    })

    if (response.ok) {
      const forecast: ForecastData = await response.json()
      return Response.json(forecast, {
        headers: {
          'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120'
        }
      })
    }

    // If API server returns 404, return null or fallback
    if (response.status === 404) {
      return Response.json(
        { error: 'No forecast data available' },
        { status: 404 }
      )
    }

    // For other errors, fall through to fallback
    throw new Error(`API server returned ${response.status}`)
  } catch (error) {
    console.error('Failed to fetch forecast from API server:', error)
    
    // Fallback: Return error response
    return Response.json(
      { 
        error: 'Forecast data unavailable',
        message: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 503 }
    )
  }
}
