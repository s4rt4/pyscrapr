# Link Bypass

> Alat untuk me-resolve URL pengalihan dan membuka link yang terbungkus gateway iklan (adf.ly, ouo.io, shrinkme, exe.io, dll). Mendukung mode single URL dan batch hingga ratusan link sekaligus.

## Deskripsi

Link Bypass adalah utility yang sering dibutuhkan saat scraping: Anda menemukan ribuan URL yang semuanya dibungkus adf.ly atau semacamnya, dan perlu tahu URL asli di baliknya sebelum bisa fetch konten sebenarnya. PyScrapr menyediakan tool ini dengan dua mode kerja. Mode pertama adalah **Direct Redirect Resolver**: mengikuti rantai HTTP 301/302/307/308 sampai URL final (mirip `curl -L`), berguna untuk t.co, bit.ly, goo.gl, dan URL shortener lain yang straightforward. Mode kedua adalah **Ad-Gateway Bypasser**: adapter khusus per-gateway yang mengetahui cara membaca halaman intermediate dan mengekstrak destination URL tanpa benar-benar menunggu countdown iklan.

Setiap gateway adapter hidup di `app/services/link_bypass.py` dengan pola modular. Misalnya adapter `adfly` tahu kalau adf.ly menyimpan URL target di variable JS `ysmm` yang di-encode dengan algoritma custom; adapter `ouo_io` tahu harus POST ke form action tertentu; adapter `shrinkme` parse base64-encoded parameter dari script tag. Teknik yang dipakai: regex extraction, base64 decode, form action parsing, JavaScript variable extraction, dan kadang multi-step (fetch page A → extract token → POST ke page B → redirect chain).

Mode batch memungkinkan Anda paste hingga 100+ URL (satu URL per baris) ke textarea, lalu tool akan resolve semuanya secara paralel (dengan semaphore untuk limit concurrent requests) dan menyajikan hasilnya sebagai tabel. Setiap baris tabel menampilkan: URL asli, URL final, jumlah redirect dalam chain, method yang dipakai (misal `redirect`, `adf.ly`, `ouo.io`), dan waktu eksekusi dalam milidetik. Kegagalan per-URL tidak menghentikan batch — error di-log per baris.

Setiap hasil dilengkapi tombol **Copy** (dengan feedback "Copied!" 2 detik), dan untuk mode single ada action **Send to Harvester** / **Send to Media Downloader** yang langsung mengirim URL final ke tool target dengan field URL pre-filled. Ini menghilangkan friction copy-paste manual — Anda bisa flow langsung dari Bypass → Harvester dalam 2 klik.

## Kapan pakai tool ini?

1. **Dataset dengan URL shortened** — punya list 500 link bit.ly hasil scrape Twitter, perlu expand ke URL asli untuk analisis domain.
2. **Adf.ly / ouo.io / shrinkme links** — menemukan halaman aggregator link (misal forum download) yang semua link-nya di-monetize via gateway iklan.
3. **Verifikasi link safety** — sebelum klik URL mencurigakan dari email, resolve dulu untuk lihat tujuan akhir tanpa expose browser Anda.
4. **Mapping t.co → domain asli** — untuk analisis social media, perlu domain real bukan t.co.
5. **Batch scraping aggregator** — scrape halaman full of obfuscated links, extract href, feed ke Bypass batch, dapat list URL clean untuk stage berikutnya.
6. **Debug 30x redirect chain** — untuk troubleshoot kenapa URL tertentu redirect loop atau akhirnya mendarat di 404.
7. **Detect tracking parameters** — resolve URL lalu compare dengan original untuk lihat parameter tracking yang ditambahkan.
8. **Clean URL sebelum save ke dataset** — simpan URL final ke database, bukan wrapper.

## Cara penggunaan

