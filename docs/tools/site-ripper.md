# Site Ripper

> Tool mirroring website lengkap untuk offline browsing — mengunduh HTML, CSS, JavaScript, font, gambar, dan favicon, lalu me-rewrite semua URL jadi relative path agar site bisa diakses tanpa internet.

## Deskripsi

Site Ripper adalah tool paling ambisius di lineup PyScrapr. Tujuannya sederhana untuk dijelaskan tapi kompleks untuk diimplementasikan: menghasilkan salinan offline sebuah website yang bisa dibuka di browser tanpa koneksi internet, dengan styling dan interaktivitas yang tetap utuh. Ini berguna untuk arsip personal, dokumentasi offline, backup situs milik sendiri, atau preservation konten yang mungkin menghilang di masa depan.

Di bawah hood, Site Ripper bekerja dalam dua pass. Pass pertama adalah **crawl + download**: crawler BFS (mirip URL Mapper tapi lebih agresif) mengunjungi setiap halaman, tapi kali ini tidak hanya mencatat URL — melainkan mengunduh seluruh asset yang dibutuhkan untuk render halaman tersebut. Modul `asset_extractor.py` memparsing HTML dan mengidentifikasi referensi di banyak tempat: `<img src>`, `<img srcset>`, `<picture><source>`, `<video src>`, `<audio src>`, `<iframe src>` (same-origin only), `<link rel="stylesheet" href>`, `<link rel="icon">`, `<script src>`, plus asset di inline style `url()` dan `@import`. Untuk file CSS, parser memfollow rantai `@import` rekursif dan ekstrak setiap `url()` reference — termasuk font files (`.woff2`, `.ttf`), background images, dan asset lain.

Pass kedua adalah **URL rewriting**. Semua absolute URL di HTML/CSS/JS yang sudah diunduh di-convert jadi relative path yang menunjuk ke file lokal. Misalnya `https://example.com/assets/style.css` di HTML jadi `../assets/style.css`. Algoritma rewriting mempertahankan struktur folder agar relative path tetap valid lintas halaman. Untuk URL ke external resource (CDN yang tidak ter-download), default behavior adalah biarkan absolute — jadi site mirror tetap butuh internet untuk resource tersebut, atau Anda bisa aktifkan mode **aggressive mirror** yang download external resource juga.

Positioning Site Ripper vs alternatif: `wget --mirror` dan HTTrack sudah ada selama dekade, tapi keduanya punya UX command-line atau GUI jadul, tidak handle modern web dengan baik (srcset, lazy-load, CSS `@import` chains), dan tidak terintegrasi dengan tooling lain. Site Ripper PyScrapr handle modern web properly, punya UI real-time yang informatif, generate PDF report otomatis via reportlab, dan terintegrasi ke ekosistem History/Scheduler/Pipeline.

Salah satu fitur premium yang tidak ada di kompetitor: **PDF report otomatis** yang di-generate setelah rip selesai. Report berisi summary (total pages, total size, time taken), breakdown by asset kind (bytes dan count untuk html/css/js/img/font/other), dan daftar broken link (asset referenced tapi gagal download). Berguna untuk audit trail atau delivery ke client.

## Kapan pakai tool ini?

- **Arsip personal blog/portfolio** — backup lengkap situs Anda untuk offline access atau insurance kalau hosting lenyap.
- **Preservation konten langka** — arsipkan forum lama, blog personal yang mau ditutup, situs dokumentasi proyek open-source yang tidak lagi maintained.
- **Offline documentation reading** — rip docs framework (misal React docs, Tailwind docs) untuk baca di pesawat / daerah tanpa internet.
- **Presentasi ke client tanpa WiFi** — mirror site final untuk demo saat client tidak menyediakan internet yang reliable.
- **Legal evidence** — arsipkan snapshot site saat dispute, dengan timestamp yang bisa diverifikasi via hash file.
- **Site migration preparation** — mirror site lama untuk reference visual saat rebuild di CMS baru.
- **SEO competitor analysis mendalam** — offline analysis struktur HTML, CSS, JS kompetitor tanpa terus-menerus request ke server mereka.
- **Training data generation** — source data untuk model NLP/ML yang butuh real-world HTML corpus.

## Cara penggunaan

