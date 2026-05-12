# Price Watcher

> Price Watcher adalah tool tier P10 di PyScrapr untuk monitor harga produk e-commerce secara periodik. Anda paste URL produk dari Shopee, Tokopedia, Amazon, Bukalapak, atau toko apa saja, tool akan auto-detect harga dari halaman, simpan baseline, lalu cek ulang sesuai interval yang Anda set (15 menit, 1 jam, 6 jam, 12 jam, atau 24 jam). Setiap pengecekan masuk ke time-series database lokal yang langsung di-render jadi grafik trend 30 hari. Kalau harga lewat threshold yang Anda tentukan (di bawah `alert_below` atau di atas `alert_above`), tool kirim notifikasi via webhook Discord/Telegram/HTTP atau email. Cocok untuk personal price hunting (tunggu diskon Black Friday), reseller (track buku Amazon), atau kompetitor pricing analysis (bandingkan beberapa toko untuk produk yang sama).

## Apa itu Price Watcher

Price Watcher menjawab problem klasik shopper online: "kapan harga turun?" dan "apakah diskon ini beneran diskon, atau cuma marketing trick?". Daripada Anda bookmark 20 link produk dan refresh manual tiap hari, Price Watcher otomatisasi proses itu. Tool jalan di background lewat APScheduler, tiap 5 menit cek produk yang sudah due (waktu interval-nya tercapai), fetch halaman, ekstrak harga, simpan ke history, dan trigger alert kalau threshold terpenuhi.

Positioning di sidebar Tools (warna lime, route `/price-watcher`, shortcut `Ctrl+0` setelah P9). Tool ini bekerja independen dari fitur scraping ad-hoc lain: produk yang Anda tambahkan akan tetap dipantau bahkan setelah Anda tutup tab UI, selama backend PyScrapr masih running. Kalau Anda restart aplikasi, scheduler resume dari state terakhir di database.

Beda Price Watcher dengan tool tracking komersial (Keepa, CamelCamelCamel) adalah scope dan kontrol. Tool komersial fokus di satu marketplace (Amazon) dan operate dari server mereka. Price Watcher lokal, mendukung situs apa saja yang punya HTML harga yang bisa di-parse, dan datanya tinggal di mesin Anda. Trade-off: Price Watcher butuh maintenance kecil (kalau situs ubah struktur, selector mungkin perlu adjust manual via Selector Playground).

> [!NOTE]
> Tool ini dirancang untuk personal use offline. Tidak ada upload data ke cloud, tidak ada telemetri. Riwayat harga 30 hari tersimpan di `data/price_watcher.db` di folder instalasi Anda.

## Cara pakai

Buka menu **Price Watcher** di sidebar Tools (ikon tag, warna lime). Halaman terbagi tiga panel: daftar produk yang sedang di-track di kiri, detail produk + chart di kanan, dan form tambah produk di header.

### Langkah 1: Tambah produk

1. Klik tombol **+ Add product** di kanan atas.
2. Paste URL produk di field `Product URL`. Format apa saja diterima (`https://`, dengan atau tanpa `www.`, dengan query string).
3. Klik **Extract preview**. Backend GET halaman, jalankan auto-detector, lalu tampilkan harga yang ditemukan beserta nama produk dan currency. Kalau auto-detect berhasil, Anda tinggal klik **Save**.
4. Kalau auto-detect gagal (tidak ada angka harga muncul, atau angka yang muncul jelas salah seperti nomor SKU), buka tab **Manual selector** dan isi CSS atau XPath selector yang menunjuk ke elemen harga. Lihat section Selector manual di bawah.
5. Pilih `Interval` (15 min, 1 hr, 6 hr, 12 hr, 24 hr). Default 6 jam.
6. (Opsional) Set `Alert below` (notif kalau harga turun di bawah angka ini) atau `Alert above` (notif kalau harga naik di atas angka ini), atau dua-duanya.
7. (Opsional) Atur `Currency` kalau auto-detect salah (IDR / USD / EUR / SGD / MYR).
8. Klik **Save**. Produk masuk ke daftar, scheduler langsung jadwalkan cek pertama.

