# Playwright (Browser Rendering)

> Rendering opsional dengan headless Chromium untuk situs yang berat JavaScript seperti React, Vue, atau SPA lainnya. Ketika httpx biasa hanya menerima HTML kosong berisi placeholder, Playwright menjalankan browser sungguhan di background, menunggu script eksekusi selesai, baru kemudian menyerahkan HTML final ke orchestrator PyScrapr untuk diproses seperti biasa. Fitur ini bersifat per-job, bisa dinyalakan hanya saat dibutuhkan supaya overhead tidak menempel di semua job.

## Apa itu Playwright Rendering

Playwright adalah library automation browser dari Microsoft yang mirip Selenium tapi lebih modern, lebih cepat, dan lebih stabil. Di PyScrapr, Playwright dipakai sebagai rendering engine alternatif untuk situs modern yang rendering konten secara client-side. Situs seperti ini tidak mengembalikan HTML lengkap saat pertama kali di-fetch; yang datang hanya shell kosong berisi `<div id="root"></div>` plus bundle JavaScript besar. Script itulah yang nanti mengisi konten sungguhan melalui API call atau hydration. httpx tidak mengerti JavaScript, jadi hanya menerima shell tersebut dan gagal menemukan gambar, link, atau teks yang terlihat di browser.

Dengan Playwright aktif, PyScrapr menjalankan Chromium instance di belakang layar, membuka URL target, menunggu sampai kondisi load tertentu (misalnya `domcontentloaded` atau `networkidle`), lalu mengambil HTML terakhir setelah semua script selesai eksekusi. HTML itu dikirim balik ke pipeline orchestrator seolah-olah datang dari httpx biasa. Dari sudut pandang kode tool (Harvester, URL Mapper, Site Ripper), tidak ada perbedaan; perubahan hanya di layer fetcher.

Penting untuk dicatat bahwa hanya halaman awal yang dirender via browser. Setelah HTML final diperoleh dan parser menemukan daftar URL asset (gambar, CSS, JS, video), download asset tersebut tetap dikerjakan oleh httpx yang jauh lebih cepat dan ringan. Pendekatan hybrid ini menggabungkan benefit browser rendering (bisa handle SPA) dengan efisiensi httpx (bisa download ratusan file paralel tanpa buka ratusan tab browser). Overhead RAM Chromium yang sekitar 200 MB hanya muncul satu kali per job, bukan per asset.

Playwright di PyScrapr juga terintegrasi dengan fitur existing seperti UA rotation dan proxy settings. Saat browser instance dibuka, user agent string diambil dari pool UA Rotation, dan jika proxy dikonfigurasi di Settings, Chromium akan dipaksa route traffic melalui proxy tersebut. Konfigurasi viewport, locale, timezone juga diwariskan dari settings global untuk konsistensi fingerprint.

## Instalasi

Playwright adalah dependency opsional, tidak ter-install by default supaya user yang tidak butuh tidak perlu download 300 MB binary Chromium.

Langkah instalasi:

```bash
pip install playwright
playwright install chromium
```

