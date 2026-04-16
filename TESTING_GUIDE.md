# PyScrapr — Comprehensive Testing Guide

Panduan ini mencakup **semua fitur** PyScrapr untuk testing manual end-to-end.
Jalankan backend + frontend terlebih dahulu:

```bash
# Terminal 1 — Backend
cd backend && python run.py

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Buka: **http://localhost:5173**

---

## 1. Dashboard

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 1.1 | Dashboard loads | Buka `/` | 5 tool cards, recent jobs, disk usage, overall stats |
| 1.2 | Tool cards clickable | Klik card "Image Harvester" | Navigate ke `/harvester` |
| 1.3 | Recent jobs link | Klik "View all" | Navigate ke `/history` |
| 1.4 | Stats accurate | Bandingkan angka di card vs History page | Jumlah match |

---

## 2. Image Harvester (P1)

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 2.1 | Basic harvest | URL: `https://picsum.photos/` → Start | Discovered > 0, Downloaded > 0, progress bar bergerak |
| 2.2 | Filter by min size | Set Min size: 50000 → harvest situs dengan banyak icon kecil | Icon kecil di-skip (Skipped count naik) |
| 2.3 | Live thumbnail | Scroll ke "Live preview" saat harvest jalan | Thumbnail gambar muncul realtime |
| 2.4 | Stop mid-harvest | Start → tunggu 2 detik → Stop | Status "Stopped", download berhenti |
| 2.5 | Download ZIP | Setelah harvest selesai → klik icon download (pojok kanan atas) | File ZIP ter-download |
| 2.6 | CSS background toggle | Enable "Parse CSS background-image" → harvest | Gambar dari CSS `url()` juga ter-extract |
| 2.7 | Deduplicate toggle | Disable deduplicate → harvest situs dengan gambar berulang | Gambar duplikat tidak di-skip |
| 2.8 | File on disk | Cek folder `downloads/<domain>/<date>_images/originals/` | File gambar tersimpan rapi |

---

## 3. URL Mapper (P2)

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 3.1 | Basic crawl | URL: `https://example.com` depth 1 → Start | Crawled 1, External skipped > 0 |
| 3.2 | Deep crawl | URL: `https://httpbin.org/` depth 2, max 20 pages | Multiple pages ter-crawl |
| 3.3 | Tree view | Setelah crawl selesai → lihat Sitemap section | Tree dengan root + children, badge status code |
| 3.4 | Graph view | Toggle ke "Graph" | Cytoscape graph dengan nodes + edges |
| 3.5 | Search filter | Ketik keyword di search box | Tree/graph di-filter, hanya match ditampilkan |
| 3.6 | Pause/Resume | Start crawl besar → Pause → cek Resume button | Resume menunjukkan "(N)" frontier count, klik Resume → crawl lanjut |
| 3.7 | Broken links | Crawl situs yang punya broken links | BrokenLinksPanel muncul dengan status 4xx/5xx merah |
| 3.8 | Export JSON | Klik export icon → JSON | File JSON ter-download dengan semua nodes |
| 3.9 | Export XML sitemap | Klik export icon → XML sitemap | File XML format Google-compatible |
| 3.10 | Export PNG | Switch ke Graph view → klik export icon → PNG | Screenshot graph ter-download |
| 3.11 | Node detail | Klik salah satu node di tree | Drawer muncul di kanan dengan URL + status + title |
| 3.12 | robots.txt respect | Enable "Respect robots.txt" → crawl situs dengan robots.txt ketat | Beberapa URL di-skip (log: "robots denied") |
| 3.13 | Rate limiting | Set Rate /s: 1 → crawl | Crawl berjalan lambat (~1 halaman/detik) |

---