### Langkah 2: Cek manual (opsional)

Kadang Anda mau cek harga sekarang juga tanpa nunggu interval. Klik produk di daftar, lalu klik tombol **Check now**. Backend fetch halaman, parse, dan tambah satu entry ke history. Hasilnya muncul di chart real-time.

### Langkah 3: Lihat chart

Panel kanan menampilkan LineChart 30 hari history. Sumbu X tanggal, sumbu Y harga. Hover di titik untuk lihat exact value + timestamp pengecekan. Kalau Anda set threshold, garis horizontal muncul di angka threshold (hijau untuk `alert_below`, merah untuk `alert_above`). Anda bisa langsung lihat apakah harga pernah cross threshold.

### Langkah 4: Edit atau hapus

Klik ikon pensil di kanan baris produk untuk edit (ubah interval, threshold, selector). Klik ikon tong sampah untuk hapus, history ikut terhapus.

## Auto-detect harga

Auto-detector adalah pipeline 4 layer yang dijalankan berurutan. Layer pertama yang return angka valid, dipakai. Kalau semua layer gagal, tool return error dan Anda perlu pakai selector manual.

### Layer 1: Open Graph meta

Banyak situs e-commerce embed harga ke meta tag standar.

```html
<meta property="product:price:amount" content="299000">
<meta property="product:price:currency" content="IDR">
<meta property="og:price:amount" content="29.99">
```

Layer ini paling reliable kalau ada, karena situs yang serius soal SEO dan social sharing biasanya isi meta ini benar.

### Layer 2: Schema.org JSON-LD

Markup terstruktur untuk Google Shopping dan rich results.

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "offers": {
    "@type": "Offer",
    "price": "299000",
    "priceCurrency": "IDR"
  }
}
```

Tool parse semua `<script type="application/ld+json">` di halaman, cari struktur `Product` atau `Offer`, ambil field `price`. Mendukung nested offers (varian produk) dengan ambil yang first valid.

### Layer 3: Site-specific selectors

Untuk situs besar yang tidak pakai meta atau JSON-LD secara konsisten, tool punya selector built-in:

| Domain | Selector |
|--------|----------|
| `shopee.co.id`, `shopee.com` | `[class*="pqTWkA"]`, `[class*="product-price"]`, `div.pqTWkA` |
| `tokopedia.com` | `[data-testid="lblPDPDetailProductPrice"]`, `span.price` |
| `bukalapak.com` | `.c-product-price__amount`, `[data-testid="product-price"]` |
| `amazon.com`, `amazon.co.uk`, dst | `span.a-price-whole`, `#priceblock_ourprice`, `.a-price .a-offscreen` |
| `lazada.co.id`, `lazada.com.my` | `span.pdp-price`, `.pdp-product-price` |
| `blibli.com` | `.product-price__final-price`, `[data-testid="product-price"]` |

Selector ini di-update berkala kalau situs ubah class name. Kalau Anda nemu situs major belum di-cover, file issue di GitHub atau tambah selector custom.

### Layer 4: Generic fallback

Selector universal yang sering match di toko kecil:

```
.price, .harga, [class*="price"], [id="price"],
[data-price], span.amount, .product-price
```

Tool ambil text node dari elemen yang match, normalize ke angka (lihat section Currency), return angka pertama yang masuk akal (di antara 100 dan 1 miliar untuk IDR, dst).

> [!TIP]
> Kalau Anda mau test auto-detect tanpa save, klik **Extract preview** saja. Ini gratis (tidak counted ke history) dan berguna untuk validate URL sebelum commit.

## Selector manual

Kalau auto-detect gagal, Anda override dengan selector. Dua format diterima:

- **CSS selector**: prefix `css:` atau tanpa prefix. Contoh: `.product-price .final`.
- **XPath**: prefix `xpath:`. Contoh: `xpath://div[@class='price-final']/span`.

