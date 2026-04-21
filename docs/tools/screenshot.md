# Screenshotter

> Screenshotter lengkap untuk PyScrapr: 19 fitur capture visual situs web dalam satu tool terintegrasi. Batch multi-URL, multi-viewport per run, element-only capture, multi-element mode, PDF export, JPEG/WebP compression, watermark, device scale Retina, dark/light color scheme, auth vault integration, scroll-through video recording (MP4/WebM/GIF), gallery browser dengan thumbnail grid, pixel-diff compare mode, ZIP export, dan scheduled captures dengan auto-change-detection. Semuanya offline, via headless Chromium Playwright, tanpa dep ke service pihak ketiga.

## Apa itu Screenshotter

Screenshotter adalah evolusi dari generasi sebelumnya. Kalau dulu tool ini hanya mampu capture PNG satu URL dengan viewport tunggal, versi sekarang menaikkan kelas jadi tier P7 lengkap, dengan 19 fitur yang dikurasi untuk menutup hampir semua kebutuhan screenshot automation yang realistis di dunia pekerjaan web developer, QA engineer, content creator, dan riset kompetitif. Anda tidak perlu lagi berpindah-pindah antara tool online, browser extension, dan script Puppeteer sendiri. Semua skenario, dari quick one-off screenshot sampai monitoring visual regression terjadwal, sudah tersedia di satu halaman UI yang terorganisir dalam 5 tab.

Tier pertama (Tier A, Core) fokus pada kemampuan capture fundamental: batch mode untuk proses banyak URL sekaligus, multi-viewport untuk capture 1 URL di beberapa ukuran layar sekaligus tanpa re-run manual, format output beragam (PNG lossless, JPEG dengan quality slider, WebP modern compact, PDF untuk dokumentasi legal), element-only screenshot via CSS selector untuk crop bagian spesifik halaman, multi-element mode yang mem-break setiap match selector jadi file terpisah, hide-elements untuk menghilangkan cookie banner / chat widget sebelum capture, wait-for-selector untuk SPA yang butuh waktu render, scroll-through trigger untuk lazy-load content, dan custom CSS injection untuk override visual target sebelum capture.

Tier kedua (Tier B, UX) menaikkan kualitas pengalaman user: integrasi dengan Auth Vault PyScrapr untuk capture halaman yang butuh session login (dashboard private, member area, admin panel), watermark text dengan pilihan posisi dan opacity untuk kebutuhan dokumentasi pihak ketiga, device scale factor 1x / 2x / 3x untuk hasil sharp di Retina display, dan color scheme mode Light / Dark / Both, di mana opsi Both akan capture 2 versi sekaligus (light + dark) dari URL yang sama dalam satu run.

Tier ketiga (Tier C, Integration) menghubungkan Screenshotter dengan ekosistem PyScrapr yang lebih luas: Gallery page menampilkan grid thumbnail semua captures, searchable by URL, paginated, dengan bulk select untuk operasi ZIP export atau delete massal. Compare mode memungkinkan Anda pilih 2 file dari gallery lalu render side-by-side atau overlay pixel-diff, dengan metric `diff_ratio` yang memberi angka konkrit seberapa besar perbedaan visual dua snapshot. Scheduled captures terintegrasi dengan APScheduler, otomatis compare hasil terbaru dengan snapshot sebelumnya untuk early-warning kalau ada perubahan layout signifikan. Tier keempat (Tier D, Advanced) menambahkan video recording scroll-through (output WebM native Playwright, dengan opsi convert ke MP4 via ffmpeg / libx264 atau GIF fps=15), dan delete capture individual atau bulk dari gallery.

## Setup

Screenshotter butuh Playwright + Chromium binary terpasang di backend. Kalau Anda sudah pernah pakai tool lain yang mengandalkan Playwright (Tech Fingerprinter mode render, Site Ripper mode JS, atau SEO Auditor mode browser), langkah ini sudah selesai.

Kalau belum, jalankan sekali di PowerShell (di dalam venv backend PyScrapr):

```powershell
pip install playwright
python -m playwright install chromium
```

Untuk video recording, Anda juga butuh ffmpeg. PyScrapr sudah bundle `imageio-ffmpeg` di `requirements.txt`, yang membawa ffmpeg binary statis cross-platform. Jadi Anda tidak perlu install ffmpeg sistem terpisah. Kalau entah kenapa library ini tidak terpasang, install manual:

```powershell
pip install imageio-ffmpeg
```

Restart backend setelah instalasi. Tool sepenuhnya offline, tidak ada call ke service pihak ketiga seperti screenshotmachine.com, urlbox, atau apiflash.

