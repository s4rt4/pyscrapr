# PyScrapr — Modular Web Scraping Toolkit

Cross-platform web scraping app with three phased capabilities:

1. **Image Harvester** — extract all images from a page (src, srcset, picture, lazy-load, CSS background optional), filter by type/size/dimension, hash-dedupe, parallel download. ✅ Phase 1
2. **URL Mapper** — crawl a domain with depth control and visualise as a tree. Phase 2.
3. **Site Ripper** — full offline mirror with URL rewriting. Phase 3.

## Stack

**Backend** — FastAPI, SQLAlchemy 2.0 async, aiosqlite, Pydantic v2, httpx, BeautifulSoup4, Pillow
**Frontend** — Vite + React 18 + TypeScript, Mantine v7, TanStack Query, React Router v6

## Architecture

```
scraper_app/
├── backend/
│   ├── app/
│   │   ├── api/            ← FastAPI routers (thin HTTP layer)
│   │   ├── services/       ← business logic (orchestrators + building blocks)
│   │   ├── repositories/   ← DB access (SQL stays here)
│   │   ├── models/         ← SQLAlchemy ORM
│   │   ├── schemas/        ← Pydantic request/response
│   │   ├── db/             ← engine, session
│   │   ├── utils/          ← pure helpers
│   │   ├── config.py
│   │   └── main.py         ← FastAPI factory
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── pages/          ← HarvesterPage, MapperPage, RipperPage, HistoryPage
│   │   ├── components/
│   │   ├── lib/            ← api client, SSE
│   │   ├── types/
│   │   ├── theme.ts
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── data/                   ← SQLite file
├── downloads/              ← scraped output (per-domain, per-date)
└── logs/
```

## Getting started

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python run.py
```

API available at `http://127.0.0.1:8000` — OpenAPI docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI available at `http://localhost:5173`. Vite proxies `/api/*` to the backend.

## Design principles

- **Repository + Service pattern** — SQL stays in `repositories/`, business logic in `services/`, HTTP in `api/`. Controllers are thin, services are testable with mock repos.
- **Async everywhere** — `httpx` + `asyncio` + `aiofiles` + SQLAlchemy async. Scales to hundreds of parallel requests without threading headaches.
- **Real-time UI** — Server-Sent Events push per-asset progress to the browser. No polling.
- **Cross-platform** — `pathlib`, no Windows-specific calls.
- **Building blocks reused across phases** — `downloader`, `filter_engine`, `deduplicator`, `image_parser` are phase-agnostic. Each phase has its own orchestrator.
