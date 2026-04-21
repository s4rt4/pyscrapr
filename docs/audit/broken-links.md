# Broken Link Checker

> Tool pencari link rusak dalam situs yang melakukan BFS crawl dari URL awal (tetap di domain), mengumpulkan semua anchor href yang ditemukan, lalu memvalidasi status HTTP setiap link menggunakan metode HEAD dengan fallback GET. Hasilnya adalah laporan terstruktur berisi total halaman yang di-crawl, total link yang diperiksa, jumlah rusak, jumlah redirect, breakdown per status code, dan daftar link rusak lengkap dengan halaman sumber. Cocok untuk QA sebelum migrasi besar, audit bulanan situs klien, atau cleanup konten lama.

## Apa itu Broken Link Checker

Broken Link Checker adalah modul PyScrapr yang fokus pada satu masalah klasik maintenance situs: link rusak. Link yang menunjuk ke halaman 404, domain yang sudah mati, redirect loop, atau URL dengan typo yang tidak pernah di-notice, sampai suatu hari user komplain atau search engine menurunkan ranking. Tool ini mengotomatiskan proses yang biasanya manual: buka situs, klik satu per satu link, cek masing-masing, catat yang rusak. Untuk situs 50 halaman dengan rata-rata 30 link per halaman, itu 1500 klik manual. Tool ini menyelesaikan pekerjaan yang sama dalam hitungan menit.

Cara kerjanya: Anda kasih satu URL awal (biasanya homepage). Tool mulai BFS crawl dari sana, tetap di domain yang sama, dengan batasan jumlah halaman maksimum (default 50). Setiap halaman yang di-fetch akan di-parse HTML-nya, semua tag `<a href>` dikumpulkan. Untuk setiap link, tool mencoba HEAD request dulu (hemat bandwidth karena tidak download body). Kalau HEAD gagal atau server tidak support (status 405, 403, 501), tool fallback ke GET. Hasil setiap check dicatat: status code, latency, redirect chain, flag ok (2xx atau 3xx dianggap ok, 4xx dan 5xx serta error koneksi dianggap broken).

Tool juga dedupe: link yang sama muncul di 10 halaman hanya di-check satu kali, tapi tetap tercatat kemunculannya di semua halaman sumber. Ini menghemat waktu dan mengurangi beban server target.

> [!NOTE]
> Tool ini berjalan synchronous. Untuk crawl max 50 halaman dengan total 500 link, biasanya selesai dalam 1 sampai 3 menit tergantung latency server target. Request paralel tidak diaktifkan by default untuk menghindari rate limit trigger.

## Cara pakai (step-by-step)

1. Buka menu **Broken Link Checker** di sidebar PyScrapr.

2. Isi field `URL awal` dengan URL halaman mulai. Biasanya homepage. Contoh: `https://blog.contoh.com` atau `https://toko.co.id`.

3. Atur `Max halaman`. Default 50 sudah cukup untuk situs kecil sampai medium. Untuk situs besar, naikkan ke 200 atau lebih, tapi ingat scan-nya akan lebih lama.

4. Atur `Timeout (detik)` untuk batas wait per link. Default 10. Naikkan kalau banyak link menuju ke CDN atau server lambat.

5. Klik `Scan`. Backend akan buat Job dengan type LINK_CHECK, mulai BFS crawl, validasi setiap link. UI akan tampilkan spinner selama proses.

6. Hasil muncul dalam bentuk:
   - **Grid statistik** 4 kartu: Halaman di-crawl, Total link, Jumlah rusak (merah), Jumlah redirect (kuning)
   - **Tabel link rusak** dengan kolom Status, URL, Sumber (halaman asal), Alasan (pesan error kalau ada)
   - **Filter status code** dropdown untuk drill down ke status tertentu (misal hanya 404 atau hanya 500)
   - **Tombol Export CSV** untuk download laporan lengkap dalam format spreadsheet