> [!NOTE]
> Folder `data/screenshots/`, `data/screenshots/videos/`, dan `data/screenshots/comparisons/` sudah masuk `.gitignore`. File hasil capture, video, dan comparison image tidak akan ikut ter-commit ke repository. Cocok untuk tool pribadi offline.

## Mode Single (tab Single)

Mode Single adalah entry point default saat Anda buka halaman `/screenshot`. Cocok untuk capture satu URL dengan setting yang Anda custom penuh. Semua 19 fitur bisa diakses di tab ini.

### Step-by-step

1. Buka PyScrapr di browser, navigasi ke menu **Screenshot** di sidebar, shortcut `Ctrl+7`. Halaman terbuka dengan tab Single aktif.

2. Paste URL target di field `Target URL`. Contoh: `https://github.com/anthropics`, `https://tokopedia.com`, `https://figma.com`. Skema `https://` atau `http://` wajib ada.

3. Pilih satu atau lebih viewport di multi-select `Viewports`. Kalau Anda pilih 3 preset (Desktop, Tablet, Mobile), satu run akan menghasilkan 3 file PNG, satu per viewport.

4. Atur opsi di 4 accordion section di bawah sesuai kebutuhan. Accordion defaultnya collapsed, expand section yang relevan saja.

5. Klik tombol `Capture`. Backend akan spawn Chromium headless, iterate setiap viewport, apply setting, capture output, dan simpan ke `data/screenshots/screenshot_<job_id>/`.

6. Hasil muncul di area bawah sebagai grid thumbnail. Setiap thumbnail klikable untuk preview besar, punya tombol download per-file, dan stats (dimensi, ukuran file, viewport, format).

### Accordion Format & Output

Section ini menentukan format file hasil dan properti visual dasar.

**output_format** - Enum `"png"` | `"jpeg"` | `"webp"` | `"pdf"`. Default `"png"`.
- PNG untuk kualitas lossless dan support transparency. Sweet spot untuk dokumentasi internal.
- JPEG untuk file size kecil, cocok untuk batch capture banyak URL. Slider `jpeg_quality` 1-100 muncul saat Anda pilih JPEG.
- WebP (via Pillow converter) untuk kompresi modern, file 20-30% lebih kecil dari JPEG dengan kualitas sama.
- PDF (via `page.pdf()` Playwright) untuk dokumentasi legal / arsip yang butuh format paginated.

**jpeg_quality** - Integer 1-100, default 85. Hanya relevan saat `output_format = "jpeg"`. Nilai 85 adalah sweet spot antara kualitas dan ukuran file.

**full_page** - Boolean, default true. Kalau aktif, tool auto-scroll sampai dasar halaman lalu capture seluruhnya. Matikan kalau cuma butuh above-the-fold.

**device_scale_factor** - Integer 1 / 2 / 3, default 1. Set 2 untuk hasil Retina (2x pixel density), 3 untuk Ultra HD. File size naik ~4x dan ~9x dibanding 1x.

**color_scheme** - Enum `"light"` | `"dark"` | `"both"`, default `"light"`.
- Light: capture tema terang.
- Dark: set `prefers-color-scheme: dark`, situs yang support akan otomatis switch.
- Both: tool capture 2 versi dalam satu run (light + dark). Kalau Anda kombinasi dengan 3 viewport, hasil jadi 6 file (3 viewport x 2 scheme).

### Accordion Element & Hide

Section ini untuk crop atau memanipulasi konten sebelum capture.

**element_selector** - String CSS selector, default kosong. Kalau diisi, tool akan capture hanya element yang match, bukan full page. Contoh: `".hero-section"`, `"#pricing-table"`, `"main article"`.

**multi_element_mode** - Boolean, default false. Hanya aktif kalau `element_selector` diisi. Kalau true, setiap match selector di-break jadi file terpisah. Misal selector `.product-card` match 12 element, hasilnya 12 file PNG (`_01.png` sampai `_12.png`).

**hide_selectors** - Array of string CSS selector, default kosong. Tool akan set `display: none !important` ke semua element yang match sebelum capture. Contoh: `[".cookie-banner", "#intercom-launcher", ".newsletter-popup"]`.

Contoh realistic: capture landing page produk tanpa cookie banner GDPR dan tanpa chat widget Intercom.

```json
{
  "url": "https://example.com",
  "hide_selectors": [".cc-window", "#intercom-container", ".notification-bar"]
}
```

### Accordion Wait & Interaction

Section ini mengontrol timing dan interaksi pre-capture.

**wait_until** - Enum `"load"` | `"domcontentloaded"` | `"networkidle"`, default `"networkidle"`.

**wait_for_selector** - String CSS selector, default kosong. Kalau diisi, tool akan tunggu element ini muncul di DOM sebelum capture. Berguna untuk SPA yang butuh waktu hydrate. Contoh: `"[data-testid=dashboard-loaded]"`.

