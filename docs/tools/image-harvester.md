# Image Harvester

> Tool khusus untuk ekstraksi dan pengunduhan massal semua gambar dari satu atau banyak halaman web sekaligus, lengkap dengan filter ukuran, deduplikasi SHA-1, dan organisasi folder otomatis per-domain.

## Deskripsi

Image Harvester adalah tool inti pertama PyScrapr yang dirancang untuk satu tujuan sederhana namun sering dibutuhkan: mengambil semua gambar yang ada di sebuah halaman web dengan cara yang cerdas, efisien, dan tidak merepotkan. Alih-alih melakukan klik kanan satu per satu atau menulis skrip Python manual, tool ini membuka halaman target, memparsing seluruh struktur HTML menggunakan parser BeautifulSoup, lalu mengumpulkan URL gambar dari berbagai titik yang mungkin menyimpan referensi gambar: atribut `src` pada tag `<img>`, atribut `srcset` untuk responsive image, tag `<source>` di dalam elemen `<picture>`, atribut lazy-load populer seperti `data-src`, `data-original`, dan `data-lazy`, meta tag `og:image` untuk social preview, hingga opsional parsing `background-image` pada CSS inline maupun eksternal.

Di bawah hood, Image Harvester menggunakan arsitektur asynchronous dengan `httpx` dan `asyncio` sehingga bisa mengunduh banyak gambar secara paralel tanpa membebani memori. Default concurrency diatur ke 8 koneksi simultan - cukup untuk memaksimalkan throughput rata-rata tanpa membuat server target menganggap request kita sebagai DDoS. Setiap gambar yang berhasil diunduh langsung dihash menggunakan SHA-1, dan hash tersebut dicek terhadap database lokal di folder tujuan. Jika hash sudah pernah ada, file dianggap duplikat dan dilewati - ini sangat berguna saat meng-harvest situs yang memakai banyak placeholder atau logo yang sama di setiap halaman.

Salah satu alasan utama tool ini dibuat adalah karena kebanyakan image downloader di market (misalnya DownThemAll atau Image Downloader extension Chrome) hanya bekerja per-tab, tidak memfilter berdasarkan dimensi, dan tidak bisa membedakan gambar "beneran" dari icon 16x16 yang tak penting. Image Harvester memecahkan masalah ini dengan dua mekanisme: pertama, filter `min_width` dan `min_height` yang membaca dimensi gambar dari header file (HEAD request + Pillow parsing) tanpa harus mengunduh full bytes; kedua, filter `min_bytes` yang memotong file mini di bawah threshold tertentu. Hasilnya: folder output hanya berisi gambar yang benar-benar relevan, bukan sampah.

Positioning Image Harvester vs alternatif komersial: tool ini gratis, offline-first (tidak ada telemetri), dan terintegrasi langsung ke ekosistem PyScrapr - artinya gambar yang di-harvest bisa langsung diklasifikasi via AI Tools (CLIP), di-export via History, atau dijadwalkan lewat Scheduler. Ini yang tidak bisa ditawarkan oleh extension browser manapun.

## Kapan pakai tool ini?

- **Riset kompetitor e-commerce** - scrape semua gambar produk dari toko kompetitor untuk menganalisis positioning visual, kualitas fotografi produk, dan gaya styling yang mereka pakai.
- **Koleksi referensi desain** - ambil semua gambar dari halaman portfolio desainer terkenal di Behance, Dribbble, atau Awwwards sekaligus untuk mood board.
- **Arsip berita lokal** - unduh semua gambar artikel dari media online seperti Kompas, Detik, atau Tempo untuk keperluan jurnalistik atau riset media.
- **Dataset training machine learning** - kumpulkan ribuan gambar dari situs stock image gratis untuk melatih model klasifikasi atau detection.
- **Backup portfolio pribadi** - download semua foto dari blog lama, tumblr yang akan ditutup, atau hosting gambar yang mau shutdown.
- **Migrasi konten CMS** - saat pindah dari WordPress ke Ghost misalnya, harvest semua `wp-content/uploads` dari situs lama dengan satu klik.
- **Analisis katalog real estate** - ambil semua foto listing dari situs properti untuk membandingkan kualitas presentasi antar agen.
- **Scraping resep dan lifestyle** - kumpulkan gambar makanan dari blog resep untuk keperluan meal planning visual atau konten Instagram.