1. Klik menu **Site Ripper** di sidebar. Form konfigurasi di kiri, panel progress kosong di kanan.

2. Masukkan **Seed URL** — halaman entry point yang akan dijadikan homepage offline mirror. Contoh: `https://docs.example.com`. Ekspektasi: URL validasi real-time + preview title via HEAD request.

3. Set **Max depth** (slider 1-5). Depth 2 cukup untuk docs kecil. Depth 4 untuk situs medium. Di atas itu, expect mirror multi-GB.

4. Toggle **Stay on domain** (default ON) dan **Aggressive external asset** (default OFF). Kalau Anda butuh mirror yang benar-benar self-contained termasuk CDN font/lib, aktifkan aggressive.

5. Pilih **Asset kinds to include** — checkbox untuk: HTML (wajib, grayed out), CSS, JavaScript, Images, Fonts, Videos, Audio, Favicons. Default semua centang.

6. Opsional: Set **Max file size per asset** (default 50MB) — file di atas threshold akan di-skip untuk mencegah download video HD tak sengaja.

7. Set **Concurrency** — jumlah asset paralel. Default 8. Site Ripper lebih berat dari Harvester, jangan naik di atas 12.

8. Klik **Mulai Rip**. Backend create job dengan 2 sub-phase. Panel kanan menampilkan phase indicator: **Phase 1/2: Crawling & Downloading**.

9. Selama Phase 1, live counter menampilkan: pages crawled, assets downloaded by kind (dengan icon representative), total bytes, errors. Anda bisa klik "Live preview" untuk melihat tree folder yang sedang terbentuk.

10. Setelah semua asset terdownload, Phase 2 otomatis mulai: **Rewriting URLs**. Progress bar menunjukkan file yang sedang diproses. Biasanya 10-20% dari total waktu.

11. Setelah selesai, ringkasan muncul: total files, total size, broken links count. Tombol **Open Mirror** membuka `index.html` hasil di browser baru, Anda bisa langsung navigate.

12. Download **PDF Report** via tombol di header — otomatis ter-generate dengan chart dan tabel. Atau **Export ZIP** untuk archive portable lengkap.

## Pengaturan / Konfigurasi

### Seed URL
Halaman entry point mirror. Wajib diisi. Default: kosong. Rekomendasi: gunakan homepage atau docs root, bukan deep page. Ubah untuk target section khusus.

### max_depth
BFS depth dari seed. Default: 3. Rekomendasi: 2 untuk landing page, 3 untuk docs standar, 4-5 untuk content-heavy site. Ubah naik dengan hati-hati — exponential growth.

### stay_on_domain
Mirror cuma same-domain. Default: true. Rekomendasi: true untuk kebanyakan use case. Ubah ke false saat site tersebar di multiple subdomain (docs.x.com, api.x.com, blog.x.com).

### aggressive_external
Download asset dari CDN external. Default: false. Rekomendasi: false untuk hemat bandwidth, true untuk truly self-contained mirror. Ubah true saat plan akses mirror dari komputer tanpa internet sama sekali.

### include_kinds
Asset kinds yang di-download. Default: all. Rekomendasi: matikan video/audio untuk text-heavy site agar hemat space. Ubah untuk scenario spesifik (misal only-images untuk portfolio rip).

### max_asset_size_mb
Skip asset di atas size ini. Default: 50MB. Rekomendasi: 10 untuk docs, 100 untuk media site. Ubah turun untuk prevent accidental large download.

### concurrency
Parallel asset downloads. Default: 8. Rekomendasi: 4 WP/shared, 8 standard, 12 enterprise. Ubah turun saat server target lambat.

### respect_robots_txt
Patuhi robots.txt. Default: true. Rekomendasi: true selalu. Ubah hanya dengan permission.

### rewrite_mode
Strategi URL rewrite. Default: `relative`. Option: `relative` (portable), `absolute_local` (pakai full `file://`), `preserve_cdn` (keep external URL intact). Rekomendasi: relative untuk portability.

### inline_small_assets
Inline asset <10KB ke HTML sebagai base64. Default: false. Rekomendasi: aktifkan untuk single-file HTML distribution, tapi tingkatkan file size.