Command pertama meng-install Python wrapper library yang ukurannya kecil. Command kedua mengunduh binary Chromium versi spesifik yang sudah dites kompatibel dengan wrapper tersebut. Ukuran binary kira-kira 280 sampai 320 MB tergantung OS dan versi. Binary disimpan di `%USERPROFILE%\AppData\Local\ms-playwright\` pada Windows atau `~/.cache/ms-playwright/` pada Linux dan macOS.

> [!NOTE]
> PyScrapr tidak akan mendorong instalasi Playwright otomatis. Jika Anda aktifkan toggle render di UI tanpa Playwright terpasang, orchestrator akan log warning "playwright not installed, falling back to httpx" dan job tetap jalan dengan httpx. Tidak ada crash, hanya tidak dapat manfaat rendering.

Setelah instalasi, restart server PyScrapr (uvicorn) supaya import Playwright ter-load di process baru. Ini wajib karena Python me-cache module imports di memory.

## Cara pakai

1. Pastikan Playwright sudah terinstal lewat dua command di section Instalasi.
2. Restart server PyScrapr setelah install supaya module ke-detect.
3. Buka salah satu tool yang support rendering: Image Harvester, URL Mapper, atau Site Ripper.
4. Isi URL target seperti biasa di input utama.
5. Scroll ke section Advanced options pada form konfigurasi job.
6. Temukan toggle "Render dengan browser (Playwright)" dan nyalakan.
7. Pilih opsi wait strategy: `load`, `domcontentloaded`, atau `networkidle`. Default `domcontentloaded` cocok untuk sebagian besar situs.
8. Sesuaikan timeout jika situs Anda berat; default 30000 milliseconds (30 detik).
9. Submit job seperti biasa. Progress bar akan menunjukkan fase "rendering browser" sebelum masuk fase "parsing" dan "downloading".
10. Tunggu job selesai. Hasil di Output folder sama persis dengan job tanpa rendering, kecuali konten yang sebelumnya tersembunyi di balik JavaScript sekarang ikut ter-capture.
11. Jika hasil masih kurang, naikkan `playwright_wait_until` ke `networkidle` atau tambah `playwright_timeout_ms` sampai 60000.
12. Compare hasil dengan job tanpa Playwright untuk memastikan rendering memang memberi nilai tambah untuk URL target tersebut.

## Contoh skenario

### Skenario 1: Harvesting gambar dari galeri React

Seorang designer ingin scrape portfolio website dibangun dengan React yang memuat gambar via API call setelah halaman load. Tanpa Playwright, Image Harvester hanya menemukan 3 placeholder `<div>` tanpa gambar. Dengan toggle "Render dengan browser" aktif dan `wait_until=networkidle`, Chromium menunggu semua API call selesai, gambar ter-inject ke DOM, dan Harvester berhasil ambil 147 gambar dari galeri tersebut. Download asset sendiri tetap cepat karena httpx yang handle.

### Skenario 2: URL Mapper pada SPA e-commerce

Tim QA ingin mapping semua halaman produk di situs e-commerce berbasis Vue. Link produk di-generate oleh router client-side dan baru muncul di DOM setelah komponen mount. URL Mapper tanpa Playwright hanya menemukan 5 link top-level (home, about, contact). Dengan Playwright aktif, Mapper berhasil extract 340 internal link karena DOM sudah final saat HTML di-capture. Tree visualization menunjukkan struktur navigasi lengkap.

### Skenario 3: Site Ripper untuk dokumentasi Docusaurus

Tim dev ingin offline copy dokumentasi internal yang dibangun dengan Docusaurus (React-based). Site Ripper tanpa Playwright menghasilkan halaman-halaman kosong karena konten markdown di-render client-side. Dengan Playwright, setiap halaman dirender dulu sehingga HTML yang disimpan sudah berisi teks lengkap, bisa dibuka offline dengan browser tanpa perlu JavaScript.

## Pengaturan detail

### playwright_enabled

Boolean global, default `false`. Ketika `false`, semua job akan pakai httpx terlepas dari toggle per-job. Berguna sebagai kill switch jika Playwright bikin masalah sistem wide.

### playwright_wait_until

String, nilai valid: `load`, `domcontentloaded`, `networkidle`. Default `domcontentloaded`.

- `load` menunggu sampai event `load` window dipicu. Relatif cepat, cocok untuk halaman sederhana.
- `domcontentloaded` menunggu DOM siap tapi tidak menunggu gambar atau script eksternal. Default yang seimbang.
- `networkidle` menunggu sampai tidak ada network request aktif selama 500 ms. Paling lengkap tapi paling lambat, berguna untuk SPA yang banyak API call.

### playwright_timeout_ms

Integer milliseconds, default 30000 (30 detik). Batas maksimum waktu tunggu sebelum Playwright menyerah dan throw error. Naikkan jadi 60000 atau 90000 untuk situs yang responsnya lambat. Turunkan jadi 15000 jika Anda scraping massal dan lebih baik skip halaman lambat daripada tunggu lama.

### playwright_viewport_width dan playwright_viewport_height

Integer, default 1920 dan 1080. Menentukan ukuran viewport browser. Beberapa situs responsive menampilkan layout berbeda berdasarkan viewport, jadi set sesuai kebutuhan (misalnya 375x667 untuk emulasi mobile).

### playwright_locale

String locale, default `en-US`. Affect header `Accept-Language` dan formatting `Intl` di JavaScript. Set ke `id-ID` kalau target adalah situs Indonesia yang menampilkan konten berbeda per locale.

### playwright_headless

Boolean, default `true`. Set `false` hanya saat debugging; browser akan tampil di screen sehingga Anda bisa lihat apa yang terjadi. Tidak cocok untuk production karena butuh display.

## Tips & best practices

1. **Aktifkan hanya untuk URL yang butuh.** Jangan pukul rata semua job dengan Playwright. httpx 5 sampai 10 kali lebih cepat; simpan browser rendering untuk situs yang memang SPA.

2. **Pakai `networkidle` dengan hati-hati.** Beberapa situs punya polling heartbeat yang tidak pernah idle. Job bisa timeout sia-sia. Coba `domcontentloaded` dulu, naik ke `networkidle` kalau hasil kurang.

3. **Monitor penggunaan RAM.** Setiap Chromium process memakan sekitar 200 MB. Jika Anda run paralel 5 job Playwright, siap-siap 1 GB lebih untuk browser saja. Batasi concurrency di Settings.

4. **Kombinasikan dengan UA Rotation.** Browser rendering tanpa UA rotation akan selalu pakai user agent Chromium default yang mudah di-fingerprint sebagai automation.

5. **Cache instance browser untuk job berurutan.** PyScrapr internal sudah re-use Chromium process dalam satu job untuk multi-page crawling seperti URL Mapper. Tidak perlu konfigurasi manual.

6. **Update Playwright rutin.** Binary Chromium terikat versi library Python. Jalankan `pip install -U playwright && playwright install chromium` tiap beberapa bulan untuk keamanan.

7. **Test dengan URL sederhana dulu.** Sebelum pakai Playwright untuk job besar, test dengan satu URL dan bandingkan hasil dengan dan tanpa rendering. Pastikan ada peningkatan nyata supaya overhead terbayar.

8. **Cek log rendering.** Log server menampilkan baris `playwright render started` dan `playwright render done in 4.2s`. Jika render lama di atas 20 detik konsisten, situs mungkin butuh wait_until lebih ringan atau timeout lebih longgar.

## Troubleshooting

### Problem: Error "playwright executable not found"

**Gejala:** Job gagal dengan exception "Executable doesn't exist at ...chromium...".

**Penyebab:** Library Playwright terinstal tapi binary Chromium belum diunduh.

**Solusi:** Jalankan `playwright install chromium` di terminal yang aktif di virtualenv PyScrapr. Pastikan command sukses sampai akhir. Restart server.

### Problem: Timeout 30000 ms exceeded

**Gejala:** Job error dengan pesan "Timeout 30000ms exceeded" di tengah rendering.

**Penyebab:** Situs lambat, koneksi jelek, atau `wait_until=networkidle` memicu heartbeat polling tanpa akhir.

**Solusi:** Naikkan `playwright_timeout_ms` ke 60000, atau ganti strategy ke `domcontentloaded`. Jika hanya sebagian URL yang timeout, tandai skip dan lanjut sisanya.

### Problem: Konsumsi RAM membengkak setelah banyak job

**Gejala:** Memory PyScrapr naik terus tidak turun meski job selesai.

**Penyebab:** Browser context tidak di-close dengan benar karena exception atau bug. Chromium zombie process tertinggal.

**Solusi:** Restart server PyScrapr. Secara proaktif, kill process chrome.exe via Task Manager. Update Playwright ke versi terbaru yang biasanya sudah patch memory leak.

### Problem: Proxy tidak dipakai oleh Playwright

**Gejala:** IP yang terlihat oleh target adalah IP asli, bukan proxy.

**Penyebab:** Proxy settings belum di-propagate ke browser context, atau proxy URL format tidak dikenali Chromium.

**Solusi:** Pastikan `proxy_enabled=true` dan URL proxy berformat `http://user:pass@host:port` atau `socks5://host:port`. Restart server supaya settings ter-apply.