7. Hasil otomatis tersimpan di History sebagai Job LINK_CHECK. Bisa di-rerun, di-compare, atau di-schedule.

## Contoh kasus pakai

- **Audit bulanan situs klien agency** - Anda handle 20 situs klien. Setiap awal bulan, scan masing-masing. Export CSV yang berisi broken links, kirim ke klien sebagai part of retainer report. Klien senang karena proaktif, Anda tidak perlu beli tool SaaS berbayar $30 per bulan.

- **Pre-migration check** - Anda akan migrasi situs dari Wordpress ke static site generator. Sebelum migrasi, scan situs untuk cari broken links. Fix dulu di Wordpress (lebih mudah), baru migrasi. Setelah migrasi, scan lagi untuk pastikan tidak ada link yang pecah karena perubahan struktur URL.

- **QA internal blog content team** - Team content rutin reference artikel lama dalam artikel baru. Kadang artikel lama di-unpublish atau URL berubah. Scan bulanan catch broken internal links sebelum user complain.

- **Cleanup arsip blog lama** - Blog Anda punya 500 artikel dari 10 tahun terakhir. Banyak link eksternal yang pasti mati. Scan, export CSV, delegasikan ke intern untuk update atau hapus link mati satu per satu.

- **Validasi launch checklist** - Tim dev selesai bikin fitur baru dengan 30 halaman baru. Scan fitur sebelum deploy ke production. Catch link rusak sebelum user lihat.

- **Vendor due diligence** - Anda evaluasi vendor jasa content. Scan portfolio situs mereka. Kalau banyak broken links, itu signal mereka tidak maintenance dengan baik.

## Apa yang di-check

Setiap link yang ditemukan divalidasi dengan urutan:
1. HEAD request ke URL (follow redirects).
2. Kalau status 405, 403, atau 501 (server tolak HEAD), fallback ke GET.
3. Kalau GET juga error, catat alasan dari exception.

Link dianggap:
- **OK**: status code 2xx atau 3xx.
- **Broken**: status 4xx, 5xx, atau connection error (timeout, DNS fail, SSL fail, dst).
- **Redirect**: status 3xx (tercatat juga sebagai OK, tapi terhitung di redirect count).

## Data yang dicatat per link

- URL absolute yang dicek
- Status code numerik (0 kalau error koneksi)
- Flag ok (boolean)
- Latency millisecond
- Redirect chain (daftar URL yang di-follow)
- Alasan (kalau error, berisi pesan dari exception)
- Halaman sumber (URL halaman tempat link ini ditemukan)

## Pengaturan

### max_pages
Batas maksimum halaman yang di-crawl dalam BFS. Default 50. Rekomendasi: 50 untuk situs kecil, 200 untuk situs medium, 1000 untuk situs besar. Catatan: scan time scales linearly.

### timeout
Timeout per request (halaman maupun link). Default 10 detik. Naikkan ke 20 kalau banyak resource di belakang WAF atau hosting lambat.

### stay_on_domain
Boolean apakah crawl hanya tetap di domain starting URL. Default true. Matikan hanya kalau Anda paham risiko crawl ke eksternal (bisa tak terkontrol).

### user_agent_rotation
Boolean global dari Settings. Default mengikuti Settings.

### proxy_rotation
Boolean global dari Settings. Rekomendasi aktifkan kalau Anda scan situs sensitive atau target IP rate-limiting.

## Tips efisiensi

- **Jangan scan dengan max_pages terlalu besar di first run**. Test dulu dengan 20 halaman untuk validate konfigurasi, baru scale up.

- **Exclude pattern yang tidak perlu**. Contohnya link ke `/logout`, `/download.pdf`, atau API endpoint. Tool saat ini tidak punya exclude filter eksplisit, tapi Anda bisa filter di CSV export manual.

- **Run di jam sepi traffic**. Kalau target adalah situs production live, jalankan scan tengah malam untuk hindari mengganggu user.

