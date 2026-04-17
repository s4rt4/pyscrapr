# URL Mapper

> Tool crawler yang memetakan seluruh struktur link sebuah situs web secara hierarkis, dengan kontrol depth, rate limiting per-host, dukungan pause/resume, dan visualisasi interaktif berupa tree + graph.

## Deskripsi

URL Mapper adalah tool kedua di lineup PyScrapr dan merupakan "mata" dari sistem - ia memberikan Anda peta lengkap semua link yang bisa dijangkau dari satu halaman awal. Dibangun di atas algoritma BFS (Breadth-First Search) dengan depth control 1 hingga 5 level, tool ini melakukan crawl secara sistematis: mulai dari URL seed, parse HTML, ekstrak semua `<a href>`, normalisasi, filter berdasarkan domain policy, lalu antrean ke level berikutnya. Setiap URL yang sudah dikunjungi disimpan ke set in-memory + SQLite agar tidak di-crawl dua kali, mencegah infinite loop saat situs punya circular reference atau kalender dinamis.

Di balik layar, URL Mapper memakai `httpx` async client dengan token-bucket rate limiter per-host - artinya kalau Anda crawl beberapa subdomain sekaligus (misal `blog.site.com` dan `shop.site.com`), masing-masing host punya quota request-per-second sendiri. Ini penting agar tidak memukul satu server berlebihan sambil tetap memaksimalkan parallelism lintas host. Tool juga secara default patuh terhadap `robots.txt` via `urllib.robotparser` - kalau path di-disallow, URL Mapper skip dan mencatatnya di log sebagai `robots-blocked`. Anda bisa override behavior ini, tapi secara default ethical crawling menjadi setting awal.

Salah satu fitur yang membedakan URL Mapper dari crawler generik seperti Screaming Frog atau Sitebulb adalah **URL normalization** yang cerdas. Tool ini: strip URL fragment (`#section`), buang tracking parameter populer (`utm_source`, `utm_medium`, `utm_campaign`, `fbclid`, `gclid`, `msclkid`), case-fold domain (tapi preserve path case karena banyak CMS case-sensitive), hapus trailing slash kecuali pada root, dan resolve relative URL terhadap base. Hasilnya: satu URL konseptual tidak ter-crawl berkali-kali karena beda param pelacakan.

Fitur unggulan lain adalah **pause/resume via SQLite checkpoint**. Crawl frontier (antrean BFS) di-persist ke tabel `crawl_frontier`, jadi kalau komputer mati mendadak atau job di-pause user, state lengkap tetap aman. Saat resume, crawler melanjutkan dari posisi terakhir tanpa re-crawl URL yang sudah selesai. Ini vital untuk site besar dengan 50.000+ halaman yang mungkin butuh berjam-jam crawl.

Positioning vs market: Screaming Frog gratis terbatas 500 URL, versi berbayar $260/tahun. Sitebulb lebih mahal lagi. URL Mapper gratis, offline, dan terintegrasi native dengan tool PyScrapr lain - hasil map bisa langsung jadi input Image Harvester atau Site Ripper.

## Kapan pakai tool ini?

- **SEO audit situs sendiri** - petakan seluruh internal link structure untuk identify orphan pages, deep pages (depth >3), dan broken links (4xx/5xx) yang merugikan ranking.
- **Riset kompetitor content strategy** - crawl blog kompetitor untuk lihat struktur kategori, jumlah artikel per topik, dan frequency pattern (via tanggal di URL).
- **Pre-migration inventory** - sebelum migrasi CMS, dapatkan list lengkap semua URL existing untuk planning redirect 301 mass.
- **Broken link detection** - jalankan URL Mapper dengan focus pada error codes, dapatkan laporan semua link rusak untuk di-fix di CMS.
- **Sitemap generation** - export hasil crawl ke format XML sitemap Google-compatible untuk submit ke Search Console.
- **Visualisasi information architecture** - pakai hybrid tree+graph view untuk presentasi ke client tentang struktur site mereka.
- **Discovery URL sebelum bulk harvest** - sebelum run Image Harvester pada 1000 artikel, gunakan URL Mapper untuk discover semua URL artikel terlebih dahulu.
- **Monitor perubahan site structure** - jalankan crawl mingguan, diff hasilnya, deteksi halaman baru/dihapus untuk content intelligence.

## Cara penggunaan

