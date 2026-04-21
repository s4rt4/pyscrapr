# Screenshot Generator

> Tool capture screenshot situs secara otomatis via headless Chromium (Playwright), dengan preset viewport desktop, laptop, tablet, hingga mobile, plus opsi full-page, dark mode emulation, dan custom dimension. Cocok buat dokumentasi, bukti visual, monitoring tampilan, atau riset UI pesaing tanpa perlu buka browser manual setiap kali.

## Apa itu Screenshot Generator

Screenshot Generator adalah modul PyScrapr yang menangkap tampilan visual sebuah situs web dan menyimpannya sebagai file PNG. Secara teknis, tool ini menjalankan instance Chromium headless (tanpa UI) di background, navigasi ke URL target, menunggu halaman selesai load sesuai strategi yang Anda pilih, lalu mengambil snapshot pixel halaman dengan viewport yang Anda tentukan. Output adalah file PNG berkualitas tinggi yang bisa Anda download langsung dari UI atau ambil lewat REST API.

Berbeda dengan tekan `PrtScn` manual, tool ini melakukan automasi penuh: Anda tinggal tempel URL, pilih ukuran layar target, klik Capture. Tool akan menyimulasikan device yang Anda pilih (iPhone 14 misalnya punya viewport 390x844), aktifkan dark mode lewat media query `prefers-color-scheme: dark` kalau perlu, lalu scroll otomatis sampai dasar halaman kalau Anda aktifkan mode full-page. Hasilnya konsisten, bebas toolbar browser, bebas kursor, bebas popup notifikasi desktop Anda.

> [!NOTE]
> Screenshot Generator butuh Playwright + browser binary Chromium. Jalankan satu kali: `pip install playwright && playwright install chromium`. Setelah itu tool siap dipakai sepenuhnya offline. Tidak ada call ke service pihak ketiga seperti screenshotmachine.com atau apiflash.

Kapan tool ini berguna? Pertama, buat dokumentasi produk SaaS yang terus-menerus update UI. Kedua, buat visual regression monitoring (gabungkan dengan Diff Detection untuk deteksi perubahan layout otomatis). Ketiga, riset UX kompetitor untuk proposal klien. Keempat, arsip historis situs yang mungkin hilang, rebrand, atau redesign kapan saja. Kelima, bukti visual untuk laporan ke klien bahwa "situs ini tampak seperti ini pada tanggal sekian".

Filosofi-nya sederhana: daripada install browser extension macam-macam, daripada pakai layanan online yang ribet sign-up dan ada limit gratisnya, daripada bikin script Puppeteer sendiri, cukup satu form di PyScrapr.

## Cara pakai (step-by-step)

1. Buka PyScrapr di browser, lalu pilih menu **Screenshot** di sidebar. Anda akan melihat form input di atas dan area hasil kosong di bawah.

2. Di field `Target URL`, paste alamat lengkap situs yang ingin di-capture. Contoh: `https://github.com`, `https://tokopedia.com/discover`, `https://figma.com`. Skema `https://` atau `http://` wajib ada.

3. Pilih **Viewport** dari dropdown. Opsi default:
   - `Desktop (1920x1080)` untuk pengalaman monitor desktop standar
   - `Desktop HD (2560x1440)` untuk monitor 2K/QHD
   - `Laptop (1366x768)` untuk laptop kerja standar
   - `Tablet (768x1024)` untuk simulasi iPad portrait
   - `Mobile (390x844)` untuk iPhone 14 portrait
   - `Mobile kecil (375x667)` untuk iPhone SE generasi lama
   - `Custom` untuk memasukkan width dan height manual

4. Kalau Anda pilih `Custom`, dua input akan muncul: lebar (px) dan tinggi (px). Cocok kalau target device spesifik yang tidak ada di preset (misalnya Galaxy Fold 280x653 saat tertutup).

5. Toggle **Full-page screenshot** (default ON). Kalau aktif, tool akan auto-scroll sampai dasar halaman, lalu capture seluruhnya. Hasilnya mungkin gambar yang sangat panjang, cocok buat dokumentasi landing page marketing. Kalau Anda cuma butuh "yang terlihat pertama kali" (above-the-fold), matikan toggle ini.

