# PDF Harvester

> PDF Harvester adalah utility di group Utilities PyScrapr untuk crawl situs, kumpulkan semua link PDF, download, ekstrak metadata plus first-page preview, dan build searchable full-text index. Anda paste seed URL, atur depth crawl (1-4) dan limit (max_pages 1-500, max_pdfs 1-200), tool akan BFS crawl stay-on-domain, deteksi PDF dari URL atau Content-Type header, download dengan throttle 1 request/sec per host plus max 3 PDF paralel. PyMuPDF extract metadata (title, author, subject, keywords, creator, producer, dates, page count, file size), first-page preview 500 char, dan full-text index 5000 char per page max 20 pages. Hasil bisa di-search dengan substring case-insensitive plus snippet, atau export ke CSV. Cocok untuk riset paper akademik, audit dokumen publik perusahaan (annual report, prospektus), due diligence kompetitor, atau compliance harvest privacy policy.

## Apa itu PDF Harvester

PDF Harvester ada di group Utilities (warna pink, route `/pdf-harvester`, bukan tier P karena positioning sebagai support utility, bukan main tool). Tool ini sederhana: "saya butuh semua PDF dari situs ini, dengan metadata dan content yang searchable". Sederhana di permukaan, tapi solve beberapa friction klasik:

- Manual download PDF satu per satu via klik dan save-as = capek + miss yang tersembunyi di dalam halaman.
- PDF tidak terindex di Google site search dengan reliable (kadang ya, kadang tidak).
- Setelah download, metadata extraction butuh tool tambahan (Adobe Acrobat, Foxit, dst).
- Full-text search di koleksi PDF butuh setup local Spotlight/Windows Search atau tool seperti pdfgrep.

PDF Harvester gabungkan crawl + download + extract + index dalam satu workflow. Hasil: folder dengan semua PDF, plus database in-memory yang searchable, plus CSV manifest.

Beda dengan [Site Ripper](/docs/tools/site-ripper.md) yang clone seluruh situs (HTML, CSS, JS, image, PDF, dst): PDF Harvester laser-focus ke PDF dengan ekstraksi spesifik dan search index. Lebih ringan, lebih tepat sasaran. Beda dengan [Image Harvester](/docs/tools/image-harvester.md) yang fokus ke gambar: PDF Harvester equivalent untuk dokumen.

> [!NOTE]
> Storage PDF di `data/pdf_harvester/{job_id}/{filename}`. Setiap job baru dapat folder terpisah. Tidak ada auto-cleanup, manage sendiri kalau disk space jadi concern (lihat section Storage di bawah).

## Cara pakai

Buka menu **PDF Harvester** di sidebar Utilities (warna pink, ikon dokumen). Halaman: form input di atas, area progress live di tengah, panel search + hasil di bawah.

### Langkah 1: Setup crawl

1. Paste `Seed URL` di header. Tool akan extract base domain dan crawl stay-on-domain.
2. Atur parameter:
   - **Max depth**: 1-4. Default 2. Depth 1 = seed only, depth 2 = seed + halaman link langsung, depth 3 = 2 hop, depth 4 = 3 hop (jarang butuh).
   - **Max pages**: 1-500. Default 50. Hard cap halaman HTML yang di-crawl.
   - **Max PDFs**: 1-200. Default 30. Hard cap PDF yang di-download.
3. (Opsional) Atur opsi:
   - **Respect robots.txt** (default on).
   - **Throttle requests per second** (default 1 per host).
   - **Verify SSL** (default on, matikan untuk dev/staging dengan self-signed cert).

### Langkah 2: Run job

Klik **Start harvest**. Backend spawn job dengan SSE progress streaming. Area progress menampilkan:

- Halaman HTML yang di-crawl: `12/50`
- Link PDF discovered: `47`
- PDF downloaded: `15/30`
- ETA berdasarkan rate

Job bisa di-cancel kapan saja via tombol Stop. PDF yang sudah di-download tetap, partial job state simpan di History.

### Langkah 3: Eksplorasi hasil

Setelah job selesai, panel hasil tampilkan grid PDF cards. Tiap card:

- Thumbnail dari first page (PNG render via PyMuPDF).
- Title (dari metadata, fallback ke filename).
- Author + page count.
- File size.
- First-page preview (500 char text).
- Source URL (halaman dimana link PDF discovered).
- Tombol Download (re-download original) dan Open folder.

Click card untuk expand: full metadata + paging preview teks per halaman.

### Langkah 4: Search

Field search di kanan atas hasil. Substring case-insensitive, search di full-text index (semua halaman PDF, max 5000 char per page x 20 page = 100k char per PDF).

Hasil search highlight snippet 80 char sebelum dan setelah match. Click snippet untuk jump ke PDF source, page tertentu.

### Langkah 5: Export

Tombol **Export CSV** download manifest dengan kolom: `filename`, `title`, `author`, `subject`, `keywords`, `creator`, `producer`, `creation_date`, `mod_date`, `page_count`, `file_size`, `source_url`, `download_url`, `local_path`.

## Crawl method & PDF detection

### BFS crawl

Tool pakai BFS (Breadth-First Search) start dari seed. Queue managed in-memory dengan visited set untuk avoid loop. Tiap iterasi:

1. Pop URL dari queue.
2. Fetch HTML (timeout 30s).
3. Parse semua `<a href>`, `<iframe src>`, `<embed src>`, `<link rel>`.
4. Untuk tiap link:
   - Kalau same-origin dengan seed dan depth belum max: tambah ke queue HTML (akan di-crawl iterasi nanti).
   - Kalau pointing ke PDF (deteksi di bawah): tambah ke queue PDF download.
5. Throttle 1s sebelum next request ke host yang sama.

Crawl stop kalau:

- Queue HTML kosong dan queue PDF kosong, atau
- `max_pages` halaman HTML sudah di-fetch, atau
- `max_pdfs` PDF sudah di-download.

### PDF detection

URL dianggap PDF kalau:

1. **URL ends dengan `.pdf`** (case insensitive): paling cepat, no HTTP request.
2. **HEAD request return `Content-Type: application/pdf`**: untuk URL tanpa `.pdf` extension (mis. download link `?file=123`). Tool kirim HEAD untuk verify sebelum commit ke GET full file.
3. **First bytes magic `%PDF-`**: fallback kalau HEAD tidak return Content-Type yang jelas. Tool GET dengan range header `bytes=0-100`, cek magic.

Concurrent download: max 3 PDF paralel via `asyncio.Semaphore(3)`. Per-host throttle 1s tetap berlaku.

## Metadata yang di-extract

Tool pakai `PyMuPDF` (alias `fitz`) untuk parse PDF. Field yang di-extract:

| Field | Source | Contoh |
|-------|--------|--------|
| `title` | doc.metadata['title'] | "Annual Report 2025" |
| `author` | doc.metadata['author'] | "ACME Corporation" |
| `subject` | doc.metadata['subject'] | "Financial Statements" |
| `keywords` | doc.metadata['keywords'] | "annual,2025,financials" |
| `creator` | doc.metadata['creator'] | "Microsoft Word for Office 365" |
| `producer` | doc.metadata['producer'] | "Adobe PDF Library 15.0" |
| `creation_date` | doc.metadata['creationDate'] | "2026-03-15T10:30:00Z" |
| `mod_date` | doc.metadata['modDate'] | "2026-03-20T14:22:00Z" |
| `page_count` | len(doc) | 87 |
| `file_size` | os.path.getsize | 4523891 bytes |
| `preview` | doc.load_page(0).get_text()[:500] | First page first 500 char |
| `text_content` | iterate pages | Full-text untuk search index |

Beberapa PDF tidak punya metadata isi (creator generic, title kosong). Tool fallback ke filename sebagai title. Field yang null di JSON.

> [!TIP]
> Metadata PDF sering mengandung clue tentang origin dokumen: software yang dipakai (Word, LaTeX, InDesign), tanggal creation actual, author internal. Useful untuk forensik atau audit kalau dokumen claim origin tertentu tapi metadata-nya bertolak belakang.

## Full-text search

### Indexing strategy

Setelah PDF download, tool iterate halaman:

- Max 20 halaman pertama (cap untuk PDF besar seperti buku 500 halaman).
- Per halaman: extract text via `page.get_text()`, ambil 5000 char pertama.
- Concat semua jadi `text_content` per PDF.
- Store di in-memory `PdfSearchIndex` dictionary `{filename: text_content}`.

Total worst case per PDF: 20 x 5000 = 100k char. Untuk 100 PDF, 10MB text di memory. Reasonable.

### Search behavior

Search query (substring) di-test terhadap `text_content` setiap PDF. Match: case-insensitive substring. Untuk match yang ditemukan, snippet generator return 80 char context (40 sebelum + 40 sesudah match, dengan ellipsis kalau mid-string).

Tidak ada fuzzy search, tidak ada stemming, tidak ada synonym. Substring murni. Untuk advanced search, export CSV dan analisis di Pandas atau Whoosh/Elasticsearch.

```
Query: "compliance"
Match found in:
  - annual-report-2025.pdf (page 3): "...our compliance framework follows ISO 27001..."
  - privacy-policy.pdf (page 1): "...this policy is published for compliance with GDPR..."
  - audit-q4.pdf (page 5): "...compliance officer reviewed all..."
```

### Limitations

- **Image-based PDF**: PDF yang isinya scan/foto (bukan teks selectable) tidak akan ter-index. PyMuPDF return empty string. Tool tidak run OCR (out of scope, pakai Metadata Inspector OCR atau tool dedicated).

- **Encrypted PDF**: kalau di-password protect, PyMuPDF return error. Lihat Troubleshooting.

- **Halaman 21+**: di-skip karena cap 20 page. Title + first page metadata tetap captured. Untuk full coverage PDF panjang, fork tool atau adjust setting `pdf_harvester_max_pages_per_doc`.

## Storage & cleanup

### Struktur folder

```
data/pdf_harvester/
  job-abc123-20260512/
    annual-report-2025.pdf
    privacy-policy.pdf
    audit-q4.pdf
    manifest.json
  job-def456-20260513/
    ...
```

`manifest.json` simpan metadata index yang sama dengan CSV export, untuk re-load tanpa re-parse PDF.

### Disk space management

PDF bisa besar (1-50 MB per file, kadang 200+ MB untuk annual report). 100 PDF mungkin 1-5 GB total. Tidak ada auto-cleanup.

Cara cleanup manual:

1. Buka folder `data/pdf_harvester/` di file explorer.
2. Identify job_id yang sudah tidak butuh (dari History tab di PyScrapr).
3. Delete folder job_id terkait.

Atau pakai retention policy di Settings: `pdf_harvester_retention_days` (default 0 = no auto-cleanup). Set ke 30 untuk auto-delete folder yang lebih dari 30 hari.

## Contoh skenario

### 1. Riset paper akademik dari journal site

PhD student riset topik X, mau download semua paper open-access dari satu journal site untuk literature review. Journal punya 500+ paper, search internal-nya jelek.

Setup: seed URL = browse page journal. Max depth 3 (browse > issue > article > PDF link). Max pages 200, max PDFs 100. Throttle 1 req/sec (sopan ke server akademik). Run overnight.

Hasil pagi: 87 PDF downloaded (sisanya behind paywall, tool report mengapa skip), metadata complete dengan field `keywords` per paper (useful untuk topic clustering). Search "machine learning" return 24 PDF dengan snippet, jadi shortcut shortlist untuk dibaca prioritas.

### 2. Audit dokumen publik perusahaan publik (annual report, prospektus)

Analis equity audit emiten Bursa Efek Indonesia. Emiten publish annual report 5 tahun terakhir di situs IR (Investor Relations). Manual download per tahun.

Setup: seed URL = halaman IR /annual-reports. Max depth 2, max PDFs 50. Hasil: 5 annual report (2021-2025) + 8 quarterly report + 3 prospektus penawaran umum + several investor presentation. Total 24 PDF, 1.2 GB. Search "revenue growth" untuk quick benchmark across years.

### 3. Due diligence: harvest semua technical spec PDF dari kompetitor