## 4. Site Ripper (P3)

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 4.1 | Basic rip | URL: `https://example.com` depth 0 → Start | 1 page, beberapa assets, progress bar |
| 4.2 | Full rip | URL situs kecil, depth 1, max 5 pages | Multiple pages + assets (CSS/JS/images/fonts) |
| 4.3 | Asset breakdown | Setelah rip selesai | Card per-kind (HTML, CSS, JS, Image, Font) dengan count + bytes |
| 4.4 | HTML rewrite | Buka file HTML hasil rip di browser | Links menunjuk ke file lokal (bukan URL absolute) |
| 4.5 | PDF report | Klik download → PDF report | PDF dengan summary, breakdown by type, broken assets list |
| 4.6 | ZIP download | Klik download → Mirror ZIP | ZIP berisi semua file mirror |
| 4.7 | Live log | Perhatikan Live log saat rip | Setiap page yang di-crawl muncul di log |
| 4.8 | Include external assets | Enable toggle → rip | Asset dari CDN (fonts.googleapis.com, cdnjs) juga ter-download |
| 4.9 | Folder structure | Cek `downloads/<domain>/<date>_mirror/site/` | Folder tree mirror URL path asli |
| 4.10 | Stop mid-rip | Start → Stop setelah beberapa detik | Status stopped, partial files tersimpan |

---

## 5. Media Downloader (P4)

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 5.1 | Probe YouTube | Paste YouTube URL → Probe | Title, uploader, duration, thumbnail muncul di ProbeCard |
| 5.2 | Download video | Start download 480p MP4 | Progress bar, speed, ETA realtime. File MP4 tersimpan |
| 5.3 | Audio only | Quality: Audio only, Format: MP3 → Start | File MP3 ter-extract dari video |
| 5.4 | Playlist probe | Paste YouTube playlist URL → Probe | List entries dengan thumbnail + duration |
| 5.5 | Playlist range | Set Start: 1, End: 3 → Start | Hanya 3 video pertama yang di-download |
| 5.6 | Downloaded files table | Setelah download selesai → scroll ke bawah | Tabel dengan thumbnail, title, filename, duration, size, status |
| 5.7 | Open folder | Setelah download → klik icon folder (pojok kanan atas) | File Explorer terbuka di folder download |
| 5.8 | Bulk mode | Klik "Bulk" → paste 3 URL → Queue | 3 job tercipta di History |
| 5.9 | Embed metadata | Enable toggle → download → cek file properties | Metadata (title, artist) embedded di file |
| 5.10 | Subtitle download | Subtitles: Download → Start | File .srt tersimpan di samping video |
| 5.11 | Cookie auth | Set Cookies: Chrome → download video age-restricted | Video ter-download (jika login di Chrome) |
| 5.12 | Stop download | Start → Stop mid-download | Download berhenti, partial file mungkin tersisa |

---

## 6. AI Tools (P5)

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 6.1 | Select harvester job | Buka AI Tools → dropdown "Select Image Harvester job" | List job harvester yang sudah DONE |
| 6.2 | Custom labels | Hapus default labels → tambah custom: "cat", "dog", "car" | Labels baru tampil sebagai chips |
| 6.3 | Start tagging | Pilih job + labels → Start tagging | Progress bar, per-image progress di log |
| 6.4 | First run model download | Pertama kali: CLIP model (~350 MB) di-download | Loading message muncul, tunggu download |
| 6.5 | Results grid | Setelah selesai → scroll ke Results | Grid gambar dengan top tag + confidence bars per label |
| 6.6 | Tag filter | Klik badge tag (misal "cat") | Hanya gambar dengan top_tag "cat" ditampilkan |
| 6.7 | No harvester jobs | Buka AI Tools tanpa pernah harvest | Pesan "Run Image Harvester first" muncul |

---

