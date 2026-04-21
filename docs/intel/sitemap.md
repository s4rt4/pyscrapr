# Sitemap Analyzer

> Tool untuk auto-detect dan mem-parsing sitemap.xml sebuah situs, menyajikan statistik URL (lastmod distribution, priority distribution, top path prefix), dan export daftar URL ke CSV/JSON. Pakai satu input (domain atau URL sitemap langsung), tool cari sendiri sitemap dari lokasi standar atau dari robots.txt.

## Apa itu Sitemap Analyzer

Sitemap Analyzer adalah modul PyScrapr yang membaca file `sitemap.xml` (dan variannya seperti `sitemap_index.xml`, `sitemap.xml.gz`, atau sitemap yang di-deklarasikan di robots.txt), parse semua entry URL di dalamnya, lalu present hasilnya sebagai laporan terstruktur. Tool auto-detect lokasi sitemap via tiga strategi: pertama, coba `/sitemap.xml` langsung; kedua, coba `/sitemap_index.xml`; ketiga, fetch `/robots.txt` dan cari directive `Sitemap:`.

Kalau yang ditemukan adalah sitemap index (file yang berisi referensi ke sub-sitemap lain), tool otomatis recurse: fetch tiap sub-sitemap, aggregate URL-nya. Recursion dibatasi max depth 2 dan max 50 sub-sitemap untuk mencegah infinite loop dan resource hog di situs dengan ribuan sub-sitemap (Wikipedia-scale).

Untuk gzipped sitemap (ekstensi `.xml.gz` atau gzip magic bytes di awal file), tool auto-decompress sebelum parsing.

> [!NOTE]
> Modul ini tidak crawl situs. Cuma baca sitemap. Kalau sitemap tidak ada atau tidak lengkap, hasil tidak akan reflect isi situs sebenarnya. Kombinasikan dengan URL Mapper untuk coverage real-crawling.

Filosofi: "dapatkan 80% peta situs dalam 5 detik dari sumber yang dibuat pemilik situs". Sitemap is truth-as-declared-by-owner. Berguna untuk seed URL Mapper, audit SEO, ekstrak URL batch untuk scraping, atau kompilasi katalog produk e-commerce.

## Cara pakai (step-by-step)

1. Buka PyScrapr, navigasi ke **Sitemap Analyzer** di sidebar.

2. Di field `URL situs atau sitemap`, masukkan salah satu dari:
   - Site root: `https://contoh.com` (tool auto-detect sitemap location)
   - URL sitemap langsung: `https://contoh.com/sitemap.xml`
   - URL sitemap index: `https://contoh.com/sitemap_index.xml`
   - URL sitemap gzipped: `https://contoh.com/sitemap.xml.gz`

3. Klik `Analisis`. Backend akan: (a) detect sitemap location kalau input adalah site root, (b) fetch, (c) decompress kalau gzipped, (d) parse XML, (e) recurse sub-sitemap kalau itu index, (f) aggregate semua URL, (g) compute stats.

4. Hasil muncul dalam beberapa section:
   - **Summary card**: total URL count, sumber deteksi (direct / guessed / robots / not_found), sitemap URL yang dipakai
   - **Lastmod distribution chart**: horizontal bar chart bucket 24h / 7d / 30d / 90d / older / unknown
   - **Priority distribution chart**: bucket 0.0-0.2 / 0.3-0.5 / 0.6-0.8 / 0.9-1.0 / unknown
   - **Top path prefix**: 10 prefix terbanyak, sorted by count. Berguna untuk tahu struktur URL site ("50% URL di bawah /produk/, 30% di /blog/")
   - **URL table**: 100 URL pertama dengan kolom loc / lastmod / priority, searchable filter
   - **Export buttons**: CSV atau JSON, download daftar URL lengkap (bukan cuma 100)

5. Kalau sitemap tidak ditemukan, tool tampilkan pesan "Sitemap tidak ditemukan". Dalam kasus itu, coba input URL sitemap langsung kalau Anda tahu pathnya (kadang di-custom seperti `/sm.xml` atau `/sitemaps/index.xml`).

## Contoh kasus pakai

- **SEO audit cepat** - Sebelum menerima job SEO klien, scan sitemap mereka. Lihat total URL, distribusi lastmod (situs aktif vs dormant), struktur path. Dari situ estimasi scope audit: 100 URL = quick win, 10000 URL = butuh tool serius.