## Cara penggunaan

1. Buka PyScrapr di browser (`http://localhost:5173` jika development, atau port yang Anda konfigurasi). Di sidebar kiri, klik menu `Image Harvester`. Halaman akan menampilkan form konfigurasi di panel kiri dan area preview kosong di kanan.

2. Di field `Target URL`, masukkan alamat halaman yang ingin di-harvest. Contoh: `https://unsplash.com/s/photos/mountain`. Tool ini menerima URL tunggal atau multiple URLs (satu per baris). Ekspektasi output: URL tervalidasi secara real-time - kalau format salah, ikon warning merah muncul di kanan field.

3. Pilih **Tipe gambar yang diizinkan** di dropdown `allowed_types`. Default-nya `jpg, jpeg, png, webp, gif`. Untuk use case tertentu Anda bisa menambahkan `svg` (hati-hati, ini XML bukan binary) atau `avif`. Ekspektasi: chip-chip ekstensi muncul di bawah field.

4. Set `Min width (px)` dan `Min height (px)` dalam pixel. Default 200x200. Untuk harvesting foto hi-res naikkan ke 800x600 atau lebih. Untuk icon kecil turunkan ke 32x32. Tool akan menolak file yang dimensinya di bawah threshold ini.

5. Set `Min size (bytes)` (ukuran file minimum). Default 10240 (10KB). Ini mencegah download placeholder 1KB atau tracking pixel.

6. Di field **Exclude patterns**, masukkan pola regex atau substring URL yang harus dilewati. Contoh: `thumb`, `icon`, `avatar`, `logo-small`. Setiap entry di baris terpisah.

7. Atur `Concurrency` (jumlah download paralel). Default 8 - jangan naikkan di atas 16 untuk situs kecil atau Anda berisiko di-block. Untuk CDN besar seperti Cloudinary, 12 masih aman.

8. Opsional: centang `Parse CSS background-image` kalau target memakai `background-image: url(...)` di inline style atau stylesheet. Ini melambatkan crawl ~20% karena harus fetch dan parse CSS file.

9. Klik tombol `Start` (warna biru besar di bawah form). Backend akan membuat job entry di database dan mengembalikan `job_id`. Ekspektasi: tombol berubah jadi disabled + spinner, dan panel kanan mulai menampilkan progress bar.

10. Pantau progress via live thumbnail grid di panel kanan. Setiap gambar yang berhasil diunduh akan muncul sebagai thumbnail kecil dengan border hijau. Gambar yang gagal (timeout, 404, filter miss) muncul dengan border merah dan tooltip error. Server-Sent Events (SSE) memastikan update real-time tanpa polling.

11. Setelah job selesai (status berubah jadi `completed`), bar atas panel kanan menampilkan ringkasan: total found, downloaded, filtered out, duplicates, errors. Anda bisa klik thumbnail apapun untuk preview full-size di lightbox modal.

12. Klik tombol `Download ZIP` di header untuk mengunduh semua gambar dalam satu archive, atau buka folder hasil di Windows Explorer secara manual. Job ini juga otomatis tercatat di History dan bisa di-replay kapanpun.

## Pengaturan / Konfigurasi

### Target URL
Alamat halaman yang akan di-harvest. Wajib diisi, harus HTTPS/HTTP valid. Mendukung input multiple (satu URL per baris). Default: kosong. Rekomendasi: mulai dari satu URL untuk testing, baru batch kalau sudah yakin pola filter-nya benar.

### allowed_types
Daftar ekstensi file yang akan diproses. Default: `["jpg", "jpeg", "png", "webp", "gif"]`. Rekomendasi umum: biarkan default untuk content photography, tambah `svg` kalau target UI/icon library, hindari `bmp`/`tiff` kecuali memang scraping arsip ilmiah. Ubah dari default saat target punya ekstensi unik seperti `avif` (Google modern) atau `heic` (Apple).

