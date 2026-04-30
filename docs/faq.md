# FAQ - Pertanyaan yang Sering Ditanyakan

> Kumpulan jawaban atas pertanyaan paling umum tentang PyScrapr. Disusun berdasarkan kategori agar mudah dicari. Jika pertanyaan Anda tidak terjawab di sini, cek dokumentasi tool spesifik di `docs/tools/` atau buka issue di GitHub.

---

## Umum

### Apa itu PyScrapr?

PyScrapr adalah aplikasi desktop self-hosted untuk scraping, data harvesting, dan arsip konten web. Aplikasi ini menggabungkan banyak tool dalam satu antarmuka - mulai dari pengambil gambar (Image Harvester), URL mapper, site ripper (mirror seluruh situs), media downloader (YouTube, Vimeo, dan ratusan platform lain), sampai AI extraction menggunakan LLM lokal. Seluruh proses terjadi di komputer Anda - tidak ada data yang dikirim ke server pihak ketiga.

### Apakah PyScrapr gratis?

Ya, PyScrapr sepenuhnya gratis dan open source. Tidak ada tier berbayar, tidak ada freemium, tidak ada subscription. Kode sumbernya tersedia di GitHub dan dapat Anda modifikasi sesuai license (lihat bagian Development). Satu-satunya "biaya" adalah resource komputer Anda dan waktu yang Anda investasikan untuk belajar.

### Apakah PyScrapr aman digunakan?

Secara umum ya. PyScrapr berjalan lokal, tidak memanggil server eksternal kecuali target scraping yang Anda tentukan. Credential yang Anda simpan di Vault dienkripsi dengan AES-256. Namun seperti aplikasi apa pun, keamanan bergantung pada bagaimana Anda menggunakannya - jangan expose port 8000 ke internet publik tanpa reverse proxy dengan autentikasi, dan gunakan master password yang kuat untuk Vault.

### Apakah PyScrapr legal?

Aplikasinya legal. Aktivitas scraping itu sendiri **tergantung konteks** - tergantung konten yang Anda scrape, Terms of Service situs target, hukum di yurisdiksi Anda, dan tujuan penggunaan data. Scraping data publik untuk riset pribadi umumnya aman, tapi mendistribusikan konten ber-copyright atau melanggar ToS bisa bermasalah. Selalu hormati `robots.txt` dan rate limits.

### Dari mana datanya disimpan?

Semua data disimpan lokal di mesin Anda. Folder default adalah `downloads/` (untuk hasil scraping) dan `data/` (untuk database SQLite berisi metadata, history, scheduled jobs, dan konfigurasi). Lokasi ini bisa diubah di Settings. Tidak ada sinkronisasi cloud - Anda sepenuhnya memegang data Anda.

### Apakah ada versi mobile?

Tidak ada aplikasi mobile native. Namun UI PyScrapr responsive - Anda bisa mengaksesnya dari browser ponsel jika backend berjalan di komputer lokal (misalnya lewat akses LAN dengan IP komputer Anda + port 5173). Untuk keperluan kontrol jarak jauh, gunakan Tailscale atau VPN rumah.

### Apakah support multi-user?

Saat ini PyScrapr dirancang sebagai **single-user tool**. Tidak ada sistem akun, otorisasi, atau pemisahan data per user. Jika Anda butuh multi-user, jalankan instance PyScrapr terpisah untuk masing-masing user (dengan folder data berbeda), atau tunggu fitur multi-tenant yang ada di roadmap Phase 5.

### Bagaimana cara update?

Jika Anda menginstal via `git clone`, update cukup dengan `git pull` di folder root, lalu re-install dependencies yang mungkin bertambah: `pip install -r backend/requirements.txt` dan `npm install` di `frontend/`. Jika Anda download ZIP, download versi baru lalu replace folder (backup dulu `data/` dan `downloads/` Anda).

---

## Instalasi

### Kenapa `pip install` gagal?

Penyebab paling umum: (1) versi Python di bawah 3.10 - upgrade ke 3.10+, (2) tidak ada build tools untuk compile C-extensions (di Windows install Visual C++ Build Tools, di Linux install `build-essential`), (3) koneksi internet terputus di tengah proses - coba ulang dengan `pip install -r requirements.txt --retries 10`, atau (4) konflik dengan package yang sudah ada - pakai virtual environment bersih.