- **Seed URL Mapper untuk crawl lengkap** - Export CSV dari sitemap, import sebagai seed list ke URL Mapper. Lebih efisien daripada mulai dari homepage dan biarkan crawler discover semua URL.

- **Katalog produk e-commerce** - Toko online biasanya maintain sitemap khusus produk (`/sitemap-products.xml`). Analyze untuk extract semua URL produk, export JSON, feed ke scraper custom untuk ambil price/stock.

- **Monitoring published content** - Jalankan analisis mingguan via Scheduler. Bandingkan sitemap minggu ini vs minggu lalu. URL baru = konten baru. Compiler list perubahan untuk newsletter internal atau kompetitor tracking.

- **Validate migrasi situs** - Setelah migrasi CMS atau platform, scan sitemap post-migration. Total URL match dengan ekspektasi? lastmod reset ke tanggal migrasi? Priority distribution masih masuk akal? Kalau ada anomali, troubleshoot sebelum publish.

- **Prioritization reporting** - Export sitemap ke CSV, filter priority >=0.8, dapat list halaman yang pemilik situs prioritaskan untuk SEO. Benchmark vs traffic reality.

- **Legal compliance** - Perusahaan regulated butuh daftar semua halaman publik di situs mereka untuk audit legal. Sitemap export ke JSON dalam 10 detik, bukannya manual enumeration.

- **Robot stewardship** - Sebelum aktifkan scraper brute-force, cek sitemap. Kalau pemilik sudah sediakan URL list lewat sitemap, hormati itu. Jangan crawl situs cuma untuk dapatkan informasi yang sudah eksplisit dipublish via sitemap.

## Apa yang dihitung

### Lastmod distribution

Tool parse field `<lastmod>` tiap URL (format ISO 8601), convert ke datetime UTC-aware, bucket ke:

| Bucket | Kriteria |
|--------|----------|
| 24h | lastmod dalam 24 jam terakhir |
| 7d | 1-7 hari yang lalu |
| 30d | 7-30 hari yang lalu |
| 90d | 30-90 hari yang lalu |
| older | >90 hari yang lalu |
| unknown | field `lastmod` tidak ada atau format tidak valid |

Distribusi ini menunjukkan "health" situs. Banyak di 24h/7d = situs aktif update. Mayoritas "older" + banyak "unknown" = situs stagnan atau sitemap auto-generate tanpa lastmod proper.

### Priority distribution

Field `<priority>` (nilai 0.0 sampai 1.0, default 0.5 di spec sitemap tapi jarang di-set eksplisit), bucket:

| Bucket | Range |
|--------|-------|
| 0.0-0.2 | low priority |
| 0.3-0.5 | medium-low |
| 0.6-0.8 | medium-high |
| 0.9-1.0 | highest priority |
| unknown | tidak ada field priority |

Info ini sinyal dari pemilik situs: halaman mana yang mereka anggap paling penting. Meski Google sudah tidak pakai field priority secara signifikan, nilai ini masih berguna untuk analisis internal.

### Top path prefix

Ekstrak segment pertama dari path URL (misal `/produk/`, `/blog/`, `/kategori/`), count per prefix, sort descending, ambil top 10. Output: list `{path: "/produk", count: 523}`.

Berguna untuk mengerti struktur informasi situs dalam satu glance. Kalau top prefix adalah `/node`, berarti CMS Drupal (typical pattern). Kalau `/?p=` dominan, WordPress default permalink belum di-pretty.

### Unique domains

Set semua netloc (host) yang muncul di loc URL. Sitemap yang baik cuma reference domain sendiri. Kalau ada domain lain (CDN, subdomain), tool tunjukkan supaya Anda tahu.

## Cara kerja internal (teknis)

### Discovery

```python
# Prioritas urutan:
1. Kalau input URL mengandung ".xml" atau ".xml.gz" atau "sitemap", treat sebagai direct
2. Coba GET /sitemap.xml, check kalau response valid XML dengan urlset/sitemapindex
3. Coba GET /sitemap_index.xml
4. Fetch /robots.txt, cari line yang match "Sitemap: <url>"
```

Kalau ketiganya gagal, return `source: not_found`, `sitemap_url: null`, error message.

### Parsing

Pakai lxml (sudah ada di requirements). Parse bytes via `etree.fromstring(data)`. Cek root element tag:

- `sitemapindex`: iterate `<sitemap>` children, extract `<loc>` sebagai sub-sitemap URL
- `urlset`: iterate `<url>` children, extract `<loc>`, `<lastmod>`, `<changefreq>`, `<priority>`
- lainnya: treat as unknown, return empty entries

