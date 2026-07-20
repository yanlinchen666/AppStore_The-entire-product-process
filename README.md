# App Store Review Analysis System

> AI-driven analysis of iOS App Store reviews, turning user feedback into
> actionable product requirements, version plans, and test cases — with full
> traceability from review to test case.

This project implements the LaienTech "iOS App Review Analysis and Version
Planning Assessment". See the assessment requirements in the repository root
[README.md](file:///d:/AI/agent_vc/AppStore_vc/README.md).

## ✨ Key Features

- **Real data collection** from the US App Store via the iTunes RSS Customer Reviews API (no page scraping).
- **Linear pipeline architecture** — 9 stages orchestrated by `AnalysisOrchestrator`, each stage has clear input/output and failure handling.
- **Model-driven semantic analysis** using Qwen3-8B for topic discovery, finding generation, PRD writing, and test case design.
- **Evidence validation** with BGE-M3 embeddings + ChromaDB: every finding is backed by real review evidence.
- **Assumption marking**: conclusions without sufficient evidence (support count < 2 or confidence < 0.4) are explicitly flagged as assumptions, not silently kept.
- **Conflict detection**: contradictory reviews are surfaced and counted.
- **Full traceability chain**: Review → Finding → Requirement → Test Case, queryable via API and UI.
- **Live progress UI**: every pipeline stage streams progress to the frontend (polling or SSE).
- **JSON / CSV import**: supports externally provided review datasets (interviewer may supply unseen data).
- **Zombie run recovery**: backend startup auto-detects interrupted runs and marks them as failed.
- **Cached sample output**: results viewable even without network access.

## 🏗️ Architecture

```
User → Frontend (React + TS + Vite)
         │  /api/*  (Vite dev proxy → :8000)
         ▼
     FastAPI  ── MySQL (runs, findings, requirements, test cases)
         │
         ├─ Collector         → iTunes RSS API (deterministic)
         ├─ Cleaner           → dedup, langdetect, sentiment (deterministic)
         ├─ VectorStore       → ChromaDB + BGE-M3 embeddings
         ├─ AnalysisService   → Qwen3-8B (topic extraction, finding gen)
         ├─ EvidenceService   → vector search + embedding similarity
         ├─ PRDService        → Qwen3-8B (requirements + version plan)
         ├─ TestCaseService   → Qwen3-8B (test cases with traceability)
         └─ ProgressService   → in-memory events + DB status
```

**Pipeline stages (9 total):**

| Stage | Name | Description |
|-------|------|-------------|
| 1 | Collection | Fetch reviews from App Store RSS or use imported data |
| 2 | Cleaning | Dedup, language detection, sentiment scoring |
| 3 | Vector Index | Build BGE-M3 embeddings in ChromaDB |
| 4 | Topic Extraction | LLM-based semantic clustering (no predefined categories) |
| 5 | Finding Generation | LLM extracts core issues from topics + reviews |
| 6 | Evidence Validation | Vector search validates findings, marks assumptions/conflicts |
| 7 | PRD Generation | LLM converts validated findings into requirements + versions |
| 8 | Test Case Generation | LLM generates test cases linked to requirements |
| 9 | Done | Mark run as completed |

> **Note**: This project uses a **linear pipeline**, not LangGraph or multi-agent
> orchestration. Each stage runs sequentially in a background thread, with
> non-fatal stages (PRD, test cases) able to fail without aborting the whole run.

For the full design including pipeline details and traceability rules, see
[Project Documents/产品文档.md](file:///d:/AI/agent_vc/AppStore_vc/AppStore_vc/Project%20Documents/产品文档.md).

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ (Node 20+ recommended)
- MySQL 8.0+
- Anaconda (for Python environment management)

### Backend

```powershell
cd AppStore_vc/backend

# Create environment
conda create -n appstore_vc python=3.10 -y
conda activate appstore_vc

# Install dependencies
pip install -r requirements.txt

# Configure
Copy-Item .env.example .env
# Edit .env: set DB_PASSWORD and SILICONFLOW_API_KEY

# Create database
mysql -u root -p -e "CREATE DATABASE appstore_vc CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Initialize tables
python -m app.create_tables

# Run
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
cd AppStore_vc/frontend
npm install
npm run dev
```

Open http://localhost:5173

## 📖 How to Use

### Option A: Analyze an App Store app
1. Open http://localhost:5173/analyze
2. Paste an App Store URL (e.g. `https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684`)
3. Optionally provide an analysis goal (e.g. "subscription and usability issues")
4. Click "开始分析" — watch live progress through all 9 pipeline stages
5. Browse results in the tabs: Reviews / Findings / PRD / Test Cases

### Option B: Import external review data (JSON / CSV)
1. Open http://localhost:5173/import
2. Upload a `.json` or `.csv` file (download sample templates from the page)
3. Click "导入数据"
4. Optionally start analysis on the imported data

**CSV format:**
```csv
app_id,app_name,author,rating,title,content,review_date,app_version
```

**JSON format:** Array of objects with the same fields.

> Re-importing the same file is safe — duplicates are automatically skipped,
> and the correct `app_id` is returned so analysis can proceed on existing data.

### Option C: View cached sample results (no network required)
Open [sample_data/sample_analysis_result.json](file:///d:/AI/agent_vc/AppStore_vc/AppStore_vc/sample_data/sample_analysis_result.json)
to inspect a representative full-pipeline output.

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [Project Documents/项目材料记录.md](file:///d:/AI/agent_vc/AppStore_vc/AppStore_vc/Project%20Documents/项目材料记录.md) | Models, prompts, model config, failure handling, anti-hallucination measures (required by assessment) |
| [Project Documents/产品文档.md](file:///d:/AI/agent_vc/AppStore_vc/AppStore_vc/Project%20Documents/产品文档.md) | Product architecture, business flow, pipeline design, traceability rules |
| [Project Documents/项目启动及配置说明.md](file:///d:/AI/agent_vc/AppStore_vc/AppStore_vc/Project%20Documents/项目启动及配置说明.md) | Detailed setup, run instructions, common issues, maintenance scripts |
| [sample_data/README.md](file:///d:/AI/agent_vc/AppStore_vc/AppStore_vc/sample_data/README.md) | Sample data usage |

## 🗂️ Data Source & Limitations

- **Source**: Apple iTunes RSS Customer Reviews API
  - URL: `https://itunes.apple.com/us/rss/customerreviews/id={app_id}/page={page}/sortBy=mostRecent/json`
- **Limitations**:
  - Max 50 reviews/page × 10 pages = ~500 reviews per app
  - Only publicly visible reviews; deleted or hidden reviews are not included
  - Developer responses are not returned by the RSS feed
  - Some historical reviews may be unavailable
- **Rate limiting**: 1-second delay between requests (`REQUEST_DELAY`) to avoid abnormal load on Apple's servers
- **Real data only**: no simulated or synthetic reviews are stored in the database

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze` | Start async analysis pipeline (returns run_id immediately) |
| GET | `/api/analyze/{run_id}/progress` | Poll progress events |
| GET | `/api/analyze/{run_id}/stream` | SSE stream of progress events |
| POST | `/api/import` | Import reviews from JSON/CSV file |
| POST | `/api/import/analyze` | Analyze previously imported reviews |
| GET | `/api/runs` | List all analysis runs |
| GET | `/api/runs/{id}` | Get full run details (topics, findings, requirements, test cases) |
| GET | `/api/runs/{id}/reviews` | Get reviews for a run |
| GET | `/api/runs/{id}/findings` | Get findings for a run |
| GET | `/api/runs/{id}/requirements` | Get PRD requirements for a run |
| GET | `/api/runs/{id}/testcases` | Get test cases for a run |
| GET | `/api/runs/{id}/traceability` | Get full traceability chain |
| GET | `/api/evidence/search` | Semantic search over review evidence |
| POST | `/api/evidence/validate` | Validate a finding against evidence |

Interactive docs at http://localhost:8000/docs

## 🔐 Environment Variables

See [backend/.env.example](file:///d:/AI/agent_vc/AppStore_vc/AppStore_vc/backend/.env.example). Required:

- `DB_PASSWORD` — MySQL password
- `SILICONFLOW_API_KEY` — API key from https://siliconflow.cn

Optional (with defaults):

- `LLM_PROVIDER` (default: `siliconflow`)
- `SILICONFLOW_LLM_MODEL` (default: `Qwen/Qwen2.5-7B-Instruct`; project uses `Qwen/Qwen3-8B`)
- `SILICONFLOW_BASE_URL` (default: `https://api.siliconflow.cn/v1`)
- `EMBEDDING_MODEL` (default: `BAAI/bge-m3`)
- `APP_STORE_COUNTRY` (default: `us`)
- `MAX_REVIEWS_PER_FETCH` (default: `200`)
- `REQUEST_DELAY` (default: `1.0`)
- `CHROMADB_PATH` (default: `./chromadb`)
- `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` (optional; graph features disabled if unreachable)

Secrets are loaded from `.env` and never committed to the repository.

## 🛠️ Maintenance Scripts

| Script | Purpose |
|--------|---------|
| `python -m app.create_tables` | Create all database tables |
| `python -m app.migrate_schema` | Apply incremental schema migrations (add new columns) |
| `python -m app.cleanup_zombies` | Detect and optionally clean up zombie runs (stuck in "running" status) |

```powershell
# Dry-run: list zombie runs without deleting
python -m app.cleanup_zombies

# Apply: mark zombie runs as failed
python -m app.cleanup_zombies --apply
```

## 🧱 Tech Stack

**Backend**: Python 3.10, FastAPI, SQLAlchemy, MySQL 8.0, ChromaDB, Pydantic
**LLM**: Qwen3-8B (SiliconFlow API), BGE-M3 embeddings (SiliconFlow API)
**Frontend**: React 18, TypeScript, Vite, TailwindCSS, Zustand, React Router, lucide-react
**Optional**: Neo4j Community (graph features; automatically disabled if credentials are invalid or server is unreachable)

## 📝 License

This project is for the LaienTech evaluation.