- **Kombinasikan dengan Scheduled Jobs**. Set scan otomatis setiap minggu, webhook notify ke Discord kalau broken count naik.

## Interpretasi status code

Berikut status code umum dan maknanya:

| Status | Makna | Aksi |
|--------|-------|------|
| 404 | Halaman tidak ditemukan | Fix href atau hapus link |
| 410 | Halaman gone (permanent) | Hapus link, ini intentional |
| 500 | Server error | Notify owner target, mungkin sementara |
| 502/503 | Bad gateway / service unavailable | Coba rescan nanti, kemungkinan transient |
| 301/302 | Redirect | Sebaiknya update href ke URL final agar hemat latency |
| 0 atau error | Tidak bisa resolve / connection | Domain mati atau DNS problem |
| 403 | Forbidden | Kadang false-positive kalau server block bot, coba Auth Vault |

## Troubleshooting

### Problem: Banyak false positive broken di satu domain
**Gejala:** Semua link ke domain X return 403. 
**Penyebab:** Domain X punya WAF yang block request tanpa UA browser real. 
**Solusi:** Aktifkan UA rotation, atau skip verify domain X dan cek manual.

### Problem: Scan lambat banget
**Gejala:** Scan 50 halaman butuh 20 menit. 
**Penyebab:** Server target lambat, atau banyak link menuju ke timeout. 
**Solusi:** Turunkan timeout ke 5 detik (agresif skip yang lambat), atau batch paralelisasi (roadmap).

### Problem: Tool tidak masuk ke halaman di balik login
**Gejala:** Scan cuma detect halaman public. 
**Penyebab:** Tool tidak login session. 
**Solusi:** Set Auth Vault profile dengan cookies valid untuk domain target. Tool akan auto-inject saat crawl.

### Problem: Link anchor #section dianggap rusak
**Gejala:** Link `#about` atau `#contact` tidak muncul di hasil. 
**Penyebab:** Intentional. Tool skip anchor fragment, mailto:, tel:, javascript:. 
**Solusi:** Normal, tidak perlu action.

### Problem: Status 0 untuk banyak link
**Gejala:** Banyak link tanpa status code. 
**Penyebab:** SSL error, DNS resolve fail, atau proxy reject. 
**Solusi:** Cek kolom Alasan untuk detail. Kalau SSL error, verify domain masih active via browser biasa.

### Problem: HTTPS mixed content warning tidak muncul
**Gejala:** Tool tidak flag link http:// di halaman https://. 
**Penyebab:** Tool cuma validate reachability, bukan mixed content warning. 
**Solusi:** Kombinasikan dengan Security Headers Scanner dan manual review.

## Keamanan dan etika

> [!WARNING]
> BFS crawl bisa generate traffic signifikan ke situs target. Scan max 50 halaman dengan 30 link per halaman = 1500 requests. Respect server, jangan scan terlalu frequent.

- Scan dengan izin pemilik situs. Untuk situs yang bukan milik Anda, rate limit di Settings sebaiknya conservative (2-3 req/s max).
- Respect robots.txt. Tool tidak probe path Disallow secara default.
- Hasil scan adalah snapshot satu waktu. Status bisa berubah 5 menit kemudian (server sementara down, dsb). Untuk keputusan penting (misal hapus link), verify manual 2-3 kali dengan jeda waktu.

## Related docs

- [URL Mapper](/docs/tools/url-mapper.md) - map semua halaman situs, complementary
- [SEO Auditor](seo.md) - audit on-page SEO setiap halaman
- [Site Ripper](/docs/tools/site-ripper.md) - kalau Anda butuh clone full situs, bukan cuma validate link
- [Scheduled Jobs](/docs/system/scheduled.md) - jadwalkan broken link check mingguan
- [Webhooks](/docs/advanced/webhooks.md) - notify Discord kalau broken count melonjak
- [Auth Vault](/docs/utilities/vault.md) - crawl halaman di balik login
