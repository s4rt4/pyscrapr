# Tech Stack Detector

> Tool fingerprinting website yang membongkar teknologi di balik sebuah situs: CMS, framework backend, JS library, web server, analytics, CDN, font service, dan ratusan kategori lain, semua dalam satu klik tanpa perlu buka DevTools dan tebak-tebak manual.

## Apa itu Tech Stack Detector

Tech Stack Detector adalah modul PyScrapr yang berfungsi menebak "tumpukan teknologi" (tech stack) dari sebuah situs web hanya dengan satu URL sebagai input. Anda tempel alamat halaman, tool akan melakukan satu request HTTP ringan ke server target, mem-parsing response lengkap (HTML body, response headers, cookies, meta tag, referensi script, inline JS snippet, URL path, dan elemen lain yang relevan), kemudian mencocokkan semua petunjuk tersebut terhadap ribuan pola fingerprint yang sudah dikurasi. Hasilnya adalah laporan terstruktur: situs X pakai WordPress 6.4 di atas PHP 8.1 dengan Nginx 1.24, theme Astra, plugin Yoast SEO, analytics Google Analytics 4, hosted di belakang Cloudflare, dengan font dari Google Fonts dan icon dari Font Awesome 6.

Modul ini dibangun di atas fingerprint library **Wappalyzer** (spesifiknya fork komunitas [enthec/webappanalyzer](https://github.com/enthec/webappanalyzer) yang lisensinya MIT), karena versi upstream Wappalyzer resmi sudah berubah jadi closed-source sejak 2023. Fork ini masih aktif di-maintain komunitas dan kompatibel 100% dengan format JSON rule Wappalyzer klasik. Per versi yang di-bundle di PyScrapr, database berisi kurang lebih **7500+ fingerprint teknologi** yang dikelompokkan ke dalam **100+ kategori**, mulai dari CMS mainstream hingga library niche yang hanya dipakai segelintir developer.

> [!NOTE]
> Tech Stack Detector tidak butuh koneksi ke server Wappalyzer pihak ketiga. Semua rule sudah di-bundle sebagai file JSON lokal di `backend/app/data/wappalyzer/`, jadi deteksi sepenuhnya offline setelah satu kali fetch situs target.

Filosofinya sederhana: daripada buka DevTools, inspect elements, cek response header satu per satu, lihat meta generator tag, grep comment HTML, Tech Stack Detector melakukan semua itu otomatis dalam hitungan detik. Buat riset kompetitor, audit klien, investigasi security, atau sekadar keingintahuan "ini situs dibikin pakai apa sih?", tool ini memangkas proses 10-15 menit manual jadi satu request.

## Cara pakai (step-by-step)

1. Buka PyScrapr di browser, lalu navigasi ke menu **Tech Detector** di sidebar kiri, atau pakai shortcut keyboard `Ctrl+6` untuk langsung lompat ke halaman tool. Halaman akan menampilkan form input minimalis di atas, dan area hasil kosong di bawah.

2. Di field `Target URL`, paste alamat lengkap situs yang ingin dianalisis. Contoh valid: `https://www.detik.com`, `https://wordpress.org`, `https://shopify.com`. Skema `https://` atau `http://` wajib ada, karena tool tidak auto-prepend protokol.

3. Opsional, aktifkan toggle **Render dengan Playwright** jika Anda yakin target adalah SPA (Single Page Application) yang meng-render konten via JavaScript di sisi client. Contoh situs seperti ini: dashboard React tanpa SSR, situs Vue kosong yang baru hidup setelah JS dijalankan. Kalau toggle ini diaktifkan, tool akan membuka halaman via headless Chromium, menunggu network idle, baru parse hasil akhirnya.

> [!TIP]
> Playwright mode butuh browser binary ter-install. Kalau belum pernah dipakai, jalankan `playwright install chromium` sekali di terminal backend. Mode ini 5-10x lebih lambat dari mode HTTP biasa, jadi jangan aktifkan kalau tidak benar-benar perlu.

4. Atur `Timeout` kalau Anda perlu toleransi lebih untuk situs lambat. Default 20 detik cukup untuk 95% kasus, tapi situs di balik WAF atau hosting lambat kadang butuh 30-40 detik.

5. Klik tombol `Scan` (biru besar di pojok kanan form). Backend akan membuat job, fetch situs target sekali, dan mulai matching rule. Biasanya selesai dalam 2-5 detik untuk mode HTTP biasa.

6. Hasil muncul di area bawah, dikelompokkan per kategori (CMS, Web Server, JS Framework, Analytics, dst). Setiap teknologi ditampilkan sebagai card dengan:
   - Logo/icon teknologi (kalau tersedia di bundle)
   - Nama teknologi
   - Badge versi (kalau berhasil ter-ekstrak, misalnya `6.4.2`)
   - Confidence bar (0-100%) yang menunjukkan seberapa yakin tool terhadap deteksi
   - Link ke website resmi teknologi untuk referensi

7. Hasil otomatis tersimpan di History, jadi Anda bisa review scan lama, bandingkan dua run untuk deteksi perubahan stack, atau export ke JSON untuk dokumentasi.

## Contoh kasus pakai

- **Riset kompetitor bisnis online** - Anda mau bikin toko online pesaing langsung toko X. Scan situs mereka untuk tahu: pakai Shopify atau WooCommerce? Plugin review apa yang dipakai? Chatbot mana? Analytics-nya Google Analytics atau sudah migrasi ke Plausible? Info ini menentukan budget dan strategi Anda.

- **Audit cepat teknologi calon klien freelance** - Klien prospek minta kuotasi bikin ulang situs mereka. Scan dulu situs existing untuk tahu CMS, framework, versi PHP/Node, ekosistem plugin. Dari situ Anda bisa estimasi kompleksitas migrasi dan siapkan proposal yang akurat, bukan pakai tebak-tebak.

- **Investigasi keamanan (defensive)** - Seorang teman bilang situs komunitasnya suka lemot dan kadang hang. Scan situsnya: ternyata pakai Joomla 3.9 (EOL sejak 2023). Dari situ Anda tahu persis security advisory yang applicable, bisa langsung cek CVE database, dan rekomendasi update urgent ke versi 4.x atau migrasi ke CMS lain.

- **Monitoring migrasi stack kompetitor** - Anda jalankan scan bulanan terhadap 10 situs kompetitor via Scheduler. Suatu hari notif datang: situs X tiba-tiba pindah dari WordPress ke Next.js + Contentful. Ini signal penting, mereka serius invest di performance dan DX, Anda bisa evaluasi apakah perlu respons strategis.

- **Dokumentasi portfolio untuk agency** - Anda punya 30+ situs klien yang pernah dibangun. Scan semuanya, export ke JSON, simpan sebagai bagian dari case study database. Info stack berguna saat klien baru tanya "tim Anda pernah handle situs dengan tech Y?".

- **Belajar dari situs favorit** - Ingin tahu bagaimana perusahaan Z yang blognya cepat banget itu set up stack-nya? Scan. Ternyata pakai Astro + Cloudflare Pages + ImageKit CDN. Dari situ Anda bisa coba replicate pattern yang sama untuk side project pribadi.

- **Filter proposal tender** - Saat dapat brief RFP untuk maintenance situs pemerintah, scan dulu situsnya. Kalau ketahuan pakai Drupal 7 (EOL), scope maintenance beda jauh dengan kalau masih Drupal 10. Hindari proposal yang under-scope.

## Apa yang dideteksi

Tech Stack Detector punya cakupan sangat luas. Berikut kategori utama beserta contoh teknologi yang masuk dalam setiap kategori:

| Kategori | Contoh teknologi |
|----------|------------------|
| **CMS** | WordPress, Drupal, Joomla, Ghost, Shopify, Magento, PrestaShop, OpenCart, Blogger, Wix, Squarespace, Webflow, Craft CMS, Strapi, Directus |
| **Web Framework (backend)** | Laravel, Symfony, CodeIgniter, CakePHP, Django, Flask, FastAPI, Rails, Express, NestJS, Spring, ASP.NET, Phoenix, Gin, Echo |
| **JS Framework (frontend)** | React, Next.js, Vue, Nuxt, Angular, Svelte, SvelteKit, Ember, Alpine.js, Stimulus, Remix, Astro, SolidJS, Qwik |
| **JS Library** | jQuery, Lodash, Underscore, Bootstrap, Tailwind CSS, Bulma, Moment.js, Day.js, D3.js, Chart.js, Three.js |
| **Web Server** | Nginx, Apache, LiteSpeed, Caddy, IIS, OpenResty, Tomcat, Jetty, Cloudflare (sebagai reverse proxy), Cloudflare Workers |
| **Bahasa pemrograman** | PHP, Python, Ruby, Node.js, Go, Java, C#, Elixir, Rust (via header, meta, atau URL signature) |
| **Database hint** | MySQL, PostgreSQL, MongoDB, Redis (via cookie names, debug headers, atau error page indicator) |
| **Analytics** | Google Analytics 4, Universal Analytics, Matomo, Plausible, Fathom, Mixpanel, Heap, Amplitude, Clicky |
| **Tag Manager** | Google Tag Manager, Tealium, Segment, Adobe Launch, Piwik PRO Tag Manager |
| **CDN** | Cloudflare, Fastly, Akamai, BunnyCDN, AWS CloudFront, KeyCDN, StackPath, jsDelivr, unpkg |
| **Ad Network** | Google AdSense, Google Ad Manager, Adsterra, Media.net, Taboola, Outbrain, Criteo |
| **Font Service** | Google Fonts, Adobe Fonts (Typekit), Font Awesome, Icomoon, Bunny Fonts |
| **Marketing Automation** | HubSpot, Mailchimp, ActiveCampaign, Klaviyo, Intercom, Drift |
| **Payment Gateway** | Stripe, PayPal, Midtrans, Xendit, Doku, Razorpay, Square |
| **Chat / Support** | Intercom, Zendesk, Crisp, LiveChat, Tawk.to, Drift |
| **E-commerce Platform** | Shopify, WooCommerce, BigCommerce, Magento, PrestaShop, Sylius, Saleor |
| **Page Builder** | Elementor, Divi, WPBakery, Beaver Builder, Brizy (khusus WordPress) |

Total cakupan lebih dari 100 kategori. Beberapa yang lebih niche: A/B testing tool (Optimizely, VWO), accessibility overlay, CAPTCHA (reCAPTCHA, hCaptcha, Turnstile), progressive web app framework, static site generator, feature flag service, error tracking (Sentry, Rollbar), session replay (Hotjar, FullStory), dan banyak lagi.

## Cara kerja internal (teknis)

Buat yang penasaran bagaimana keajaibannya terjadi, berikut flow di balik layar:

1. **Fetch sekali, parse banyak kali.** Tool melakukan satu GET request ke URL target via `http_factory` internal PyScrapr (yang otomatis pakai UA rotation + proxy kalau di-konfigurasi di Settings). Response body, status code, headers, dan cookies semuanya di-cache in-memory.

2. **Rule matching.** Setiap rule Wappalyzer berbentuk JSON object berisi pattern untuk berbagai "surface area":
   - `headers`: regex terhadap response header (misal `X-Powered-By: PHP/8.1`)
   - `cookies`: regex terhadap nama cookie (misal `wordpress_logged_in_*`)
   - `html`: regex terhadap full HTML body (misal `<meta name="generator" content="WordPress`)
   - `meta`: regex terhadap meta tag spesifik
   - `scriptSrc`: regex terhadap atribut `src` di tag `<script>`
   - `scripts`: regex terhadap isi inline `<script>`
   - `url`: regex terhadap URL itu sendiri

3. **Version extraction.** Banyak rule punya suffix `\;version:\1` di regex. Artinya: capture group pertama di regex di-extract sebagai string versi. Contoh: regex `jquery[-\.](\d+\.\d+\.\d+)\;version:\1` terhadap URL `jquery-3.6.0.min.js` akan menghasilkan versi `3.6.0`.

4. **Confidence scoring.** Default confidence per match adalah 100. Kalau rule kasih suffix `\;confidence:50`, itu artinya match ini cuma "lumayan yakin". Confidence dari multiple pattern yang sama-sama match untuk satu teknologi akan di-accumulate (dengan cap 100). Teknologi dengan confidence rendah (<50) biasanya false-positive, di UI ditandai dengan warna kuning/oranye.

5. **Implies chain.** Banyak teknologi implicit menunjukkan keberadaan teknologi lain. WordPress `implies` PHP dan MySQL. Next.js `implies` React. Saat WordPress ter-detect, PHP dan MySQL otomatis ditambahkan ke hasil (dengan confidence inherit).

6. **Requires chain.** Sebaliknya, beberapa teknologi cuma valid kalau teknologi prasyaratnya sudah match dulu. Misal plugin WordPress X `requires` WordPress - kalau WordPress tidak ter-detect, plugin X juga di-drop.

7. **Excludes chain.** Kalau X `excludes` Y dan X match, Y langsung di-drop meskipun Y juga punya evidence. Ini mencegah konflik antara dua teknologi yang mutually exclusive.

> [!IMPORTANT]
> Beberapa field fingerprint Wappalyzer upstream tidak didukung di versi PyScrapr saat ini (masuk roadmap deferred):
> - `dom`: butuh DOM tree yang sudah di-parse browser (hanya tersedia saat Playwright mode)
> - `js`: butuh eksekusi JavaScript dan inspeksi `window` object
> - `dns`: butuh DNS lookup terpisah
> - `certIssuer`: butuh inspeksi TLS certificate chain
> - `css`: butuh fetch dan parse external stylesheet
>
> Ini artinya ~10-15% rule tidak sepenuhnya exercised. Kalau Anda butuh deteksi yang mengandalkan field di atas, tunggu update atau buka issue.

## Pengaturan

Tool ini sengaja dirancang minimal dari sisi konfigurasi, karena 90% use case cuma butuh "scan URL ini". Opsi yang tersedia:

### timeout
Batas waktu maksimum (detik) tool menunggu response dari server target. Default: 20. Rekomendasi: naikkan ke 40-60 untuk situs di belakang WAF atau hosting lambat. Turunkan ke 10 kalau Anda batch-scan banyak URL dan toleran situs tertentu gagal.

### render_with_playwright
Boolean untuk aktifkan mode browser rendering. Default: false. Rekomendasi: aktifkan hanya kalau mode HTTP biasa return hasil kosong pada situs yang jelas pakai teknologi modern. Perhatikan, butuh `playwright install chromium` sekali. Mode ini 5-10x lebih lambat.

### user_agent_rotation
Boolean global dari Settings. Default: mengikuti Settings. Rekomendasi: biarkan ON. Beberapa situs serve konten berbeda untuk bot vs browser, UA Chrome modern lebih mungkin dapat konten lengkap.

### proxy_rotation
Boolean global dari Settings. Default: mengikuti Settings. Rekomendasi: aktifkan kalau Anda sering scan dari IP yang sudah pernah ter-rate-limit, atau target geo-block IP Anda.

### nocache
Boolean untuk append query param `?_nocache=<timestamp>` ke URL. Default: false. Rekomendasi: aktifkan saat target di balik Cloudflare dan Anda curiga hasil scan di-cache versi lama.

### include_low_confidence
Boolean apakah hasil dengan confidence <50 ditampilkan. Default: false. Rekomendasi: aktifkan saat Anda riset mendalam dan mau lihat "kandidat lemah" juga, matikan untuk laporan eksekutif yang cuma mau yang yakin.

## Tips akurasi

Beberapa praktik yang meningkatkan kualitas deteksi:

- **Scan homepage biasanya cukup**, tapi tidak selalu. Landing page korporat kadang cuma HTML statis pemasaran, sementara stack utama baru kelihatan di halaman lain. Strategi aman: scan `/`, lalu `/blog` atau `/articles`, dan `/contact` atau `/login`. Gabungkan hasil.

- **Situs di belakang Cloudflare** mungkin nge-cache response dengan agresif. Kalau Anda melihat teknologi terlihat "aneh" atau tidak berubah meskipun target sudah update, aktifkan toggle `nocache` atau append `?_nocache=1` manual di URL.

- **WAF bisa bikin hasil kacau.** Kalau tool return status 403 atau 503 dengan confidence rendah di semua kategori, kemungkinan besar Anda kena Web Application Firewall challenge page, bukan situs asli. Coba aktifkan proxy rotation + UA rotation, atau pakai Playwright mode.

- **Situs SPA pure (React/Vue tanpa SSR)** sudah pasti butuh Playwright. Kalau Anda buka `View Source` dan cuma lihat `<div id="root"></div>` plus bundle JS, wajib toggle `Render dengan Playwright`. Mode HTTP biasa tidak akan ter-detect teknologi apa-apa di situs seperti ini.

- **Situs dengan load balancer berbeda-beda** bisa return stack yang sedikit beda per request (misal header `X-Served-By` berubah). Scan 2-3 kali dan ambil union-nya kalau Anda butuh gambaran lengkap.

- **Pakai History diff** untuk monitoring perubahan stack dari waktu ke waktu. Scan situs yang sama minggu ini vs bulan lalu, bandingkan di History view, cari diff.

## Troubleshooting

### Problem: Tidak ada teknologi terdeteksi
**Gejala:** Job selesai dengan hasil kosong atau cuma 1-2 teknologi generic. 
**Penyebab:** Situs SPA yang render di client, atau response utama adalah HTML skeleton tanpa petunjuk apa-apa. 
**Solusi:** Aktifkan toggle `Render dengan Playwright`, scan ulang. Kalau masih kosong, cek manual via View Source, mungkin target memang sengaja obfuscate semua signature.

### Problem: Status 0 atau timeout
**Gejala:** Error "Connection timeout" atau status code 0 di log. 
**Penyebab:** Situs block scraping per-IP, firewall block koneksi, atau server target down. 
**Solusi:** Aktifkan proxy rotation di Settings, naikkan timeout ke 40 detik, coba scan ulang setelah 5-10 menit. Kalau masih gagal, verify manual apakah situs accessible dari browser Anda.

### Problem: Versi tidak terdeteksi
**Gejala:** Teknologi ter-detect tapi kolom versi kosong. 
**Penyebab:** Tidak semua rule Wappalyzer punya regex dengan capture group versi. Banyak teknologi di-detect via indicator yang tidak mengekspos versi (misal class CSS unik). 
**Solusi:** Normal, tidak ada yang perlu diperbaiki. Kalau Anda butuh versi exact, cek manual via header (`X-Generator`, `X-Powered-By`) atau inspect bundle JS.

### Problem: "Python module wappalyzer not found"
**Gejala:** Error startup atau error saat scan pertama. 
**Penyebab:** Anda mungkin pernah baca tutorial Wappalyzer Python dan coba `pip install wappalyzer`, tapi PyScrapr tidak pakai library itu. 
**Solusi:** Rule berada sebagai file JSON di `backend/app/data/wappalyzer/`. Tidak butuh dep library tambahan. Pastikan folder tersebut ada dan berisi file `technologies/*.json`. Kalau folder kosong, re-clone repo atau restore dari git.

### Problem: Banyak false positive jQuery
**Gejala:** jQuery selalu muncul dengan confidence 100 meskipun Anda yakin situs modern tidak pakai jQuery. 
**Penyebab:** Wajar. Banyak script pihak ketiga (ads network, chat widget, tracking pixel) bundle jQuery sendiri. Dari perspektif fingerprint, jQuery memang ter-load di browser user. 
**Solusi:** Tidak ada. Kalau Anda riset stack aplikasi utama, filter mental saja dependency dari third-party script.

### Problem: Hasil antara HTTP mode dan Playwright mode berbeda jauh
**Gejala:** Mode biasa detect 5 teknologi, Playwright mode detect 15. 
**Penyebab:** Playwright eksekusi JS, jadi semua teknologi yang loaded runtime (analytics async, chat widget lazy-load) ikut ter-detect. 
**Solusi:** Ini expected, bukan bug. Gunakan Playwright mode kalau Anda butuh gambaran lengkap "yang user akhirnya jalankan di browser", gunakan HTTP mode kalau Anda cuma butuh stack inti yang di-serve server.

### Problem: Semua scan return hasil sama persis meski target berbeda
**Gejala:** Tidak peduli URL apa, hasilnya selalu sama. 
**Penyebab:** Proxy Anda mungkin return landing page provider proxy, bukan situs target. 
**Solusi:** Matikan proxy, scan ulang. Kalau hasil berubah, berarti proxy Anda bermasalah. Update proxy list di Settings.

## Keamanan / etika

Tech Stack Detector dirancang minimal footprint, tapi tetap ada aturan main yang layak diperhatikan:

> [!WARNING]
> Scan sebuah situs berarti Anda melakukan request HTTP ke server mereka. Meskipun cuma satu GET, secara legal itu tetap "akses" yang tercatat di log server mereka.

- **Satu GET request per scan.** Tool tidak melakukan brute force path, tidak probe `/admin`, tidak test credential default, tidak enumerate subdomain. Footprint minimal ke server target. Cukup seperti satu visit browser biasa.

- **Respect robots.txt.** Kalau `/wp-admin/` atau path tertentu di-Disallow di robots.txt, tool tidak akan probe path tersebut meskipun ada rule yang butuh hit endpoint tersebut. Kalau Anda matikan respect robots di Settings (tidak direkomendasikan), pertanggungjawaban ada di Anda.

- **Jangan scan situs orang lain tanpa izin dalam kapasitas komersial.** Kalau Anda freelancer yang bikin report stack-scan untuk klien mereka bayar, pastikan target situsnya punya relasi legitimate dengan klien. Scan situs random tanpa otorisasi dalam kapasitas bisnis bisa masuk kategori Terms of Service violation, dan di yurisdiksi tertentu bisa jadi masalah legal.

- **Hasil deteksi tidak 100% akurat.** Confidence 100% bukan berarti teknologi X 100% dipakai. Ada kemungkinan false positive (script pihak ketiga bawa library yang sama), versi yang salah ekstrak (regex tidak sempurna), atau deteksi lama kalau situs baru migrasi. **Untuk keputusan penting, terutama yang menyangkut security (misal "situs ini pakai X versi vulnerable, mari saya laporkan"), selalu validasi manual.** Tool ini assistant, bukan oracle.

- **Simpan hasil dengan sensitivity yang sesuai.** Report stack situs korporat terkadang adalah informasi sensitif kompetitif. Jangan publish ke public GitHub repo, jangan share ke grup WhatsApp terbuka.

## Related docs

- [URL Mapper](url-mapper.md) - untuk discover semua halaman situs sebelum batch-scan tech stack
- [Site Ripper](site-ripper.md) - alternatif kalau Anda butuh konten lengkap, bukan cuma metadata stack
- [Playwright Rendering](/docs/advanced/playwright.md) - detail mode headless browser yang dipakai toggle render
- [Proxy Rotation](/docs/advanced/proxy.md) - setup proxy pool untuk scan situs sensitive atau geo-restricted
- [UA Rotation](/docs/advanced/ua-rotation.md) - profile browser untuk bypass simple bot detection
- [History & Export](../system/history.md) - review hasil scan lama, export JSON, atau re-run
- [Scheduled Jobs](/docs/system/scheduled.md) - jadwalkan scan periodik untuk monitoring perubahan stack kompetitor
- [Diff Detection](/docs/system/diff.md) - bandingkan dua hasil scan untuk detect perubahan stack
