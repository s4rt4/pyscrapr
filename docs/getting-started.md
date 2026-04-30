# Getting Started dengan PyScrapr

> Panduan lengkap dari instalasi sampai first successful job. Dokumen ini dirancang untuk pengguna yang baru pertama kali membuka PyScrapr dan ingin memahami cara kerjanya dari nol.

PyScrapr adalah aplikasi scraping dan data harvesting all-in-one yang berjalan secara lokal di komputer Anda. Tidak ada cloud, tidak ada tracking, tidak ada subscription - semua proses terjadi di mesin Anda sendiri. Panduan ini akan menuntun Anda dari nol sampai berhasil menjalankan job pertama Anda dan memahami apa yang bisa dilakukan selanjutnya.

---

## Sebelum mulai

Sebelum menginstal apa pun, pastikan lingkungan Anda memenuhi kebutuhan minimum PyScrapr. Aplikasi ini dirancang ringan dan berjalan pada sebagian besar komputer modern, namun ada beberapa prasyarat teknis yang harus dipenuhi.

### System requirements

- **Operating System**: Windows 10/11 (disarankan), macOS 12+, atau Linux (Ubuntu 20.04+, Fedora 36+, Arch). PyScrapr diuji paling intensif di Windows 11 karena itu adalah platform pengembangan utama, tetapi cross-platform compatibility dijaga.
- **Python**: versi 3.10 atau lebih baru. Versi di bawah itu tidak didukung karena PyScrapr menggunakan beberapa fitur typing modern (`|` untuk union types, `match` statements di beberapa modul advanced).
- **Node.js**: versi 18 LTS atau lebih baru. Diperlukan untuk menjalankan frontend (React + Vite + Mantine).
- **Disk space**: minimum 2 GB untuk aplikasi + dependencies. Namun siapkan setidaknya 20 GB jika Anda berencana menggunakan Media Downloader atau AI Tagger (CLIP model sendiri sekitar 600 MB, Ollama bisa lebih besar lagi).
- **RAM**: 4 GB cukup untuk penggunaan dasar. 8 GB direkomendasikan jika Anda akan menjalankan AI extraction atau scraping paralel dengan banyak worker.
- **CPU**: prosesor 64-bit modern (Intel Core i3 generasi 8+ atau AMD Ryzen 3 1000+ atau setara). GPU tidak wajib, tapi akan mempercepat AI features jika tersedia.
- **Internet**: koneksi stabil saat instalasi (untuk download dependencies). Setelah terpasang, internet hanya dibutuhkan saat melakukan scraping.

### Skills prerequisites

PyScrapr mencoba semaksimal mungkin ramah untuk non-developer, tetapi ada beberapa keterampilan dasar yang akan membuat perjalanan Anda jauh lebih mulus.

- **Basic CLI (Command Line Interface)**: Anda perlu nyaman membuka terminal (CMD, PowerShell, Bash, atau zsh) dan menjalankan perintah sederhana seperti `cd`, `python --version`, atau `npm install`. Jika Anda belum pernah, lihat tutorial singkat CLI di Mozilla Developer Network atau YouTube terlebih dahulu - 15 menit cukup untuk memahami dasar.
- **Understanding of URLs**: Anda harus paham konsep dasar URL - apa itu scheme (`https://`), domain (`example.com`), path (`/articles/123`), dan query string (`?id=42`). Ini penting karena banyak tool di PyScrapr menerima URL input dan perilaku mereka bergantung pada struktur URL.
- **Basic file management**: memahami konsep folder, file, dan path absolut vs relatif. PyScrapr akan menulis ke folder `downloads/` dan `data/` - Anda perlu tahu di mana lokasinya untuk mengambil hasil scraping.

Tidak perlu bisa programming. Tidak perlu paham HTML/CSS. Tidak perlu paham regex. Fitur advanced seperti Custom Pipeline memang memungkinkan scripting, tapi itu opsional.

---

## Spesifikasi minimum sistem

PyScrapr adalah aplikasi all-in-one yang mengintegrasikan banyak tool berat (CLIP model AI, Chromium browser, scientific Python stack). Berikut tabel kebutuhan minimum vs rekomendasi:

### RAM