### Kenapa `npm install` lama sekali?

`npm install` memang memakan waktu 2–8 menit tergantung kecepatan internet dan jumlah dependencies. Jika lebih dari 15 menit tanpa progress, kemungkinan ada masalah jaringan. Solusi: gunakan registry mirror yang lebih cepat seperti `npm config set registry https://registry.npmmirror.com/` (Asia), atau coba `pnpm install` sebagai alternatif (pnpm 2–3x lebih cepat).

### Port 8000 atau 5173 sudah dipakai aplikasi lain

Cari aplikasi yang memakainya: di Windows `netstat -ano | findstr :8585`, di Linux/macOS `lsof -i :8585`. Setelah ketemu, matikan aplikasinya, atau ubah port PyScrapr: backend di `backend/app/config.py` (parameter `port`), frontend di `frontend/vite.config.ts` (parameter `server.port`). Jangan lupa update URL API di konfigurasi frontend jika mengubah port backend.

### Antivirus memblokir

Windows Defender dan beberapa antivirus pihak ketiga kadang memblokir Playwright browser binaries atau yt-dlp karena heuristik "suspicious behavior". Solusi: tambahkan folder `scraper_app/` ke exclusion list antivirus, atau nonaktifkan sementara real-time scanning saat instalasi selesai. Jangan nonaktifkan permanen.

### Pesan error "Module not found"

Biasanya berarti virtual environment tidak aktif saat menjalankan `python run.py`. Pastikan Anda melihat `(.venv)` di prompt terminal Anda. Jika tidak, aktifkan dengan `.venv\Scripts\activate` (Windows) atau `source .venv/bin/activate` (Unix). Jika masih error, coba `pip install -r requirements.txt` ulang di venv yang benar.

### Error SSL saat install

Error seperti "SSL: CERTIFICATE_VERIFY_FAILED" biasanya terjadi karena Python tidak punya CA certificates terbaru atau ada proxy/firewall kantor yang memotong SSL. Di macOS, jalankan `/Applications/Python\ 3.11/Install\ Certificates.command`. Di Windows, install ulang Python dengan opsi default. Untuk proxy corporate, setup variabel `REQUESTS_CA_BUNDLE` menunjuk ke CA bundle perusahaan Anda.

### Python versi saya di bawah 3.10

Anda harus upgrade. PyScrapr menggunakan fitur sintaks modern yang tidak ada di Python 3.9 ke bawah (union types dengan `|`, `match` statement, struktur `TypeAlias`). Download Python 3.11 atau 3.12 dari python.org dan install berdampingan - Anda bisa punya multiple Python version dalam satu sistem.

---

## Scraping

### Apakah saya bisa scraping situs apa saja?

Secara teknis hampir bisa, tapi tergantung proteksi situs. Situs statis HTML mudah. Situs JavaScript-heavy (React/Vue SPA) perlu mode "JS rendering" yang menggunakan Playwright. Situs dengan Cloudflare, PerimeterX, atau DataDome butuh tool Bypass. Situs login-required butuh Vault dengan cookie yang valid. Dari segi legal dan etis, selalu periksa `robots.txt` dan ToS target.

### Bagaimana kalau situs pakai Cloudflare?

Gunakan tool **Bypass** di Utilities. Bypass menggunakan curl_cffi dan browser fingerprinting untuk meniru Chrome asli, sehingga challenge Cloudflare (termasuk JS challenge 5 detik) bisa dilewati dalam banyak kasus. Untuk CAPTCHA interaktif Cloudflare Turnstile, Anda mungkin perlu integrasi solver eksternal seperti 2Captcha.

### Bagaimana kalau situs butuh login?

Ada dua cara: (1) login manual di browser lalu ekspor cookie via extension "EditThisCookie" atau "Get cookies.txt", lalu import ke Vault PyScrapr, atau (2) gunakan mode "Playwright login recorder" di Vault - PyScrapr akan membuka browser, Anda login manual, dan cookie session otomatis ditangkap dan disimpan terenkripsi.

### Kenapa downloader stuck di 0%?

