# PyScrapr — Modular Web Scraping Toolkit

![version](https://img.shields.io/badge/version-0.2.0-blue) ![python](https://img.shields.io/badge/python-3.10+-green) ![license](https://img.shields.io/badge/license-personal_use-yellow)

Cross-platform all-in-one web scraping platform with 14 integrated tools.

## 🧰 Tools (5 core phases)

| Phase | Tool | Description |
|-------|------|-------------|
| P1 | **Image Harvester** | Extract all images (src/srcset/picture/lazy-load/CSS bg), filter, dedupe, parallel download |
| P2 | **URL Mapper** | BFS crawl with depth control, Tree + Cytoscape graph view, pause/resume, robots.txt |
| P3 | **Site Ripper** | Full offline mirror with URL rewriting, PDF report, ZIP export |
| P4 | **Media Downloader** | YouTube/Instagram/TikTok/1000+ sites via yt-dlp, format picker, playlist range |
| P5 | **AI Tools (CLIP)** | Zero-shot image tagging with free-form labels |

## 🛠️ Utilities

- **AI Extract (Ollama)** — LLM-powered text structuring to JSON
- **Custom Pipeline (Monaco)** — Python snippets to transform scraped data
- **Selector Playground** — Live CSS/XPath tester
- **Link Bypass** — Redirect resolver + ad-gateway bypasser (adf.ly, ouo.io)
- **Auth Vault** — Per-site cookie/header/token storage

## 🔧 System

- **Scheduled Jobs** — Cron-based automation (APScheduler)
- **Diff Detection** — Compare two runs, highlight changes
- **History** — All jobs with re-run + export (CSV/JSON/Excel)
- **Settings** — 30+ configurable options with dependency updater

## ⚡ Cross-cutting features

- 🪝 **Webhooks** — Discord, Telegram, generic HTTP (auto-fire on job done)
- 🔄 **Proxy rotation** — HTTP/HTTPS/SOCKS5 round-robin across all tools
- 🎭 **UA rotation** — 6 browser profiles, per-request switching
- 🧩 **CAPTCHA solver** — 2Captcha / Anti-Captcha integration
- 📊 **System monitor** — Realtime CPU/RAM/network in footer
- 🌓 **Dark/light theme** — Mantine v7, persisted
- ⌨️ **Keyboard shortcuts** — Ctrl+1-5 tools, Ctrl+K smart URL, Ctrl+D theme
- 🔔 **Notification sound** — Web Audio beep on job done

## 📦 Stack

**Backend:** FastAPI · SQLAlchemy async · httpx · BeautifulSoup · yt-dlp · OpenCLIP · reportlab · APScheduler · Pillow

**Frontend:** React 18 · TypeScript · Vite · Mantine v7 · TanStack Query · Cytoscape · Monaco Editor · dayjs

## 🚀 Getting started

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python run.py
```

API runs at `http://127.0.0.1:8000` · OpenAPI docs at `/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

UI at `http://localhost:5173`

### 3. Optional

- **Ollama** (for AI Extract): [ollama.com](https://ollama.com) → `ollama pull llama3.2`
- **CLIP model** (auto-downloaded on first use, ~350 MB)

## 🗂️ Architecture

```
scraper_app/
├── backend/
│   ├── app/
│   │   ├── api/              ← 17 routers (thin HTTP layer)
│   │   ├── services/         ← 30+ services (orchestrators + building blocks)
│   │   ├── repositories/     ← DB access (SQL stays here)
│   │   ├── models/           ← SQLAlchemy ORM
│   │   ├── schemas/          ← Pydantic request/response
│   │   ├── db/               ← async engine + session
│   │   └── utils/
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── pages/            ← 15 routes (Dashboard, 5 tools, 5 utilities, 4 system)
│   │   ├── components/       ← Reusable UI (SitemapTree/Graph, BulkModal, StatusBar)
│   │   ├── hooks/
│   │   ├── lib/              ← api, sse, sound, notify, utils
│   │   └── types/
├── data/                     ← SQLite + pipelines.json + auth_vault.json + settings.json
├── downloads/                ← organized per-domain, per-date, per-module
└── logs/
```

## 📖 Design principles

- **Repository + Service pattern** — SQL in `repositories/`, business in `services/`, HTTP in `api/`
- **Async everywhere** — httpx + asyncio + aiofiles + SQLAlchemy async
- **Real-time UI** — Server-Sent Events push progress, no polling
- **Cross-platform** — `pathlib` only, no Windows-specific calls
- **Batteries-included** — all deps in single `requirements.txt`, no optional groups
- **Factory pattern** — `http_factory.py` builds pre-configured clients with proxy/UA/auth applied
- **Global EventBus** — webhook + pipeline listeners subscribe once, fire on job events

## 📝 License

Personal / educational use only. For any commercial redistribution, contact the author.
Respect target sites' Terms of Service. Scraping behavior (rate limits, robots.txt) is
configurable — user is responsible for ethical use.

## 📋 See also

- [CHANGELOG.md](./CHANGELOG.md) — Version history
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) — Comprehensive test cases (22 sections, 120+ tests)