### Cara dapat selector

1. Buka halaman produk di browser.
2. Klik kanan di angka harga, pilih **Inspect**.
3. Di DevTools, klik kanan di elemen yang highlight di Elements tab, pilih **Copy > Copy selector** (CSS) atau **Copy > Copy XPath**.
4. Paste di Price Watcher.

Kadang selector yang Chrome generate panjang dan rapuh (`html > body > div:nth-child(3) > main > ...`). Lebih bagus pakai class atau data attribute yang stabil. Anda bisa pakai **[Selector Playground](/docs/utilities/playground.md)** dulu untuk validate selector pendek yang Anda buat sendiri terhadap angka harga.

### Contoh selector siap pakai

Shopee (kalau auto-detect kebingungan karena lazy load):

```css
div[class*="WL5XU8"] div[class*="pqTWkA"]
```

Tokopedia (versi PDP yang baru):

```css
[data-testid="lblPDPDetailProductPrice"]
```

Amazon (varian Buy Box):

```css
#corePrice_feature_div .a-price-whole
```

Toko kecil custom (cari class yang unique di sekitar angka):

```css
.product-info__price-current
```

> [!WARNING]
> Selector yang terlalu spesifik (full path dari Chrome DevTools) sering rusak setelah situs deploy update kecil. Lebih baik pakai class name atau data attribute, dan kalau perlu, kombinasikan dua selector pendek untuk specificity.

## Schedule + interval

Pilihan interval mempengaruhi tradeoff antara responsiveness alert dan beban ke server target.

| Interval | Cek per hari | Rekomendasi untuk |
|----------|-------------|-------------------|
| 15 min | 96 | Flash sale yang berlangsung beberapa jam (campaign 11.11 / 12.12 / Harbolnas) |
| 1 hr | 24 | Niche items dengan harga volatile (limited stock, gadget pre-order) |
| 6 hr | 4 | Default, cocok untuk mayoritas produk e-commerce massa |
| 12 hr | 2 | Buku, peralatan rumah tangga, harga stabil |
| 24 hr | 1 | Investasi tracking jangka panjang, produk yang jarang diskon |

Backend APScheduler tick tiap 5 menit, scan database `price_products` untuk produk dengan `next_check_at <= now()`. Job di-queue ke worker pool (max 3 concurrent), eksekusi fetch + extract + insert history + update `next_check_at = now() + interval`.

> [!IMPORTANT]
> Jangan agresif. Kalau Anda set 50 produk di Shopee semua interval 15 menit, itu 4800 request per hari ke satu domain. Bisa kena rate limit atau IP block. Konsultasi etika di section paling bawah.

## Threshold alert

Dua field di form tambah/edit produk:

- **Alert below**: kirim notif kalau harga turun di bawah angka ini.
- **Alert above**: kirim notif kalau harga naik di atas angka ini (jarang dipakai, tapi berguna untuk seller yang track kompetitor jangan kemahalan).

Format input: angka tanpa pemisah ribuan (`299000`, bukan `299.000`). Currency mengikuti currency produk.

### Cara setup channel notifikasi

1. Buka **Settings > Notifications**.
2. Konfigurasi salah satu (atau semua):
   - **Webhook URL**: paste URL webhook Discord/Telegram/HTTP. Tool kirim POST JSON dengan field `product_name`, `current_price`, `threshold_type`, `threshold_value`, `url`.
   - **Email SMTP**: setup host, port, user, password, from. Lihat [Email Notifications](/docs/advanced/email.md).
3. Di form produk Price Watcher, centang `Notify via webhook` atau `Notify via email` (bisa dua-duanya).

Format payload webhook contoh (Discord):

```json
{
  "embeds": [{
    "title": "Price drop detected",
    "description": "iPhone 15 Pro 256GB - Tokopedia Official Store",
    "color": 3066993,
    "fields": [
      {"name": "Current price", "value": "Rp 18.499.000", "inline": true},
      {"name": "Threshold (below)", "value": "Rp 19.000.000", "inline": true},
      {"name": "URL", "value": "https://tokopedia.com/..."}
    ]
  }]
}
```