1. Dari sidebar PyScrapr, klik menu `URL Mapper`. Form konfigurasi muncul di panel kiri, panel kanan menampilkan placeholder untuk visualisasi tree dan graph.

2. Di field `Target URL`, masukkan alamat awal crawl. Contoh: `https://example.com`. URL ini jadi root node di tree output. Ekspektasi: ikon checkmark hijau muncul jika URL reachable (preflight HEAD request).

3. Pilih `Max depth` (slider 1-5). Depth 1 = hanya link langsung dari seed. Depth 3 adalah sweet spot untuk mapping umum. Depth 5 bisa crawl ribuan URL, siapkan waktu dan bandwidth. Ekspektasi: estimasi jumlah URL muncul di bawah slider berdasarkan fan-out rata-rata.

4. Toggle `Stay on domain`. Default ON - crawler hanya mengikuti link yang masih di domain seed. Matikan kalau ingin explore external link (hati-hati: bisa melebar ke seluruh internet).

5. Atur `Respect robots.txt` (default ON). Biarkan aktif kecuali Anda crawl site sendiri atau ada permission tertulis.

6. Set `Rate /s per host`. Default 2 request/detik. Untuk site besar yang bisa handle load, naikkan ke 5-10. Untuk WordPress shared hosting, turunkan ke 1.

7. Opsional: di advanced settings, set exclude URL patterns (regex list) untuk skip seksi tertentu - misal `/tag/`, `/author/`, `/search?`, `/page/\d+` untuk hindari duplikasi pagination.

8. Klik `Start crawl`. Backend creates job, returns job_id, SSE stream terbuka. Ekspektasi: live counter muncul menampilkan "Discovered: X, Visited: Y, Queued: Z".

9. Saat crawl berjalan, tree view di panel kanan populate incrementally. Node dengan status OK berwarna hijau, 3xx kuning, 4xx orange, 5xx merah. Kalau Anda perlu pause, klik tombol `Pause`, crawler stop gracefully dan simpan checkpoint.

10. Untuk resume, klik `Resume` pada job yang paused. Crawler lanjut dari antrean tersimpan.

11. Setelah crawl selesai, pindah ke view `Graph` untuk visualisasi Cytoscape.js dengan layout cola. Drag-drop node, zoom, pan. Klik node untuk buka detail drawer dengan metadata: response time, content-type, status code, title, inbound/outbound links.

12. Export hasil via dropdown `Export`: pilih `PNG screenshot`, `JSON`, atau `XML sitemap` (Google Sitemap compatible). File tersimpan di folder output.

## Pengaturan / Konfigurasi

### Target URL
URL awal crawl. Wajib. Harus HTTP/HTTPS valid dan reachable. Default: kosong. Rekomendasi: gunakan homepage untuk mapping penuh, atau halaman spesifik untuk subsection analysis. Ubah ketika fokus hanya di category tertentu seperti `/blog/` saja.

### Max depth
Kedalaman crawl BFS. Default: 3. Rekomendasi: 2 untuk quick overview, 3 untuk audit umum, 4-5 untuk deep mapping. Ubah sesuai estimasi ukuran site - setiap +1 depth bisa lipatgandakan jumlah URL.

### stay_on_domain
Boolean apakah crawler hanya ikuti link same-domain. Default: true. Rekomendasi: biarkan true untuk audit internal, set false untuk backlink discovery. Ubah ketika Anda ingin tahu ke mana outbound link mengarah.

### respect_robots_txt
Boolean untuk patuhi robots.txt. Default: true. Rekomendasi: SELALU true kecuali crawl site sendiri. Ubah hanya dengan permission tertulis dari site owner.

### rate_limit_rps
Request per detik per host. Default: 2. Rekomendasi: 1 untuk hosting shared, 2-3 untuk VPS biasa, 5-10 untuk CDN besar (Cloudflare, Akamai). Ubah turun kalau dapat 429/503, naik kalau crawl terlalu lambat dan server jelas bisa handle.

### exclude_patterns
List regex/substring URL yang di-skip. Default: kosong. Rekomendasi umum: `["/tag/", "/author/", "/feed", "?replytocom=", "/wp-json/"]`. Ubah berdasarkan CMS target dan pattern noise yang terlihat di hasil.

### include_patterns
Kebalikan exclude - hanya URL match pattern ini yang di-crawl. Default: kosong (semua allowed). Rekomendasi: gunakan saat fokus narrow, misal `["/blog/"]` untuk audit blog section saja.

