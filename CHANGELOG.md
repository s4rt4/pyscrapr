# Changelog

## [0.2.0] — 2026-04-18

### Added — Sprint A/B/C (advanced features)

**Webhooks & Notifications**
- Discord webhook with rich embeds (color-coded by status)
- Telegram Bot integration (Markdown formatting)
- Generic HTTP webhook (any URL accepting POST JSON)
- Auto-fire on job done/error via EventBus global listeners
- Settings panel with "Send test" button
- Trigger toggles: on completion, on errors, only when Diff detects changes

**AI Text Structuring (Ollama)**
- HTTP client to local Ollama instance (`localhost:11434`)
- `/api/llm/health`, `/api/llm/generate`, `/api/llm/extract` endpoints
- AI Extract page with 4 preset templates: product info, article summary, entities, contact info
- Schema description + JSON mode for structured output
- Graceful offline fallback with install guide

**Custom Python Pipeline**
- Monaco Editor (Python syntax highlighting) for writing transforms
- `exec()` executor with stdout capture + pre-imported stdlib (re, json, datetime, math, statistics)
- CRUD stored in `data/pipelines.json`
- Auto-run on job completion (opt-in per pipeline per job type)
- Test run panel: use job data OR paste sample JSON
- 4 preset snippets: filter by size, regex clean, extract domain, aggregate stats

**Factory-based HTTP integration**
- `services/http_factory.py` — centralized `build_client()` + `build_downloader()`
- UA rotation per-request (6 browser profiles) wired into all orchestrators
- Proxy rotation (round-robin/random) applied across Harvester/Mapper/Ripper/Media
- Auth Vault cookies auto-injected by matching target URL domain
- Media Downloader: proxy + UA + cookies injected into yt-dlp opts

### Changed
- EventBus now supports global listeners (for cross-cutting concerns)
- All orchestrators reuse shared HTTP factory (reduces duplicated config)

### Fixed
- Traffic counter negative overflow after app restart
- Sidebar scrollbar visual clutter (hidden via `type="never"`)

---

## [0.1.0] — 2026-04-17

### Initial Release

**5 core phases:**
- P1 Image Harvester: extract/filter/dedupe images from any page
- P2 URL Mapper: BFS crawl with tree + Cytoscape graph view, pause/resume
- P3 Site Ripper: full offline mirror with URL rewriting + PDF report
- P4 Media Downloader: YouTube/IG/TikTok via yt-dlp, format picker, ffmpeg
- P5 AI Tools: CLIP zero-shot image tagging with free-form labels

**Advanced features:**
- Selector Playground: live CSS/XPath tester
- Link Bypass: redirect resolver + ad-gateway bypasser (adf.ly, ouo.io)
- Auth Vault: per-site cookie/header/token storage
- Proxy Rotator + UA rotation
- CAPTCHA solver integration (2Captcha, Anti-Captcha)
- Scheduled jobs (APScheduler), Diff/change detection
- Unified data export (CSV/JSON/Excel), REST API generator
- Bulk URL queue, job re-run, smart URL detector

**UI/UX:**
- Dashboard with quick actions
- Grouped sidebar navigation (Tools / Utilities / System)
- System monitor footer (CPU/RAM/network)
- Dark/light theme toggle
- Keyboard shortcuts
- ErrorBoundary + loading skeletons
- Empty states with CTAs

**Stack:**
- Backend: FastAPI + SQLAlchemy async + httpx + yt-dlp + CLIP
- Frontend: React 18 + Mantine v7 + Vite + TypeScript