**scroll_through** - Boolean, default false. Kalau aktif, tool akan scroll halaman dari atas ke bawah dalam beberapa step (trigger lazy-load image, infinite scroll content) sebelum capture. Durasi scroll kira-kira 3-5 detik, menambah total time tapi hasil lebih lengkap.

**timeout_ms** - Integer milliseconds, default 30000. Naikkan ke 60000-90000 untuk situs lambat.

### Accordion Advanced

Section ini untuk customization tingkat lanjut.

**custom_css** - String CSS raw, default kosong. Di-inject via `page.add_style_tag({content: ...})` sebelum capture. Contoh: hide floating action button yang tidak bisa ditarget lewat `hide_selectors` biasa, atau override warna background untuk konsistensi report.

```css
body { background: #ffffff !important; }
.fab-button { display: none !important; }
.debug-overlay { visibility: hidden; }
```

**watermark_text** - String, default kosong. Kalau diisi, text di-burn ke output image sebagai overlay semi-transparan.

**watermark_position** - Enum `"top-left"` | `"top-right"` | `"bottom-left"` | `"bottom-right"` | `"center"`, default `"bottom-right"`.

**watermark_opacity** - Float 0.0 - 1.0, default 0.5.

**use_auth_vault** - Boolean, default false. Kalau aktif, tool akan lookup cookies dari Auth Vault untuk domain target, inject ke browser context sebelum navigate. Berguna untuk capture halaman yang butuh login.

> [!TIP]
> Kombinasikan `use_auth_vault` + `wait_for_selector` saat capture dashboard internal. Login page kadang redirect beberapa kali, `wait_for_selector` memastikan dashboard final sudah muncul sebelum tool capture.

## Mode Batch (tab Batch)

Mode Batch memungkinkan Anda capture banyak URL sekaligus dengan setting yang sama. Cocok untuk dokumentasi multi-halaman, audit portofolio, atau bulk monitoring kompetitor.

### Cara pakai

1. Klik tab **Batch** di halaman Screenshot.

2. Paste daftar URL di textarea `Target URLs`, satu URL per baris. Contoh 5 URL kompetitor e-commerce:

```
https://tokopedia.com
https://shopee.co.id
https://lazada.co.id
https://bukalapak.com
https://blibli.com
```

3. Atur viewport dan semua option yang sama seperti mode Single. Setting akan di-apply seragam ke semua URL.

4. Klik `Start Batch`. Tool akan proses URL satu per satu dengan concurrency limit 3 parallel (biar tidak overload mesin Anda dan tidak kena rate-limit dari multiple target).

5. Progress bar menunjukkan status per-URL. Hasil muncul bertahap di bawah, thumbnail baru appear saat URL selesai.

### Concurrency & rate limit

Backend menggunakan asyncio semaphore dengan batas 3 concurrent capture. Angka ini dipilih sebagai kompromi: cukup cepat untuk batch 10-20 URL (selesai dalam 30-60 detik), tidak overload RAM mesin desktop biasa (3 instance Chromium eat ~1.5 GB RAM), dan cukup polite untuk rate-limit target. Kalau Anda batch ke domain yang sama (misal 10 URL dari `shopee.co.id`), tool otomatis throttle ke 1 concurrent per-domain untuk mencegah kena WAF / rate-limit.

### Use cases batch

- **Screenshot kompetitor page untuk pitch deck.** 10 kompetitor, 3 viewport masing-masing, hasil 30 file siap paste ke slide.
- **Dokumentasi produk multi-halaman sekaligus.** Landing page, pricing, about, contact, blog index, semuanya capture sekali dengan watermark company logo.
- **Bulk portfolio archive.** 30 situs klien lama, capture homepage di desktop + mobile, untuk showcase agency.
- **QA pra-deploy checklist.** Staging site 15 halaman, capture semuanya di multi-viewport, compare lawan production capture yang sama.

## Gallery (tab Gallery)

Gallery adalah browser terpusat untuk semua captures yang pernah Anda ambil. Data diambil dari endpoint `GET /api/screenshot/gallery?limit=&offset=&search=`, jadi Gallery selalu up-to-date dengan hasil terbaru.

### Browse past captures

Tab Gallery menampilkan grid thumbnail responsif. Default 24 items per halaman, Anda bisa scroll atau pakai pagination button di bawah. Setiap thumbnail menampilkan:
- Preview gambar (scaled down)
- URL asli (truncated)
- Tanggal capture
- Viewport yang dipakai
- Format output (PNG / JPEG / WebP / PDF badge)
- Checkbox untuk bulk select

