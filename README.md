# Respiro - Agentic Asthma Management System

Respiro transforms asthma care from a passive "digital diary" into an **active, autonomous guardian**. Instead of waiting for a patient to report symptoms, Respiro uses Agentic AI to predict risks and intervene *before* an attack happens (e.g., turning on air purifiers or rescheduling outdoor activities).

## Architecture

### The 5-Agent System

1. **The Orchestrator (The Brain):** Built on **LangGraph**, it manages the system state, ensuring safety and consistency. It handles priority interrupts (stopping everything for a medical emergency) and maintains long-term context across user sessions.

2. **The Sentry (The Senses):** A sensor fusion agent that monitors **Real-Time Context**. It aggregates hyper-local air quality (Google AQI), pollen data (Ambee), and physiological biometrics (Apple HealthKit/Fitbit) to detect triggers instantly.

3. **The Clinical Agent (The Doctor):** Uses deterministic, rule-based logic (not just LLMs) to execute the patient's **Asthma Action Plan**. It adheres to **FHIR standards** to ensure medical accuracy and interoperability with hospital systems.

4. **The Negotiator (The Interface):** An empathetic, generative AI persona (powered by **Amazon Bedrock**) that communicates with the user. It handles lifestyle logistics, such as autonomously rescheduling **Google Calendar** events to avoid pollution peaks or calculating cleaner commute routes.

5. **The Rewards Agent (The Incentivizer):** Drives adherence through gamification. It validates good behavior (e.g., taking meds, avoiding triggers) and unlocks real-world value via API integrations with insurance providers (lower premiums) or pharmacies (discounts).

## Key Features

- **Hyper-Personalization:** Uses vector memory (ChromaDB) to remember user quirks (e.g., "User dislikes powder inhalers") for tailored advice.

- **Physical Agency:** It doesn't just talk; it acts. It controls **IoT Smart Home** devices (Air Purifiers) via AWS IoT Core to physically alter the patient's environment.

- **Safety First:** Implements "Human-in-the-Loop" checks for critical medical interventions, preventing AI hallucinations in high-stakes scenarios.

- **San Francisco Clean-Air Routing:** Builds an OSMnx graph enriched with elevation, Aclima baselines, and real-time PurpleAir data to compute "fastest vs cleanest" commutes, complete with Wind Breaker, Fog Guard, and Calendar Sentry reasoning.

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- AWS Account with Bedrock, IoT Core, and S3 access
- API keys for: Google Calendar, HealthKit/Fitbit, Ambee, Google AQI, OpenAI, PurpleAir, Google Pollen, Mapbox, Open-Meteo (public)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd carbonflow
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
pnpm install
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Required Environment Variables

See `.env.example` for complete list. Key variables:

- `AWS_BEDROCK_REGION` - AWS region for Bedrock
- `AWS_BEDROCK_MODEL_ID` - Bedrock model ID (e.g., "anthropic.claude-3-sonnet-20240229-v1:0")
- `GOOGLE_CALENDAR_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CALENDAR_CLIENT_SECRET` - Google OAuth client secret
- `OPENAI_API_KEY` - OpenAI API key for embeddings
- `AWS_IOT_ENDPOINT` - AWS IoT Core endpoint
- `S3_BUCKET_NAME` - S3 bucket for data storage
- `PURPLEAIR_API_KEY` - PurpleAir API token for hyper-local PM2.5
- `GOOGLE_POLLEN_API_KEY` - Google Pollen Forecast API key
- `EARTH_ENGINE_SERVICE_ACCOUNT` + `EARTH_ENGINE_PRIVATE_KEY_PATH` - Earth Engine credentials for Aclima exports
- `MAPBOX_ACCESS_TOKEN` / `NEXT_PUBLIC_MAPBOX_TOKEN` - Mapbox tokens for backend + frontend visualization
- `OPEN_METEO_BASE_URL` - Optional override for Open-Meteo (defaults to official API)

### Running the Application

1. Start the API server:
```bash
python respiro_api.py
```

2. Start the frontend (in another terminal):
```bash
cd frontend
pnpm dev
```

3. Access the application at `http://localhost:3000`

### Building the San Francisco Routing Dataset

```bash
python -m respiro.data.sf_dataset
```

The command downloads the OSMnx street network, attaches elevation + grade metadata, and caches PurpleAir/Aclima layers under `respiro/data_cache/sf_routing`. A background worker inside `api_server.py` refreshes PurpleAir snapshots every 15 minutes so the `RouteIntelligenceService` can serve low-latency requests.

## API Documentation

### Patient Endpoints

- `GET /api/patient/{patient_id}/status` - Get current patient state
- `GET /api/patient/{patient_id}/recommendations` - Get clinical recommendations
- `GET /api/patient/{patient_id}/calendar` - Get calendar events
- `GET /api/patient/{patient_id}/rewards` - Get rewards status
- `GET /api/patient/{patient_id}/memory` - Get personalization memory
- `POST /api/patient/{patient_id}/approval` - Submit approval response

### Session Management

- `POST /api/sessions/create` - Create a new orchestrator session
- `POST /api/sessions/{session_id}/execute` - Execute orchestrator for a session

### Agent Endpoints

- `GET /api/agent/sentry/trigger` - Get real-time trigger detection
- `GET /api/agent/clinical/action-plan` - Get FHIR action plan

### Routing

- `GET /api/route?start=lat,lon&end=lat,lon&sensitivity=asthma` - Returns fastest vs cleanest GeoJSON routes plus meteorology context.

### WebSocket

- `WS /ws/{session_id}` - Real-time agent updates

## Project Structure

```
carbonflow/
├── respiro/                 # Main Respiro package
│   ├── agents/             # All 5 agent implementations
│   ├── orchestrator/       # LangGraph state machine
│   ├── integrations/       # External service integrations
│   ├── memory/            # Vector memory system
│   ├── models/            # Data models (FHIR, patient data)
│   ├── tools/             # Agent tools
│   ├── utils/             # Shared utilities
│   └── storage/           # S3 storage layer
├── frontend/              # Next.js frontend
│   ├── app/              # Next.js app router
│   ├── components/       # React components
│   └── lib/             # API client and types
├── respiro_api.py        # FastAPI server
└── requirements.txt      # Python dependencies
```

## Technology Stack

- **Orchestration:** LangGraph
- **LLM:** Amazon Bedrock (Claude)
- **Vector DB:** ChromaDB
- **Storage:** AWS S3
- **IoT:** AWS IoT Core
- **FHIR:** fhir.resources
- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **API:** FastAPI, WebSockets

## Safety & Compliance

- Human-in-the-loop approval for critical interventions
- FHIR-compliant medical data
- Comprehensive error handling and retries
- Structured logging with S3 archival
- Safety checkpoints to prevent AI hallucinations

## License

[Your License Here]