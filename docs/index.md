# Selamat datang di PyScrapr

PyScrapr adalah **platform web scraping modular all-in-one** yang mengintegrasikan 20+ tools scraping, download, analisis, audit, dan otomatisasi dalam satu aplikasi desktop offline.

Dokumentasi ini adalah panduan lengkap (deskripsi, cara pakai, pengaturan, tips, dan troubleshooting) untuk setiap fitur.

## Apa saja yang bisa dilakukan PyScrapr?

### Scraping & Download
- **[Image Harvester](/docs/tools/image-harvester.md)** - Extract semua gambar dari halaman dengan filter & dedupe
- **[URL Mapper](/docs/tools/url-mapper.md)** - Crawl site dengan tree/graph visualization
- **[Site Ripper](/docs/tools/site-ripper.md)** - Clone situs penuh untuk offline browsing
- **[Media Downloader](/docs/tools/media-downloader.md)** - YouTube/IG/TikTok/1000+ sites via yt-dlp
- **[Tech Fingerprinter](/docs/tools/tech-detector.md)** - Bongkar CMS, framework, server, JS lib yang dipakai situs (7500+ fingerprint Wappalyzer)
- **[Screenshotter](/docs/tools/screenshot.md)** - 19 fitur: batch, multi-viewport, element-only, PDF, video, gallery, compare, scheduled
- **[Threat Scanner](/docs/tools/threat-scanner.md)** - Static malware analysis: magic bytes, YARA, archive inspection, PDF/Office/PE analyzer, hash reputation (VT + MalwareBazaar), risk score 0-100

### Audit & Intel
- **[SEO Auditor](/docs/audit/seo.md)** - Audit on-page SEO dengan skor 0-100 dan daftar isu per severity
- **[Broken Link Checker](/docs/audit/broken-links.md)** - BFS crawl situs lalu validasi setiap link (HEAD/GET)
- **[Security Headers Scanner](/docs/audit/security-headers.md)** - Cek HSTS, CSP, XFO, cookie flags dengan grade A-F
- **[SSL Certificate Inspector](/docs/audit/ssl.md)** - Inspeksi sertifikat TLS, expiry countdown, SAN, hostname match
- **[Domain Intel](/docs/intel/domain.md)** - WHOIS, DNS records, dan enumerasi subdomain via crt.sh dalam satu lookup
- **[Wayback Machine Explorer](/docs/intel/wayback.md)** - Telusuri arsip historis web dari Internet Archive + save on-demand
- **[Sitemap Analyzer](/docs/intel/sitemap.md)** - Auto-detect sitemap.xml, parse URL, statistik dan export CSV/JSON

### AI & Intelligence
- **[AI Tagger](/docs/tools/ai-tools.md)** - Auto-tag gambar dengan zero-shot classification (CLIP)
- **[AI Extract (Ollama)](/docs/utilities/ai-extract.md)** - Ekstrak JSON terstruktur dari teks mentah

### Power Utilities
- **[Custom Pipeline](/docs/utilities/pipeline.md)** - Transformasi data dengan Python snippets
- **[Selector Playground](/docs/utilities/playground.md)** - Test CSS/XPath sebelum scraping
- **[Link Bypass](/docs/utilities/bypass.md)** - Resolve redirect + adf.ly/ouo.io
- **[Auth Vault](/docs/utilities/vault.md)** - Simpan cookies/tokens per-domain

### Automation & Management
- **[Scheduled Jobs](/docs/system/scheduled.md)** - Cron-based automation
- **[Diff Detection](/docs/system/diff.md)** - Bandingkan dua run
- **[History](/docs/system/history.md)** - Semua jobs dengan re-run & export
- **[Settings](/docs/system/settings.md)** - 30+ konfigurasi

### Advanced features
- **[Webhooks](/docs/advanced/webhooks.md)** - ![Discord](https://cdn.simpleicons.org/discord/5865F2) Discord / ![Telegram](https://cdn.simpleicons.org/telegram/26A5E4) Telegram / HTTP notifications
- **[Proxy Rotation](/docs/advanced/proxy.md)** - HTTP/HTTPS/SOCKS5
- **[CAPTCHA Solver](/docs/advanced/captcha.md)** - 2Captcha/Anti-Captcha
- **[UA Rotation](/docs/advanced/ua-rotation.md)** - 6 browser profiles
- **[REST API](/docs/advanced/rest-api.md)** - Local data access
- **[Bulk Queue](/docs/advanced/bulk-queue.md)** - Multi-URL batch submit
- **[Playwright Rendering](/docs/advanced/playwright.md)** - Headless Chromium untuk JS-heavy sites
- **[Email Notifications](/docs/advanced/email.md)** - SMTP alternatif webhook
- **[Cluster / Worker Nodes](/docs/advanced/cluster.md)** - Distributed scraping multi-machine

## Cepat mulai

Baru pertama kali? Baca **[Getting Started](/docs/getting-started.md)** dulu untuk panduan instalasi dan orientasi UI.

## Masalah?

Lihat **[FAQ](/docs/faq.md)** untuk solusi masalah umum.

## Tips navigasi

- **Ctrl+/** - Fokus search docs
- **Ctrl+1-8** - Navigasi cepat ke P1-P8 tools
- **Ctrl+K** - Smart URL input (paste URL, auto-detect tool)
- **Ctrl+D** - Toggle dark/light mode

---

> [!IMPORTANT]
> PyScrapr dibangun sebagai personal offline toolkit. Gunakan dengan bijak, hormati Terms of Service situs target, respect rate limits, dan jangan scraping data yang dilindungi tanpa izin.