Klik thumbnail untuk buka modal preview besar dengan metadata lengkap (dimensi asli, file size, job_id, semua option yang di-apply saat capture).

### Filter & search

Search bar di atas grid memfilter berdasarkan URL. Query `tokopedia` akan tampilkan semua capture dari domain yang mengandung substring tersebut. Search case-insensitive, partial match. Untuk filter advanced (by format, by date range, by viewport), pakai dropdown filter yang ada di sebelah search bar.

### Bulk actions

Setelah Anda tick checkbox pada beberapa thumbnail (atau pakai tombol `Select all visible`), dua action muncul di toolbar:

**ZIP export.** Tool akan bundle semua file terpilih ke satu archive `.zip` dengan struktur folder per-job-id, lalu trigger download. Endpoint: `POST /api/screenshot/export/zip` dengan body array file IDs. Cocok untuk kirim hasil ke klien atau arsip ke storage eksternal.

**Delete.** Hapus file terpilih dari disk + row di database. Endpoint: `DELETE /api/screenshot/gallery/{job_id}`. Konfirmasi wajib untuk mencegah accident delete.

### Compare 2 screenshots

Fitur unik Gallery: pilih exactly 2 thumbnail (tick 2 checkbox), tombol `Compare` aktif. Klik untuk buka modal comparison dengan 2 mode.

**Side-by-side.** Dua image ditampilkan berdampingan kiri-kanan. Berguna untuk visual inspection manual, misal "apakah redesign terbaru lebih clean dari versi lama?".

**Overlay pixel diff.** Tool hitung pixel-by-pixel difference antara 2 image (setelah resize ke dimensi yang sama kalau beda), highlight pixel yang berbeda dengan warna merah. Hasil render sebagai image baru di `data/screenshots/comparisons/<comparison_id>.png`, dilengkapi metric `diff_ratio`.

`diff_ratio` adalah angka float 0.0 - 1.0 yang menunjukkan proporsi pixel yang berbeda:
- 0.000 - 0.005 (< 0.5%): identik atau perbedaan trivial (anti-aliasing font rendering, timestamp dinamis). Safe untuk di-ignore.
- 0.005 - 0.05: perubahan minor, kemungkinan ada text update, icon swap, atau padding adjustment.
- 0.05 - 0.20: perubahan signifikan, ada component baru, layout shift, atau theme change.
- > 0.20: perubahan major, kemungkinan redesign besar atau halaman error.

> [!IMPORTANT]
> `diff_ratio` sensitive terhadap dimensi. Compare 2 capture dari viewport berbeda akan selalu tinggi karena content reflow. Pastikan 2 file yang Anda compare punya viewport + color_scheme yang sama untuk apple-to-apple comparison.

## Video Recording (tab Video)

Tab Video merekam scroll-through video situs, output WebM, MP4, atau GIF. Cocok untuk demo produk, showcase responsive, atau dokumentasi animasi UI.

### Scroll-through video

1. Klik tab **Video**.
2. Paste URL target.
3. Pilih viewport (sama seperti Single mode).
4. Atur `scroll_duration_ms`, default 5000 (5 detik). Ini total durasi video, tool akan auto-scroll dari top ke bottom halaman dalam waktu segini.
5. Atur `fps`, default 30. Frame per second, makin tinggi makin smooth tapi file makin besar.
6. Pilih `output_format`: `"webm"` / `"mp4"` / `"gif"`.
7. Aktifkan `use_auth_vault` kalau target butuh login.
8. Klik `Record`. Tool spawn Chromium, navigate, mulai record video native Playwright (format WebM default), scroll perlahan sesuai durasi, stop recording, lalu convert kalau format target bukan WebM.

### Format selection

**WebM.** Format native Playwright, tidak butuh post-processing. Kualitas baik, file size kecil, tapi support browser terbatas (Chrome/Firefox native, Safari butuh fallback). Cocok untuk embed di docs internal atau upload ke service yang sudah support WebM.

**MP4.** Convert dari WebM via ffmpeg libx264. Universal support (semua browser, semua video player, semua chat app bisa play), tapi file size lebih besar dari WebM sekitar 20-40%. Cocok untuk share ke klien via email, embed di LinkedIn post, atau arsip long-term.

**GIF.** Convert dari WebM via ffmpeg, default fps 15 (GIF tidak bisa handle 30fps smooth tanpa bloat). File size paling besar dibanding WebM/MP4 untuk durasi yang sama, tapi universal playable (termasuk di platform yang tidak support video embed, misal GitHub comment atau beberapa forum legacy). Cocok untuk quick demo yang butuh auto-play loop tanpa user action.

### Tips fps vs file size tradeoff