Namespace handling: XML sitemap spec pakai namespace `http://www.sitemaps.org/schemas/sitemap/0.9`. Tool prepend namespace untuk find, tapi fallback ke find tanpa namespace (beberapa situs tidak declare namespace).

### Recursion

Worklist BFS (queue). Start dengan root sitemap. Tiap iterasi:
1. Pop (url, depth)
2. Kalau sudah visited, skip (dedupe)
3. Fetch bytes
4. Gunzip kalau perlu
5. Parse
6. Kalau sitemapindex dan depth < MAX_DEPTH (2), enqueue semua sub
7. Kalau urlset, collect semua URL ke final list
8. Tambahkan metadata sub-sitemap ke `sub_sitemaps` list untuk report

Limit: max 50 sub-sitemap enqueued total. Ini untuk proteksi di situs massive (Wikipedia punya ribuan sub-sitemap). Kalau limit ter-hit, results tetap valid tapi parsial.

### Lastmod parsing

Coba format berikut berurutan:
- `YYYY-MM-DDTHH:MM:SS+ZZ:ZZ`
- `YYYY-MM-DDTHH:MM:SSZ`
- `YYYY-MM-DD`
- `YYYY-MM-DDTHH:MM:SS.ffff+ZZ:ZZ`
- ISO fromisoformat fallback

Kalau semua gagal, datetime None, lastmod masuk bucket "unknown".

### Gzip handling

```python
if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
    data = gzip.decompress(data)
```

Magic bytes `1f 8b` adalah gzip signature. Cover case ekstensi `.xml` tapi server tetap gzip payload.

## Pengaturan

### MAX_DEPTH
Hardcoded 2. Sitemap index > sub-sitemap > ... depth 2 artinya kita bolehin up to 2 level nesting. Kalau situs pakai lebih dalam, cuma depth 0-2 yang di-recurse.

### MAX_SUB_SITEMAPS
Hardcoded 50. Untuk situs massive seperti news agregator, setting lebih besar butuh edit code. Atau invoke API langsung per sub-sitemap individually.

### sample_urls truncation
Response `analyze` hanya include 100 URL pertama di `sample_urls` untuk efisiensi payload. Untuk URL list lengkap, pakai endpoint `/api/sitemap/download?url=...&format=csv`.

### timeout
30 detik per HTTP request. Sitemap biasanya serve cepat (plain XML), tapi situs pakai CDN bisa lambat kalau miss cache.

## Tips akurasi

- **Sitemap adalah hint, bukan truth.** Sitemap di-generate oleh CMS/tool yang pemilik situs pakai. Kalau plugin sitemap mereka broken, output tidak akurat. URL di sitemap bisa 404 (stale). Content di sitemap bisa tidak include halaman baru yang belum di-regenerate.

- **Cross-check dengan URL Mapper.** Untuk laporan comprehensive, jalankan dua-duanya. Bandingkan: URL yang di sitemap tapi tidak ketemu saat crawl = link rot. URL yang ketemu saat crawl tapi tidak di sitemap = mungkin orphan pages atau sitemap tidak up-to-date.

- **Perhatikan `changefreq` - meski tool tidak aggregate ini, field ada di tiap URL.** Kalau field ini set ke `never` untuk page yang jelas masih update, sitemap stale.

- **lastmod granularity matter.** Beberapa CMS set lastmod hanya ke date (YYYY-MM-DD), beberapa full timestamp. Kalau lastmod cuma date, tool tetap parse sebagai midnight UTC, jadi situs yang "update kemarin" bisa fall ke bucket 24h atau 7d tergantung jam scan.

- **Priority 0.5 mungkin tidak eksplisit.** Default spec adalah 0.5 kalau tidak di-set. Tool report sebagai "unknown" karena field memang tidak ada. Ini intentional: kita report apa yang ada, bukan apa yang default.

- **robots.txt Sitemap: directive bisa multiple.** Beberapa situs declare banyak sitemap di robots. Tool pakai yang pertama ditemukan. Kalau Anda butuh yang lain, fetch manual dari browser dan paste URL spesifik.

## Troubleshooting

### Problem: "no sitemap found"
**Gejala:** source: not_found, total_urls: 0. 
**Penyebab:** Situs tidak punya sitemap di lokasi standar, dan tidak declare di robots.txt. 
**Solusi:** Cek manual `https://situs.com/robots.txt` di browser. Mungkin sitemap ada di path non-standar (`/sm.xml`, `/sitemap/main.xml`, `/media/sitemap.xml`). Input URL tersebut direct.