## 7. Selector Playground

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 7.1 | Fetch page | URL: `https://example.com` → Fetch | HTML source muncul di panel kiri, badge 200 + size |
| 7.2 | CSS selector | Selector: `h1` mode: CSS → Test | 1 match: tag=h1, text="Example Domain" |
| 7.3 | Multiple matches | Selector: `p` → Test | 2 matches dengan text content |
| 7.4 | XPath selector | Switch ke XPath, selector: `//a` → Test | Link elements matched |
| 7.5 | Complex CSS | Selector: `div > p:first-child` → Test | Hanya paragraph pertama |
| 7.6 | Attribute display | Match element dengan attributes (misal `img`) | Kolom Attributes menampilkan src, alt, dll |
| 7.7 | Invalid selector | Selector: `???invalid` → Test | Error notification "Invalid CSS selector" |
| 7.8 | Use in Harvester | Klik "Use in Harvester" setelah match | Navigate ke Harvester page |
| 7.9 | Large page | Fetch halaman besar (Wikipedia article) → test selectors | Source ditampilkan (truncated 50KB), selectors jalan |

---

## 8. Link Bypass

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 8.1 | Direct redirect | URL: `https://httpbin.org/redirect/3` → Resolve | Final: `https://httpbin.org/get`, chain: 4, method: redirect |
| 8.2 | Shortened URL | URL: bit.ly link (jika punya) → Resolve | Final URL revealed, method: redirect |
| 8.3 | Ad-gateway (adf.ly) | URL: adf.ly link → Resolve | Final URL extracted, method: adf.ly |
| 8.4 | Failed bypass | URL: linkvertise link (heavy JS) → Resolve | Method: failed, error message tentang Playwright |
| 8.5 | Batch mode | Paste 5 URL (mix redirect + gateway) → Resolve all | Tabel dengan semua 5 results, badge method per-row |
| 8.6 | Copy final URL | Klik "Copy" pada result | URL ter-copy ke clipboard |
| 8.7 | No redirect | URL: `https://example.com` (no redirect) → Resolve | Final = Original, method: failed (no redirect detected) |

---

## 9. Auth Vault

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 9.1 | Add profile manual | Add profile → domain: test.com, cookies: `{"session":"abc"}` | Profile muncul di tabel |
| 9.2 | Edit profile | Add profile dengan domain yang sama → beda cookies | Cookies ter-update (upsert) |
| 9.3 | Delete profile | Klik trash icon pada profile | Profile hilang dari tabel |
| 9.4 | Import from Chrome | Import from browser → Chrome → domain: (kosong) | Cookies imported, count domains shown |
| 9.5 | Import filtered | Import → Chrome → domain: "github.com" | Hanya cookies github.com yang imported |
| 9.6 | JSON editor | Buka Add profile → edit cookies JSON | JSON editor dengan format-on-blur |
| 9.7 | Persistence | Tambah profile → restart backend → buka Vault | Profile masih ada (tersimpan di data/auth_vault.json) |

---

## 10. Scheduled Jobs

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 10.1 | Create schedule | New schedule → tool: harvester, URL: example.com, cron: `*/5 * * * *` | Schedule muncul di tabel |
| 10.2 | Cron display | Lihat kolom Cron | Badge monospace dengan expression |
| 10.3 | Disable toggle | Toggle enabled OFF | Schedule paused |
| 10.4 | Delete schedule | Klik trash icon | Schedule hilang |
| 10.5 | Schedule fires | Buat schedule `* * * * *` (setiap menit) → tunggu 1 menit | Job baru muncul di History (auto-created oleh scheduler) |
| 10.6 | Run count | Setelah schedule fires | Kolom "Runs" bertambah, "Last run" ter-update |

---

## 11. Diff / Change Detection

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 11.1 | Compare two jobs | Pilih Job A dan Job B (sama-sama harvester dari URL yang sama) → Compare | New/removed/unchanged counts ditampilkan |
| 11.2 | No changes | Compare job dengan dirinya sendiri (atau 2 identical runs) | "No changes detected" message |
| 11.3 | New items | Compare old run vs new run (situs berubah) | Panel hijau "New items" dengan URL list |
| 11.4 | Removed items | Compare new run vs old run | Panel merah "Removed items" |
| 11.5 | Status changed (mapper) | Compare 2 mapper jobs | Panel kuning "Status changed" (misal 200 → 404) |

---