- fps 60 + MP4 + durasi 10 detik = smooth cinematic, file ~15-25 MB.
- fps 30 + MP4 + durasi 10 detik = smooth default, file ~6-10 MB. Sweet spot untuk demo produk.
- fps 15 + MP4 + durasi 10 detik = jerky tapi tetap readable, file ~3-5 MB. Cocok untuk share lewat email dengan quota terbatas.
- fps 15 + GIF + durasi 5 detik = GIF optimal, file ~5-15 MB tergantung kompleksitas visual.

> [!WARNING]
> Video recording berat RAM dan CPU. Satu session bisa eat 500 MB - 1 GB RAM selama recording aktif. Jangan jalankan batch video recording bareng tool lain yang berat. Tutup aplikasi lain saat record durasi > 30 detik.

## Scheduled Captures (tab Schedule)

Tab Schedule adalah deep-link ke halaman `/scheduled` PyScrapr dengan template `screenshot` pre-filled. Gunanya: jadwalkan capture recurring untuk monitoring visual otomatis.

### Integrasi APScheduler

PyScrapr pakai APScheduler sebagai job scheduler backend. Anda set cron expression standar (atau pilih preset: hourly, daily, weekly), tool akan trigger capture di interval tersebut. Tool name yang didaftarkan: `screenshot`. Semua option yang Anda set di tab Schedule (URL, viewport, format, hide_selectors, dll.) disimpan sebagai payload scheduled job, dan di-apply tiap kali job fire.

### Auto-compare dengan snapshot sebelumnya

Fitur pembeda scheduled screenshot: setelah setiap capture, tool otomatis bandingkan hasil terbaru dengan capture sebelumnya dari URL + viewport + color_scheme yang sama. `diff_ratio` dihitung dan disimpan di `ScheduledJobRun.stats`. Kalau Anda set threshold (misal `diff_threshold: 0.05`), run dengan diff > threshold akan trigger webhook / email notification (kalau di-setup di Settings).

### Use case monitoring visual harian

- **E-commerce product page monitoring.** Setiap pagi jam 8, capture halaman produk flagship kompetitor. Kalau ada perubahan harga, label promo baru, atau banner flash sale, `diff_ratio` lompat, Anda dapat notif Discord.
- **Homepage corporate perusahaan target.** Weekly capture, arsip historis gratis, tahu kapan mereka ganti hero message atau launch campaign baru.
- **Status page service publik.** Setiap jam, capture status.github.com / status.openai.com dalam desktop viewport, archive + diff. Kalau ada incident banner muncul, Anda tahu sebelum manually cek.
- **Situs pemerintah / regulasi.** Monitor halaman tertentu yang jarang update. Kalau ada perubahan, itu biasanya signifikan (kebijakan baru, form baru, tender baru).

## Contoh kasus pakai

### 1. Kompetitor tracking e-commerce

Anda pelaku bisnis fashion online, ingin monitor 5 kompetitor utama. Setup: batch mode, 5 URL homepage, multi-viewport (Desktop + Mobile), format JPEG quality 85 untuk hemat disk. Schedule untuk run daily jam 9 pagi. Set `diff_threshold: 0.05`. Kalau ada kompetitor ubah hero banner atau tambah promo besar, notif masuk ke Discord tim Anda dalam 15 menit setelah mereka deploy.

### 2. QA visual regression pre-deploy

Tim Anda akan deploy perubahan CSS global di web app utama. 30 menit sebelum deploy, batch capture 20 halaman production di viewport Desktop + Tablet + Mobile, simpan ke folder `pre_deploy_20260421`. Setelah deploy, re-capture 20 halaman sama. Di Gallery, bulk compare pair-by-pair. Threshold 0.02 sebagai acceptable (anti-aliasing noise), > 0.02 butuh review manual. Proses yang biasanya manual per halaman selesai dalam 10 menit.

### 3. Dokumentasi produk responsive (desktop + mobile + tablet sekali klik)

Anda writing documentation untuk feature baru SaaS produk sendiri. Capture UI di 3 breakpoint sekaligus pakai multi-viewport (Desktop 1920, Tablet 768, Mobile 390), format PNG, device_scale_factor 2 untuk Retina sharp. Satu run, 3 file siap embed ke docs markdown. Dalam 1 jam Anda bisa selesaikan dokumentasi 20 page feature yang tadinya butuh 1 hari.

### 4. Arsip situs bersejarah

Ada situs komunitas yang sudah 10 tahun ada dan Anda khawatir shutdown. Scheduled weekly capture full-page PNG (tanpa compression, maximum fidelity), device_scale 2x, color_scheme both (light + dark), kombinasi dengan scroll_through untuk trigger lazy-load image. Setiap minggu Anda punya 2 arsip (light + dark) dari situs itu, masing-masing PDF juga untuk format alternatif. Kalau suatu saat situs hilang, Anda punya visual record 5 tahun ke belakang.

