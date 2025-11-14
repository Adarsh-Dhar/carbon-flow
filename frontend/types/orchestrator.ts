/**
 * TypeScript type definitions for CarbonFlow Orchestrator data structures
 */

export interface OrchestratorState {
  status: 'operational' | 'idle' | 'inactive' | 'unknown'
  last_ingestion_timestamp: string | null
  last_forecast_timestamp: string | null
  last_enforcement_trigger: string | null
  last_accountability_trigger: string | null
  last_cycle_timestamp: string | null
  cycle_duration_seconds: number | null
}

export interface ForecastPrediction {
  aqi_category: string
  threshold: number
  estimated_hours_to_threshold: number
}

export interface ForecastDataSources {
  cpcb_aqi?: number
  nasa_fire_count?: number
  avg_wind_speed_24h_kmh?: number
  stubble_burning_percent?: number
  sensor_data_age_hours?: number
  meteorological_forecast_retrieved?: boolean
}

export interface ForecastData {
  prediction: ForecastPrediction
  confidence_level: number
  reasoning: string
  timestamp: string
  data_sources: ForecastDataSources
}

export interface CPCBStation {
  station: string
  aqi: number
  pm25: number | null
  pm10: number | null
  timestamp: string | null
  latitude?: number | null
  longitude?: number | null
  is_hotspot?: boolean
}

export interface NASAData {
  fire_count: number
  region: string
  timestamp: string | null
  confidence_high: number
}

export interface DSSData {
  stubble_burning_percent: number | null
  vehicular_percent: number | null
  industrial_percent: number | null
  dust_percent: number | null
  timestamp: string | null
}

export interface SensorData {
  cpcb_data: CPCBStation[]
  nasa_data: NASAData | null
  dss_data: DSSData | null
  data_quality?: {
    completeness: number
    age_hours: number
  }
}

export interface LogEntry {
  timestamp: string
  level: string
  message: string
}

export interface LogsResponse {
  logs: LogEntry[]
  count: number
}

export interface AgentHistoryEntry {
  timestamp: string
  status: 'success' | 'failed' | 'triggered'
  message: string
}

export interface AgentHistory {
  sensor_ingest: AgentHistoryEntry[]
  forecast: AgentHistoryEntry[]
  enforcement: AgentHistoryEntry[]
  accountability: AgentHistoryEntry[]
}

