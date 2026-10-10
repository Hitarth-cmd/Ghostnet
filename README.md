# OceanGuard AI — Marine Debris Intelligence & Ecological Shield

An end-to-end operational decision-support and responder coordination platform for marine debris / ghost-gear detection, geographic localization, Lagrangian ocean-drift forecasting, ecological threat assessment, and NGO/responder field intervention.

Built with a modular multi-agent pipeline around the detection model (treated as a stable black box with a fixed input/output interface), backed by peer-reviewed geospatial datasets and verified responder workflows.


---

## 🚀 Key Modules & Capabilities

### 1. Interactive Marine-Monitoring Map
- **High-Aesthetic Tactical GIS**: Custom Dark Matter, Ocean Satellite (Esri World Imagery), and Positron Light basemaps with 3D terrain pitch and smooth zoom.
- **Dynamic Marine Layers**:
  - **Detections**: Classified debris objects (`marine_debris`, `suspected_ghost_gear`, `unknown_floating_object`) with confidence halos and incident status colors.
  - **Drift Cones**: 24h, 48h, and 72h Lagrangian particle drift trajectories with uncertainty probability envelopes.
  - **Coral Reefs**: UNEP-WCMC Global Distribution of Coral Reefs (GCRMN) with shallow-water reef contours.
  - **Marine Life Habitats**: Olive Ridley Sea Turtle nesting beaches (Gahirmatha/Rushikulya), Spinner Dolphin habitats, Whale Shark congregation corridors, and Dugong zones (SWOT / OBIS-SEAMAP).
  - **Marine Protected Areas (WDPA)**: National marine parks, wildlife sanctuaries, and biosphere reserves.
  - **High-Risk Zones**: Spatial polygons representing critical ecological intersection zones.
  - **Ecological Alert Pins**: Live pulsing threat points highlighting protected habitats under imminent drift threat.
- **Filter Toolbar**: Instant filtering by All Debris, Actionable (≥70%), Review (<70%), or Dispatched.
- **Interactive Popups**: Click any detection, reef, or alert point for live telemetry, distance, ETA, and quick actions.

### 2. NGO & Authorized Responder Module
- **Role-Based Authentication**: Registration & JWT authentication for NGOs, Rescue Organizations, Cleanup Teams, Coast Guard, and Marine Researchers.
- **Operational Alerts Inbox**:
  - **Human Verification Queue (<70%)**: Low-confidence detections flagged for human-in-the-loop review. Responders can inspect geometry and click **"✓ Verify as Debris"** or **"✕ Reject (False Positive)"** with operational notes.
  - **Actionable Cleanup Stream (≥70%)**: High-confidence detections and verified debris fields ready for immediate interception.
- **Incident Lifecycle Management**:
  - Responders can transition incidents across states: `unverified` → `verified` → `assigned` → `being_handled` → `resolved / recovered`.
  - Assign specific field teams / vessels (e.g. *Vessel Sagar Rakshak-2*, *Coastal Response Unit Goa*).
  - Add operational field notes and dispatch reasons.
- **Full Incident Audit Trail**: Complete immutable log (`IncidentAction`) tracking who modified the incident, previous vs. new status, timestamp, and notes.

### 3. Marine-Life & Ecological Threat Alerts
- **Autonomous Proximity Engine**: Computes distance (km) and drift arrival time (hours) from debris fields to vulnerable marine ecosystems.
- **Ecological Targets Monitored**:
  - Coral Reef Communities (Lakshadweep, Gulf of Mannar, Andaman & Nicobar, Gulf of Kutch, Malvan).
  - Endangered Turtle Rookeries (Olive Ridley nesting beaches).
  - Marine Mammal & Cetacean Corridors (Spinner Dolphins, Blue Whales, Dugongs).
  - Mangrove & Estuarine Biospheres (Sundarbans).
- **Severity Rating**: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
- **Scientific Provenance**: Every alert records its source citation (e.g. *UNEP-WCMC WDPA*, *GCRMN v4.1*, *SWOT 2024*), species at risk, and recommended mitigation actions.
- **Interactive Alert Actions**: Responders can acknowledge active alerts and mark them mitigated/resolved.