### max_urls_total
Hard cap jumlah URL. Default: 10.000. Rekomendasi: naikkan ke 50.000 untuk site besar, turunkan ke 1000 untuk quick scan. Ubah sebagai safety net agar crawl tidak meledak.

### user_agent
UA string untuk request. Default: PyScrapr identifier. Rekomendasi: biarkan default agar transparent. Ubah ke Chrome UA kalau server diskriminasi bot.

### timeout_seconds
Timeout per request. Default: 15. Rekomendasi: 30 untuk site lambat (banyak di Indonesia), 10 untuk site global fast. Ubah naik saat banyak entry timeout.

## Output

Hasil crawl disimpan di struktur berikut:

```
downloads/
└── <domain>/
    └── <YYYY-MM-DD>_map/
        ├── crawl.db               # SQLite, full data
        ├── urls.json              # flat list all URLs + metadata
        ├── tree.json              # hierarchical structure
        ├── graph.json             # nodes + edges for Cytoscape
        ├── sitemap.xml            # Google-compatible
        ├── broken-links.csv       # 4xx/5xx report
        └── screenshot.png         # graph visualization
```

- **crawl.db** adalah source of truth - SQLite dengan tabel `urls`, `links`, `crawl_frontier`. Bisa di-query manual dengan DB Browser.
- **urls.json**: `[{url, status, depth, parent, title, content_type, response_time_ms, ...}]`
- **tree.json**: nested structure ready untuk Mantine Tree component.
- **sitemap.xml**: format standar Google, gunakan untuk submit ke Search Console.

## Integrasi dengan fitur lain

- **Image Harvester** - export `urls.json`, filter URL artikel, paste sebagai multi-URL input ke Harvester untuk bulk image extraction.
- **Site Ripper handoff** - Site Ripper bisa langsung mengimpor URL list dari job Mapper untuk targeted mirroring (bukan seluruh site).
- **History & Scheduler** - jadwalkan weekly crawl, diff hasil minggu ini vs minggu lalu untuk content change detection.
- **Pipeline integration** - kirim broken-links.csv ke Email Reporter untuk alert otomatis ke tim SEO.
- **Export module** - convert hasil ke Excel/CSV untuk analisis lebih lanjut di Google Sheets/Tableau.
- **API integration** - endpoint `/api/url-mapper/{job_id}/graph` mengembalikan JSON untuk integrasi dashboard eksternal.

## Tips & Best Practices

1. **Mulai dari depth 2 untuk site baru** - sebelum commit ke depth 4-5, lihat struktur dasar dengan depth 2. Anda bisa extract insight fan-out dan estimasi total URL. Baru increase kalau worth it.

2. **Gunakan exclude_patterns agresif untuk WordPress** - tanpa filter, WP site bisa explode ke ratusan ribu URL karena tag/author/date archive. Exclude `/tag/`, `/author/`, `/\d{4}/\d{2}/`, `?replytocom=` sejak awal.

3. **Monitor rate limit adaptively** - kalau Anda lihat response time naik tajam di tengah crawl, pause dan turunkan `rate_limit_rps`. Server yang mulai slow = sinyal Anda terlalu agresif.

4. **Simpan crawl.db untuk audit trail** - SQLite file kecil (~10MB per 10.000 URL) dan bisa di-query kapanpun. Simpan ke Git/cloud sebagai historical snapshot.

5. **Pakai hybrid view strategically** - tree view bagus untuk hierarchy analysis (IA audit), graph view bagus untuk link equity flow. Jangan cuma andalkan salah satu.

6. **Screenshot PNG bukan untuk archive** - PNG graph hanya 2D snapshot, kehilangan interactivity. Untuk archive proper, export JSON + render ulang saat butuh.

7. **Gabungkan robots.txt check dengan manual inspection** - tool patuhi robots.txt, tapi kadang robots.txt itu sendiri misconfigured. Manual cek `/robots.txt` site untuk validate aturan logis.

8. **Test exclude patterns di regex101.com dulu** - salah regex berarti crawl melenceng. Validate pattern di sandbox sebelum production crawl.

## Troubleshooting

### Problem: Crawl stuck di "Queued: 0, Visited: 0" tanpa progress
**Gejala:** Setelah klik Start, counter tidak bergerak, tidak ada error visible, indikator spinning terus.
**Penyebab:** Seed URL unreachable (DNS fail), firewall memblock, atau robots.txt disallow semua (`/`).
**Solusi:** Test URL manual via curl/browser. Cek `/robots.txt` - kalau ada `Disallow: /`, matikan toggle respect robots atau pilih seed lain. Cek log server firewall.