### 5. Screenshot halaman login dengan Auth Vault

Klien minta screenshot dashboard admin mereka untuk dokumentasi onboarding. Anda pernah diberikan akses. Setup: login manual sekali di browser biasa, export cookies, import ke Auth Vault PyScrapr untuk domain target. Lalu di Screenshotter: URL ke dashboard path, `use_auth_vault: true`, `wait_for_selector: "[data-testid=dashboard-ready]"` untuk memastikan dashboard final load. Hasil capture sudah dalam state logged-in, bersih dari halaman login redirect.

### 6. Monitoring halaman produk e-commerce (scheduled + compare)

Anda vendor marketplace, ingin monitor apakah produk Anda masih muncul di halaman kategori unggulan marketplace X. Scheduled job daily, URL halaman kategori, multi-viewport Desktop + Mobile, hide_selectors untuk banner iklan rotating yang selalu berubah (biar tidak false-positive diff). Threshold `diff_ratio 0.10`. Kalau marketplace mengubah algoritma ranking dan produk Anda hilang dari atas, `diff_ratio` tinggi, notif masuk, Anda tahu harus boost iklan atau intervention lain.

## Pengaturan detail

Semua field yang bisa di-pass ke endpoint `POST /api/screenshot/capture` dan `POST /api/screenshot/batch`:

| Field | Tipe | Default | Valid range / enum |
|-------|------|---------|---------------------|
| `url` | string | required | URL valid dengan scheme http(s) |
| `urls` | array of string | required di batch | maksimal 100 URL per batch |
| `viewports` | array of string | `["desktop"]` | `desktop`, `desktop_hd`, `laptop`, `tablet`, `mobile`, `mobile_sm`, `custom` |
| `custom_width` | integer | null | 320 - 3840 px |
| `custom_height` | integer | null | 240 - 2160 px |
| `output_format` | string | `"png"` | `png`, `jpeg`, `webp`, `pdf` |
| `jpeg_quality` | integer | 85 | 1 - 100 |
| `full_page` | boolean | true | true / false |
| `device_scale_factor` | integer | 1 | 1, 2, 3 |
| `color_scheme` | string | `"light"` | `light`, `dark`, `both` |
| `element_selector` | string | `""` | valid CSS selector atau kosong |
| `multi_element_mode` | boolean | false | true / false |
| `hide_selectors` | array of string | `[]` | list CSS selector valid |
| `wait_until` | string | `"networkidle"` | `load`, `domcontentloaded`, `networkidle` |
| `wait_for_selector` | string | `""` | CSS selector valid atau kosong |
| `scroll_through` | boolean | false | true / false |
| `timeout_ms` | integer | 30000 | 5000 - 180000 |
| `custom_css` | string | `""` | raw CSS |
| `watermark_text` | string | `""` | max 120 char |
| `watermark_position` | string | `"bottom-right"` | `top-left`, `top-right`, `bottom-left`, `bottom-right`, `center` |
| `watermark_opacity` | float | 0.5 | 0.0 - 1.0 |
| `use_auth_vault` | boolean | false | true / false |

Untuk video endpoint `POST /api/screenshot/video`, field tambahan:

| Field | Tipe | Default | Valid range |
|-------|------|---------|-------------|
| `scroll_duration_ms` | integer | 5000 | 1000 - 60000 |
| `fps` | integer | 30 | 10 - 60 |
| `output_format` | string | `"webm"` | `webm`, `mp4`, `gif` |

## Tips & best practices

- **Hide cookie banner dengan `hide_selectors`.** Hampir semua situs Eropa tampilkan GDPR cookie banner besar. Pass `[".cc-window", "#onetrust-banner-sdk", ".cookie-consent"]` akan menutup 90% banner umum. Kalau Anda sering capture situs tertentu, save preset `hide_selectors` Anda sendiri.

- **Scroll-through wajib untuk situs lazy-load.** Situs modern (Medium article, Instagram grid, infinite feed) hanya load image saat dalam viewport. Tanpa `scroll_through: true`, hasil full-page Anda dapat placeholder blur, bukan image final. Aktifkan selalu untuk situs content-heavy.

- **`wait_for_selector` untuk SPA async.** React/Vue/Svelte app yang fetch data after mount butuh waktu render. Set selector yang unik untuk state "loaded" (misal `[data-loaded=true]`, `.dashboard-ready`, `#main-content:not(.skeleton)`), tool akan tunggu sampai selector muncul, baru capture.

- **JPEG quality 85 adalah sweet spot.** Di bawah 75, artefak kompresi kelihatan di area gradient. Di atas 90, ukuran file naik sharply tanpa peningkatan visual berarti. 85 = kualitas indistinguishable dari PNG untuk mata biasa, file 60-70% lebih kecil.

