# OSINT Harvester

> OSINT Harvester adalah tool tier P9 di PyScrapr untuk passive intelligence gathering dari halaman web publik. Anda masukkan satu URL atau seed domain, tool akan crawl (opsional), parse HTML mentah + JavaScript inline, dan ekstrak artefak yang sering tercecer: alamat email, akun social media, nomor telepon Indonesia, link ke cloud storage publik (S3, Google Drive, Dropbox, Pastebin, Gist), API key yang bocor di source code frontend, plus pattern custom regex Anda sendiri. Hasil rapi dalam tabel per-kategori, bisa di-export CSV / JSON, dan setiap finding di-link balik ke URL tempat dia ditemukan untuk verifikasi manual. Tool ini didesain untuk audit situs sendiri, riset OSINT yang legal, atau menemukan kebocoran credential di proyek frontend tim Anda sebelum attacker yang menemukannya.

## Apa itu OSINT Harvester

OSINT (Open Source Intelligence) adalah praktek mengumpulkan informasi dari sumber publik untuk membentuk gambaran tentang sebuah target. Dalam konteks web, sumber publik berarti halaman yang bisa Anda akses tanpa autentikasi: homepage, about page, kontak, blog, footer, file `robots.txt`, sitemap, file JS yang di-load browser, komentar HTML, dan metadata. Banyak organisasi tidak sadar betapa banyak data yang ter-expose di sana.

Threat sederhana yang sering luput: developer commit `.env` ke repo public, lalu file itu di-serve oleh build tool. API key Stripe, AWS, OpenAI, atau Mailgun bisa di-baca siapa saja yang `view-source` halaman. Marketing intern paste alamat email tim sales di footer untuk SEO, tahun depan domain itu di-scrape spam bot dan inbox tim banjir phishing. Founder tag akun Twitter pribadinya di halaman tim, attacker pakai itu untuk profile social engineering.

OSINT Harvester adalah jawaban PyScrapr untuk pertanyaan: "Apa saja yang bocor di situs saya kalau saya jadi attacker yang baru pertama lihat?". Anda jalankan ini di domain Anda sendiri, bandingkan output dengan ekspektasi, lalu remediasi yang perlu di-remediasi.

Positioning tool ini berbeda dari scanner Burp Suite atau OWASP ZAP. Tool ini tidak melakukan probing aktif, tidak ada injection, tidak ada brute force. Murni passive: GET halaman, parse, regex extract, return. Footprint serupa scraper biasa, server target tidak akan tahu Anda sedang audit.

> [!WARNING]
> Pakai tool ini hanya pada domain yang Anda miliki, klien yang memberi izin tertulis, atau riset jurnalistik yang etika-nya jelas. Menjalankan OSINT Harvester di domain pihak ketiga tanpa izin lalu menggunakan hasil untuk spam, harassment, atau competitive harvesting adalah pelanggaran etika dan beberapa yurisdiksi pidana. Lihat section Etika di bawah.

## Cara pakai

Buka PyScrapr, navigasi ke menu **OSINT Harvester** di sidebar Tools (warna hijau, ikon daun, shortcut `Ctrl+9`). Halaman terbuka dengan dua mode tab: Single page dan Crawl mode.

### Mode 1: Single page

Mode paling cepat dan paling fokus. Anda paste satu URL, tool fetch halaman itu saja, parse, extract, return.

1. Pilih tab **Single page**.
2. Paste URL target di field `URL halaman`. Format apapun diterima (`example.com`, `https://example.com/about`, `www.example.com`).
3. (Opsional) Atur kategori yang ingin di-extract via toggle: Email, Social, Phone, Cloud, Secret, Custom regex. Default semua aktif kecuali Secret.
4. Klik **Harvest**. Backend GET halaman dengan timeout 30 detik, parse, run regex matchers, dedupe, return.
5. Hasil muncul di panel kanan dalam bentuk tabel per-kategori dengan kolom: nilai, source URL (tempat ditemukan), context snippet 80 karakter, dan jumlah occurrence kalau muncul lebih dari sekali.