## 12. History Page

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 12.1 | All types visible | Buka History | Semua job type (harvester, mapper, ripper, media, ai) terlihat |
| 12.2 | Status badges | Cek kolom Status | done=hijau, error=merah, stopped=kuning, running=cyan |
| 12.3 | Re-run job | Klik icon refresh pada job DONE | Notifikasi "Re-run started", job baru muncul di tabel |
| 12.4 | Export CSV | Klik icon download → CSV pada job DONE | File CSV ter-download |
| 12.5 | Export JSON | Klik icon download → JSON | File JSON ter-download |
| 12.6 | Export Excel | Klik icon download → Excel | File .xlsx ter-download, bisa dibuka di Excel |
| 12.7 | Auto refresh | Start job baru dari tab lain → kembali ke History | Job baru muncul otomatis (refresh 3s) |
| 12.8 | Empty state | Hapus semua jobs dari DB → buka History | "No jobs yet" + "Start your first harvest" button |

---

## 13. Settings Page

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 13.1 | Load settings | Buka Settings | 4 card settings (Scraping, Harvester, Media, Ripper) + Disk + About + Dependencies |
| 13.2 | Change concurrency | Ubah Default concurrency: 12 → Save | Notifikasi "Settings updated", value tersimpan |
| 13.3 | Verify persistence | Reload halaman | Value masih 12 (bukan default 8) |
| 13.4 | Reset defaults | Klik "Reset defaults" | Semua value kembali ke default, notifikasi "Reset" |
| 13.5 | Disk usage | Cek section Disk usage | Downloads size + DB size + free disk space |
| 13.6 | yt-dlp version | Scroll ke Dependencies | yt-dlp version ditampilkan + badge "up to date" atau "update available" |
| 13.7 | yt-dlp update | Klik "Update" / "Reinstall" | Loading → notifikasi sukses/gagal, versi ter-update |
| 13.8 | browser-cookie3 version | Cek section Dependencies | Version + latest displayed |
| 13.9 | Check updates | Klik "Check updates" | Refresh version info dari PyPI |
| 13.10 | Proxy settings | Isi proxy_list + proxy_mode di settings (via API) | Proxy tersimpan di data/settings.json |
| 13.11 | CAPTCHA settings | Isi captcha_provider + captcha_api_key | Tersimpan, balance bisa dicek via `/api/vault/captcha/balance` |
| 13.12 | Save disabled | Tanpa mengubah apapun | Save button disabled (grayed out) |
| 13.13 | Dirty indicator | Ubah satu field | Save button enabled (cyan) |

---

## 14. Smart URL (Header)

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 14.1 | YouTube URL | Paste YouTube URL di header → Enter | Auto-navigate ke Media Downloader |
| 14.2 | Instagram URL | Paste Instagram URL → Enter | Auto-navigate ke Media Downloader |
| 14.3 | Regular URL | Paste `https://example.com` → Enter | Dropdown menu: Harvester / Mapper / Ripper / Media |
| 14.4 | Select tool | Pilih "Image Harvester" dari dropdown | Navigate ke Harvester dengan URL pre-filled |

---

## 15. Theme Toggle

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 15.1 | Dark → Light | Klik icon sun/moon di header | Semua halaman berubah ke light mode |
| 15.2 | Light → Dark | Klik lagi | Kembali ke dark mode |
| 15.3 | No visual artifacts | Di light mode, cek semua pages | Tidak ada background gelap tertinggal (belang-belang) |
| 15.4 | Persistence | Toggle ke light → reload page | Tetap light mode (Mantine menyimpan di localStorage) |

---

## 16. System Status Bar (Footer)

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 16.1 | CPU display | Lihat footer kiri | CPU % + ring progress, warna adaptif (hijau/kuning/merah) |
| 16.2 | RAM display | Lihat footer | RAM % + ring progress + tooltip "X.XX / Y.YY GB" |
| 16.3 | Network speed | Lihat footer tengah | Download speed ↓ + Upload speed ↑ (B/s, KB/s, MB/s) |
| 16.4 | Traffic counter | Lihat footer kanan | Total download + upload since app start |
| 16.5 | Auto refresh | Tunggu beberapa detik | Angka berubah (polling 2s) |
| 16.6 | Under load | Start download besar → lihat footer | Speed naik, CPU mungkin naik |