Tool punya logic anti-spam: alert hanya di-trigger sekali per cross threshold. Kalau harga turun di bawah `alert_below` lalu naik lagi lalu turun lagi, alert ke-2 dikirim. Tapi kalau harga tetap di bawah threshold selama 10 cek berturut, hanya 1 alert (yang pertama).

> [!TIP]
> Untuk produk yang Anda mau tracking jangka panjang tanpa notif, biarkan kedua threshold kosong. Tool tetap simpan history, Anda lihat chart manual kapan saja.

## Currency + format harga

Indonesia pakai pemisah titik untuk ribuan dan koma untuk desimal (`1.234.567,50`). Mayoritas situs en-US pakai sebaliknya (`1,234,567.50`). Tool normalize otomatis berdasarkan currency yang di-detect atau di-set manual.

| Currency | Pemisah ribuan | Pemisah desimal | Contoh format |
|----------|---------------|----------------|---------------|
| IDR | `.` | `,` (jarang) | `Rp 1.234.567` |
| USD | `,` | `.` | `$1,234.56` |
| EUR | `.` atau spasi | `,` | `€1.234,56` |
| SGD | `,` | `.` | `S$1,234.56` |
| MYR | `,` | `.` | `RM1,234.56` |

Parser pakai heuristic: kalau angka punya pemisah `.` dan `,`, pemisah terakhir adalah desimal. Kalau cuma satu jenis pemisah dan posisinya 3 digit dari belakang dengan currency IDR/EUR, itu pemisah ribuan. Kalau ada doubt, set currency manual di form.

Output chart selalu pakai format sesuai currency. Tabel history juga.

## Contoh skenario

### 1. Monitor produk gadget Tokopedia untuk diskon Black Friday

Anda incar Sony WH-1000XM5 di Tokopedia Official Store. Harga normal Rp 5.500.000, Anda mau beli kalau turun di bawah Rp 4.500.000 (sale Black Friday biasanya 15-25%).

Setup: paste URL PDP, interval 1 hour (Black Friday window pendek, butuh response cepat), alert_below 4500000, webhook Discord aktif. Anda biarkan jalan dari Oktober. Akhir November notif Discord muncul: harga drop ke Rp 4.299.000. Anda buka link langsung, checkout sebelum stock habis.

### 2. Track harga buku Amazon US untuk reseller

Anda reseller buku Indonesia, sourcing dari Amazon US (titip jasa kirim). Margin tipis, Anda butuh harga sumber stabil dan tahu titik beli optimal. 30 SKU buku rekomendasi customer.

Setup: add 30 produk batch, interval 12 hr (Amazon US tidak terlalu volatile), currency USD, alert_below ditentukan per buku berdasarkan margin breakeven Anda. History 30 hari kasih pattern: buku non-fiksi cenderung sale tiap awal bulan, buku akademik volatile saat semester baru. Anda time inventory purchase di sweet spot.

### 3. Awasi stock + harga Shopee saat campaign 11.11

H-3 sampai H+1 campaign 11.11, situs Shopee biasanya update harga setiap beberapa jam. Anda incar 5 item: powerbank, speaker, charger, kabel HDMI, mouse gaming. Total budget Rp 1.500.000.

Setup: 5 produk, interval 15 min selama window campaign, semua dengan `alert_below` di harga target. Hari-H, Anda dapat 4 notif dalam 12 jam, checkout 4 dari 5 dengan total Rp 1.350.000 (vs estimasi non-campaign Rp 1.800.000). Setelah 12 Nov, edit semua produk turunkan interval ke 24 hr atau hapus.

### 4. Kompetitor pricing analysis

Anda toko online jual sepeda lipat. Ada 4 kompetitor utama jual model serupa. Anda butuh data kapan mereka diskon untuk respons strategis (matching atau beat).