### 4. Autonomous Data Collection & Provenance
Real-world geographic and environmental data is autonomously collected and locally cached so the application never fabricates missing ecological facts:
- `backend/data/cached_mpas.geojson`: WDPA Protected Areas.
- `backend/data/cached_coral_reefs.geojson`: UNEP-WCMC Coral Reefs.
- `backend/data/cached_species_habitats.geojson`: SWOT / OBIS Sea Turtle and Cetacean habitats.
- `backend/data/demo_coastline.geojson`: NOAA GSHHG vector coastline.
- `backend/data/currents_grid.zarr`: Ocean surface velocity grid for drift advection.

---

## 🤖 Multi-Agent System Architecture

The OceanGuard backend coordinates six specialized agents:

```
Satellite Observation / SAR Scene
               ↓
    [ 1. Detection Agent ]  (Existing ML Model / Provider — black box)
               ↓  { coordinates, confidence, object_class, area_m2 }
    [ 2. Drift Agent ]      (OpenDrift particle ensemble: 24h, 48h, 72h horizons)
               ↓  { trajectory lines + uncertainty cone }
    [ 3. Geospatial Agent ] (Shapely intersection with WDPA, Coral Reefs, Habitats)
               ↓  { MPA overlap, habitat proximity, distance to shore }
    [ 4. Risk Agent ]       (Deterministic explainable risk & priority scoring)
               ↓  { risk_score, risk_level, priority_rank, recommended_action }
    [ 5. Ecological Alert Agent ] (Detects reef & species threats; dispatches alerts)
               ↓  { CRITICAL / HIGH alerts, arrival ETA, species at risk }
    [ 6. RAG & Report Agent ]     (Evidence retrieval & narrative synthesis)
               ↓
    [ Persistence & Distribution ]
      • Database (Detections, Trajectories, Alerts, Audit Logs)
      • Responder Alerts Inbox (Verification Queue & Actionable Alerts)
      • Interactive Map Visualization & Telemetry
```

---

## 🛠️ Installation & Quickstart

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ and npm
- (Optional) Git

### 1. Clone & Set Environment Variables

```bash
cd ghostnet
```

