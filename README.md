# PyScrapr - Modular Web Scraping Toolkit

![version](https://img.shields.io/badge/version-0.3.0-blue) ![python](https://img.shields.io/badge/python-3.10+-green) ![license](https://img.shields.io/badge/license-personal_use-yellow)

Cross-platform all-in-one web scraping platform with 20+ integrated tools across 8 phases plus a dedicated audit & intel suite.

## 🧰 Tools (8 phases)

| Phase | Tool | Description |
|-------|------|-------------|
| P1 | **Image Harvester** | Extract all images (src/srcset/picture/lazy-load/CSS bg), filter, dedupe, parallel download |
| P2 | **URL Mapper** | BFS crawl with depth control, Tree + Cytoscape graph view, pause/resume, robots.txt |
| P3 | **Site Ripper** | Full offline mirror with URL rewriting, PDF report, ZIP export |
| P4 | **Media Downloader** | YouTube/Instagram/TikTok/1000+ sites via yt-dlp, format picker, playlist range |
| P5 | **AI Tagger (CLIP)** | Zero-shot image tagging with free-form labels |
| P6 | **Tech Fingerprinter** | Detect CMS, framework, server, JS lib (7500+ Wappalyzer fingerprints) |
| P7 | **Screenshotter** | Batch capture, multi-viewport, element-only, PDF, video, gallery, compare, scheduled |
| P8 | **Threat Scanner** | Static malware analysis: magic bytes, YARA, archive inspection, PDF/Office/PE analyzer, hash reputation, risk score 0-100 |

## 🔎 Audit & Intel

| Module | Description |
|--------|-------------|
| **SEO Auditor** | Meta / OG / Twitter / heading audit with 0-100 score and per-severity issue list |
| **Broken Link Checker** | BFS crawl + HEAD/GET status check, full report |
| **Security Headers Scanner** | HSTS, CSP, XFO, cookie flags graded A-F |
| **SSL Inspector** | TLS cert details, expiry countdown, SAN, hostname match |
| **Domain Intel** | WHOIS + DNS records + subdomain enumeration via crt.sh |
| **Wayback Explorer** | archive.org snapshots browser + on-demand save |
| **Sitemap Analyzer** | Auto-detect sitemap.xml, parse URLs, stats and CSV/JSON export |

## 🛠️ Utilities

- **AI Extract (Ollama)** - LLM-powered text structuring to JSON
- **Custom Pipeline (Monaco)** - Python snippets to transform scraped data
- **Selector Playground** - Live CSS/XPath tester
- **Link Bypass** - Redirect resolver + ad-gateway bypasser (adf.ly, ouo.io)
- **Auth Vault** - Per-site cookie/header/token storage

## 🔧 System

- **Scheduled Jobs** - Cron-based automation (APScheduler)
- **Diff Detection** - Compare two runs, highlight changes
- **History** - All jobs with re-run + export (CSV/JSON/Excel)
- **Settings** - 50+ configurable keys (tools, AI explainer, threat, webhooks, email, cluster, playwright)

## ⚡ Cross-cutting features

- 🪝 **Webhooks** - Discord, Telegram, generic HTTP (auto-fire on job events)
- 📧 **Email notifications** - SMTP alerts as alternative or complement to webhooks
- 🔄 **Proxy rotation** - HTTP/HTTPS/SOCKS5 round-robin across all tools
- 🎭 **UA rotation** - 6 browser profiles, per-request switching
- 🧩 **CAPTCHA solver** - 2Captcha / Anti-Captcha integration
- 🎬 **Playwright rendering** - Headless Chromium for JS-heavy sites
- 🤖 **AI Threat Explainer** - DeepSeek / Ollama / OpenAI plain-language verdicts for Threat Scanner findings, with hash cache and threshold guard
- 🌐 **Cluster / Worker nodes** - Distributed scraping across multiple machines via shared token
- 📊 **System monitor** - Realtime CPU/RAM/network in footer
- 🌓 **Dark/light theme** - Mantine v7, persisted
- ⌨️ **Keyboard shortcuts** - Ctrl+1-8 tools, Ctrl+K smart URL, Ctrl+D theme, Ctrl+/ docs search
- 🔔 **Notification sound** - Web Audio beep on job done

## 📦 Stack

**Backend:** FastAPI · SQLAlchemy async · httpx · BeautifulSoup · lxml · yt-dlp · OpenCLIP · reportlab · APScheduler · Pillow · Playwright · dnspython · yara-python · pymupdf · oletools · pefile · py7zr · python-magic

**Frontend:** React 18 · TypeScript · Vite · Mantine v7 · @mantine/charts · TanStack Query · Cytoscape · Monaco Editor · Fuse.js · zustand · dayjs

## 🚀 Getting started

### Prerequisites

- **Python 3.10 / 3.11 / 3.12** (3.14 not yet compatible with torch wheels)
- **Node.js 18+**
- Windows 10/11, macOS, or Linux

### Quickest path (Windows) - one-click setup

```cmd
setup.bat
```

Interactive script that detects Python + npm, installs all backend and frontend deps, optionally installs Playwright Chromium, and optionally creates a Desktop shortcut. First run takes 5-10 minutes (torch ~200 MB + other deps).

Then launch anytime with:
```cmd
run-pyscrapr.bat
```
or double-click the Desktop shortcut. This opens 2 windows (backend + frontend) and auto-opens the browser when backend is ready.

### Manual install (all platforms)

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python run.py
```
API at `http://127.0.0.1:8000`, OpenAPI at `/docs`.

**Frontend (separate terminal):**
```bash
cd frontend
npm install
npm run dev
```
UI at `http://localhost:5173`.

### Optional components

- **Playwright Chromium** (~300 MB) - needed only if you enable "Render dengan browser" toggle:
  ```bash
  python -m playwright install chromium
  ```
- **Ollama** (for AI Extract / AI Threat Explainer) - [ollama.com](https://ollama.com) → `ollama pull llama3.2`
- **CLIP model** - auto-downloaded on first use (~350 MB)
- **YARA rules** - YARAForge core ruleset auto-fetched to `data/yara-rules-fetched/` on first scan
- **SMTP credentials** (for email notifications) - configure in Settings UI
- **Worker nodes** (for distributed scraping) - run same backend on each node, set `worker_mode=worker` + shared token

## 🗂️ Architecture

```
scraper_app/
├── backend/
│   ├── app/
│   │   ├── api/              ← 30+ routers (thin HTTP layer)
│   │   ├── services/         ← 50+ services (orchestrators + building blocks,
│   │   │                       includes threat_scanner, threat_ai_explainer,
│   │   │                       screenshot_capture/compare/video, security_scanner,
│   │   │                       seo_auditor, ssl_inspector, domain_intel, etc.)
│   │   ├── repositories/     ← DB access (SQL stays here)
│   │   ├── models/           ← SQLAlchemy ORM
│   │   ├── schemas/          ← Pydantic request/response
│   │   ├── db/               ← async engine + session
│   │   └── utils/
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── pages/            ← Dashboard + 8 P-tools + 7 audit/intel + 5 utilities + 4 system
│   │   ├── components/       ← Reusable UI (SitemapTree/Graph, BulkModal, StatusBar, charts)
│   │   ├── hooks/
│   │   ├── lib/              ← api, sse, sound, notify, utils
│   │   └── types/
├── data/                     ← SQLite + pipelines.json + auth_vault.json + settings.json
│                              + yara-rules/ + ai_threat_cache + quarantine/
├── downloads/                ← organized per-domain, per-date, per-module
└── logs/
```

## 📖 Design principles

- **Repository + Service pattern** - SQL in `repositories/`, business in `services/`, HTTP in `api/`
- **Async everywhere** - httpx + asyncio + aiofiles + SQLAlchemy async
- **Real-time UI** - Server-Sent Events push progress, no polling
- **Cross-platform** - `pathlib` only, no Windows-specific calls
- **Batteries-included** - all deps in single `requirements.txt`, no optional groups
- **Factory pattern** - `http_factory.py` builds pre-configured clients with proxy/UA/auth applied
- **Global EventBus** - webhook + pipeline + threat-scan listeners subscribe once, fire on job events

## 📝 License

Personal / educational use only. For any commercial redistribution, contact the author.
Respect target sites' Terms of Service. Scraping behavior (rate limits, robots.txt) is
configurable - user is responsible for ethical use.

## 📋 See also

- [CHANGELOG.md](./CHANGELOG.md) - Version history
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Comprehensive test cases (22 sections, 120+ tests)