### min_width / min_height
Dimensi minimum gambar dalam pixel. Default: 200x200. Rekomendasi: 400x400 untuk konten editorial, 1000x1000 untuk wallpaper/print, 64x64 untuk icon scraping. Ubah saat target menampilkan banyak thumbnail placeholder yang Anda tidak inginkan.

### min_bytes
Ukuran file minimum dalam byte. Default: 10240 (10KB). Rekomendasi: 50000 (50KB) untuk foto berkualitas, 5000 (5KB) untuk icon. Ubah ke nilai tinggi ketika banyak noise dari spacer GIF / 1x1 tracking pixel.

### exclude_patterns
Daftar pola substring/regex URL yang dilewati. Default: kosong. Rekomendasi: `["thumb", "small", "preview", "avatar", "placeholder"]` untuk kebanyakan e-commerce. Ubah tergantung naming convention target - inspect 3-4 URL gambar yang tidak Anda inginkan untuk menemukan pola.

### concurrency
Jumlah download paralel. Default: 8. Rekomendasi: 4 untuk situs kecil/WordPress, 8 untuk medium, 12-16 untuk CDN besar. Ubah turun kalau dapat HTTP 429 (rate limit), naik kalau jaringan fast tapi total time lambat.

### parse_css_background
Boolean untuk parse `background-image` CSS. Default: false. Rekomendasi: aktifkan hanya saat halaman memakai hero image via CSS (cek via inspect element). Ubah ke true saat menemukan gambar tertentu tidak ter-harvest padahal kelihatan di browser.

### follow_srcset
Boolean untuk mengikuti `srcset` dan memilih ukuran terbesar. Default: true. Rekomendasi: biarkan true hampir selalu. Ubah ke false hanya kalau Anda sengaja ingin versi kecil untuk bandwidth hemat.

### user_agent
String User-Agent header. Default: modern Chrome UA. Rekomendasi: biarkan default. Ubah ke `Googlebot/2.1` saat situs serve versi berbeda untuk bot vs human.

## Output

Semua file disimpan di struktur folder yang konsisten dan mudah ditelusuri:

```
downloads/
└── <domain>/
    └── <YYYY-MM-DD>_images/
        ├── originals/
        │   ├── a4f3b2c1e8d9...jpg
        │   ├── 7e9f2a1b5c3d...png
        │   └── ...
        ├── manifest.json
        └── thumbnails/
            ├── a4f3b2c1e8d9_thumb.jpg
            └── ...
```