---

## 17. Notification Sound

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 17.1 | Done beep | Start harvest → tunggu selesai | Bunyi "ding-dong" saat notifikasi "Done" muncul |
| 17.2 | Error beep | Trigger error (URL invalid + start) | Bunyi buzz rendah |
| 17.3 | Disable sound | Settings → Notification sound: OFF → Save → trigger done | Tidak ada bunyi |

---

## 18. Bulk URL Queue

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 18.1 | Open modal | Media Downloader → klik "Bulk" | Modal muncul dengan textarea + tool selector |
| 18.2 | URL count | Paste 5 URL (satu per baris) | "5 URLs detected" counter |
| 18.3 | Queue submit | Klik "Queue 5 jobs" | Notifikasi "5 job(s) queued", modal tutup |
| 18.4 | Jobs created | Buka History | 5 job baru dengan status pending/running/done |
| 18.5 | Invalid URLs filtered | Campur URL valid + teks random | Hanya URL valid yang dihitung |

---

## 19. Data API (REST)

Test via browser atau curl:

| # | Test case | Command | Expected |
|---|-----------|---------|----------|
| 19.1 | Basic query | `curl http://localhost:8000/api/data/{job_id}` | JSON response with data array, total, pagination |
| 19.2 | Limit + offset | `curl "...?limit=5&offset=10"` | 5 items starting from index 10 |
| 19.3 | Filter | `curl "...?filter=kind:image"` | Only image assets returned |
| 19.4 | Sort | `curl "...?sort=-size_bytes"` | Sorted by size descending |
| 19.5 | Unknown job | `curl .../api/data/nonexistent` | 404 "Job not found" |

---

## 20. OpenAPI Docs

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 20.1 | Swagger UI | Buka `http://localhost:8000/docs` | Interactive API documentation, semua 64+ endpoints |
| 20.2 | Try it out | Klik endpoint → "Try it out" → Execute | Response ditampilkan |
| 20.3 | ReDoc | Buka `http://localhost:8000/redoc` | Alternative API docs view |

---

## 21. Orphan Job Recovery

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 21.1 | Kill mid-job | Start harvest → kill backend (Ctrl+C) → restart | Job yang tadinya RUNNING berubah ke STOPPED + "Interrupted by server restart" |
| 21.2 | Log message | Cek backend log saat startup | "Recovered X orphaned job(s) on startup" |

---

## 22. Error Handling

| # | Test case | Steps | Expected |
|---|-----------|-------|----------|
| 22.1 | Network timeout | Disconnect internet → start harvest | Error notification user-friendly (bukan stack trace) |
| 22.2 | Invalid URL | Input `not-a-url` → Start | Error "Invalid URL" |
| 22.3 | Server down | Stop backend → klik Start di frontend | Error notification "Failed to fetch" |
| 22.4 | Retry logic | Start harvest pada situs yang kadang timeout | Live log menunjukkan "Retry 1/3..." messages |

---

## Quick Checklist — Smoke Test (5 menit)

Untuk verifikasi cepat semua major features:

- [ ] Buka Dashboard — 5 tool cards terlihat
- [ ] Start harvest `https://picsum.photos/` — images ter-download
- [ ] Start mapper `https://example.com` depth 1 — tree muncul
- [ ] Start ripper `https://example.com` depth 0 — HTML + PDF tersimpan
- [ ] Probe YouTube URL — title + duration muncul
- [ ] Buka Playground → fetch `https://example.com` → test `h1` selector — 1 match
- [ ] Bypass `https://httpbin.org/redirect/2` — final URL resolved
- [ ] Buka Auth Vault → Add profile test.com — tersimpan
- [ ] Buka History — semua job terlihat, export CSV works
- [ ] Buka Settings — ubah concurrency → Save → reload → value persistent
- [ ] Toggle light/dark mode — no visual artifacts
- [ ] Cek footer — CPU, RAM, network speed updating