1. **Buka Link Bypass** — sidebar "Bypass". Ekspektasi: dua tab/panel — Single URL dan Batch.
2. **Mode Single: paste URL** — text field, format lengkap dengan protokol. Ekspektasi: input aktif, tombol Resolve enabled.
3. **Klik Resolve** — tunggu 1-10 detik tergantung gateway. Ekspektasi: spinner, lalu card result muncul.
4. **Review result card** — original URL, final URL, method, chain length, waktu. Ekspektasi: method terdeteksi otomatis (misal "adf.ly" atau "redirect").
5. **Copy atau Send** — klik Copy untuk clipboard, atau Send to Harvester/Media untuk navigate dengan URL pre-fill. Ekspektasi: toast "Copied!" atau redirect ke halaman target.
6. **Mode Batch: switch tab** — klik tab Batch. Ekspektasi: textarea besar.
7. **Paste URL list** — satu URL per baris. Trim empty lines otomatis. Ekspektasi: tidak ada validasi upfront.
8. **Klik Resolve All** — proses parallel dengan concurrency limit (biasanya 5-10). Ekspektasi: progress bar atau row-by-row update.
9. **Review tabel hasil** — kolom: No, Original, Final, Method, Chain, Time, Action. Ekspektasi: error row di-highlight merah dengan pesan.
10. **Sort / filter hasil** — biasanya ada sort per kolom. Ekspektasi: misal sort by Method untuk group.
11. **Export atau Copy batch** — copy tabel ke clipboard (format TSV/CSV), atau gunakan tombol Export jika tersedia. Ekspektasi: data siap di-paste ke Excel.
12. **Retry failed rows** — select yang gagal, resolve ulang (kadang transient error).

## Pengaturan / Konfigurasi

### URL (Single mode)

Satu URL lengkap. Tidak ada validasi pre-submit; invalid URL akan menghasilkan error saat resolve.

### Batch Textarea

Multi-line text, satu URL per baris. Whitespace dan baris kosong di-skip. Tidak ada hard limit di UI, tapi batch >500 URL bisa timeout atau lambat.

### Concurrency

Di-atur di backend (default 5-10 parallel). Tidak diekspos di UI untuk mencegah user overload situs target. Untuk adjust, edit `app/services/link_bypass.py` — cari `asyncio.Semaphore(...)`.

### Timeout per URL

Default 15 detik per URL di backend. URL yang lebih lambat akan dianggap gagal. Tidak ada UI override.

### Follow Redirects (mode Direct)

Selalu aktif — memang tujuan tool ini. Limit max 20 redirect untuk anti-loop.

### Supported Gateways

Saat ini (dapat bertambah):
- **adf.ly** / **adfly.ly** — JS variable `ysmm` decode.
- **ouo.io** / **ouo.press** — form POST + session cookie.
- **shrinkme.io** — base64 + JS variable.
- **exe.io** / **exey.io** — mirror shrinkme family.
- **linkvertise** (partial) — multi-step challenge.
- **bit.ly / t.co / goo.gl / tinyurl / is.gd** — pure HTTP redirect.

Gateway yang tidak dikenali akan fallback ke mode Direct Redirect. Kalau juga tidak ada redirect, final URL = original URL.

### User-Agent

Default menggunakan UA browser realistic (Chrome desktop) untuk menghindari block. Tidak ada UI override.

### Proxy

Belum tersedia di UI Bypass saat ini. Jika butuh resolve via proxy (misal untuk regional gateway), jalankan backend di env yang sudah punya proxy set.

## Output

Tidak ada file output persistence by default. Hasil hanya di UI, copy manual.

Struktur data internal per result:
```json
{
  "original": "https://adf.ly/abc",
  "final": "https://example.com/target",
  "method": "adf.ly",
  "chain_length": 3,
  "chain": ["url1", "url2", "url3"],
  "elapsed_ms": 1250,
  "error": null
}
```

Kalau ingin export, integrate dengan Custom Pipeline yang panggil endpoint `/api/bypass/resolve` dan simpan hasilnya ke JSON/CSV.

## Integrasi dengan fitur lain