Sales engineer prep proposal untuk competitive bid. Kompetitor publish technical datasheet di situs produk mereka untuk SEO + lead gen.

Setup: seed URL = produk page kompetitor. Max depth 3 (browse > product family > product detail > datasheet PDF). Max PDFs 80. Hasil: 60 datasheet semua line produk. Metadata `creator` reveal tool yang dipakai (Adobe FrameMaker, common untuk technical docs). Search istilah-istilah spesifik (`MTBF`, `temperature range`, `certifications`) untuk identify gap di produk sendiri.

### 4. Compliance: collect semua privacy policy / Terms of Service

Privacy officer perusahaan B2B mau benchmark privacy policy 50 kompetitor untuk pattern compliance. Manual download privacy policy 50 situs = 1-2 hari dengan klik per situs.

Setup: ada list 50 domain. Run PDF Harvester per domain (atau batch script via REST API), seed URL = homepage tiap domain. Max depth 2 (homepage > footer > privacy/terms page > PDF). Max PDFs 5 per domain (privacy + terms + cookie + DPA + data processing addendum). Total 1-2 jam jalan paralel. Output 200+ PDF, search "GDPR Article 28" untuk identify yang explicit reference, search "data retention" untuk policy compare.

## Tips & best practices

- **Set max_pdfs reasonable.** 30-50 untuk eksplorasi awal. Kalau hasil terlihat promising, baru re-run dengan limit lebih tinggi.

- **Throttle penting.** Default 1 req/sec sopan. Jangan turunkan untuk situs akademik atau pemerintah (mereka biasanya pakai server kecil). Naikkan hanya untuk situs corporate yang clearly handle traffic besar.

- **Cek robots.txt situs target.** Beberapa situs (mis. arXiv) explicit allow crawl dengan rate limit specific. Hormati. Beberapa explicit forbid (mis. paywall journal), jangan paksa.

- **Deteksi rate limit awal.** Kalau Anda lihat banyak HTTP 429 di progress log, langsung stop, naikkan throttle. Continuing di rate sama bisa bikin IP block.

- **Manfaatkan metadata untuk filter.** Setelah harvest, filter CSV by `creator` (kalau Anda hanya butuh dokumen dari software tertentu) atau `creation_date` (kalau Anda butuh hanya dokumen baru tahun ini).

- **Backup periodik.** Folder `data/pdf_harvester/` adalah asset Anda kalau riset jangka panjang. Backup ke external drive atau cloud (dengan privacy consideration kalau dokumen Anda confidential).

## Troubleshooting

### Problem: PDF gagal parse via PyMuPDF

**Gejala:** Error log "PyMuPDF MuPDF error: format error". PDF terdownload tapi metadata kosong.
**Penyebab:** PDF malformed, atau format aneh (mis. PDF/A-3 dengan embedded XML).
**Solusi:** PDF tetap terdownload, Anda bisa buka manual via Acrobat/Foxit/browser. Metadata sebagian mungkin extractable via tool lain (qpdf, pdfinfo). Open issue kalau ada pattern repeat.

### Problem: PDF terenkripsi (password protected)

**Gejala:** PyMuPDF raise `MuPDFError: cannot open encrypted document`.
**Penyebab:** PDF di-password protect (owner password atau user password).
**Solusi:** Tool skip extract metadata + text, tapi PDF tetap downloaded. Kalau Anda punya password legitimate, decrypt manual via qpdf (`qpdf --password=X --decrypt input.pdf output.pdf`), lalu re-run harvest pakai folder lokal.

### Problem: Ukuran PDF besar (300+ MB), download timeout

**Gejala:** PDF besar gagal download dengan error timeout.
**Penyebab:** Default timeout 60 detik tidak cukup untuk file besar di koneksi lambat.
**Solusi:** Naikkan `pdf_harvester_download_timeout_seconds` di Settings (mis. ke 300). Atau skip file besar dengan setting `pdf_harvester_max_filesize_mb` default 100, Anda bisa turunkan untuk filter atau naikkan untuk include.

### Problem: Crawl macet di halaman tertentu