### Problem: Hasil HTML identik dengan non-Playwright

**Gejala:** Job dengan dan tanpa Playwright menghasilkan HTML sama.

**Penyebab:** Situs target sebenarnya server-side rendered, jadi httpx sudah cukup; atau wait_until terlalu cepat sehingga Chromium tidak sempat menunggu konten.

**Solusi:** Coba `wait_until=networkidle` dan bandingkan lagi. Jika tetap sama, situs memang SSR dan Anda tidak butuh Playwright untuk URL tersebut.

### Problem: Chromium crash di server headless Linux

**Gejala:** Error "Failed to launch browser process" di server Linux tanpa display.

**Penyebab:** Library dependency Chromium tidak ada di container atau minimal Linux.

**Solusi:** Jalankan `playwright install-deps chromium` sebagai root untuk install apt package (libnss3, libxss1, libasound2, dll). Untuk container Docker, gunakan image `mcr.microsoft.com/playwright/python` yang sudah lengkap.

## Keamanan / batasan

- Binary Chromium adalah software eksternal berukuran besar; update rutin untuk patch keamanan.
- Browser rendering membuka potensi eksekusi JavaScript dari situs target; jangan render situs yang Anda curigai malicious tanpa sandbox tambahan.
- Playwright menulis cookie dan cache ke disk lokal; data bisa berisi tracking dari situs target. Bersihkan berkala dari folder cache.
- Performance lebih lambat 5 sampai 10 kali dibanding httpx untuk halaman awal.
- Memory usage tambahan sekitar 200 MB per browser instance aktif.
- Tidak support download video streaming HLS/DASH via browser; gunakan Media Downloader untuk use case itu.
- Hanya initial page yang dirender; iframe dan pop-up tidak otomatis tertangkap kecuali kode khusus.
- Tidak ada UI preview screenshot; jika butuh debugging visual, set `headless=false` dan jalankan lokal.
- Render blocking ke script eksternal yang diblok oleh ad-blocker bisa menyebabkan hang; nonaktifkan ad-blocker di profile Chromium.