Single page cocok untuk audit cepat halaman tunggal, contact page klien, atau debug regex custom Anda di sample known-content sebelum jalankan crawl besar.

### Mode 2: Crawl

Crawl mode adalah single page tapi diperluas: tool akan follow link internal sampai depth tertentu, harvest tiap halaman, lalu agregat hasil.

1. Pilih tab **Crawl mode**.
2. Paste seed URL di field `Seed URL`. Tool akan extract base domain dari URL ini, dan crawl hanya stay-on-domain.
3. Atur `Depth` (1-3, default 2). Depth 1 = seed page only. Depth 2 = seed + halaman yang di-link langsung dari seed. Depth 3 = seed + 2 hop link discovery.
4. Atur `Max pages` (default 50, max 200). Guard supaya crawl tidak runaway di situs besar.
5. (Opsional) Toggle kategori sama seperti single page mode.
6. Klik **Mulai Crawl**. Backend spawn job, register di History, mulai BFS crawl dengan SSE progress streaming.
7. Progress bar tampilkan jumlah halaman yang sudah di-fetch, jumlah finding per kategori running total, ETA berdasarkan rate.
8. Setelah selesai, hasil agregat muncul. Setiap finding tetap di-link ke source URL spesifik supaya Anda bisa verifikasi.

Crawl mode butuh waktu lebih lama (2-10 menit untuk 50 halaman tergantung response time situs target) tapi memberi gambaran menyeluruh.

## Kategori ekstraksi

OSINT Harvester punya 6 kategori extractor, masing-masing dengan regex matcher dan validator yang spesifik.

### 1. Email