### Problem: HTTP 403 Forbidden pada kebanyakan URL
**Gejala:** Semua entry di hasil adalah status 403, tree kosong.
**Penyebab:** Server deteksi bot via User-Agent atau header missing. Beberapa WAF (Cloudflare, Sucuri) block default Python UA.
**Solusi:** Ganti `user_agent` ke Chrome modern: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...`. Kalau masih block, tambahkan header `Accept`, `Accept-Language`, `Referer` di advanced.

### Problem: Out of memory saat crawl site besar (50.000+ URL)
**Gejala:** Python process crash, Windows menampilkan "out of memory", atau browser tab PyScrapr freeze.
**Penyebab:** In-memory seen-set + tree structure balloon melebihi RAM available.
**Solusi:** Turunkan `max_urls_total` dulu. Untuk crawl benar-benar besar, aktifkan mode **Stream to disk** di advanced settings - seen-set di-persist ke SQLite bukan RAM (lebih lambat tapi hemat memory). Tutup aplikasi lain sebelum crawl.

### Problem: URL normalization merge URL yang seharusnya berbeda
**Gejala:** Anda lihat 500 URL di browser, tapi URL Mapper cuma melaporkan 300.
**Penyebab:** Overly aggressive normalization menggabungkan param yang sebenarnya bermakna (misal `?id=123` vs `?id=456`).
**Solusi:** Di advanced, set `preserve_query_params` dengan list param yang harus di-keep: `["id", "page", "category"]`. Hanya `utm_*`, `fbclid` dll yang di-strip.

### Problem: SSL error pada subdomain tertentu saat crawl multi-subdomain
**Gejala:** Log menunjukkan banyak `SSLCertVerificationError` pada satu subdomain, subdomain lain OK.
**Penyebab:** Subdomain tersebut punya cert expired atau mismatch. Umum di internal/staging subdomain.
**Solusi:** Tambahkan subdomain ke exclude list, atau aktifkan `verify_ssl: false` khusus untuk host tersebut di per-host config.

### Problem: Rate limiter terlalu lambat, crawl butuh berjam-jam
**Gejala:** Crawl site 1000-URL butuh 4+ jam meski seharusnya 10 menit.
**Penyebab:** `rate_limit_rps` terlalu konservatif untuk target yang bisa handle lebih.
**Solusi:** Naikkan bertahap: 2 → 5 → 8. Monitor response time - kalau tetap <500ms, lanjut naik. Kalau mulai timeout/429, turunkan.

### Problem: Resume tidak lanjut dari posisi terakhir, malah mulai dari awal
**Gejala:** Klik Resume pada job paused, tapi counter "Visited" reset ke 0.
**Penyebab:** File SQLite checkpoint corrupt atau schema mismatch (setelah upgrade PyScrapr).
**Solusi:** Cek `downloads/<domain>/<date>_map/crawl.db` masih ada dan bisa dibuka via DB Browser. Kalau schema berubah, migrasi manual atau accept loss dan start fresh.

### Problem: Graph view kosong/blank padahal tree view ada data
**Gejala:** Tree tab normal, Graph tab hanya background kosong, tidak ada node.
**Penyebab:** Cytoscape.js gagal render karena dataset terlalu besar (>5000 node) atau JavaScript error di console.
**Solusi:** Buka browser DevTools → Console. Kalau ada memory error, aktifkan **Sampling mode** - graph hanya render top 2000 node berdasarkan PageRank. Untuk data penuh, pakai JSON export + visualize di Gephi.

### Problem: Encoding issue pada title/content dari situs non-English
**Gejala:** Title halaman muncul sebagai gibberish seperti `Ã¢â‚¬Å"` di node detail.
**Penyebab:** Server tidak set charset header, parser default ke UTF-8 padahal content-nya Latin-1 atau lainnya.
**Solusi:** Update PyScrapr ke versi yang memakai `chardet` auto-detection. Sebagai workaround, set `force_encoding: "iso-8859-1"` di advanced untuk situs tertentu.

### Problem: Disk space penuh karena crawl.db membesar cepat
**Gejala:** File crawl.db mencapai 500MB+ untuk crawl yang baru 5000 URL.
**Penyebab:** Kemungkinan `store_full_html: true` aktif, menyimpan seluruh HTML body ke DB.
**Solusi:** Matikan `store_full_html`. Hanya simpan metadata (title, headers, link list). Full HTML arsip sebaiknya ditangani Site Ripper.