| Skenario | Minimum | Rekomendasi |
|---|---|---|
| Tools ringan saja (Image Harvester, URL Mapper, Sitemap, SEO Auditor) | 4 GB | 8 GB |
| AI Tagger (CLIP) aktif | 8 GB | 16 GB |
| Threat Scanner + AI Explainer + YARA | 8 GB | 16 GB |
| Playwright + Screenshotter + multiple tabs | 8 GB | 16 GB |
| Worker mode (distributed scraping) | 4 GB per node | 8 GB per node |

### Storage

| Komponen | Ukuran |
|---|---|
| Source code + Node modules | ~600 MB |
| Python deps (FastAPI, SQLAlchemy, etc) | ~150 MB |
| **torch (CPU build)** | ~250 MB |
| **torch (CUDA build, opsional GPU)** | ~2-3 GB |
| **CLIP model (auto-download saat pertama AI Tagger jalan)** | ~350 MB |
| **Chromium binary (Playwright)** | ~300 MB |
| **YARA rules bundle (auto-fetch dari YARAForge)** | ~50 MB |
| Wappalyzer fingerprints (built-in) | ~5 MB |
| **Ollama model (jika dipakai untuk AI Extract / Threat Explainer)** | 2-8 GB per model |
| Database SQLite | tumbuh sesuai jumlah job (1 GB cukup untuk ribuan job) |
| Downloads folder (user-controlled) | tergantung pemakaian |

**Total disk minimum yang perlu disiapkan**: 5 GB untuk install dasar tanpa GPU + Ollama. **10-15 GB rekomendasi** kalau pakai semua fitur termasuk Ollama dan GPU torch.

### CPU

- Minimum: dual-core x86_64
- Rekomendasi: quad-core untuk parallel scraping + Playwright rendering
- AI Tagger (CLIP) jalan di CPU OK tapi lambat (10-15 detik per gambar). GPU CUDA optional, butuh torch CUDA build (+2-3 GB disk).

### OS

- Windows 10/11 (tested via Laragon Python 3.10)
- macOS 12+ (Apple Silicon supported)
- Linux: Ubuntu 22.04+ atau distro modern equivalent
- Python 3.10 / 3.11 / 3.12 (3.14 belum kompatibel dengan torch wheels)
- Node.js 18+ untuk frontend dev/build

### Network

- Internet diperlukan untuk: scraping target situs, VirusTotal/MalwareBazaar lookup, DeepSeek/OpenAI API, YARA auto-fetch, CLIP model download pertama kali, Playwright Chromium install
- Offline-friendly setelah setup awal: scraping local files, OSINT pada cached HTML, Threat Scanner static analysis tidak butuh internet (kecuali hash reputation)

### Bandwidth

- Light scraping: <100 MB/hari
- Site Ripper full mirror: 100 MB - 1 GB per situs medium
- Media Downloader (video): bisa GB-an, tergantung quality + jumlah video
- Recommendation: koneksi 10 Mbps+ untuk pengalaman comfortable

### Tips hemat resource

- Matikan Playwright (`playwright_enabled=false` di Settings) jika target situs SSR (saving 300 MB Chromium binary running di RAM)
- Skip CLIP / AI Tagger jika tidak butuh image classification (saving ~350 MB model + ~1 GB RAM saat aktif)
- Pakai Ollama hanya untuk AI Extract; untuk Threat Explainer pakai DeepSeek API yang lebih ringan
- Set `max_concurrent_downloads=2` di Settings untuk mesin lemah
- Bersihkan `data/screenshots/` dan `downloads/` secara berkala

---

## Instalasi

Instalasi PyScrapr terdiri dari 6 langkah. Ikuti berurutan - melewati langkah akan menyebabkan error di langkah berikutnya.

### Step 1: Install Python

Python adalah bahasa yang menjalankan backend PyScrapr. Kami menggunakan Python 3.10+ karena fitur-fitur modernnya.