1. **Image Harvester** — "Send to Harvester" setelah resolve, langsung scrape image dari URL final yang sudah clean.
2. **Media Downloader** — "Send to Media" untuk download file dari URL yang sebelumnya diobfuscate gateway.
3. **Custom Pipeline** — panggil `POST /api/bypass/resolve` batch dari script untuk clean URL di dataset besar.
4. **URL Mapper** — gabung dengan mapper: crawl situs, ekstrak link, jalankan Bypass batch untuk normalisasi.
5. **Site Ripper (tidak langsung)** — biasanya tidak perlu karena Ripper melakukan redirect follow sendiri, tapi untuk link eksternal yang di-gate, Bypass bisa dipakai sebagai pre-processing.

## Tips & Best Practices

1. **Resolve di batch kecil dulu** — 20-50 URL untuk validasi method detection benar sebelum batch 500.
2. **Catat URL gagal** — bikin list "blocked domains" untuk skip di masa depan; setiap domain yang konsisten gagal kemungkinan besar anti-bot.
3. **Respect rate limit** — jika batch besar menghasilkan banyak error 429 (Too Many Requests), turunkan concurrency atau tambah jeda antar batch.
4. **Beware phishing / malware target** — Bypass akan resolve apa saja. Jangan otomatis "Send to Media" dari URL mencurigakan.
5. **Gunakan method filter** — setelah batch, filter row dengan method `redirect` saja untuk separate URL shortener simple dari gateway iklan.
6. **Timing sebagai health signal** — URL yang butuh >5 detik mungkin akan sulit di-scrape juga; pertimbangkan skip.
7. **Update regex adapter berkala** — gateway sering ubah algoritma. Jika adf.ly tiba-tiba fail semua, buka `link_bypass.py` dan check apakah regex `ysmm` masih match.
8. **Simpan hasil final URL ke database** — jangan resolve ulang URL yang sudah di-resolve kemarin; bikin cache file.

## Troubleshooting

### Problem: Adf.ly selalu gagal / return error
- **Symptom**: method terdeteksi "adf.ly" tapi error "Failed to extract ysmm".
- **Cause**: adf.ly update algoritma JS mereka; regex di adapter tidak lagi match.
- **Solution**: buka halaman adf.ly di browser, view source, cari variabel JS yang berisi token. Update pattern di `app/services/link_bypass.py` function `bypass_adfly`. Atau report issue agar maintainer fix.

### Problem: Ouo.io resolve tapi final URL masih ouo.io domain
- **Symptom**: chain length 1, final URL = original.
- **Cause**: ouo.io butuh session cookie / CAPTCHA yang adapter belum handle.
- **Solution**: sementara pakai browser manual. Atau cek apakah ada path `ouo.io/qs/...` yang bisa di-skip langsung ke destination.

### Problem: Batch sebagian besar gagal timeout
- **Symptom**: 50% rows error "Timeout after 15s".
- **Cause**: target site lambat, atau concurrency terlalu tinggi untuk rate limit.
- **Solution**: turunkan concurrency di backend (edit semaphore), atau split batch jadi lebih kecil dengan jeda.

### Problem: Final URL beda dari expected
- **Symptom**: resolve bit.ly yang harusnya ke youtube.com, malah ke landing page bit.ly.
- **Cause**: bit.ly interstitial page (tergantung suspek spam level).
- **Solution**: tambah header `Accept: text/html,...` lengkap agar dianggap browser. Edit adapter di backend.

### Problem: "Invalid URL" saat submit
- **Symptom**: error immediate tanpa fetch.
- **Cause**: URL tidak punya scheme `http://` atau `https://`.
- **Solution**: prepend scheme manual.

### Problem: Tombol "Send to Harvester" tidak navigate
- **Symptom**: klik tapi tetap di halaman Bypass.
- **Cause**: URL final kosong/null, atau route tidak ter-register.
- **Solution**: pastikan resolve sukses dulu (final URL harus valid); cek konsol browser untuk error JS.