| Aspek | Detail |
|-------|--------|
| Regex | RFC 5322 simplified: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` |
| Sumber yang di-cek | HTML body, `mailto:` href, JSON-LD structured data, komentar HTML, alt/title attribute |
| Filter | Anti-decoy: skip `noreply`, `donotreply`, `example@example.com`, `test@test.com`, `user@domain.com`. Skip image filename yang mirip email (`logo@2x.png`) |
| Output | Alamat email + count per source URL |

Cocok untuk: audit kebocoran kontak tim, riset cold outreach (untuk relasi bisnis legitimate), build daftar kontak resmi.

### 2. Social handles

| Platform | Pattern |
|----------|---------|
| Twitter / X | `twitter.com/<handle>`, `x.com/<handle>` |
| Facebook | `facebook.com/<page>`, `fb.com/<page>` |
| Instagram | `instagram.com/<handle>` |
| LinkedIn | `linkedin.com/in/<slug>`, `linkedin.com/company/<slug>` |
| YouTube | `youtube.com/c/<channel>`, `youtube.com/@<handle>` |
| GitHub | `github.com/<user>` |
| TikTok | `tiktok.com/@<handle>` |
| Telegram | `t.me/<handle>`, `telegram.me/<handle>` |
| Discord | invite link `discord.gg/<code>`, `discord.com/invite/<code>` |

Filter: skip share-button tracker URL (`twitter.com/share?url=...`), skip widget embed.

### 3. Indonesian phones

| Format | Contoh |
|--------|--------|
| `+62` formal | `+62 21 5550-1234`, `+6281234567890` |
| `08` lokal | `0812-3456-7890`, `08123456789` |
| `021` landline Jakarta | `021-5550-1234`, `(021) 5550 1234` |
| Format kota lain | `024-` Semarang, `031-` Surabaya, `0274-` Yogya, dst |

Validator: minimal 9 digit setelah country/area code, maximal 13 digit total. Skip nomor di dalam tag `<style>` atau `<script>` numerik literal.

### 4. Cloud artifacts

Link ke external storage / sharing service yang sering jadi sumber kebocoran tidak sengaja.

| Service | Pattern |
|---------|---------|
| AWS S3 | `*.s3.amazonaws.com`, `s3.<region>.amazonaws.com/<bucket>`, `*.s3-<region>.amazonaws.com` |
| Google Drive | `drive.google.com/file/d/<id>`, `docs.google.com/document/d/<id>` |
| Dropbox | `dropbox.com/s/<id>`, `dropbox.com/scl/fi/<id>` |
| Pastebin | `pastebin.com/<id>`, `pastebin.com/raw/<id>` |
| GitHub Gist | `gist.github.com/<user>/<id>`, `gist.githubusercontent.com/<user>/<id>` |
| Mega | `mega.nz/file/<id>`, `mega.nz/folder/<id>` |
| OneDrive | `1drv.ms/...`, `onedrive.live.com/...` |

Cocok untuk: cek apakah marketing tim Anda link ke S3 bucket public yang seharusnya restricted, audit Pastebin paste yang mungkin sisa debug session.

### 5. Secret leaks (DEFAULT OFF)

| Tipe | Pattern |
|------|---------|
| AWS Access Key | `AKIA[0-9A-Z]{16}` |
| AWS Secret Key | heuristic `[A-Za-z0-9/+=]{40}` di dalam JS dengan keyword sekitar `aws_secret`, `secret_access_key` |
| Stripe live key | `sk_live_[a-zA-Z0-9]{24,}` |
| Stripe public key | `pk_live_[a-zA-Z0-9]{24,}` |
| OpenAI API key | `sk-[a-zA-Z0-9]{48}` |
| Google API key | `AIza[0-9A-Za-z\-_]{35}` |
| Mailgun key | `key-[a-z0-9]{32}` |
| Slack token | `xox[baprs]-[0-9a-zA-Z\-]{10,}` |
| Generic JWT | `eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+` |

> [!WARNING]
> Secret extractor default OFF dan harus di-enable manual via toggle. Outputnya redacted otomatis: hanya 4 karakter pertama + 4 terakhir yang ditampilkan (`AKIA****EXAMPLE`), dengan source URL untuk Anda lihat sendiri di browser. Tujuannya: hindari secret tampil di screenshot atau log Anda saat audit. Kalau Anda butuh value penuh, klik tombol "Reveal" per finding (tercatat di audit log lokal).

### 6. Custom regex

Anda bisa tambah pattern Anda sendiri di field `Custom regex` (max 5 pattern per scan). Format: satu regex per baris, label opsional dipisah `|`. Contoh:

```
\bSKU-\d{6}\b|product-sku
NDA-\d{4}-\d{2}|nda-doc-id
\binternal-[a-z0-9]{8}\b|internal-ref
```

Tool akan test setiap pattern di setiap halaman, output di tab "Custom" terpisah dengan label sebagai grouping.

## Filter & opsi

Beberapa toggle dan setting yang fine-tune behavior:

- **Render JavaScript** (default OFF). Saat OFF, tool pakai HTTP fetch biasa via httpx. Cepat dan ringan, tapi miss konten yang di-render React/Vue/Angular setelah page load. Saat ON, tool dispatch ke Playwright (`tools.playwright_enabled` harus true), wait `domcontentloaded`, ambil HTML akhir. Lebih lambat (2-5 detik per halaman) tapi catch SPA content.

- **Stay on domain** (default ON). Crawl mode hanya follow link yang same-origin dengan seed. Matikan untuk allow follow external link sampai depth - hati-hati, scope bisa meledak.

- **Respect robots.txt** (default ON). Tool baca `/robots.txt` di seed domain, skip path yang `Disallow`. Matikan kalau Anda audit situs sendiri dan robots.txt-nya juga yang Anda kontrol.

- **Stealth mode** (default OFF). Pakai Playwright Stealth (lihat docs Playwright). Berguna untuk situs yang aktif anti-bot. Off by default karena overhead-nya 200-500ms per halaman.

- **Min context length**. Default 80 karakter. Jumlah karakter sebelum + sesudah finding yang ditampilkan untuk konteks. Naikkan kalau Anda butuh lihat lebih banyak surrounding text.

- **Dedupe across pages** (default ON). Email yang sama muncul di 10 halaman dihitung 1 finding dengan count 10. Matikan kalau Anda butuh per-page evidence untuk laporan.

## Output & export

Hasil scan tersedia dalam dua format export.

### JSON export

Klik tombol **Export JSON** di kanan atas hasil. Struktur:

```json
{
  "scan_id": "osint-2026-04-29-abc123",
  "seed": "https://example.com",
  "mode": "crawl",
  "pages_crawled": 47,
  "duration_seconds": 312,
  "findings": {
    "email": [
      {
        "value": "contact@example.com",
        "count": 12,
        "sources": [
          {"url": "https://example.com/about", "context": "...email kami contact@example.com untuk inquiry..."},
          {"url": "https://example.com/contact"}
        ]
      }
    ],
    "social": [...],
    "phone": [...],
    "cloud": [...],
    "secret": [...],
    "custom": [...]
  }
}
```

Cocok untuk: import ke tool lain (Splunk, ELK, custom dashboard), simpan sebagai evidence audit, diff dengan scan sebelumnya untuk cek delta.

### CSV export

Klik tombol **Export CSV**. Format flat: satu baris per finding dengan kolom `category`, `value`, `source_url`, `context`, `count`. Cocok untuk Excel atau Google Sheets, terutama saat Anda butuh share hasil ke stakeholder non-teknis.

### History entry

Setiap scan tercatat di History dengan `type=OSINT_HARVEST`, parameter (seed, depth, max_pages, kategori aktif), summary (counts per kategori), durasi. Anda bisa rerun dari History dengan satu klik, semua parameter dipertahankan.

## Contoh skenario

### 1. Audit kebocoran kontak situs sendiri

Founder startup mau cek seberapa banyak alamat email tim ter-expose di domain perusahaan. Mode Crawl, depth 3, max pages 100, kategori Email + Social aktif. Hasil: 47 alamat email unik (banyak yang format `nama@startup.com` dari tim, beberapa email pribadi tim sales yang ter-paste di blog post 2 tahun lalu, dan satu `wp-admin@startup.com` yang tidak boleh ada di public). Action: redact email pribadi dari blog lama, hapus user `wp-admin` yang sudah tidak dipakai, ganti dengan form contact.

### 2. Riset OSINT public figure (legal)

Jurnalis riset tokoh politik publik. Crawl situs partai dan kampanye, depth 2, max pages 80, kategori Email + Social + Phone. Tujuan: validasi info kontak resmi yang konsisten dengan klaim publik. Etika: target adalah figur publik dalam kapasitas publik, sumber semua publik, tidak ada upaya hack atau bypass authentication. Hasil di-cite di artikel sebagai "menurut situs resmi X".

### 3. Competitor email research (legitimate)

Sales lead butuh kontak resmi tim partnership di kompetitor untuk inquiry kerja sama produk komplementer. Mode Single page di halaman "Partners" atau "Contact" kompetitor. Hasil: alamat partnerships@kompetitor.com. Outreach legitimate dengan disclosure jelas siapa Anda dan tujuan, bukan spam blast.

### 4. Cloud bucket discovery untuk app sendiri

DevOps audit aplikasi web internal. Crawl admin portal yang seharusnya hanya akses internal. Kategori Cloud aktif. Hasil: 3 link `*.s3.amazonaws.com/internal-uploads/...` di JS bundle yang ternyata public-readable. Action: tutup public access bucket, regenerate URL pre-signed untuk asset yang memang perlu publik.

### 5. Secret leak hunt di proyek frontend tim

Lead engineer audit frontend bundle pre-deploy. Single page mode di staging URL, kategori Secret aktif (toggle on manual). Hasil: 1 finding `AKIA****EXAMPLE` di bundle.js + 1 `sk_live_****abcd` Stripe live key. Action: rotate kedua key segera, audit git history untuk first appearance, tambah pre-commit hook untuk block commit dengan secret pattern.

### 6. Compliance audit GDPR / PDP

Privacy officer cek apakah formulir kontak di website mengirim data ke cloud third-party yang tidak di-disclose di privacy policy. Crawl situs, kategori Cloud + Custom regex untuk endpoint API third-party (`api.thirdparty.com`, `analytics.<vendor>.com`). Hasil: 2 endpoint analytics yang belum tercantum di privacy policy. Action: update privacy policy atau cabut integration.

## Etika & batasan

> [!IMPORTANT]
> Tool ini didesain untuk audit, riset, dan due diligence yang etis. Aturan dasar yang wajib Anda patuhi sebelum menjalankan scan ke domain non-milik:

- **Audit own site dulu.** Default workflow: jalankan ke domain Anda sendiri atau klien yang memberi izin tertulis. Itu use case primary.

- **Jangan untuk spam.** Hasil email harvest tidak boleh dipakai untuk cold blast tanpa basis legitimate (eksisting relasi bisnis, opt-in, atau context yang masuk akal). Banyak yurisdiksi (UE GDPR, Indonesia PDP, US CAN-SPAM) punya aturan tegas. Spam berbasis harvest = pelanggaran.

- **Hormati robots.txt by default.** Toggle off-nya hanya untuk situs Anda sendiri.

- **Throttle request.** Crawl mode default delay 1 detik antar request. Jangan turunkan ke 0 untuk domain pihak ketiga - itu DoS-light. Setting di config.

- **Jangan publish secret yang Anda temukan di domain pihak ketiga.** Kalau Anda iseng scan situs random dan ketemu AWS key, jangan tweet, jangan posting blog "lihat saya temukan apa". Kontak pemilik domain via responsible disclosure (security@domain, atau via HackerOne kalau ada bug bounty).

- **Jangan kombinasikan dengan brute force atau scan port di domain non-izin.** Tool ini passive. Begitu Anda mulai aktif probing port atau brute force endpoint berdasarkan finding, scope berubah dan legalitas-nya berbeda. Pisahkan dengan tegas.

- **Riset jurnalistik = pertanggungjawaban editor.** Kalau Anda jurnalis, runaway scan dan publish data tanpa redaksi etis adalah resep masalah. Konsultasi dengan editor / legal counsel sebelum publish.

- **Bug bounty scope.** Kalau target ada di program bug bounty, baca scope-nya dulu. Beberapa program explicit allow OSINT recon, beberapa explicit forbid.

## Pengaturan teknis

Setting key relevan di `settings.json`:

| Key | Tipe | Default | Keterangan |
|-----|------|---------|------------|
| `osint_enabled` | boolean | true | Master switch tool |
| `osint_default_depth` | integer | 2 | Default depth untuk crawl mode |
| `osint_max_pages` | integer | 50 | Hard cap halaman per scan |
| `osint_crawl_delay_ms` | integer | 1000 | Delay antar request dalam crawl |
| `osint_request_timeout_seconds` | integer | 30 | Timeout per page fetch |
| `osint_render_js_default` | boolean | false | Default state toggle Render JS |
| `osint_stay_on_domain_default` | boolean | true | Default state toggle Stay on domain |
| `osint_respect_robots_default` | boolean | true | Default state toggle Respect robots.txt |
| `osint_secret_enabled_default` | boolean | false | Default state toggle Secret extractor |
| `osint_secret_redact` | boolean | true | Redact value secret di output |
| `osint_user_agent` | string | `"Mozilla/5.0 (PyScrapr OSINT) Harvester/1.0"` | UA string |
| `osint_history_retention_days` | integer | 90 | Berapa lama scan disimpan di History |

## Tips

- **Single page dulu sebelum crawl.** Test regex custom di sample known-content single page sebelum spawn crawl 50 halaman yang mungkin hasilkan output salah karena regex bug.

- **Compare scan periodik.** Jalankan scan situs sendiri tiap kuartal, simpan JSON. Diff antar scan = signal kalau ada finding baru (mis. developer baru push secret tanpa sadar).

- **Combine dengan Exposure Scanner.** OSINT Harvester catch leak di body halaman publik. Exposure Scanner catch leak di path tersembunyi (`.env`, `.git/`). Dua angle berbeda, jalankan dua-duanya untuk audit komprehensif.

- **Custom regex disimpan per-project.** Bookmark setup regex spesifik ke project Anda di catatan tim. Recurring audit jadi konsisten.

- **Render JS hanya saat perlu.** Mayoritas situs marketing / corporate site SSR atau static. SPA admin / dashboard yang JS-heavy baru butuh Render JS toggle.

- **Export JSON untuk arsip.** CSV bagus untuk eyeballing, tapi JSON preserve full structure (multiple sources per finding) yang berguna saat re-analisis 6 bulan kemudian.

## Troubleshooting

### Problem: Crawl macet di "fetching..." selama menit

**Gejala:** Progress bar di 5/50 stuck lama, tapi tidak ada error.
**Penyebab:** Situs target lambat respond, atau toggle Render JS aktif tapi Playwright tidak terinstall.
**Solusi:** Cek log backend untuk pesan timeout. Kalau JS rendering yang lambat, matikan toggle Render JS dan retry. Kalau memang situsnya lambat, naikkan `osint_request_timeout_seconds` di Settings.

### Problem: Email count terlihat tidak masuk akal (ribuan)

**Gejala:** Hasil 5000+ email, tapi situs target jelas kecil.
**Penyebab:** Regex match string yang mirip email di JS minified bundle, false positive masif.
**Solusi:** Jalankan ulang dengan toggle Render JS off (skip parse JS bundle), atau filter manual hasil JSON post-scan. Future improvement: regex email akan punya context guard di sekitar `mailto:` atau `@`.

### Problem: Secret extractor ON tapi 0 finding padahal Anda tahu ada key

**Gejala:** Anda tahu ada `sk-...` di file source, tapi scan return 0.
**Penyebab:** Render JS off, key ada di JS bundle yang tidak di-fetch terpisah. Atau key di-obfuscate / split.
**Solusi:** Aktifkan toggle Render JS, retry. Kalau key di-split (`"sk-" + "abc..." + "...xyz"`), regex tidak akan catch - itu by design (anti false positive di code legitimate yang kebetulan match prefix).

### Problem: "robots.txt blocked all crawl"

**Gejala:** Crawl return 0 halaman, error message robots.
**Penyebab:** robots.txt situs target Disallow `/`.
**Solusi:** Kalau itu situs Anda sendiri, matikan toggle Respect robots.txt. Kalau bukan, hormati robots.txt; tool sengaja tidak provide bypass otomatis.

### Problem: Custom regex error "invalid pattern"

**Gejala:** Error saat klik Harvest dengan custom regex aktif.
**Penyebab:** Regex syntax tidak valid (kurung tidak balance, escape salah).
**Solusi:** Test regex di [regex101.com](https://regex101.com) flavor Python sebelum paste. Tool pakai Python `re` module, bukan PCRE.

### Problem: SSE crawl progress tidak update di UI

**Gejala:** Job jalan di backend (log menunjukkan progress), tapi UI stuck di 0%.
**Penyebab:** Browser EventSource terputus, atau proxy memotong long-lived connection.
**Solusi:** Refresh halaman, scan akan recovery dari History saat selesai. Atau cek browser DevTools Network tab apakah EventSource connection masih hidup.

## Related docs

- [Exposure Scanner](/docs/audit/exposure.md) - audit path tersembunyi (.env, .git/) yang complement OSINT body scan
- [Domain Intel](/docs/intel/domain.md) - WHOIS + DNS + subdomain enumeration sebelum OSINT mulai
- [URL Mapper](/docs/tools/url-mapper.md) - crawl-only tanpa OSINT extraction kalau Anda butuh peta URL saja
- [Threat Scanner](/docs/tools/threat-scanner.md) - kalau finding cloud artifact ternyata file binary suspect
- [Custom Pipeline](/docs/utilities/pipeline.md) - transformasi hasil OSINT JSON ke format custom Anda
- [Settings](/docs/system/settings.md) - semua flag OSINT Harvester
- [Playwright Rendering](/docs/advanced/playwright.md) - detail toggle Render JS dan Stealth mode