### Problem: total_urls jauh lebih kecil dari ekspektasi
**Gejala:** Situs besar (ribuan halaman), hasil cuma 100-200 URL. 
**Penyebab:** Kemungkinan sitemap index dengan banyak sub-sitemap, limit MAX_SUB_SITEMAPS (50) ter-hit. Atau sitemap memang inkomplit. 
**Solusi:** Cek field `sub_sitemaps` di response JSON mentah (lihat Network tab browser). Kalau ada banyak "fetch_failed" atau list terpotong, coba analyze sub-sitemap individually.

### Problem: XML parse error
**Gejala:** Error "sitemap xml parse failed" di log. 
**Penyebab:** Server return HTML (404 page) dengan status 200, atau XML invalid (encoding issue, BOM, rogue character). 
**Solusi:** Fetch URL manual di browser, verify response benar-benar XML. Kalau HTML, URL salah. Kalau XML tapi malformed, report ke pemilik situs.

### Problem: lastmod semua "unknown" padahal sitemap jelas punya field
**Gejala:** Distribution 100% di bucket unknown. 
**Penyebab:** Format lastmod exotic (hanya Unix timestamp, format non-ISO, atau wrapped quotation). 
**Solusi:** Inspect sample lastmod raw di UI table. Kalau format tidak standar, report sebagai feature request untuk tambah parser format.

### Problem: priority semua "unknown"
**Gejala:** 100% unknown. 
**Penyebab:** Sitemap tidak include priority field sama sekali (perfectly legal, spec sitemap tidak require). 
**Solusi:** Normal. Priority bukan field wajib dan banyak CMS modern tidak emit.

### Problem: Gzip sitemap error
**Gejala:** "gunzip failed" di log. 
**Penyebab:** File katanya `.gz` tapi isinya bukan gzip valid, atau file doubled-compressed. 
**Solusi:** Download manual via wget/curl, inspect dengan `file <name>` atau `hexdump -C <name> | head`. Kalau bukan gzip, report ke pemilik.

### Problem: Download CSV kosong atau corrupt
**Gejala:** File download ada tapi isi kosong / tidak ada URL. 
**Penyebab:** Analyze cached state vs download fresh fetch. 
**Solusi:** Re-run Analyze, tunggu hingga sukses, baru download.

## Keamanan / etika

> [!WARNING]
> Sitemap adalah data publik by design. Tool ini baca, tidak ubah apa-apa di server.

- **Request minimal footprint.** Analysis umumnya 1-10 request HTTP (1 untuk root sitemap, beberapa untuk sub-sitemap). Tidak brute force, tidak probe path non-sitemap.

- **Respect robots.txt.** Tool fetch `/robots.txt` hanya untuk cari Sitemap directive, bukan untuk probe rules lain. Tidak crawl URL yang di-Disallow.

- **Rate-limiting.** Kalau situs rate-limit per IP, recursion sub-sitemap bisa kena. Pakai proxy rotation di Settings kalau scan banyak sitemap.

- **Jangan scrape data yang di-protect.** URL di sitemap adalah publik, tapi konten di balik URL bisa privat (paywall, member area). Punya daftar URL tidak berarti boleh akses kontennya.

- **Etika export.** Kalau Anda export sitemap ke CSV untuk klien, attribute source. Jangan claim Anda "audit crawl" full situs kalau sebenarnya cuma parse sitemap.

- **Competitive intelligence limits.** Pakai sitemap kompetitor untuk riset OK dalam kapasitas personal/strategic research. Pakai untuk automasi scraping massive konten mereka bisa melanggar Terms of Service situs atau law di beberapa yurisdiksi. Be responsible.

## Related docs

- [Domain Intel](/docs/intel/domain.md) - WHOIS + DNS + subdomain enumeration
- [Wayback Machine Explorer](/docs/intel/wayback.md) - snapshot historis URL yang ditemukan
- [URL Mapper](/docs/tools/url-mapper.md) - crawl aktif untuk complement sitemap findings
- [Tech Stack Detector](/docs/tools/tech-detector.md) - setelah tahu URL, bisa scan tech stack per page
- [Bulk Queue](/docs/advanced/bulk-queue.md) - feed URL dari sitemap export ke batch jobs
- [Scheduled Jobs](/docs/system/scheduled.md) - jadwalkan analyze periodik untuk monitoring perubahan sitemap