Setup: add 4 URL produk kompetitor (model A), 4 URL untuk model B, dst. Interval 6 hr. Tidak set alert (Anda mau lihat trend, bukan notif spam). Tiap minggu Anda buka chart, compare 4 line dalam satu view (export CSV ke Excel kalau perlu side-by-side). Hasil: kompetitor C cenderung diskon weekend, kompetitor A diskon awal bulan. Anda atur strategi diskon situs sendiri counter-cyclical (diskon pertengahan minggu untuk capture customer yang sudah scan harga mereka).

### 5. Restock detector

Produk yang Anda tunggu sering out of stock di toko langganan. Saat habis, situs sering ganti display: hilang harga dan tombol beli, ganti "Sold out" atau "Out of stock". Saat restock, harga muncul lagi.

Setup: add URL produk, selector manual yang menunjuk ke angka harga. Saat out of stock, extractor return error (atau angka 0). Saat restock, extractor return angka valid, history insert. Tool deteksi transition dari `null` ke valid number, trigger alert dengan label khusus "Restock detected".

> [!NOTE]
> Restock detector adalah pattern manual, bukan fitur dedicated. Anda set `alert_below` ke angka tinggi (di atas harga normal) supaya tiap pengecekan yang return valid number trigger notif. Setelah restock notif, hapus produk atau set ulang threshold normal.

## Tips & best practices

- **Test selector via Extract preview dulu.** Sebelum save, klik preview minimal sekali. Konfirmasi angka yang muncul masuk akal. Hemat waktu debug nanti.

- **Set interval realistis.** 24 jam cukup untuk 80% use case. 15 menit hanya untuk window campaign atau flash sale.

- **Group produk pakai tag.** Field `Tag` opsional di form. Anda bisa filter daftar produk by tag (`shopee-1111`, `book-reseller`, `competitor-watch`).

- **Backup database periodik.** File `data/price_watcher.db` adalah satu-satunya source of truth history. Copy ke external drive tiap bulan kalau Anda tracking long-term.

- **Cek log scheduler kalau alert tidak nongol.** Settings > Logs > Filter `price_watcher`. Cek apakah job execute on schedule.

- **Pisah currency.** Jangan campur 10 produk IDR dengan 5 produk USD di satu view tanpa filter, chart aggregate jadi tidak masuk akal. Pakai tag atau filter currency.

## Troubleshooting

### Problem: Auto-detect return angka aneh (jutaan padahal produk Rp 50.000)

**Gejala:** Preview menunjukkan Rp 2.500.000 padahal halaman jelas Rp 50.000.
**Penyebab:** Selector generic match angka lain (rating count, sold count, SKU), bukan harga.
**Solusi:** Pakai selector manual yang spesifik ke elemen harga. Inspect halaman, copy class name yang Anda yakin.

### Problem: Selector berubah setelah situs update

**Gejala:** Produk yang sebelumnya jalan tiba-tiba history kosong atau error "selector not found".
**Penyebab:** Situs target deploy update, class name berubah.
**Solusi:** Edit produk, klik **Extract preview** dengan selector lama untuk konfirmasi gagal. Lalu inspect halaman versi baru, ambil selector baru. Simpan. History lama tetap, lanjut dari titik ini.

### Problem: Rate limit / 429 dari Shopee atau Tokopedia

**Gejala:** Error "HTTP 429 Too Many Requests" di log scheduler.
**Penyebab:** Anda track terlalu banyak produk dengan interval pendek di satu domain.
**Solusi:** Naikkan interval (dari 15 min ke 1 hr atau 6 hr), atau kurangi jumlah produk per domain. Aktifkan proxy rotation di Settings kalau Anda butuh banyak request.

### Problem: Currency salah parse (harga 299.000 jadi 299)

**Gejala:** Chart menunjukkan harga Rp 299 padahal aslinya Rp 299.000.
**Penyebab:** Parser interpret `.` sebagai pemisah desimal (karena default heuristic atau currency mis-set ke USD).
**Solusi:** Edit produk, set Currency manual ke IDR. Hapus history salah via tombol **Clear history** atau langsung lewat SQL kalau Anda nyaman.