### user_agent
HTTP UA header. Default: Chrome modern UA. Ubah kalau server diskriminasi.

## Output

Struktur folder lengkap mirror:

```
downloads/
└── <domain>/
    └── <YYYY-MM-DD>_mirror/
        ├── site/                      # entry point for browsing
        │   ├── index.html            # rewrite dari seed URL
        │   ├── about/
        │   │   └── index.html
        │   ├── blog/
        │   │   ├── index.html
        │   │   └── post-slug/
        │   │       └── index.html
        │   └── assets/
        │       ├── css/
        │       ├── js/
        │       ├── img/
        │       ├── fonts/
        │       └── media/
        ├── manifest.json              # every file + metadata
        ├── broken-links.csv           # failed asset list
        ├── report.pdf                 # auto-generated report
        └── rip.log                    # detailed log
```

- Buka `site/index.html` di browser untuk navigate mirror offline.
- `report.pdf` berisi summary + breakdown + broken list untuk audit.
- `manifest.json` memetakan original URL ke local path, berguna untuk re-import atau diff.

## Integrasi dengan fitur lain

- **URL Mapper handoff** — import URL list dari Mapper untuk targeted rip (hanya section tertentu, bukan full site).
- **Image Harvester cross-check** — bandingkan jumlah gambar di mirror vs hasil Harvester untuk validation.
- **AI Tools classification** — klasifikasi semua gambar di mirror via CLIP untuk content tagging.
- **Scheduler** — jadwalkan monthly rip untuk archival snapshot (arsip resmi).
- **History compare** — diff mirror antar waktu, deteksi content changes, surface git-style diff HTML.
- **Pipeline post-processing** — optimize images di mirror (WebP), minify CSS/JS untuk distribusi.
- **Export module** — ZIP archive atau upload ke cloud storage via rclone integration.

## Tips & Best Practices

1. **Test pada subsection dulu** — sebelum rip full site 100GB, rip satu folder seperti `/docs/getting-started/` depth 2 untuk validate config benar.

2. **Matikan video/audio jika tidak perlu** — satu video 4K bisa 1GB+. Cek preview asset list dulu, exclude kind yang irrelevant untuk use case.

3. **Buka mirror hasil di browser incognito** — tanpa extension/cache bisa bias, incognito render murni HTML+CSS+JS yang ada di disk. Validasi visual lebih reliable.

4. **Preserve original domain di `manifest.json`** — mapping file penting untuk debug kalau ada link broken atau untuk regenerate mirror nanti.

5. **Pakai aggressive_external hanya saat benar-benar perlu** — CDN font provider seperti Google Fonts biasanya tetap online dekade kedepan, tidak perlu di-mirror. Aggressive mode tingkatkan rip time 2-3x.

6. **Monitor folder size saat rip berjalan** — setting `max_asset_size_mb` mencegah file individual besar, tapi total bisa tetap meledak. Cancel kalau sudah melewati kuota disk yang Anda siapkan.

7. **Arsipkan beserta `rip.log`** — log berisi exact command, config, timestamp, hash asset. Penting kalau mirror akan dipakai sebagai evidence legal.

8. **Re-run reguler untuk site yang cepat berubah** — news site, dokumentasi yang ter-update: jadwalkan weekly rip, simpan tiap versi dengan tanggal.

## Troubleshooting

### Problem: Mirror dibuka di browser, CSS tidak ter-apply
**Gejala:** Halaman render plain HTML tanpa styling, meski folder `assets/css/` berisi file CSS.
**Penyebab:** URL rewriting gagal untuk tag `<link rel="stylesheet">`, atau browser block karena protocol file:// restriction.
**Solusi:** Cek path di HTML via View Source — pastikan relative path benar. Jika file:// restriction, jalankan lokal HTTP server: `python -m http.server 8000` di folder site, buka via localhost.

### Problem: Font tidak ter-load di mirror
**Gejala:** Text render dengan fallback font system, bukan font custom seperti yang di live site.
**Penyebab:** Font file (woff2/ttf) tidak ter-download karena CORS block, atau CSS `@import` chain tidak ke-follow sampai file font.
**Solusi:** Aktifkan `aggressive_external: true` untuk download Google Fonts dll. Cek `broken-links.csv` untuk lihat URL font yang gagal. Re-run rip dengan config fix.

