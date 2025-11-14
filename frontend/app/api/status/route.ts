import { OrchestratorState } from '@/types/orchestrator'

const API_SERVER_URL = process.env.NEXT_PUBLIC_API_SERVER_URL || 'http://localhost:8000'

export async function GET() {
  try {
    // Fetch orchestrator status from Python API server
    const response = await fetch(`${API_SERVER_URL}/api/status`, {
      next: { revalidate: 30 } // Revalidate every 30 seconds
    })

    if (response.ok) {
      const status: OrchestratorState = await response.json()
      return Response.json(status, {
        headers: {
          'Cache-Control': 'public, s-maxage=30, stale-while-revalidate=60'
        }
      })
    }

    // If API server is unavailable, return default state
    return Response.json(
      {
        status: 'unknown',
        last_ingestion_timestamp: null,
        last_forecast_timestamp: null,
        last_enforcement_trigger: null,
        last_accountability_trigger: null,
        last_cycle_timestamp: null,
        cycle_duration_seconds: null
      },
      { status: 503 }
    )
  } catch (error) {
    console.error('Failed to fetch status from API server:', error)
    
    return Response.json(
      {
        status: 'unknown',
        last_ingestion_timestamp: null,
        last_forecast_timestamp: null,
        last_enforcement_trigger: null,
        last_accountability_trigger: null,
        last_cycle_timestamp: null,
        cycle_duration_seconds: null
      },
      { status: 503 }
    )
  }
}