## FAQ

**Q: Apakah Playwright support Firefox atau WebKit?**
A: Secara library ya, tapi PyScrapr saat ini hanya pakai Chromium karena paling umum dan kompatibel. Support Firefox/WebKit ada di roadmap untuk fingerprint diversity.

**Q: Berapa banyak job paralel yang aman dengan Playwright?**
A: Rule of thumb 1 job Playwright per 500 MB RAM free. Di mesin 8 GB RAM dengan aplikasi lain jalan, aman 3-4 job paralel. Di mesin 16 GB bisa 8-10.

**Q: Apakah cookie dari Auth Vault dipakai di browser context?**
A: Ya, Auth Vault cookie di-inject ke browser context sebelum navigate ke URL target. Authentication berjalan seperti di tool lain.

**Q: Bisa eksekusi custom JavaScript di halaman?**
A: Saat ini tidak ada UI untuk custom script, tapi internal API Playwright di orchestrator bisa `page.evaluate(script)`. Fitur expose ke UI ada di roadmap.

**Q: Apakah Playwright bisa handle CAPTCHA?**
A: Tidak langsung; browser rendering bukan solver. Pairkan dengan fitur CAPTCHA Solver yang aktif saat element captcha ter-detect di DOM.

**Q: Perbedaan Playwright vs Selenium vs Puppeteer untuk scraping?**
A: Playwright lebih modern, auto-wait built-in, API lebih clean, dan support multi-browser. Selenium warisan lama, Puppeteer hanya Chromium dari Google. Pilihan Playwright di PyScrapr karena stabil dan wrapper Python-nya first-class (bukan third-party).

**Q: Apakah screenshot halaman bisa disimpan?**
A: Ya, ada setting `playwright_save_screenshot` (default off) yang menyimpan PNG viewport ke folder output tiap job untuk debugging visual.

**Q: Apakah performance Playwright affect scheduled jobs?**
A: Scheduled job yang pakai Playwright jelas lebih lambat dari versi httpx. Estimasi waktu di Scheduler mungkin off; monitor durasi pertama lalu adjust interval supaya tidak overlap.

