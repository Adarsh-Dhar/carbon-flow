import { LogsResponse } from '@/types/orchestrator'

const API_SERVER_URL = process.env.NEXT_PUBLIC_API_SERVER_URL || 'http://localhost:8000'

export async function GET(request: Request) {
  try {
    // Get limit from query params (default: 50)
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '50', 10)

    // Fetch recent logs from Python API server
    const response = await fetch(`${API_SERVER_URL}/api/logs/recent?limit=${limit}`, {
      next: { revalidate: 10 } // Revalidate every 10 seconds for logs
    })

    if (response.ok) {
      const logsData: LogsResponse = await response.json()
      return Response.json(logsData, {
        headers: {
          'Cache-Control': 'public, s-maxage=10, stale-while-revalidate=30'
        }
      })
    }

    // If API server is unavailable, return empty logs
    return Response.json(
      { logs: [], count: 0 },
      { status: 503 }
    )
  } catch (error) {
    console.error('Failed to fetch logs from API server:', error)
    
    return Response.json(
      { logs: [], count: 0 },
      { status: 503 }
    )
  }
}