### Problem: JavaScript dynamic content tidak muncul offline
**Gejala:** Section tertentu kosong yang di live site berisi data dari API.
**Penyebab:** JS di site fetch data dari backend API — saat offline, fetch gagal, content tidak render.
**Solusi:** Ini limitasi inherent — Site Ripper tidak bisa mirror backend. Sebagai workaround, aktifkan **Snapshot mode** di advanced: Site Ripper akan render halaman via headless browser, capture DOM setelah JS execute, save sebagai static HTML tanpa JS dependency.

### Problem: "Too many open files" error di tengah rip
**Gejala:** Log error `OSError: [Errno 24] Too many open files`, rip stuck.
**Penyebab:** Concurrency tinggi + asset kecil banyak = file descriptor exhaustion (limit OS default 1024 di Linux, 512 di Windows).
**Solusi:** Turunkan `concurrency` ke 4. Di Linux, naikkan ulimit: `ulimit -n 4096`. Di Windows, restart PyScrapr untuk clear handle.

### Problem: Disk penuh sebelum rip selesai
**Gejala:** Error `[Errno 28] No space left`, file terpotong.
**Penyebab:** Site lebih besar dari estimasi — video/asset besar yang tidak ke-filter.
**Solusi:** Sebelum rip, lakukan **dry run** (toggle di advanced) — tool akan estimasi size via HEAD request semua asset tanpa download. Baca estimasi, setujui atau adjust include_kinds.

### Problem: URL rewriting merusak link yang sudah valid relative
**Gejala:** Halaman internal link (`href="/about/"`) ter-convert jadi broken path (`href="../about/"`) yang salah level.
**Penyebab:** Bug rewriting atau nested folder depth tidak ter-kalkulasi benar saat cross-page reference.
**Solusi:** Update ke versi terbaru. Sebagai workaround gunakan `rewrite_mode: absolute_local` yang pakai full path — kurang portable tapi lebih reliable.

### Problem: Mirror tidak include halaman pagination
**Gejala:** Blog page 1 ada, page 2/3/4 tidak ada di mirror.
**Penyebab:** Pagination link di-exclude oleh filter, atau depth tidak cukup.
**Solusi:** Cek include/exclude patterns. Tambah depth +1. Kalau pagination via infinite scroll (JS-based), gunakan snapshot mode headless.

### Problem: SSL error pada beberapa asset dari CDN
**Gejala:** Log banyak `SSLError` untuk host CDN eksternal.
**Penyebab:** CDN pakai cert modern (ECDSA, TLS 1.3) yang outdated Python-nya tidak support.
**Solusi:** Upgrade Python ke 3.11+. Update `certifi`. Kalau masih, whitelist host tersebut di `skip_ssl_verify_hosts`.

### Problem: Broken link report menunjukkan URL yang tidak pernah ada di site
**Gejala:** `broken-links.csv` list URL yang Anda tidak kenali, mengarah ke tracking/analytics domain.
**Penyebab:** Site load analytics script (Google Analytics, Hotjar, dll) yang PyScrapr coba download gagal.
**Solusi:** Tambahkan pattern analytics ke `exclude_asset_patterns`: `["google-analytics.com", "googletagmanager.com", "hotjar.com", "facebook.net"]`. Re-run — hasil bersih dan mirror lebih kecil.

### Problem: Memory usage balloon saat rip site besar
**Gejala:** Python RAM usage >4GB, mesin jadi sangat lambat.
**Penyebab:** HTML parser Beautiful Soup simpan full DOM tree untuk setiap page di memory.
**Solusi:** Aktifkan **streaming parser mode** di advanced — pakai lxml iterparse untuk memory efficiency. Tutup aplikasi lain. Untuk benar-benar besar, rip per-section kemudian gabungkan manual.

### Problem: PDF report tidak ter-generate
**Gejala:** Rip selesai, semua file ada, tapi `report.pdf` missing.
**Penyebab:** `reportlab` tidak terinstall, atau permission write di folder output.
**Solusi:** `pip install reportlab`. Cek permission folder. Kalau masih, lihat log — ada error traceback spesifik.