## Stealth mode (anti-bot fingerprinting)

PyScrapr secara default mengaktifkan layer stealth untuk mengurangi sidik jari otomatis yang dikenal sebagai bot. Setting `playwright_stealth_enabled` (default `true`) ada di Settings UI bagian Playwright.

### Apa yang disembunyikan

Browser headless punya banyak indikator yang gampang ditangkap WAF, bot manager, dan anti-fraud system. Stealth layer menutupi:

- `navigator.webdriver` default `true` di headless, ditipu jadi `undefined`
- `navigator.plugins` default kosong, di-isi PDF Viewer palsu
- `navigator.languages` default cuma `["en-US"]`, di-set lebih realistis
- Object `chrome` hilang di headless, di-inject minimal
- WebGL renderer default "Google SwANGLE" sebagai giveaway, di-spoof ke vendor umum
- API `navigator.permissions` leak status notifications/geolocation, di-patch
- Pattern iframe contentWindow di-handle
- Canvas/WebGL fingerprint randomize minor noise

Plus launch args: `--disable-blink-features=AutomationControlled` yang menghilangkan flag `cdc_*` injection.

### Implementation dua layer

1. **Browser launch args** gratis, tanpa dep tambahan, langsung dari Chromium. Default selalu aktif kalau setting ON.
2. **playwright-stealth library** 17 evasion module yang di-inject sebagai init script ke tiap page baru. Lazy import: kalau library tidak terpasang, layer ini di-skip silently dan hanya layer 1 yang aktif.

Install library tambahan (opsional, untuk full coverage):

```powershell
& "C:\laragon\bin\python\python-3.10\python.exe" -m pip install playwright-stealth
```

> [!NOTE]
> Tanpa playwright-stealth, layer 1 (launch args) tetap aktif. Sudah cukup untuk situs Cloudflare basic. Tapi untuk DataDome atau Akamai, layer 2 dibutuhkan.

### Kapan stealth membantu

- Cloudflare tier basic (challenge "Checking your browser")
- DataDome basic
- Akamai BotManager basic
- Imperva Incapsula basic
- Custom WAF yang cek `navigator.webdriver`

### Kapan stealth TIDAK cukup

- Cloudflare Turnstile v2 (sudah deteksi pattern stealth ini juga)
- FingerprintJS Pro (analisis behavioral mouse + timing)
- PerimeterX dengan device attestation
- Situs yang require active solver CAPTCHA

Untuk kasus advanced, kombinasikan dengan: residential proxy rotation, real Chrome (channel chrome bukan Chromium bundled), dan rate limiting sangat lambat.

### Disable kalau tidak perlu

Stealth menambah sekitar 50-100 ms overhead per page. Untuk situs yang terkonfirmasi tidak punya bot detection, matikan via Settings: Playwright: Stealth mode toggle untuk performance maksimal.

### Test fingerprint

Cara cek apakah stealth efektif:

1. Buka Screenshot tool, scan `https://bot.sannysoft.com/`
2. Tanpa stealth: banyak indikator merah (WebDriver, Chrome, Plugins length, Languages, dll)
3. Dengan stealth: mayoritas hijau

Test alternatif: `https://abrahamjuliot.github.io/creepjs/` untuk lihat skor fingerprint detail.

## Related docs

- [Image Harvester](/docs/tools/image-harvester.md) - Tool utama yang sering butuh Playwright untuk galeri React.
- [URL Mapper](/docs/tools/url-mapper.md) - Mapping situs SPA butuh rendering supaya link router ter-capture.
- [Site Ripper](/docs/tools/site-ripper.md) - Offline copy situs modern wajib dengan Playwright kalau SSR tidak aktif.
- [Proxy Rotation](/docs/advanced/proxy.md) - Proxy settings otomatis dipakai oleh browser instance.
- [UA Rotation](/docs/advanced/ua-rotation.md) - User agent rotation diwariskan ke browser context.
- [Settings](/docs/system/settings.md) - Section Playwright untuk tuning global default.