- **PDF untuk dokumentasi legal.** Kalau Anda butuh bukti visual untuk legal matter (takedown request, proof of content existence pada tanggal X), PDF lebih diterima oleh proses formal dibanding PNG. Playwright `page.pdf()` embed metadata tanggal generate otomatis.

- **Device scale 2x untuk Retina display.** Screenshot dari scale 1x akan tampak blurry di MacBook Retina display atau monitor 4K. Capture di 2x menghasilkan file 4x lebih besar tapi tampak sharp di semua device modern. Wajib untuk material presentation ke klien yang pakai laptop high-DPI.

- **Kombinasikan multi-viewport + color_scheme both** untuk satu request menghasilkan matrix 3x2 = 6 capture sekaligus. Dokumentasi responsive dark/light mode selesai dalam satu klik.

- **Watermark untuk distribusi third-party.** Kalau hasil capture Anda akan di-share ke external (artikel blog, post sosial media, pitch deck ke klien baru), tambah watermark text seperti "captured via PyScrapr for ACME Corp" di position `bottom-right` dengan opacity 0.3. Deterrent kecil tapi real untuk plagiasi.

## Troubleshooting

### Problem: "Playwright not installed"

**Gejala:** HTTP 503 dengan pesan `pip install playwright && playwright install chromium`.
**Penyebab:** Module Python `playwright` belum ter-install, atau Chromium binary belum di-download.
**Solusi:** Di PowerShell, aktifkan venv backend, jalankan:

```powershell
pip install playwright
python -m playwright install chromium
```

Restart backend, coba capture lagi.

### Problem: Capture terpotong di bagian bawah

**Gejala:** Full-page mode aktif, tapi hasil PNG cuma capture setengah halaman, sisanya terpotong.
**Penyebab:** Tool hit `timeout_ms` saat scroll panjang sebelum capture selesai.
**Solusi:** Naikkan `timeout_ms` ke 60000 atau 90000. Kalau situs punya infinite scroll yang tidak pernah benar-benar berhenti, matikan `full_page`, atau set explicit `wait_for_selector` di footer untuk signal "scroll sudah cukup".

### Problem: Element not found saat pakai element_selector

**Gejala:** Error "selector X did not match any elements" atau hasil capture kosong.
**Penyebab:** Selector yang Anda pakai tidak valid untuk halaman saat ini (mungkin element butuh state tertentu, atau selector salah ketik, atau element render via JS yang belum jalan).
**Solusi:** Cek dulu selector Anda di Selector Playground (`Ctrl+P`). Paste URL target, paste selector, verify match count. Kalau match di Playground tapi tidak di Screenshot, aktifkan `wait_for_selector` dengan selector yang sama untuk memaksa tool tunggu element muncul.

### Problem: Auth Vault tidak apply, capture tetap dapat halaman login

**Gejala:** `use_auth_vault: true`, tapi hasil tetap login page redirect.
**Penyebab:** Domain di Auth Vault tidak exact match dengan domain target. Cookie Vault di-lookup exact per-domain (tidak ada cascade dari `example.com` ke `app.example.com`).
**Solusi:** Buka Auth Vault, verify domain entry. Kalau Anda login ke `https://app.example.com`, domain key harus `app.example.com` (bukan `example.com` atau `.example.com`). Kalau perlu, duplicate entry ke multiple subdomain.

### Problem: Video file terlalu besar

**Gejala:** MP4 output 50-100 MB untuk recording 10 detik.
**Penyebab:** Kombinasi fps tinggi + viewport besar + device scale 2x bikin bitrate membengkak.
**Solusi:** Turunkan fps ke 15. Turunkan viewport ke desktop (1920x1080) dari desktop_hd (2560x1440). Atau ganti format ke GIF kalau Anda bisa tolerir kualitas lebih rendah untuk file size lebih kecil.

### Problem: ffmpeg error saat convert MP4/GIF

**Gejala:** Error `ffmpeg not found` atau `subprocess returned non-zero` saat output format MP4 / GIF.
**Penyebab:** Library `imageio-ffmpeg` belum terpasang atau corrupt.
**Solusi:** Reinstall:

```powershell
pip uninstall imageio-ffmpeg -y
pip install imageio-ffmpeg
```

Kalau masih error, cek log backend, biasanya pesan ffmpeg verbose cukup jelas. Bisa jadi codec specific problem, coba ganti output ke WebM dulu untuk confirm capture itu sendiri bekerja.

### Problem: Dark mode tidak berefek