### Problem: Deadlock saat dua crawl jalan paralel
**Gejala:** Dua job URL Mapper stuck, database locked error di log.
**Penyebab:** SQLite default tidak handle concurrent write dengan baik; dua job menulis ke file DB berbeda tapi metadata DB sama.
**Solusi:** Jalankan satu job URL Mapper saja dalam satu waktu. Kalau benar-benar butuh paralel, switch metadata storage ke PostgreSQL (config di `.env`).

## FAQ

**Q: Berapa URL maksimum yang bisa di-map sekali jalan?**
A: Technical limit 1 juta URL per job (SQLite friendly). Practical limit 100.000 untuk UX yang responsif. Di atas itu pertimbangkan pecah per-section.

**Q: Apakah URL Mapper bisa deteksi JavaScript-generated links?**
A: Tidak by default - parser hanya baca static HTML. Kalau situs pakai infinite scroll atau router SPA, banyak URL tidak ketahuan. Gunakan mode **Headless browser** (experimental) atau pair dengan Site Ripper yang punya JS execution.

**Q: Bagaimana URL Mapper menangani redirect?**
A: Redirect 301/302 di-follow secara default (max 5 hops), target final di-record sebagai node terpisah dengan edge "redirect_to" dari source. Redirect chain terlihat di node detail drawer.

**Q: Bisakah saya export ke format lain selain JSON/XML?**
A: Ya - CSV via Export menu (simple flat), Excel via Pipeline → Excel Exporter, atau GraphML untuk Gephi compatibility.

**Q: Bagaimana deteksi broken link yang akurat?**
A: Tool record status code setiap request. Filter `status >= 400` di hasil. Untuk soft-404 (halaman 200 tapi content "Not Found"), gunakan Pipeline Content Classifier.

**Q: Apakah hasil crawl bisa di-compare antar run?**
A: Ya, via History → Compare function. Tool menampilkan diff: URL baru, URL hilang, status change. Berguna untuk monitoring site yang sering update.

**Q: Bisakah crawl site yang butuh login?**
A: Ya, via cookie injection di advanced settings. Paste cookie string dari browser, crawler akan include di setiap request.

**Q: Apakah sitemap XML hasil export bisa langsung di-submit ke Google?**
A: Ya, format sudah compliant dengan Sitemap Protocol 0.9. Upload ke root site, submit URL-nya di Search Console.

**Q: Kenapa beberapa URL muncul dua kali dengan depth berbeda?**
A: Seharusnya tidak - URL unik by canonical form. Kalau muncul duplikat, biasanya karena trailing slash atau capitalization yang tidak ter-normalize. Report sebagai bug.

**Q: Apa bedanya URL Mapper dengan Site Ripper?**
A: Mapper hanya discover URL (tidak download content). Ripper download semua asset untuk offline browsing. Mapper ringan (MB-level output), Ripper berat (GB-level). Sering dipakai berurutan: Map dulu, pilih section, Rip targeted.

## Keterbatasan

- Tidak eksekusi JavaScript - SPA dan infinite scroll tidak sepenuhnya ter-crawl.
- Tidak parse sitemap.xml existing sebagai seed - harus input manual URL utama.
- Maksimum depth 5 - untuk site ekstrem deep, pecah ke beberapa crawl.
- Rate limiter per-host berbasis in-memory token bucket - kalau PyScrapr restart, counter reset.
- Tidak ada distributed crawling - single machine only.
- Graph layout bisa lambat untuk >5000 node (Cytoscape limitation).
- Tidak mem-follow link di PDF, Word, atau file document (hanya HTML links).
- Robot.txt parser tidak 100% support semua edge case spec (extension seperti Crawl-delay di-handle, tapi Sitemap directive tidak).

## Related docs

- [Image Harvester](image-harvester.md) - bulk download gambar dari URL list hasil Mapper
- [Site Ripper](site-ripper.md) - full offline mirror untuk URL yang sudah di-map
- [Media Downloader](media-downloader.md) - download video yang ditemukan di crawl
- [Scheduler](/docs/system/scheduled.md) - automate weekly crawl untuk monitoring
- [History & Compare](../system/history.md) - diff hasil crawl antar waktu
- [Export formats](/docs/system/history.md) - detail format XML sitemap, JSON, CSV