**Gejala:** Progress stuck di halaman x/50 lama.
**Penyebab:** Halaman lambat respond, atau JS-rendered (tool tidak run JS by default).
**Solusi:** Tool tunggu sampai timeout (30s) lalu skip. Kalau pattern repeat, exclude path tersebut via setting filter atau skip dengan max_pages.

### Problem: Hasil search empty padahal kata pasti ada di PDF

**Gejala:** Search "compliance" return 0 result, tapi Anda buka PDF manual dan kata ada.
**Penyebab:** PDF image-based (scan), text tidak extractable via PyMuPDF.
**Solusi:** Run OCR external (Tesseract, pdfocr) untuk convert ke searchable PDF, lalu re-import. PyScrapr [Metadata Inspector](/docs/utilities/metadata.md) punya OCR fitur untuk single-file workflow.

## Etika

> [!IMPORTANT]
> PDF di internet tunduk pada copyright dan ToS situs hosting. Patuhi aturan dasar.

- **Copyright awareness.** Annual report perusahaan publik biasanya public domain untuk konsumsi (read, analyze). Tapi redistribusi tetap butuh attribution dan tidak boleh commercial resale.

- **Scientific paper paywall.** Banyak paper di-locked di paywall (Elsevier, Springer, etc). Kalau situs requires login, tool tidak akan dapat akses. Jangan circumvent (mis. login dengan akun teman, dst). Pakai open-access alternative (arXiv, PubMed Central, SSRN).

- **Fair use untuk research.** Untuk konsumsi internal research (Anda baca, Anda analisis untuk thesis/decision Anda), banyak yurisdiksi consider fair use. Untuk publikasi atau redistribusi, butuh permission atau license.

- **Hormati robots.txt.** Default on. Jangan disable untuk situs pihak ketiga.

- **Throttle sopan.** Server akademik / pemerintah / nonprofit biasanya budget hosting terbatas. Jangan agresif.

- **Government documents.** Dokumen pemerintah Indonesia (Perpres, Permen, UU) public domain. Audit publik welcome. Tapi tetap throttle dan attribute source.

- **Confidential leak.** Kalau Anda accidentally harvest PDF yang ternyata confidential (leak via misconfig server), jangan share. Notify pemilik via security email atau responsible disclosure. Jangan publish.

## Pengaturan teknis

| Key | Tipe | Default | Keterangan |
|-----|------|---------|------------|
| `pdf_harvester_enabled` | boolean | true | Master switch |
| `pdf_harvester_max_depth_default` | integer | 2 | Default depth |
| `pdf_harvester_max_pages_default` | integer | 50 | Default cap HTML pages |
| `pdf_harvester_max_pdfs_default` | integer | 30 | Default cap PDF download |
| `pdf_harvester_throttle_per_host_seconds` | float | 1.0 | Delay per request ke host sama |
| `pdf_harvester_concurrent_downloads` | integer | 3 | PDF paralel download |
| `pdf_harvester_download_timeout_seconds` | integer | 60 | Timeout per PDF |
| `pdf_harvester_max_filesize_mb` | integer | 100 | Skip PDF lebih besar dari ini |
| `pdf_harvester_max_pages_per_doc` | integer | 20 | Cap page untuk extraction |
| `pdf_harvester_chars_per_page` | integer | 5000 | Cap char per page di index |
| `pdf_harvester_retention_days` | integer | 0 | Auto-cleanup (0 = off) |
| `pdf_harvester_respect_robots` | boolean | true | Hormati robots.txt |

## Related docs

- [Site Ripper](/docs/tools/site-ripper.md) - clone seluruh situs (HTML+CSS+JS+assets+PDF) untuk offline browsing
- [URL Mapper](/docs/tools/url-mapper.md) - peta URL situs tanpa download asset
- [Metadata Inspector](/docs/utilities/metadata.md) - PDF property + OCR untuk image-based PDF
- [Image Harvester](/docs/tools/image-harvester.md) - equivalent harvest untuk gambar
- [Custom Pipeline](/docs/utilities/pipeline.md) - transformasi manifest CSV jadi format custom
- [Settings](/docs/system/settings.md) - semua flag PDF Harvester