**Gejala:** `color_scheme: dark` aktif tapi hasil tetap tema light.
**Penyebab:** Situs target tidak support `prefers-color-scheme` media query. Tema gelap mereka di-kontrol lewat toggle manual di UI, bukan OS-level preference.
**Solusi:** Tool hanya simulasi OS-level preference. Kalau target butuh klik toggle, pakai `custom_css` untuk force dark styling, atau terima bahwa situs target belum support system dark mode.

### Problem: Diff ratio 0.30+ padahal visual tampak sama

**Gejala:** Manual inspection compare tampak identik, tapi `diff_ratio` tinggi.
**Penyebab:** Anti-aliasing font rendering beda per-capture session, atau timestamp dinamis (jam, counter visitor, ad rotation).
**Solusi:** Pakai `hide_selectors` untuk element dinamis sebelum capture. Kalau ada widget rotation yang tidak bisa di-hide, accept bahwa diff baseline untuk URL tersebut akan selalu 0.05-0.10, set threshold lebih tinggi.

## Keamanan & etika

Screenshotter tampak innocent, tapi tetap ada garis etis yang layak dijaga.

> [!WARNING]
> Setiap capture = 1 HTTP visit ke server target. Batch 100 URL = 100 bot visit yang tercatat di access log mereka. Scheduled daily ke 10 URL = 3650 visits per tahun per URL. Angka yang tidak bisa di-abaikan.

- **Hormati robots.txt dan Terms of Service.** Meskipun tool ini sendiri tidak parse robots.txt (karena capture dianggap visit, bukan crawling), prinsip etiketnya: kalau situs jelas-jelas melarang automated access, scheduled capture rutin bisa dianggap violation spirit of robots.txt.

- **Jangan simpan credentials sensitif di Auth Vault untuk shared system.** Auth Vault adalah convenience untuk personal offline tool. Kalau mesin PyScrapr Anda shared dengan orang lain, atau backup folder masuk ke cloud sync (OneDrive, Dropbox), cookies session Anda bisa ter-expose. Idealnya: pakai Auth Vault hanya di mesin personal, dan rotate / delete entry setelah task selesai.

- **Jangan capture halaman login / dashboard orang lain lalu publikasikan.** Walau Anda punya legitimate access, capture UI private service dan share ke publik bisa melanggar Terms of Service layanan tersebut (dan kadang data privacy regulation).

- **Watermark disarankan untuk dokumentasi pihak ketiga.** Kalau hasil screenshot untuk pitch deck klien atau dokumentasi publik yang mengandung UI pihak ketiga (kompetitor, partner, vendor), tambah watermark "captured for [internal review]" kecil di bottom-right. Ini signal bahwa capture untuk internal research, bukan untuk redistribution.

- **Scheduled capture ke banyak domain = bot traffic patterns.** Kalau Anda setup 20 scheduled job yang hit 20 domain berbeda setiap jam, pola traffic dari IP Anda bisa trigger WAF / Cloudflare bot detection di salah satu target. Tool akan mulai dapat challenge page, bukan situs asli. Kombinasikan dengan proxy rotation kalau ini jadi masalah.

- **Copyright UI third-party.** Capture landing page kompetitor untuk riset internal = fair use di banyak yurisdiksi. Capture lalu publish ke artikel "10 worst designed websites 2026" = potensi masalah copyright atau defamation, terutama kalau disertai komentar merendahkan. Pakai dengan etika.

- **Storage sensitivity.** File screenshot di `data/screenshots/` bisa berisi info sensitif (dashboard admin, halaman dengan data user, internal tool). Meskipun folder sudah di-gitignore, pastikan backup laptop Anda (Time Machine, Windows Backup) sadar bahwa folder ini sensitif, atau exclude dari backup cloud.

## Related docs

- [Playwright Rendering](/docs/advanced/playwright.md) - detail headless browser yang dipakai di balik Screenshotter
- [UA Rotation](/docs/advanced/ua-rotation.md) - profile browser yang di-apply saat capture
- [Proxy Rotation](/docs/advanced/proxy.md) - saat target geo-block atau IP Anda kena rate-limit
- [Diff Detection](/docs/system/diff.md) - engine di balik mode compare Gallery
- [Scheduled Jobs](/docs/system/scheduled.md) - APScheduler integration untuk capture terjadwal
- [Auth Vault](/docs/utilities/vault.md) - simpan cookies / session untuk capture halaman private
- [Selector Playground](/docs/utilities/playground.md) - test CSS selector sebelum pakai di `element_selector` atau `hide_selectors`
- [History & Export](../system/history.md) - semua capture run tercatat di History, re-run dengan satu klik
- [Webhooks](/docs/advanced/webhooks.md) - Discord / Telegram / HTTP notification saat scheduled capture detect diff > threshold