6. Toggle **Dark mode** (default OFF). Kalau aktif, tool akan set `color_scheme: dark` di browser context dan `page.emulate_media(color_scheme="dark")`. Situs yang support `prefers-color-scheme` akan otomatis switch ke tema gelap. Situs yang tidak support tetap tampak normal.

7. Pilih strategi **Wait until**:
   - `networkidle` (default): menunggu sampai tidak ada request network selama 500ms. Paling lengkap, agak lambat.
   - `load`: menunggu event `load` di window. Cepat, tapi kadang elemen async belum muncul.
   - `domcontentloaded`: paling cepat, cuma menunggu DOM siap. Cocok untuk halaman simple.

8. Atur **Timeout (ms)** kalau perlu. Default 30000 (30 detik). Naikkan kalau target lambat (situs di balik WAF, hosting sharehost murah). Turunkan kalau Anda batch-capture banyak URL.

9. Klik tombol `Capture`. Backend akan spawn Chromium instance, navigasi, dan ambil screenshot. Biasanya selesai dalam 3-10 detik untuk halaman normal.

10. Hasil muncul di area bawah:
    - Preview gambar besar dengan border
    - Stats grid: dimensi, ukuran file, viewport yang dipakai, dark mode on/off, final URL, judul halaman, status HTTP
    - Tombol **Download** untuk simpan PNG ke disk lokal
    - Tombol **Capture lagi** untuk re-run dengan setting yang sama (berguna kalau konten situs dinamis dan Anda mau compare dua snapshot)

## Contoh kasus pakai

- **Dokumentasi produk SaaS tim internal** - Tim product Anda release feature baru setiap minggu. Alih-alih minta designer ambil screenshot manual tiap update, jadwalkan scan rutin via Scheduled Jobs: capture dashboard setiap kali ada release, simpan ke folder per-tanggal, attach ke changelog docs.

- **Visual regression testing** - Anda punya 20 landing page produk. Setelah deploy perubahan CSS global, capture semua 20 halaman sebelum dan sesudah. Pakai Diff Detection untuk membandingkan dua snapshot. Kalau ada perubahan tak terduga di halaman yang seharusnya tidak terpengaruh, langsung ketahuan.

- **Portfolio showcase untuk agency** - Anda freelancer web developer yang pernah bikin 30+ situs. Capture homepage semuanya di viewport desktop + mobile, jadikan gallery di portfolio Anda. Kalau klien minta "contoh kerja Anda untuk e-commerce", tinggal filter dan share.

- **Riset UX kompetitor** - Mau pitch redesign situs klien. Capture 10 kompetitor di industri yang sama, di viewport mobile dan desktop. Paste ke slide deck, buat side-by-side comparison dengan situs klien saat ini, bangun argumentasi data-driven untuk budget redesign.

- **Arsip historis situs** - Ada situs favorit yang Anda khawatir akan shutdown atau redesign. Capture full-page setiap bulan, simpan sebagai dokumentasi pribadi. Kalau suatu saat situs benar-benar hilang, Anda masih punya visual record.

- **Bukti visual ke klien untuk bug report** - Klien bilang "situs saya di mobile tampak aneh". Capture langsung dengan viewport `Mobile (390x844)`, tempel ke reply email atau ticket. Zero setup, bukti langsung siap.

- **Content untuk blog post atau social media** - Nulis artikel "10 situs desain terbaik 2026". Capture full-page setiap situs di viewport desktop, upload gambar ke artikel. Lebih profesional dari screenshot manual yang ada tab browser-nya kelihatan.

- **Audit aksesibilitas visual dasar** - Capture situs klien di dark mode. Kalau ternyata tampak rusak (kontras jelek, icon hilang), itu signal buat rekomendasi perbaikan theme support ke klien.

## Opsi viewport lengkap