### Problem: Karakter non-ASCII di path/filename corrupt
**Gejala:** Folder dengan karakter Cina/Arab muncul sebagai `???` atau bloat hex.
**Penyebab:** OS filesystem encoding (Windows legacy cp1252) tidak support UTF-8 penuh.
**Solusi:** Di Windows 10+, enable "Use UTF-8 for worldwide language support" di Region settings. Atau aktifkan **ASCII-safe filenames** di config — path dihash jadi ASCII, mapping di manifest.json.

## FAQ

**Q: Berapa besar mirror site rata-rata?**
A: Blog biasa: 50-500MB. Dokumentasi framework: 500MB-2GB. News site depth 3: 2-10GB. E-commerce: 5-50GB. Selalu lakukan dry run dulu untuk estimasi.

**Q: Apakah bisa mirror WordPress site yang pakai lazy-load?**
A: Ya — asset_extractor baca atribut lazy-load populer (`data-src`, `data-lazy-src`). Untuk WP dengan plugin aneh, tambah custom attribute ke config `lazy_load_attrs`.

**Q: Mirror hasil bisa di-host di server lain tidak?**
A: Ya, karena semua relative path. Upload folder `site/` ke static hosting (Netlify, GitHub Pages), buka via URL, site offline berjalan mirip aslinya.

**Q: Apakah interaktif (form, search) tetap berfungsi offline?**
A: Tidak — form submit butuh backend. Search biasanya butuh API. Mirror hanya static snapshot. Untuk search offline, pair dengan Pipeline Search Index generator.

**Q: Apakah cookie/session state di-preserve?**
A: Tidak — setiap halaman di-mirror dalam public state (non-logged-in). Kalau butuh mirror logged-in view, inject cookie di advanced settings sebelum rip.

**Q: Bagaimana kalau saya cuma butuh HTML tanpa asset?**
A: Uncheck semua kind kecuali HTML di `include_kinds`. Mirror jadi super ringan tapi tanpa styling. Berguna untuk text-mining use case.

**Q: Apakah respect `<meta name="robots" content="noindex">`?**
A: Tidak by default — robots meta untuk search engine, bukan arsip. Tapi ada toggle `respect_meta_robots` untuk yang strict.

**Q: Bisakah re-rip incremental (hanya yang berubah)?**
A: Ya via **Incremental mode** — compare hash/etag dengan manifest.json run sebelumnya, hanya download yang berubah. Menghemat bandwidth signifikan untuk monitoring.

**Q: Kenapa beberapa gambar broken di mirror padahal ada di live site?**
A: Biasanya karena gambar di-load via JS dinamis, atau CORS block, atau `srcset` parsing edge case. Cek `broken-links.csv` untuk URL spesifik, debug manual.

**Q: Apakah mirror bisa dipakai sebagai bukti hukum?**
A: Technically PDF report + log file + hash manifest membentuk chain of evidence, tapi untuk validitas legal sebaiknya notarisasi timestamp via service eksternal (OpenTimestamps, dll).

## Keterbatasan

- Tidak eksekusi JavaScript secara default — SPA sepenuhnya tidak mirror dengan baik (aktifkan snapshot mode sebagai workaround).
- Tidak mirror backend behavior — API, form submit, search tidak berfungsi.
- Tidak handle streaming media (HLS, DASH) — hanya direct file URL.
- WebSocket/real-time features tidak relevan.
- Ukuran disk bisa cepat meledak — estimasi via dry run wajib untuk site besar.
- Tidak ada cloud storage direct integration (pakai rclone manual).
- Link ke external domain tetap absolute kecuali aggressive mode — butuh internet partial.
- Tidak support site di behind CAPTCHA atau bot-challenge aktif.
- PDF report terbatas 50 halaman (reportlab perf limit).

## Related docs

- [URL Mapper](url-mapper.md) — discover struktur URL sebelum targeted rip
- [Image Harvester](image-harvester.md) — alternatif ringan kalau cuma butuh gambar
- [Media Downloader](media-downloader.md) — untuk video yang di-embed iframe
- [Pipeline](../advanced/pipeline.md) — minify, optimize asset post-rip
- [Scheduler](../advanced/scheduler.md) — automate periodic archival
- [Export & ZIP](../system/export.md) — packaging untuk distribution