Beberapa kemungkinan: (1) target URL tidak merespons - cek manual di browser dulu, (2) rate limit tercapai - tunggu beberapa menit, (3) User-Agent diblokir - ubah di Settings, (4) proxy mati - cek konfigurasi proxy, atau (5) disk penuh - cek free space di drive penyimpanan download. Lihat log detail di History untuk diagnosa yang lebih akurat.

### Kenapa hasilnya sedikit sekali?

Mungkin karena filter terlalu ketat (misal minimum width 500px padahal gambar di situs kebanyakan 200px), atau situs memakai lazy loading sehingga gambar baru muncul setelah scroll. Untuk kasus kedua, aktifkan mode "JS rendering" + "auto-scroll" di tool terkait. Juga cek apakah content dimuat lewat API terpisah yang butuh endpoint-sniffing.

### Site loading dengan JavaScript, bagaimana?

Aktifkan opsi **"JS Rendering"** atau **"Render with Playwright"** di tool yang Anda pakai. Ini akan membuka halaman via browser headless (Chromium) yang mengeksekusi JavaScript layaknya browser asli. Trade-off: lebih lambat (karena harus load browser) dan lebih berat di resource, tapi bisa menangani SPA modern.

### Kena rate limit, bagaimana?

Turunkan parallel workers (di Settings), tambahkan delay antar request (opsi "throttle ms" di tool), rotasi User-Agent, dan pertimbangkan pakai proxy. Jika situs serius tentang rate limit, hormati saja - scraping di kecepatan wajar jauh lebih sustainable daripada hit-and-run.

### Kena block IP?

Tunggu beberapa jam sampai hari sampai block dicabut. Untuk jangka panjang: gunakan proxy pool (di Settings → Network), rotasi IP residential jika punya akses, atau gunakan layanan seperti Bright Data/ScraperAPI (PyScrapr support integrasi via custom proxy).

---

## Media Downloader

### Format apa yang paling kompatibel?

Untuk video, **MP4 (H.264 + AAC)** adalah format paling universal - playable di hampir semua device dan player. Untuk audio, **MP3 (320 kbps)** atau **M4A (AAC)** untuk kualitas/kompatibilitas, atau **FLAC/WAV** jika butuh lossless. PyScrapr default ke MP4 + AAC untuk video, MP3 untuk audio-only extract.

### Kenapa download YouTube gagal?

YouTube sering update internal API, dan yt-dlp (library yang dipakai) harus update juga untuk mengikuti. Solusi pertama: update yt-dlp dengan `pip install --upgrade yt-dlp` di venv backend Anda. Jika masih gagal, cek apakah video memiliki geo-restriction (butuh VPN/proxy), age-restriction (butuh cookie akun), atau memang sudah dihapus.

### Apakah bisa download private video?

Bisa jika Anda punya akses. Login ke YouTube/Vimeo/dll di browser, ekspor cookie ke `cookies.txt`, lalu upload file tersebut ke Vault PyScrapr dan pilih saat melakukan download. yt-dlp akan menggunakan cookie tersebut untuk autentikasi.

### Subtitle auto-translate tidak bekerja

Fitur auto-translate menggunakan YouTube's internal translation (jika subtitle asli ada) atau LibreTranslate/Ollama lokal (jika dikonfigurasi). Jika tidak bekerja: (1) pastikan video memiliki subtitle asli (banyak video tidak punya), (2) cek koneksi ke Ollama jika pakai local translation, atau (3) coba bahasa tujuan lain - beberapa pair bahasa tidak didukung.

### Bagaimana download live stream?

PyScrapr mendukung download live stream via opsi "Record Live" di Media Downloader. Sistem akan merekam stream dari titik Anda start sampai Anda stop atau stream berakhir. Perlu disk space besar - live stream 1080p 2 jam bisa 3–5 GB.

### Playlist terlalu besar

Untuk playlist besar (ratusan video), gunakan opsi "Limit" untuk membatasi jumlah video, atau "Filter by date" untuk hanya ambil upload terbaru. Anda juga bisa split ke multiple scheduled jobs yang berjalan bergantian agar tidak membebani sistem sekaligus.

---

## AI Tagger

### CLIP model harus di-download berapa MB?

Default CLIP model (ViT-B/32) sekitar **600 MB**. Ada varian lebih besar (ViT-L/14, sekitar 1.7 GB) yang akurasi lebih tinggi tapi lebih lambat. Download hanya sekali di penggunaan pertama - setelah itu di-cache lokal.