### Problem: Notifikasi tidak terkirim padahal harga sudah cross threshold

**Gejala:** Chart menunjukkan harga turun di bawah `alert_below`, tapi tidak ada notif.
**Penyebab:** Webhook URL invalid, atau alert sudah pernah trigger di cycle sebelumnya dan harga belum kembali di atas threshold.
**Solusi:** Test webhook di Settings > Notifications > Test webhook. Cek log untuk record alert sebelumnya. Reset alert flag manual di database kalau perlu.

### Problem: Scheduler tidak jalan setelah restart aplikasi

**Gejala:** PyScrapr restart, beberapa jam lewat, tidak ada pengecekan baru di history.
**Penyebab:** APScheduler tidak start, atau database lock.
**Solusi:** Cek Settings > System Status > APScheduler. Restart manual via tombol. Cek log error startup.

## Keamanan & etika

> [!IMPORTANT]
> Price Watcher membuat request ke situs e-commerce. Walaupun footprint kecil per produk, kalau Anda track 100 produk dengan interval pendek, total request bisa signifikan. Hormati situs target dan ikuti aturan dasar.

- **Hormati robots.txt.** Tool default cek `robots.txt` situs target dan skip kalau path produk Disallow. Toggle off hanya untuk situs Anda sendiri.

- **Interval reasonable.** Jangan set 1 menit interval kustom via SQL hack. Minimum di UI 15 menit ada alasannya: sopan ke server target dan menghindari pattern bot yang mencolok.

- **User agent jujur.** Default UA string mengandung kata "PyScrapr". Beberapa user tergoda ganti ke UA browser asli untuk bypass deteksi. Itu pilihan Anda, tapi sadari implikasinya: kalau situs target deteksi pattern dan block, jangan kaget.

- **Jangan resell data harga.** Data harga dari Price Watcher untuk personal decision atau internal analysis. Jangan resell ke pihak ketiga sebagai data product (itu beda use case yang butuh license komersial dari marketplace).

- **Privacy untuk diri sendiri.** Database lokal. Tidak ada upload, tidak ada telemetri. Tapi kalau Anda backup ke cloud (Dropbox, Google Drive), file `price_watcher.db` ikut. Pertimbangkan apakah Anda mau metadata produk yang Anda watch ter-sync ke cloud.

- **Notifikasi via webhook publik.** Discord webhook URL kalau bocor bisa di-abuse orang lain. Simpan URL itu seperti password.

## Pengaturan teknis

| Key | Tipe | Default | Keterangan |
|-----|------|---------|------------|
| `price_watcher_enabled` | boolean | true | Master switch tool |
| `price_watcher_tick_interval_seconds` | integer | 300 | Frekuensi scheduler tick (jangan turunkan di bawah 60) |
| `price_watcher_max_concurrent_checks` | integer | 3 | Job paralel saat banyak produk due bersamaan |
| `price_watcher_request_timeout_seconds` | integer | 30 | Timeout per fetch produk |
| `price_watcher_history_retention_days` | integer | 365 | Retain history (auto cleanup di luar window) |
| `price_watcher_default_interval_hours` | integer | 6 | Default interval form |
| `price_watcher_user_agent` | string | `"Mozilla/5.0 (PyScrapr Price Watcher)"` | UA string |
| `price_watcher_respect_robots` | boolean | true | Hormati robots.txt |

## Related docs

- [Selector Playground](/docs/utilities/playground.md) - test CSS/XPath sebelum simpan ke Price Watcher
- [Webhooks](/docs/advanced/webhooks.md) - setup Discord/Telegram/HTTP notif
- [Email Notifications](/docs/advanced/email.md) - alternatif SMTP untuk alert
- [Scheduled Jobs](/docs/system/scheduled.md) - automation umum di luar Price Watcher
- [Diff Detection](/docs/system/diff.md) - bandingkan history harga di window tertentu
- [Settings](/docs/system/settings.md) - semua flag Price Watcher