#### Backend Environment (`backend/.env`):
```ini
DATA_MODE=demo
MODEL_PROVIDER=mock
LLM_PROVIDER=mock
JOB_BACKEND=inline
DATABASE_URL=sqlite:///ghostnet_demo.db
GHOSTNET_SECRET_KEY=your-secure-jwt-secret-key-at-least-32-chars
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

#### Frontend Environment (`frontend/.env.local`):
```ini
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_MAP_STYLE_URL=https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json
```

---

### 2. Run the Backend

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
On startup:
- Tables are initialized automatically via SQLAlchemy (`init_db()`).
- Demo detections, realistic incident history, ecological alerts, and demo responder users are seeded idempotently.
- Swagger API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

#### Demo Responder Accounts:
| Role | Email | Password | Organization |
|---|---|---|---|
| **Responder** | `responder@oceanguard.org` | `responder123` | Ocean Guardians Marine NGO |
| **Field Cleanup** | `cleanup@marinerescue.org` | `cleanup123` | Rapid Marine Cleanup Taskforce |
| **Researcher** | `researcher@incois.gov.in` | `researcher123` | INCOIS Ocean Observation |
| **Admin** | `admin@oceanguard.org` | `admin123456` | OceanGuard AI Command |

---

### 3. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing the Complete System

### Run the Backend Automated Test Suite (53 Tests)
```bash
cd backend
python -m pytest
```
All 53 unit and integration tests validate:
- Authentication & JWT token security
- NGO registration and login
- Responder alerts inbox (verification queue & actionable stream)
- Incident lifecycle transitions (`verify`, `reject`, `assign`, `being_handled`, `resolve`)
- Incident audit trail logging
- Ecological alert generation, proximity detection, and resolution
- Drift trajectory simulations (24h/48h/72h)
- Geospatial intersections and risk scoring
- Deterministic RAG citations
- Map API endpoints (Coral Reefs, Species Habitats, Protected Areas, Trajectories)

### Verify Frontend Production Build
```bash
cd frontend
npm run build
```
Compiles TypeScript, checks type validity, and builds all Next.js static pages with 0 errors.

---

## 🔌 Connecting an External ML Model

The platform treats the detection model as a pluggable component. To attach your actual trained PyTorch, ONNX, or TensorFlow model:

1. Open `backend/app/detection/providers/`.
2. Implement the `BaseDetectionProvider` interface (see `mock.py` as an example):
   ```python
   class MyModelProvider(BaseDetectionProvider):
       def detect(self, scene_id: str, image_bytes: bytes) -> list[DetectionRecord]:
           # 1. Run inference on input image
           # 2. Convert pixel boxes/masks to EPSG:4326 GeoJSON polygons
           # 3. Return DetectionRecord with confidence, lat, lon, geometry
           ...
   ```
3. Set `MODEL_PROVIDER=custom` in `backend/.env`.
4. Downstream agents (Drift, Geospatial, Risk, Ecological Alerts, RAG, Responder Inbox, Map) run automatically without requiring any changes to the model.

---

## 📂 Project Structure

```
ghostnet/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints
│   │   │   ├── alerts.py    # Ecological alerts & threat geojson
│   │   │   ├── detections.py# Detection catalog & sync analysis
│   │   │   ├── map.py       # GIS layers (coral, habitats, MPAs, trajectories)
│   │   │   ├── users.py     # NGO auth, inbox & incident lifecycle
│   │   │   └── system.py    # Health & system status
│   │   ├── auth.py          # JWT creation, password hashing, verification
│   │   ├── database.py      # SQLAlchemy setup & session lifecycle
│   │   ├── drift/           # OpenDrift Lagrangian advection engine
│   │   ├── geospatial/      # Autonomous data collector & spatial queries
│   │   │   ├── alert_engine.py   # Proximity detection for reefs & species
│   │   │   └── data_collector.py # Caching for WDPA, GCRMN, SWOT, NOAA
│   │   ├── models/          # Database ORM models (Detection, Alert, User, etc.)
│   │   ├── orchestrator/    # Multi-agent coordination pipeline
│   │   ├── rag/             # Offline evidence retrieval & citations
│   │   ├── risk/            # Explainable ecological risk scoring
│   │   └── seed.py          # Database seeding (detections, users, alerts)
│   ├── data/                # Locally cached scientific GeoJSON layers
│   └── tests/               # 53 pytest test cases
├── frontend/
│   ├── app/
│   │   ├── globals.css      # Custom styling, fonts, glassmorphism
│   │   └── page.tsx         # Dashboard coordinator with filter pills
│   ├── components/
│   │   ├── MapView.tsx      # Tactical marine map (MapLibre GL)
│   │   ├── ResponderPortal.tsx # Full NGO & Responder operations modal
│   │   ├── EcologicalAlertBanner.tsx # Real-time threat alert ticker
│   │   ├── DetectionPanel.tsx  # Target inspector & agent execution
│   │   ├── LayerToggle.tsx     # Operational layer switcher
│   │   ├── StatsBar.tsx        # Status overview & counter pills
│   │   └── DataSourcesModal.tsx# Scientific provenance inspector
│   ├── lib/api.ts           # Typed API client with JWT support
│   └── types/index.ts       # TypeScript interfaces
└── README.md
```

---

## 📜 Scientific Data Licenses & Citations
- **UNEP-WCMC Protected Planet**: World Database on Protected Areas (WDPA), CC-BY 3.0 IGO.
- **UNEP-WCMC / GCRMN**: Global Distribution of Coral Reefs (WCMC 008), CC-BY 4.0.
- **SWOT / OBIS-SEAMAP**: State of the World's Sea Turtles & Duke University Marine Geospatial Ecology Lab.
- **NOAA GSHHG**: Global Self-consistent Hierarchical High-resolution Geography, Public Domain.
- **INCOIS**: Indian National Centre for Ocean Information Services surface drift observations.