### Perlu GPU?

Tidak wajib, tapi sangat membantu. Tanpa GPU (CPU only), CLIP tagging 100 gambar bisa makan 2–5 menit. Dengan GPU NVIDIA + CUDA, bisa di bawah 30 detik. Pastikan install `torch` dengan CUDA support jika punya GPU - lihat [pytorch.org](https://pytorch.org) untuk command install yang sesuai kartu Anda.

### Akurasi CLIP seberapa?

CLIP sangat baik untuk semantic matching umum (objek, scene, aktivitas) - akurasi zero-shot 70–90% untuk kategori umum. Untuk domain spesifik (medical imaging, satellite, dll), akurasi turun signifikan. Untuk kasus itu, gunakan model fine-tuned atau model lain yang sesuai domain.

### Bisa pakai model AI lain?

Ya. Untuk vision/tagging, PyScrapr support CLIP variants dan BLIP. Untuk text extraction/summarization, support Ollama yang bisa menjalankan Llama, Qwen, Mistral, Gemma, dll. Tambah custom model di Settings → AI Models dengan memberikan path lokal atau Hugging Face model ID.

---

## Storage & Performance

### Berapa disk space yang dibutuhkan?

Aplikasi sendiri: ~2 GB (termasuk Chromium Playwright dan dependencies). Data hasil scraping: **tak terbatas** - tergantung berapa banyak dan apa yang Anda download. Rule of thumb: siapkan 50 GB jika pakai Media Downloader aktif, 200 GB jika arsipkan website besar dengan Site Ripper.

### Folder `downloads/` makin besar, bagaimana?

Manfaatkan fitur **Auto-cleanup** di Settings → Storage. Anda bisa set policy: hapus file lebih lama dari N hari, hapus job yang statusnya gagal, atau compress ke ZIP setelah N hari. Atau manual: buka History, select jobs lama, klik "Delete with files".

### Database SQLite akan jadi besar?

Database metadata biasanya ringan - bahkan dengan 1000 jobs, size di bawah 100 MB. Tapi jika Anda pakai fitur "Save full HTML" atau "Index content for search", database bisa membengkak. Cek size dengan lihat file `data/pyscrapr.db`. Vacuum berkala via Settings → Storage → "Optimize database".

### RAM usage tinggi

PyScrapr default tidak boros RAM (backend ~200 MB, frontend dev ~500 MB). Tapi Playwright browser per instance ~300–500 MB, jadi jika Anda jalankan banyak parallel JS-rendering jobs, RAM bisa tembus 4–8 GB. Turunkan parallel workers, atau upgrade RAM jika sering butuh scraping masif.

---

## Advanced

### Apakah Webhook aman?

Webhook Anda adalah URL yang diberikan oleh Discord/Telegram/dll. Anggap seperti API key - jangan share, jangan commit ke Git. PyScrapr menyimpannya terenkripsi. Namun ketika PyScrapr POST ke URL tersebut, traffic berjalan via HTTPS ke server terkait (Discord dll) - amannya tergantung service tujuan.

### Proxy saya tidak bekerja

Cek format: harus `http://host:port` atau `http://user:pass@host:port` untuk HTTP, `socks5://host:port` untuk SOCKS5. Test proxy dengan tool eksternal (curl/browser) dulu untuk memastikan alive. Jika proxy butuh whitelisting IP, pastikan IP publik Anda terdaftar. Untuk proxy corporate, cek apakah butuh NTLM/Kerberos auth (PyScrapr support basic auth saja).

### CAPTCHA solver mahal?

Tergantung service. 2Captcha sekitar $2–3 per 1000 CAPTCHA solved. Anti-Captcha serupa. Untuk penggunaan personal ringan (beberapa puluh per hari), biaya sangat kecil. Untuk volume tinggi, biaya bisa membengkak - pertimbangkan solusi lain (proxy rotation, session reuse) sebelum mengandalkan CAPTCHA solver.

### Custom Pipeline aman?

Custom Pipeline mengeksekusi Python code yang Anda tulis sendiri. Jadi **seaman code Anda**. PyScrapr tidak menjalankan pipeline dalam sandbox ketat - script punya akses ke filesystem dan network. Jangan jalankan pipeline dari sumber tidak terpercaya. Pipeline Anda sendiri aman selama Anda paham apa yang ditulis.

### Bisa integrate dengan tool lain via REST API?

Bisa. PyScrapr expose REST API di `http://localhost:8585`. Dokumentasi interaktif tersedia di `http://localhost:8585/docs` (Swagger UI) dan `http://localhost:8585/redoc`. Anda bisa trigger job dari skrip Python/Node sendiri, dari n8n, dari Zapier (via self-hosted webhook relay), atau dari tool lain yang bisa HTTP POST.

---

## Development

### Bagaimana contribute?

Fork repository di GitHub, buat branch dengan nama deskriptif (misal `feat/new-tool-xyz` atau `fix/bug-123`), commit perubahan dengan message jelas, lalu open Pull Request. Sebelum submit PR, jalankan test suite dan linting (`pytest` untuk backend, `npm run lint` untuk frontend). Baca `CONTRIBUTING.md` di repo untuk guideline detail.

### License-nya apa?

PyScrapr dirilis di bawah **MIT License** - artinya Anda bebas menggunakan, memodifikasi, mendistribusikan, bahkan untuk komersial, selama Anda menyertakan notice copyright asli. License lengkap ada di file `LICENSE` di root repo.

### Ada API documentation?

Ya. API documentation auto-generated dari kode berkat FastAPI, tersedia di `http://localhost:8585/docs` (Swagger UI interaktif) dan `http://localhost:8585/redoc` (ReDoc, lebih clean untuk baca). Untuk dokumentasi konseptual dan contoh integrasi, lihat `docs/advanced/api.md`.

### Kalau nemu bug?

Buka issue di GitHub repository dengan template "Bug Report". Sertakan: (1) versi PyScrapr (cek di header), (2) OS + versi Python + versi Node, (3) langkah reproduksi yang jelas, (4) expected behavior vs actual behavior, (5) log error dari terminal dan/atau History page, (6) screenshot jika relevan. Makin detail, makin cepat bug-nya bisa diperbaiki.

---

Jika pertanyaan Anda tidak tercakup di sini, jangan ragu membuka diskusi di GitHub Discussions atau mengirimkan email ke maintainer. Dokumen FAQ ini akan terus diperbarui berdasarkan pertanyaan-pertanyaan baru yang masuk dari komunitas pengguna PyScrapr.

---

## Pertanyaan tambahan - Use case spesifik

### Bisakah PyScrapr dipakai untuk riset akademis?

Sangat bisa. Banyak peneliti menggunakan web scraping untuk corpus building, media monitoring, dan analisis tren. PyScrapr cocok karena semua data disimpan lokal (penting untuk kepatuhan IRB/etika riset) dan bisa diekspor ke CSV/JSON untuk diolah di R/Python/SPSS. Ingat untuk selalu dokumentasikan metode pengambilan data dan hormati sumber.

### Bisakah saya memakai PyScrapr untuk SEO monitoring?

Bisa. Kombinasi URL Mapper + Scheduled + Diff sangat efektif untuk memantau perubahan struktur situs kompetitor, deteksi halaman baru, dan tracking perubahan meta title/description. Tambahkan Webhook untuk notifikasi real-time saat kompetitor publish artikel baru.

### Apakah PyScrapr cocok untuk arsip jurnalistik?

Ya, Site Ripper dirancang salah satunya untuk use case ini. Wartawan dan researcher sering perlu arsip snapshot situs sebelum konten dihapus/diedit. PyScrapr menyimpan hasil dengan timestamp, dan Anda bisa kombinasikan dengan tool seperti Wayback Machine CDX API untuk arsip historis.

### Bagaimana kalau saya butuh data real-time?

PyScrapr fokus pada **batch scraping**, bukan streaming real-time. Untuk polling cepat (setiap beberapa detik), gunakan Scheduled Jobs dengan interval pendek - tapi hati-hati dengan rate limit situs target. Untuk true real-time (WebSocket, Server-Sent Events), Anda mungkin perlu solusi custom di luar PyScrapr.

### Bisakah saya menjalankan PyScrapr di server cloud?

Bisa, meski aplikasi dirancang desktop-first. Deploy backend ke VPS (Ubuntu 22.04 direkomendasikan) dengan systemd service, frontend build jadi static files dan serve via Nginx/Caddy. Tambahkan reverse proxy dengan basic auth atau OAuth proxy (Pomerium, Authelia) sebelum expose ke internet - **jangan pernah** expose port 8000 langsung.

### Apakah ada Docker image resmi?

Saat ini belum ada Docker image resmi, tapi komunitas sudah membuat Dockerfile unofficial. Pantau halaman "Community" di repo untuk update. Docker image resmi ada di roadmap Phase 5 - ingin memastikan dulu semua fitur stabil sebelum diselipkan containerization.

### Bagaimana cara backup data PyScrapr?

Cukup backup dua folder: `data/` (berisi database SQLite, vault terenkripsi, dan konfigurasi) dan `downloads/` (hasil scraping). Keduanya adalah file biasa - salin ke external drive, cloud storage, atau NAS. Untuk backup otomatis, gunakan tool seperti Duplicati, Restic, atau Syncthing. Test restore secara berkala - backup tidak berguna kalau tidak bisa direstore.

### Bagaimana performanya di laptop lama?

PyScrapr tetap jalan di laptop 8+ tahun (Core i5 gen 4, RAM 4 GB) untuk tool-tool ringan seperti Image Harvester dan URL Mapper. Yang berat adalah AI Tagger (butuh RAM 8 GB+) dan parallel JS rendering (butuh CPU multi-core). Jika laptop Anda terbatas, turunkan parallel workers ke 1–2 dan hindari tool AI. Alternatifnya, jalankan backend di komputer lebih kuat dan akses UI dari laptop via LAN.

Semoga bagian tambahan ini menjawab pertanyaan-pertanyaan lebih spesifik. Jika ada use case Anda yang belum tercakup, silakan kirim pertanyaan - akan kami tambahkan di revisi berikutnya.

---

## Pertanyaan tentang etika dan best practice

### Apakah etis melakukan scraping?

Tergantung bagaimana dan apa yang di-scrape. Scraping data publik untuk keperluan pribadi, riset, atau pembelajaran umumnya dianggap etis. Scraping yang dianggap tidak etis: (1) membebani server target dengan request berlebihan, (2) mengambil data pribadi orang tanpa izin, (3) mendistribusikan ulang konten ber-copyright, atau (4) melanggar ToS secara eksplisit untuk keuntungan komersial.

### Apa itu robots.txt dan haruskah saya mematuhinya?

`robots.txt` adalah file di root situs (`https://situs.com/robots.txt`) yang memberitahu bot mana yang boleh/tidak mengakses path tertentu. Meski secara teknis tidak mengikat hukum di kebanyakan yurisdiksi, **mengikuti robots.txt adalah praktik etis standar**. PyScrapr tidak otomatis menghormatinya - Anda harus aware dan manual menghindari path yang disallow.

### Berapa delay yang "sopan" antar request?

Tergantung situs. Untuk situs kecil/personal, 2–5 detik antar request adalah sopan. Untuk situs besar (Wikipedia, Reddit, dll), 1 detik masih oke. Untuk situs dengan API resmi dan rate limit jelas, ikuti dokumen API mereka. Selalu ingat: Anda bukan satu-satunya user - setiap request Anda mengonsumsi resource server.

### Bagaimana cara menghargai website owner?

Beberapa cara: (1) identifikasi diri di User-Agent (misal `PyScrapr/1.0 (contact: email@example.com)`) - banyak ops team akan menghargai transparansi, (2) cek apakah ada API resmi sebelum scraping HTML, (3) cache hasil agar tidak re-scrape data yang sama berulang, (4) sebutkan sumber jika data dipublish.

### Apakah saya perlu izin untuk scraping?

Untuk data publik tanpa redistribusi: umumnya tidak perlu izin eksplisit, tapi hormati ToS. Untuk data di balik login, data pribadi, atau konten yang akan direpublish: **sangat disarankan minta izin tertulis**. Kasus hukum scraping (hiQ vs LinkedIn, Meta vs Bright Data, dll) masih berkembang - aturan bisa berbeda per negara.

Semoga FAQ ini cukup komprehensif. Ingat: PyScrapr adalah tool - tanggung jawab penggunaannya ada di tangan Anda. Gunakan dengan bijak.