1. Kunjungi [python.org/downloads](https://www.python.org/downloads/) dan download versi terbaru (3.10 atau lebih baru - jangan 3.9 ke bawah).
2. Saat installer berjalan, **centang "Add Python to PATH"** di layar pertama. Ini krusial. Jika dilewat, Anda harus menambahkannya manual di environment variables.
3. Pilih "Install Now" untuk instalasi default, atau "Customize installation" jika ingin mengubah lokasi (biasanya tidak perlu).
4. Setelah selesai, buka terminal baru dan verifikasi:
 ```bash
   python --version
   ```
 Output yang diharapkan: `Python 3.11.x` atau serupa. Jika muncul "command not found", restart terminal atau restart komputer.

Pada macOS/Linux, Python 3 sering sudah terpasang. Cek dulu dengan `python3 --version`. Jika versi di bawah 3.10, upgrade via Homebrew (`brew install python@3.11`) atau package manager distro Anda.

### Step 2: Install Node.js

Node.js menjalankan frontend React PyScrapr.

1. Kunjungi [nodejs.org](https://nodejs.org/) dan download versi **LTS** (Long Term Support). Per April 2026, versi LTS adalah 20.x - aman digunakan.
2. Jalankan installer dengan setting default. Centang opsi "Automatically install the necessary tools" jika ditawarkan (Windows) - ini memasang build tools yang mungkin dibutuhkan beberapa npm package.
3. Verifikasi setelah selesai:
 ```bash
   node --version
   npm --version
   ```
 Output: `v20.x.x` dan `10.x.x` (atau lebih baru).

Jika Anda sudah memiliki Node.js tapi versinya di bawah 18, uninstall dulu lalu install ulang versi LTS terbaru. Menggunakan `nvm` (Node Version Manager) adalah alternatif elegan jika Anda bekerja dengan banyak proyek Node.

### Step 3: Download PyScrapr

Ada dua cara: clone via Git (direkomendasikan, memudahkan update) atau download ZIP.

**Opsi A - Git clone:**
```bash
git clone https://github.com/s4rt4/pyscrapr
cd pyscrapr
```

**Opsi B - Download ZIP:**
1. Buka halaman GitHub repository.
2. Klik tombol hijau "Code" → "Download ZIP".
3. Extract ke lokasi yang Anda inginkan (hindari path dengan spasi atau karakter non-ASCII - beberapa tool Node/Python punya masalah dengan itu).
4. Masuk ke folder hasil extract via terminal.

### Step 4: Install backend dependencies

Backend PyScrapr menggunakan banyak library Python (FastAPI, Playwright, yt-dlp, Pillow, dll). Kami sangat menyarankan menggunakan virtual environment agar tidak mengotori instalasi Python global Anda.

```bash
cd backend
python -m venv .venv
```

Aktifkan virtual environment:

- **Windows (CMD/PowerShell)**: `.venv\Scripts\activate`
- **macOS/Linux**: `source .venv/bin/activate`

Jika berhasil, prompt terminal Anda akan berubah menunjukkan `(.venv)` di depan. Lalu install dependencies:

```bash
pip install -r requirements.txt
```

Proses ini memakan waktu 5–15 menit tergantung kecepatan internet. Beberapa package seperti Playwright akan mendownload browser binaries yang cukup besar (~300 MB). Bersabar.

Setelah selesai, jalankan sekali:
```bash
playwright install chromium
```
untuk memastikan browser engine terpasang. PyScrapr menggunakan Chromium untuk fitur yang butuh JavaScript rendering.

### Step 5: Install frontend dependencies

Buka terminal kedua (biarkan terminal backend tetap terbuka), lalu:

```bash
cd frontend
npm install
```

Ini juga memakan waktu (2–8 menit). npm akan men-download ratusan package kecil ke folder `node_modules/`. Ini normal - itulah cara ekosistem Node bekerja.

Jika Anda melihat peringatan (warnings) tentang deprecated packages, abaikan saja selama tidak ada **error** (merah). Warnings tidak memblokir aplikasi.

### Step 6: Jalankan

Sekarang saatnya menjalankan aplikasi. PyScrapr membutuhkan dua proses berjalan bersamaan: backend dan frontend.

**Terminal 1 (backend):**
```bash
cd backend
.venv\Scripts\activate  # aktifkan venv lagi jika terminal baru
python run.py
```
Anda akan melihat output seperti `Uvicorn running on http://localhost:8585`. Biarkan terminal ini terbuka.

**Terminal 2 (frontend):**
```bash
cd frontend
npm run dev
```
Vite akan memulai development server dan menampilkan `Local: http://localhost:5173`.

**Buka browser**, navigasi ke [http://localhost:5173](http://localhost:5173). Selamat - PyScrapr sekarang berjalan di mesin Anda!

---

## Orientasi UI

Pertama kali buka PyScrapr, Anda akan melihat layout tiga area: sidebar kiri, konten utama di tengah, dan footer sistem monitor di bawah. Berikut tur singkatnya.

### Sidebar kiri

Sidebar adalah menu navigasi utama. Dikelompokkan dalam beberapa section:

- **Tools** - ini adalah jantung PyScrapr. Berisi Dashboard sebagai home screen, lalu P1 sampai P5 (Phase 1 sampai Phase 5) yang mencakup tools utama: Image Harvester, URL Mapper, Site Ripper, Media Downloader, dan seterusnya.
- **Utilities** - tool-tool tambahan yang sifatnya helper atau advanced: AI Extract (content extraction dengan LLM lokal via Ollama), Pipeline (custom data transformation), Playground (sandbox untuk testing selector), Bypass (untuk situs yang pakai Cloudflare), Vault (penyimpanan credential terenkripsi).
- **System** - manajemen operasional: Scheduled (cron-like job scheduler), Diff (bandingkan hasil scraping antar run), History (log semua job), Settings (konfigurasi aplikasi).
- **Help** - akses dokumentasi. Di sini Anda bisa membaca semua panduan termasuk yang sedang Anda baca.

Klik ikon di sebelah nama section untuk collapse/expand. Di mobile/narrow window, sidebar akan otomatis menjadi drawer.

### Header atas

Header berisi tiga elemen:

- **Logo + version**: branding PyScrapr dengan nomor versi di belakangnya. Berguna saat melaporkan bug.
- **Smart URL input**: field input di tengah. Paste URL apa pun di sini, dan PyScrapr akan **auto-detect** tool paling relevan. Paste link YouTube → Media Downloader menyala. Paste link blog artikel → AI Extract diusulkan. Paste link dengan banyak gambar → Image Harvester disarankan. Cara tercepat untuk memulai job.
- **Theme toggle**: ikon matahari/bulan di kanan. Klik untuk beralih antara light dan dark mode. Preferensi disimpan di localStorage.

### Footer bawah

Footer adalah **system monitor** real-time. Menampilkan:

- **CPU usage**: persentase penggunaan CPU proses PyScrapr.
- **RAM usage**: memori aktif.
- **Network speed**: download/upload saat ini (KB/s atau MB/s).
- **Traffic total**: akumulasi data terkirim/diterima selama session.

Monitor ini berguna untuk melihat apakah job Anda masih aktif atau sudah stuck, serta mendeteksi bottleneck resource.

---

## Your first job - Image Harvester

Mari kita jalankan job pertama Anda. Sebagai contoh, kita akan mengambil semua gambar dari artikel Wikipedia tentang kucing: `https://en.wikipedia.org/wiki/Cat`.

1. **Buka sidebar kiri**, klik bagian **Tools**, lalu pilih **Image Harvester**. Halaman tool akan terbuka di konten utama.
2. **Temukan field URL** di bagian atas halaman tool. Ini tempat Anda mengetik alamat sumber gambar.
3. **Paste URL**: `https://en.wikipedia.org/wiki/Cat`. PyScrapr akan melakukan preview otomatis setelah Anda selesai mengetik (atau klik tombol "Preview" jika muncul).
4. **Atur opsi filter**. Anda akan melihat beberapa opsi: minimum width (misal 200px untuk menghindari icon kecil), minimum file size (misal 10 KB), allowed formats (JPG, PNG, WebP, GIF), dan maksimum jumlah gambar yang akan di-download.
5. **Pilih folder output**. Secara default, hasil disimpan di `downloads/image-harvester/<domain>/<timestamp>/`. Anda bisa mengubahnya jika mau.
6. **Klik tombol "Start" atau "Harvest"**. Job akan masuk antrean dan mulai dieksekusi.
7. **Perhatikan progress bar**. Anda akan melihat jumlah gambar yang ditemukan, jumlah yang sudah di-download, dan error count (jika ada). Sistem monitor di footer akan menunjukkan traffic network meningkat.
8. **Tunggu selesai**. Untuk artikel Wikipedia tentang kucing, biasanya 20–40 gambar akan terkumpul dalam waktu kurang dari satu menit.
9. **Review hasil**. Setelah status berubah menjadi "Done", tombol "Open folder" atau "Download ZIP" akan muncul. Klik "Download ZIP" untuk mendapatkan archive berisi semua gambar.
10. **Cek hasilnya**. Extract ZIP tadi, dan Anda akan menemukan file-file gambar dengan nama yang sudah dinormalisasi (tanpa karakter aneh, dengan ekstensi yang benar). Metadata setiap gambar (URL asli, ukuran, format, alt text) disimpan di file `manifest.json` di dalam ZIP yang sama.

Selamat - Anda baru saja menjalankan job scraping pertama Anda!

---

## Setelah first job - apa selanjutnya?

PyScrapr punya banyak tool. Berikut rekomendasi berdasarkan use case umum:

- **Jika mau riset situs kompetitor** → gunakan **URL Mapper**. Tool ini akan crawl semua halaman dalam satu domain dan memberi Anda peta struktur situs (sitemap), jumlah halaman per kategori, dan link graph.
- **Jika mau arsip dokumentasi** → **Site Ripper** adalah pilihan yang tepat. Download seluruh situs beserta asset-nya (CSS, gambar, JS) agar bisa dibrowse offline, mirip seperti `wget -r` tapi dengan UI yang jauh lebih nyaman.
- **Jika mau download video/audio** → **Media Downloader** mendukung YouTube, Vimeo, Twitter/X, TikTok, dan ratusan situs lain (powered by yt-dlp). Bisa download playlist, pilih kualitas, extract audio saja, dan auto-translate subtitle.
- **Jika mau auto-tag gambar** → **AI Tagger** khususnya fitur CLIP tagging. Upload folder gambar, dan PyScrapr akan memberi tag semantik otomatis (misal "cat sitting on couch", "red sports car at sunset").
- **Jika mau otomasi** → kombinasikan **Scheduled Jobs** + **Webhooks**. Jadwalkan scraping harian, lalu kirim notifikasi ke Discord/Telegram saat ada konten baru.

---

## Konfigurasi lanjutan

Setelah nyaman dengan dasar, saatnya explore konfigurasi lanjutan.

**Settings page walkthrough.** Buka System → Settings. Di sini Anda bisa mengatur bahasa UI, theme default, direktori download, maximum parallel workers (default 4, naikkan jika mesin Anda kuat), timeout HTTP, User-Agent custom, dan banyak lagi.

**Ollama install (untuk AI Extract).** Jika ingin menggunakan AI Extract, Anda perlu menginstal [Ollama](https://ollama.ai) secara terpisah. Setelah terpasang, pull model yang ringan seperti `llama3.2:3b` atau `qwen2.5:7b`. PyScrapr akan auto-detect Ollama yang berjalan di `localhost:11434`.

**Proxy setup.** Jika ISP Anda memblokir situs tertentu atau Anda ingin scraping dari IP berbeda, tambahkan proxy di Settings → Network. Format: `http://user:pass@host:port` atau SOCKS5. Anda bisa punya multiple proxy dengan rotation rules.

**Auth Vault untuk login-required sites.** Beberapa situs butuh login. Gunakan Vault (di Utilities) untuk menyimpan cookie atau credential yang dienkripsi lokal (AES-256 dengan master password). PyScrapr akan memakai cookie ini otomatis saat scraping situs terkait.

**Webhook Discord/Telegram.** Di Settings → Notifications, daftarkan webhook URL Discord atau bot token Telegram. Lalu di setiap job, Anda bisa mengaktifkan notifikasi untuk event: job started, job completed, job failed, atau content changed.

---

## Tips umum

Beberapa tips produktivitas setelah pengalaman beberapa minggu menggunakan PyScrapr:

1. **Keyboard shortcuts**. Tekan `?` di mana saja untuk melihat daftar shortcut. Yang paling berguna: `Ctrl+K` (command palette), `G H` (go home / dashboard), `G S` (go settings), `/` (focus ke smart URL input).
2. **Dashboard sebagai home**. Kustomisasi dashboard dengan widget job-job yang sering Anda monitor. Ini jauh lebih cepat daripada masuk ke halaman History setiap kali.
3. **Scheduled + Diff + Webhook = auto monitoring**. Kombinasi tiga fitur ini bikin PyScrapr berfungsi seperti UptimeRobot atau VisualPing tapi self-hosted dan gratis.
4. **Custom Pipeline untuk transform data**. Belajar dasar Python? Anda bisa menulis pipeline yang mengolah hasil scraping - misalnya konversi harga dari USD ke IDR, atau filter hanya artikel yang mengandung kata kunci tertentu.
5. **REST API untuk integrasi**. PyScrapr expose REST API di `http://localhost:8585/docs` (Swagger UI). Anda bisa menjalankan scraping dari skrip Anda sendiri, tool n8n, atau Zapier via webhook.
6. **Gunakan Preview sebelum Run**. Sebagian besar tool punya preview mode yang tidak benar-benar download. Pakai ini dulu untuk memverifikasi filter dan opsi sebelum meng-commit job penuh.
7. **History dan Retry**. Setiap job lama bisa di-retry dari History dengan satu klik - semua parameter dipertahankan. Berguna untuk re-scrape situs yang kontennya berubah.

---

## Troubleshooting awal

Masalah umum yang sering dialami saat first-run:

- **Port conflict (8000/5173 sudah dipakai)**. Jika ada aplikasi lain yang sudah menempati port tersebut, backend/frontend gagal start. Solusi: ubah port di `backend/app/config.py` dan `frontend/vite.config.ts`, atau matikan aplikasi penempat port. Gunakan `netstat -ano | findstr :8000` (Windows) untuk mencari aplikasi pelaku.
- **Permission denied (Windows antivirus)**. Defender atau antivirus pihak ketiga kadang memblokir Playwright browser binaries. Solusi: tambahkan folder PyScrapr ke whitelist antivirus.
- **Missing dependencies**. Jika `pip install` selesai dengan error, baca pesan error-nya - biasanya menunjuk package spesifik. Coba install ulang hanya package tersebut: `pip install <nama-package>`. Untuk masalah di Windows, install "Visual C++ Build Tools" mungkin perlu.
- **DNS/proxy issues**. Jika `pip` atau `npm install` timeout, mungkin DNS atau proxy Anda bermasalah. Coba set DNS ke 1.1.1.1 (Cloudflare) atau 8.8.8.8 (Google). Untuk npm di balik proxy kantor: `npm config set proxy http://user:pass@host:port`.
- **Dark background artifacts**. Pada monitor tertentu, dark mode PyScrapr bisa memunculkan garis atau banding halus. Ini masalah rendering GPU. Solusi: disable hardware acceleration di browser, atau switch ke light mode.

---

## Langkah berikutnya

Sekarang Anda sudah tahu dasar PyScrapr. Berikut tautan untuk mendalami lebih lanjut:

- **Tools documentation**: lihat folder `docs/tools/` untuk panduan setiap tool secara detail (Image Harvester, URL Mapper, Site Ripper, Media Downloader, AI Extract, dll).
- **Utilities documentation**: `docs/utilities/` menjelaskan Pipeline, Playground, Bypass, dan Vault.
- **System documentation**: `docs/system/` untuk Scheduled Jobs, Diff, History, dan Settings.
- **Advanced guides**: `docs/advanced/` - tips untuk power user, custom pipeline scripting, REST API integration.
- **FAQ**: `docs/faq.md` - jawaban untuk pertanyaan yang paling sering ditanyakan.
- **Best practices**: hormati `robots.txt`, rate-limit request Anda, jangan scrape data yang dilindungi copyright untuk distribusi. PyScrapr adalah alat - tanggung jawab penggunaannya ada di tangan Anda.

Selamat mengeksplorasi PyScrapr. Jika Anda menemui kesulitan, dokumentasi ini akan terus diperbarui - dan jangan ragu membuka issue di GitHub kalau ada yang tidak jelas.

---

## Appendix A: Glossary istilah penting

Sebelum benar-benar mendalami PyScrapr, ada baiknya Anda kenali sejumlah istilah yang akan sering muncul di dokumentasi dan UI. Daftar ini disusun khusus untuk pengguna Indonesia yang mungkin belum terbiasa dengan terminologi scraping dan web engineering.

- **Scraping**: proses otomatis mengambil data dari halaman web. Berbeda dengan "mengunduh", scraping biasanya melibatkan parsing terstruktur - misal mengambil judul artikel, harga produk, atau URL gambar, bukan sekadar menyimpan file HTML mentah.
- **Crawling**: proses mengikuti link dari satu halaman ke halaman lain secara rekursif untuk memetakan struktur situs. Scraping fokus pada "apa isi halaman", crawling fokus pada "halaman mana saja yang ada".
- **Selector (CSS/XPath)**: pola untuk memilih elemen tertentu di halaman HTML. CSS selector (`div.article > h2`) lebih sederhana, XPath (`//div[@class='article']/h2`) lebih powerful. PyScrapr menerima keduanya di banyak tool.
- **User-Agent**: string identifikasi browser yang dikirim ke server setiap request. Default PyScrapr memakai UA Chrome terbaru agar tidak terlihat sebagai bot.
- **Headless browser**: browser tanpa tampilan grafis, dijalankan di background. PyScrapr memakai Chromium headless via Playwright untuk rendering JavaScript.
- **Rate limit**: batasan jumlah request per satuan waktu yang diizinkan situs target. Melanggar rate limit biasanya berbuah HTTP 429 atau IP block.
- **Manifest**: file metadata (biasanya JSON) yang menyertai hasil scraping. Berisi informasi seperti URL asal, timestamp, ukuran file, dan checksum.

Istilah-istilah ini akan Anda temui berulang kali - pahami sekarang agar tidak bingung saat mendalami dokumentasi tool spesifik di `docs/tools/`.

## Appendix B: Workflow harian yang direkomendasikan

Setelah beberapa minggu memakai PyScrapr secara rutin, kebanyakan power user mengembangkan workflow yang mirip. Berikut adalah template yang bisa Anda adaptasi:

1. **Pagi**: buka Dashboard, cek Scheduled Jobs yang selesai semalam. Review hasil Diff untuk melihat situs mana yang kontennya berubah.
2. **Siang**: jika ada konten baru menarik dari Diff, lakukan scraping mendalam - misal Site Ripper untuk arsip penuh atau AI Extract untuk ringkasan.
3. **Sore**: review hasil, organize ke folder berlabel, tandai yang ingin diolah lebih lanjut dengan Pipeline custom.
4. **Malam**: setup scheduled job baru berdasarkan insight hari itu, pastikan webhook notifikasi aktif untuk job yang akan berjalan otomatis besok pagi.

Workflow ini tidak wajib - sesuaikan dengan ritme Anda. Yang penting adalah memanfaatkan fitur automation (Scheduled + Diff + Webhook) agar PyScrapr bekerja saat Anda tidur.

## Appendix C: Kesalahan umum pengguna baru

Berikut beberapa kesalahan yang sering dilakukan user baru - mengetahuinya di awal bisa menghemat berjam-jam frustasi:

1. **Tidak aktifkan virtual environment**. Akibatnya dependencies terpasang global dan konflik dengan project lain. Selalu aktifkan `.venv` sebelum `pip install` atau menjalankan `python run.py`.
2. **Lupa restart terminal setelah install Python**. PATH environment variable hanya di-refresh saat terminal baru dibuka. Jika `python --version` tidak dikenali padahal installer sudah selesai, tutup dan buka terminal ulang.
3. **Clone ke folder dengan path bermasalah**. Hindari path dengan spasi, karakter non-ASCII, atau terlalu panjang (Windows punya batas 260 karakter default). Gunakan path sederhana seperti `C:\pyscrapr\` atau `~/projects/pyscrapr`.
4. **Langsung jalankan job besar tanpa Preview**. Banyak user langsung scrape situs 10.000 halaman, lalu kaget saat stuck atau menghabiskan disk. Selalu Preview dulu dengan limit kecil (10–50 item).
5. **Tidak baca robots.txt**. Selain masalah etis, beberapa situs akan block IP Anda cepat jika terdeteksi scraping area yang disallow. Cek `https://situs.com/robots.txt` sebelum mulai.
6. **Menjalankan banyak parallel workers di koneksi lambat**. Jika bandwidth Anda 5 Mbps, menjalankan 16 workers tidak akan lebih cepat dari 4 workers - justru bisa lambat karena congestion. Sesuaikan workers dengan bandwidth.
7. **Tidak backup vault master password**. Master password Vault tidak bisa direcover - kalau lupa, semua credential di dalamnya hilang. Simpan password di password manager (Bitwarden/1Password/KeePass).

Dengan menghindari kesalahan-kesalahan ini, pengalaman onboarding Anda akan jauh lebih lancar. Setelah Anda familiar, eksperimen dengan konfigurasi dan batasan lebih lanjut.