### Problem: Chain length 0 padahal jelas ada redirect
- **Symptom**: URL asli dan final sama meski lewat shortener.
- **Cause**: httpx mungkin tidak menerima redirect karena status code non-standard (misal 200 + meta refresh).
- **Solution**: backend perlu parse `<meta http-equiv="refresh">` manual. Saat ini Link Bypass hanya handle HTTP-level redirect, bukan HTML meta refresh.

### Problem: Batch paste dari Excel muncul error parse
- **Symptom**: 200 baris di-split jadi 400 rows dengan error parsing.
- **Cause**: Excel paste sering include tab/CRLF extra.
- **Solution**: paste dulu ke Notepad, save, copy lagi; atau pre-process di editor text yang jelas LF.

### Problem: Cloudflare-protected URL gagal
- **Symptom**: "HTTP 403 Cloudflare challenge".
- **Cause**: target di belakang CF dengan bot protection.
- **Solution**: Link Bypass tidak bypass Cloudflare. Gunakan browser manual untuk URL-URL ini, atau tool CF-bypass khusus seperti cloudscraper.

## FAQ

**Q: Apakah legal bypass iklan?**
A: Gray area. Gateway seperti adf.ly di-monetize oleh pembuat link; bypass merampas revenue mereka. Gunakan untuk tujuan legitimate (analisis, verifikasi keamanan) dan pertimbangkan etika.

**Q: Berapa banyak gateway yang didukung?**
A: Saat ini ~6-8 major gateways. Ditambah terus.

**Q: Bisa tambah gateway custom?**
A: Ya, edit `app/services/link_bypass.py` dan buat function adapter baru + registration di router regex.

**Q: Apakah saya bisa ditrack?**
A: Backend PyScrapr yang fetch URL, bukan browser Anda. IP yang tercatat di log gateway adalah IP mesin server PyScrapr (biasanya IP rumah Anda karena lokal).

**Q: Rate limit default?**
A: Concurrency 5-10, tergantung config backend.

**Q: Batch besar (1000 URL) aman?**
A: Secara teknis bisa, tapi akan lambat dan rawan trigger rate limit gateway. Split per 100.

**Q: Support link LinkedIn / Twitter redirect?**
A: LinkedIn `lnkd.in` harusnya ya (plain redirect). Twitter `t.co` ya.

**Q: Bisa decode short URL custom corporate?**
A: Kalau pakai 301/302 standard, ya. Kalau pakai JS/SPA, tidak.

**Q: Hasil disimpan ke disk?**
A: Tidak by default.

**Q: Adf.ly break, harus tunggu update?**
A: Atau perbaiki sendiri di kode; adapter sengaja didesain simple agar bisa di-patch cepat.

## Keterbatasan

- **Gateway sering berubah** — adapter butuh maintenance berkala.
- **Tidak handle CAPTCHA** — gateway dengan reCAPTCHA full (contoh beberapa adfly custom) tidak akan resolve.
- **Tidak Cloudflare bypass** — URL di balik CF protection akan gagal.
- **Tidak JS-rendered** — sama seperti Playground, hanya HTTP-level bypass.
- **Tidak ada persistence cache** — resolve URL yang sama 2 kali = fetch 2 kali.
- **Hanya 1 level bypass** — kalau URL A mengarah ke URL gateway B lagi, tool mungkin tidak rekursif auto-resolve (tergantung method detection).
- **Tidak support proxy rotation** — jika IP di-blacklist oleh gateway, tidak ada failover.

## Related docs

- [Image Harvester](../tools/image-harvester.md) — destination umum untuk URL yang sudah di-resolve.
- [Media Downloader](../tools/media-downloader.md) — untuk download file dari URL final.
- [Custom Pipeline](./pipeline.md) — otomasi batch bypass di script.
- [Auth Vault](./vault.md) — tidak langsung terpakai di Bypass, tapi relevant untuk stage selanjutnya.
- [Index dokumentasi](../index.md) — navigasi utama.