| Preset | Width x Height | Simulasi device |
|--------|----------------|-----------------|
| `desktop` | 1920x1080 | Monitor desktop Full HD standar |
| `desktop_hd` | 2560x1440 | Monitor 2K/QHD |
| `laptop` | 1366x768 | Laptop kerja standar (masih paling umum) |
| `tablet` | 768x1024 | iPad portrait generasi klasik |
| `mobile` | 390x844 | iPhone 14 portrait |
| `mobile_sm` | 375x667 | iPhone SE (device kecil) |
| `custom` | user-defined | Viewport bebas sesuai kebutuhan |

Tool tidak menyertakan preset untuk setiap device di dunia. Kalau Anda butuh ukuran spesifik (Galaxy S24 Ultra 412x915, Pixel 8 Pro 448x992, iPad Pro 12.9" 1024x1366), pakai mode `custom` dan masukkan dimensi persis dari spesifikasi device.

## Cara kerja internal (teknis)

Buat yang penasaran dengan flow di balik layar:

1. **Spawn Chromium instance.** Tool membuka headless Chromium lewat Playwright async API. Setiap capture memulai browser baru (bukan share singleton seperti PlaywrightRenderer), supaya setting viewport dan color scheme bersih tanpa kontaminasi dari request sebelumnya.

2. **Apply User-Agent rotation.** Tool pakai profile UA dari `UARotator` sesuai mode yang diset di Settings (`random`, `round_robin`, atau profile spesifik). UA di-pass ke context browser lewat `new_context(user_agent=...)`, bukan cuma header layer, jadi `navigator.userAgent` di JS target juga ikut konsisten.

3. **Set viewport.** Viewport di-pass ke `new_context(viewport={width, height})`. Playwright akan resize window dan emulate device pixel ratio default.

4. **Apply color scheme.** Kalau dark mode aktif, tool set `color_scheme="dark"` di context dan juga panggil `page.emulate_media(color_scheme="dark")` untuk memastikan CSS media query match.

5. **Navigate.** `page.goto(url, wait_until=..., timeout=...)` dengan strategi wait sesuai pilihan user.

6. **Capture.** `page.screenshot(path=..., full_page=True|False, type="png")`. Kalau full_page, Playwright auto-scroll dan stitch hasil jadi satu PNG panjang.

7. **Extract metadata.** Ambil `page.title()`, `page.url` (final URL setelah redirect), dan status HTTP dari response object.

8. **Parse PNG dimensions.** Tool baca header PNG file langsung (signature 8 byte + IHDR chunk) untuk dapat width/height actual, tanpa dep library image tambahan.

9. **Persist Job row.** Hasil capture di-log ke database sebagai Job dengan type `screenshot`, stats berisi file size, dimensions, dan HTTP status. File PNG tersimpan di `data/screenshots/screenshot_<job_id>.png`.

10. **Cleanup.** Context dan browser di-close dalam finally block, supaya tidak ada zombie process.

> [!IMPORTANT]
> Folder `data/screenshots/` sudah masuk `.gitignore` sehingga file hasil capture tidak ikut ter-commit ke repository. Cocok untuk tool pribadi offline.

## Pengaturan

Tool ini punya beberapa parameter yang bisa diatur per-capture:

### viewport
Key preset atau string `"custom"`. Default: `"desktop"`. Rekomendasi: pakai preset yang ada kalau cocok, hindari custom untuk hasil yang konsisten antar run.

### custom_width / custom_height
Integer (px), hanya berlaku saat viewport = `"custom"`. Rekomendasi: ambil dari [Material design breakpoints](https://m3.material.io/foundations/layout/applying-layout/window-size-classes) atau spek device resmi vendor, jangan asal angka.

### full_page
Boolean. Default: true. Rekomendasi: ON untuk dokumentasi lengkap landing page, OFF kalau cuma butuh hero section atau ingin file size kecil.

### dark_mode
Boolean. Default: false. Rekomendasi: ON kalau target situs advertise support dark theme dan Anda mau validasi implementasinya.

### wait_until
String enum: `"load"` | `"domcontentloaded"` | `"networkidle"`. Default: `"networkidle"`. Rekomendasi: `networkidle` untuk kualitas maksimum, `load` kalau Anda batch-capture dan butuh speed, `domcontentloaded` hanya untuk situs statis sederhana.

### timeout_ms
Integer (milliseconds). Default: 30000 (30 detik). Rekomendasi: naikkan ke 60000 untuk situs di balik CDN lambat atau WAF aggressive, turunkan ke 15000 kalau Anda batch-capture banyak URL dan bersedia situs lambat di-skip.

## Tips kualitas

Beberapa praktik yang meningkatkan kualitas hasil capture:

- **Scroll animations bisa merusak full-page.** Beberapa situs pakai scroll-triggered animation yang hanya play saat user scroll. Dengan full-page mode, Playwright scroll cepat ke bawah, animasi mungkin masih mid-play saat screenshot diambil. Matikan full-page untuk situs seperti ini, atau pakai wait strategy `networkidle` + timeout lebih panjang.

- **Cookie consent banner sering masuk frame.** Situs Eropa atau situs yang comply GDPR biasanya tampilkan popup cookie di load pertama. Hasil capture akan ada banner besar menutupi konten. Workaround: buat capture kedua setelah manual accept di browser biasa, atau combine dengan Auth Vault untuk inject cookie `cookies_accepted=true` sebelum capture.

- **Chat widget floating** (Intercom, Drift, Crisp) sering muncul di sudut kanan bawah setelah beberapa detik. Kalau mengganggu, turunkan timeout atau pakai `domcontentloaded` supaya capture terjadi sebelum widget sempat load.

- **Situs yang pakai Cloudflare Turnstile** atau CAPTCHA challenge bakal tampil challenge page saat browser headless terdeteksi. Hasilnya screenshot CAPTCHA, bukan situs. Workaround: pakai proxy residential, UA yang realistis, atau gabungkan dengan CAPTCHA Solver module.

- **Font rendering beda antar OS.** Hasil capture di Windows (Chromium Windows) tampak sedikit beda dari capture di Linux (Chromium Linux) karena font fallback. Kalau konsistensi visual penting untuk regression testing, selalu jalankan dari OS yang sama.

- **Viewport height kecil di full-page mode tetap tampak penuh.** Viewport height cuma menentukan "apa yang terlihat pertama kali" (fold). Dengan full_page true, tool akan scroll sampai dasar terlepas dari height viewport. Jadi height 600 dan 1200 menghasilkan gambar panjang yang sama saat full_page aktif, beda hanya pada mode non-full-page.

## Troubleshooting

### Problem: "Playwright not installed"
**Gejala:** HTTP 503 dengan pesan berisi `pip install playwright && playwright install chromium`. 
**Penyebab:** Module Python `playwright` belum ter-install, atau binary Chromium-nya belum di-download. 
**Solusi:** Jalankan dua perintah tersebut di terminal backend Anda (di venv yang sama dengan backend PyScrapr). Setelah selesai, reload backend dan coba capture lagi.

### Problem: Timeout saat navigate
**Gejala:** Error berisi "Timeout 30000ms exceeded" atau "net::ERR_TIMED_OUT". 
**Penyebab:** Situs target lambat, atau wait strategy `networkidle` tidak pernah tercapai karena ada long-polling / WebSocket / analytics heartbeat. 
**Solusi:** Naikkan `timeout_ms` ke 60000-90000, atau ganti wait strategy ke `load` atau `domcontentloaded`.

### Problem: Hasil screenshot blank putih
**Gejala:** PNG ter-save tapi isinya cuma background kosong. 
**Penyebab:** Situs butuh JavaScript yang belum selesai render saat capture diambil, atau target adalah SPA yang error loading initial data. 
**Solusi:** Pakai wait strategy `networkidle`, naikkan timeout. Kalau masih blank, cek console error manual via browser biasa, mungkin target butuh cookie otentikasi.

### Problem: File sangat besar (>10 MB)
**Gejala:** Hasil full-page PNG mencapai puluhan MB. 
**Penyebab:** Normal untuk full-page situs panjang dengan banyak gambar high-res. PNG lossless. 
**Solusi:** Matikan full_page kalau cukup above-the-fold. Atau post-process lewat compressor eksternal (TinyPNG, ImageOptim) setelah download.

### Problem: Halaman berbahasa Indonesia tapi capture dapat versi English
**Gejala:** Target biasanya serve bahasa Indonesia ke browser normal, tapi capture dapat versi default English. 
**Penyebab:** UA rotation mungkin pilih profile dengan `Accept-Language: en-US`, situs langsung serve English. 
**Solusi:** Tidak ada direct override di tool saat ini. Roadmap: dukung override header Accept-Language per-capture.

### Problem: Dark mode tidak berefek
**Gejala:** Toggle dark mode aktif, tapi hasil capture tetap tema light. 
**Penyebab:** Situs target tidak support `prefers-color-scheme` media query. Tema gelap mereka di-kontrol lewat toggle manual di UI. 
**Solusi:** Tidak ada. Dark mode tool ini hanya mensimulasikan OS-level preference. Kalau target butuh klik toggle, pakai module lain yang support browser interaction scripting.

### Problem: Viewport mobile menampilkan versi desktop
**Gejala:** Capture di viewport 390x844 tapi tampilan masih desktop layout. 
**Penyebab:** Situs tidak pakai `@media (max-width: ...)` CSS query. Mereka deteksi mobile lewat UA sniffing. 
**Solusi:** Settings > UA Rotation, pilih profile `chrome_mobile` (kalau tersedia) atau workaround: matikan UA rotation, biarkan default Playwright Chromium (`HeadlessChrome`).

## Keamanan / etika

Screenshot Generator terlihat innocent, tapi tetap ada aturan main:

> [!WARNING]
> Setiap capture = 1 kunjungan HTTP ke server target. Server mereka melihat IP, UA, dan path yang diakses. Capture dianggap sebagai bot visit oleh banyak analytics service.

- **Jangan batch-capture situs orang lain secara agresif.** Puluhan capture per menit ke domain yang sama bisa masuk kategori abuse/scraping. Kalau Anda monitor kompetitor, beri jeda minimal 5-10 menit antar capture, atau batasi ke 1x per jam.

- **Respect robots.txt untuk bot visit.** Walaupun tool ini sendiri tidak parse robots.txt (karena capture bukan crawling), prinsipnya: kalau robots.txt disallow user-agent crawler, screenshot rutin bisa dianggap violation spirit of robots.txt.

- **Jangan capture halaman login/dashboard orang lain.** Walaupun Anda punya cookie sesi (dari Auth Vault misalnya), capture UI private service dan share-kan ke publik bisa melanggar ToS.

- **Hormati copyright UI.** Capture landing page kompetitor untuk riset internal = fair use. Capture UI mereka, crop bagian logo + tagline, publish di artikel "top 10 worst landing pages" = mungkin masalah copyright atau defamation. Gunakan dengan bijak.

- **Simpan hasil dengan sensitivity yang sesuai.** Screenshot dashboard admin internal company (walau akses Anda legitimate) berisi data sensitif. Jangan upload ke cloud storage publik, jangan attach ke ticket support publik.

- **Browser fingerprint-nya jelas bot.** Playwright headless tanpa extra stealth setup akan terdeteksi sebagai bot oleh fingerprinting service (Cloudflare Bot Management, PerimeterX). Kalau target di balik layanan seperti itu, hasil capture mungkin bukan situs asli tapi challenge page. Itu expected behavior.

## Related docs

- [Playwright Rendering](/docs/advanced/playwright.md) - detail mode headless browser yang sama dipakai tool ini
- [UA Rotation](/docs/advanced/ua-rotation.md) - profile browser yang di-apply saat screenshot
- [Proxy Rotation](/docs/advanced/proxy.md) - kalau target geo-block atau IP Anda kena rate-limit
- [Diff Detection](/docs/system/diff.md) - bandingkan dua snapshot untuk deteksi perubahan visual
- [Scheduled Jobs](/docs/system/scheduled.md) - jadwalkan capture rutin untuk monitoring
- [History & Export](../system/history.md) - review hasil capture lama
- [Auth Vault](/docs/utilities/vault.md) - inject cookie/session sebelum capture area private
- [Site Ripper](/docs/tools/site-ripper.md) - kalau Anda butuh konten HTML lengkap selain gambar