- **originals/** berisi file gambar asli, dinamai dengan 16 karakter pertama SHA-1 hash + ekstensi asli.
- **manifest.json** mencatat setiap file: source_url, local_path, width, height, bytes, hash, timestamp. Berguna untuk audit atau re-import.
- **thumbnails/** berisi thumbnail 256px (generated via Pillow) untuk preview cepat.

Format file: binary asli, tidak dikonversi. Jika butuh konversi ke WebP, gunakan integrasi Pipeline → Image Converter.

## Integrasi dengan fitur lain

- **AI Tools (CLIP classification)** - hasil harvest bisa langsung di-feed ke AI Tools untuk zero-shot classification. Misal: Anda harvest 500 foto dari Pinterest, lalu klasifikasikan ke label `["beach", "mountain", "urban", "indoor"]` dalam hitungan menit.
- **History & Export** - setiap job tersimpan di History dengan metadata lengkap. Anda bisa re-run job yang sama, export hasil ke ZIP/JSON, atau compare antar run untuk deteksi perubahan konten.
- **Scheduler** - jadwalkan harvest harian/mingguan pada URL tertentu. Berguna untuk monitoring katalog produk kompetitor atau arsip berita otomatis.
- **Pipeline post-processing** - pipe hasil ke Image Converter (WebP), Image Resizer (thumbnail set), atau Metadata Stripper (hapus EXIF sebelum publikasi ulang).
- **Site Ripper handoff** - kalau Anda perlu seluruh site (HTML+CSS+JS), mulai dari Site Ripper; tapi kalau cuma gambar, Image Harvester lebih cepat 5-10x.
- **URL Mapper precursor** - gunakan URL Mapper dulu untuk discover semua halaman di site, lalu feed list URL-nya ke Image Harvester untuk bulk harvest.

## Tips & Best Practices

1. **Mulai dari satu URL untuk kalibrasi filter** - sebelum batch ratusan halaman, jalankan satu URL dulu, lihat hasilnya, baru tune `min_width`/`exclude_patterns`. Ini menghemat waktu debugging signifikan.

2. **Pakai `exclude_patterns` untuk memotong noise** - kalau target punya banyak thumbnail path seperti `/150x150/` atau `/thumb/`, masukkan pola ini di exclude. Satu regex bisa menghilangkan 70% sampah.

3. **Hormati robots.txt meski tool tidak memaksa** - secara default Image Harvester tidak mem-block berdasarkan robots.txt (karena ini user-initiated download), tapi untuk ethical scraping cek file tersebut secara manual dan patuhi `Disallow`.

4. **Gunakan concurrency lebih rendah untuk situs WordPress** - banyak WP host di shared hosting yang mudah lambat. Turunkan ke 4 untuk menghindari 503/504.

5. **Aktifkan `parse_css_background` hanya saat perlu** - fitur ini melambatkan crawl 20-40% karena fetch CSS external. Aktifkan setelah Anda konfirmasi via DevTools bahwa gambar penting disajikan via background-image.

6. **Manfaatkan SHA-1 dedup untuk incremental harvest** - kalau Anda re-run job yang sama minggu depan, duplikat otomatis di-skip. Jadi "harvest mingguan" hanya mengunduh gambar baru.

7. **Set User-Agent wajar** - situs tertentu block default Python UA. PyScrapr sudah pakai Chrome UA modern, tapi kalau masih di-block, coba `Googlebot` yang kadang di-allowlist.

8. **Pasangkan dengan AI Tools untuk auto-tagging** - alih-alih manual review 1000 gambar, jalankan CLIP classification dengan label relevan, lalu filter hasilnya di grid view. Menghemat jam-jam kerja.

## Troubleshooting

### Problem: HTTP 429 Too Many Requests
**Gejala:** Job berhenti tiba-tiba, panel error menunjukkan banyak entry dengan status 429, sebagian besar gambar tidak terunduh.
**Penyebab:** Server target menerapkan rate limit per-IP; concurrency Anda terlalu tinggi atau request rate melewati threshold mereka.
**Solusi:** Turunkan `concurrency` ke 2-4. Tunggu 5-10 menit sebelum retry. Kalau masih kena 429, tambahkan delay eksplisit via setting `request_delay_ms` ke 500-1000.

### Problem: SSL Certificate verification failed
**Gejala:** Log menampilkan `SSLError: certificate verify failed` untuk URL HTTPS tertentu.
**Penyebab:** Situs target pakai self-signed certificate, certificate expired, atau mismatch CN. Bisa juga bundle CA di Python installation outdated.
**Solusi:** Update `certifi` (`pip install --upgrade certifi`). Kalau masalah persist dan Anda yakin target aman, aktifkan toggle **Insecure SSL** di advanced settings - tapi hanya untuk target personal/development, JANGAN untuk production.

### Problem: Tidak ada gambar ter-harvest padahal halaman jelas ada gambar
**Gejala:** Job selesai dengan `downloaded: 0`, tapi saat buka URL di browser terlihat banyak gambar.
**Penyebab:** Gambar di-load via JavaScript (SPA seperti React/Vue). Image Harvester hanya parse HTML statis, tidak menjalankan JS.
**Solusi:** Inspect page source (Ctrl+U) vs DevTools Elements - kalau `<img>` tidak ada di source, berarti rendered by JS. Gunakan Site Ripper dengan headless browser mode, atau cari API endpoint yang men-serve list gambar (biasanya JSON) dan harvest dari situ.

### Problem: PermissionError saat menulis file
**Gejala:** Error `[WinError 5] Access is denied` atau `PermissionError: [Errno 13]` di log.
**Penyebab:** Folder `downloads/` read-only, atau file lama sedang di-lock proses lain (antivirus scanning), atau path terlalu panjang (>260 chars di Windows).
**Solusi:** Tutup antivirus real-time scan sementara. Pindahkan folder `downloads/` ke root drive untuk memperpendek path. Di Windows 10+, enable long path via registry `LongPathsEnabled=1`.

### Problem: Memory error pada harvest besar (>5000 gambar)
**Gejala:** Python process crash atau OS menampilkan "Out of memory". Browser tab PyScrapr freeze.
**Penyebab:** Live thumbnail grid menumpuk di DOM browser. Concurrency tinggi + file besar bikin memory spike.
**Solusi:** Turunkan `concurrency` ke 4. Set `max_thumbnails_in_grid` ke 200 di settings. Restart browser setiap 2000 file. Untuk harvest mega-scale, gunakan mode headless via API langsung tanpa UI.

### Problem: Gambar ter-download tapi file corrupt (tidak bisa dibuka)
**Gejala:** Thumbnail tidak muncul, file size terlihat normal, tapi Pillow/Photo Viewer error "invalid image".
**Penyebab:** Server return HTML error page (404, cloudflare challenge) dengan content-type gambar palsu. Atau koneksi putus di tengah download.
**Solusi:** Aktifkan **Validate after download** di settings - tool akan verify via Pillow dan hapus file invalid. Periksa log error untuk URL spesifik, buka manual di browser untuk lihat apakah ada challenge page.

### Problem: Encoding error pada URL dengan karakter non-ASCII
**Gejala:** `UnicodeDecodeError` atau `KeyError` saat parsing URL berisi karakter Cina, Arab, atau karakter aksen.
**Penyebab:** URL tidak ter-percent-encode dengan benar sebelum request.
**Solusi:** Update ke versi PyScrapr terbaru yang memakai `urllib.parse.quote` dengan safe chars yang benar. Sebagai workaround, encode manual URL-nya dengan tool online IDN converter sebelum paste ke form.

### Problem: Disk penuh di tengah job
**Gejala:** Job berhenti di tengah, error `OSError: [Errno 28] No space left on device`.
**Penyebab:** Folder target berada di drive dengan sisa space terbatas; ratusan gambar hi-res bisa makan GB dalam hitungan menit.
**Solusi:** Cek disk sebelum job besar (klik **Estimate Size** di form - tool akan HEAD-sampling dulu). Pindahkan `downloads/` ke drive lebih besar via settings `download_root`. Untuk stream ke external drive, mount terlebih dahulu.

### Problem: Dependency `Pillow` tidak ter-install
**Gejala:** Error startup `ModuleNotFoundError: No module named 'PIL'`.
**Penyebab:** Environment Python tidak lengkap; Pillow dibutuhkan untuk dimension checking dan thumbnail generation.
**Solusi:** Jalankan `pip install -r requirements.txt` di folder backend. Kalau gagal install karena build tools, install Pillow pre-built: `pip install --only-binary :all: Pillow`.

### Problem: Performa sangat lambat di WiFi rumah
**Gejala:** Download speed ~50KB/s meskipun internet Anda 100Mbps.
**Penyebab:** Target server throttle per-IP, atau TCP connection overhead dari banyak small files.
**Solusi:** Naikkan `concurrency` ke 12 untuk maximize parallelism. Pastikan DNS cepat (pakai Cloudflare 1.1.1.1). Kalau problem konsisten di server tertentu, itu memang throttle mereka - tidak ada solusi client-side.

### Problem: Duplicate detection false positive
**Gejala:** Gambar berbeda tidak ter-download, log menunjukkan skip karena duplicate, tapi sebenarnya konten beda.
**Penyebab:** Dua URL berbeda memang serve file byte-identik (shared CDN asset). Ini bukan bug, SHA-1 correctly flag sebagai dup.
**Solusi:** Kalau Anda butuh semua dari kedua URL (untuk tracking asal), disable dedup via toggle **Keep duplicates** dan biar filesystem naming yang handle.

## FAQ

**Q: Apakah Image Harvester bisa download dari situs yang butuh login?**
A: Secara native tidak, karena belum ada mekanisme session cookie injection di form. Sebagai workaround, ekspor cookies dari browser via extension seperti "Get cookies.txt", lalu paste ke field **Cookie header** di advanced settings. Ini bekerja untuk kebanyakan auth berbasis cookie.

**Q: Berapa jumlah maksimum URL yang bisa di-harvest dalam satu job?**
A: Tidak ada hard limit, tapi secara praktis 50-100 URL per job optimal. Untuk batch 500+, pecah jadi beberapa job atau gunakan Scheduler untuk chain. Database SQLite mulai lambat di satu job dengan >10.000 gambar.

**Q: Apakah tool ini menghargai hak cipta?**
A: Tool ini hanya teknis mengunduh file publik yang sudah di-serve oleh server - sama seperti browser. Legalitas penggunaan kembali gambar adalah tanggung jawab user. Untuk penggunaan komersial, selalu cek license di source site.

**Q: Bisakah saya men-download hanya gambar baru sejak run terakhir?**
A: Ya, otomatis. SHA-1 dedup memastikan file yang sudah ada di-skip. Untuk deteksi "gambar baru" by URL (bukan by content), gunakan History diff view yang membandingkan manifest antar run.

**Q: Format apa yang paling efisien untuk simpan hasil?**
A: File asli (JPG/PNG/WebP) sudah optimal untuk preservation. Kalau butuh storage hemat, aktifkan pipeline post-processing ke WebP 85% quality - biasanya cut size 60% tanpa loss perceptible.

**Q: Apakah bisa harvest Instagram/TikTok?**
A: Untuk halaman profile publik Instagram, kadang bisa tapi tidak reliable karena mereka render via JS berat. Untuk Instagram, gunakan Media Downloader yang memakai yt-dlp dengan support khusus Instagram.

**Q: Bagaimana cara harvest gambar di-behind pagination?**
A: Pakai URL Mapper dulu untuk discover semua halaman pagination, export list URL-nya, lalu paste ke Image Harvester sebagai multi-URL input. Atau gunakan Site Ripper kalau pattern URL-nya predictable.

**Q: Kenapa beberapa file lebih kecil dari `min_bytes` masih ter-download?**
A: Filter `min_bytes` dicek via Content-Length header. Kalau server tidak kirim header tersebut (transfer-encoding: chunked), filter di-bypass dan validation hanya terjadi post-download.

**Q: Bisakah output langsung di-upload ke cloud storage (S3, Drive)?**
A: Belum ada direct upload, tapi Anda bisa pakai rclone atau Google Drive sync pada folder `downloads/`. Fitur native upload direncanakan di roadmap Phase 4.

**Q: Apakah aman untuk dijalankan 24/7 sebagai harvesting service?**
A: Ya, backend FastAPI stabil untuk long-running. Pastikan disk rotation policy di place (auto-archive folder >30 hari ke external drive), dan monitor log file size agar tidak meledak.

## Keterbatasan

- Tidak menjalankan JavaScript - situs SPA (React/Vue/Angular) yang render gambar via JS tidak ter-harvest. Gunakan Site Ripper untuk kasus ini.
- Tidak mendukung WebSocket/streaming gambar (misal live camera feed).
- Tidak ada OCR built-in - kalau butuh ekstrak text dari gambar, kombinasikan dengan Pipeline OCR module.
- Dedup berbasis SHA-1 exact match - tidak deteksi near-duplicate (image yang sedikit dimodifikasi terdeteksi sebagai berbeda).
- Tidak parse gambar di dalam iframe cross-origin karena CORS policy.
- Maksimal file size per gambar default 100MB - di atas itu akan di-skip untuk keamanan.
- Tidak ada priority queue antar job - FIFO sederhana, job lama blocking job baru.

## Related docs

- [URL Mapper](url-mapper.md) - untuk discover semua halaman di site sebelum bulk harvest
- [Site Ripper](site-ripper.md) - alternatif saat butuh full offline mirror bukan cuma gambar
- [AI Tools (CLIP)](ai-tools.md) - klasifikasi otomatis hasil harvest dengan zero-shot labels
- [Pipeline & Post-processing](/docs/utilities/pipeline.md) - konversi, resize, strip metadata
- [Scheduler](/docs/system/scheduled.md) - jadwalkan harvest periodik
- [History & Export](../system/history.md) - review dan replay job lama
