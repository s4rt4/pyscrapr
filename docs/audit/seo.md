# SEO Auditor

> Tool audit SEO on-page satu klik yang membedah semua sinyal penting: title, meta description, canonical, heading hierarchy, alt gambar, Open Graph, Twitter Card, structured data, word count, dan puluhan indikator lain, lalu menghasilkan skor 0-100 plus daftar isu terurut berdasarkan severity. Cocok untuk audit cepat sebelum publish, review kompetitor, atau QA berkala terhadap ratusan halaman.

## Apa itu SEO Auditor

SEO Auditor adalah modul PyScrapr yang dirancang khusus untuk membaca kualitas SEO on-page sebuah halaman web hanya dari satu URL input. Anda paste alamat halaman, tool akan melakukan satu request HTTP ringan ke server target, mem-parsing HTML lengkap menggunakan BeautifulSoup, lalu mengekstrak dan mengevaluasi puluhan elemen penting: tag title, meta description, meta robots, canonical link, atribut lang, viewport, Open Graph tags, Twitter Card tags, hierarki heading (H1 sampai H4), jumlah gambar yang tidak punya atribut alt, rasio link internal vs eksternal, ada atau tidaknya structured data (JSON-LD dan microdata), favicon, dan total jumlah kata di body halaman.

Hasil audit dikembalikan dalam bentuk dua layer: data mentah yang rapi (title aslinya apa, panjangnya berapa, OG tag-nya seperti apa, dst) untuk Anda inspeksi manual, dan layer analisis yang sudah mengubah data mentah tersebut menjadi daftar isu konkret dengan severity (error, warning, info) beserta skor agregat 0 sampai 100. Dengan pendekatan dua layer ini, Anda bisa lihat gambaran cepat dari skor saja, atau drill down ke isu spesifik kalau butuh detail.

Filosofi tool ini sederhana. Daripada Anda harus buka DevTools, cek View Source, lihat Lighthouse panel, baca OG tag satu per satu, copy title ke Notepad untuk hitung panjangnya, cek H1 pakai Ctrl+F, dan hitung manual berapa gambar yang alt-nya kosong, SEO Auditor melakukan semuanya dalam hitungan detik. Proses audit yang biasanya memakan 10 sampai 20 menit per halaman dipangkas jadi satu klik.

> [!NOTE]
> SEO Auditor tidak melakukan crawl. Satu scan mengaudit satu halaman saja. Kalau Anda butuh audit banyak halaman sekaligus, kombinasikan dengan URL Mapper untuk discover halaman dulu, lalu batch-submit via Bulk Queue.

## Cara pakai (step-by-step)

1. Buka PyScrapr, navigasi ke menu **SEO Auditor** di sidebar. Halaman akan menampilkan form input URL di atas dan area hasil kosong di bawah.

2. Di field `URL target`, paste alamat halaman yang mau diaudit. Contoh valid: `https://blog.contoh.com/artikel-tentang-cuaca`, `https://toko.co.id/produk/laptop-xyz`. Skema http atau https wajib ada.

3. Atur `Timeout (detik)` kalau situs target lambat. Default 20 detik cukup untuk 95% kasus. Naikkan ke 40 kalau target di belakang WAF atau hosting lambat.

4. Klik tombol `Audit`. Backend akan membuat job dengan type SEO_AUDIT, fetch halaman sekali via httpx, parse HTML, hitung semua sinyal, build daftar isu, kalkulasi skor, dan return ke UI.

5. Hasil muncul di area bawah dengan struktur visual sebagai berikut:
   - **Skor ring chart** di kiri atas, ukuran besar, warna berubah sesuai tingkat skor (merah kalau dibawah 50, kuning dibawah 75, hijau teal kalau 75 ke atas)
   - **Grid statistik** berisi panjang title, panjang description, jumlah H1, rasio gambar dengan atau tanpa alt, dan total word count
   - **Daftar isu** dalam bentuk Alert component, warna sesuai severity (merah untuk error, kuning untuk warning, biru untuk info)
   - **Tabel meta tag utama** berisi title, description, canonical, robots, lang, viewport
   - **Card Open Graph dan Twitter** side-by-side yang menampilkan semua tag yang ditemukan
   - **Outline heading H1 dan H2** untuk lihat struktur konten halaman

6. Hasil audit tersimpan otomatis di History sebagai Job dengan type SEO_AUDIT. Anda bisa buka lagi lewat History kalau butuh audit ulang atau bandingkan dengan audit lama.

> [!TIP]
> Untuk audit massal, pakai fitur Bulk Queue. Anda bisa paste daftar URL sekaligus, tool akan eksekusi audit satu per satu, hasilnya tersimpan di History dan bisa di-export ke CSV untuk laporan ke klien.

## Contoh kasus pakai

- **Audit pre-publish artikel blog** - Anda baru selesai menulis artikel 1500 kata di CMS. Sebelum klik publish, paste URL preview ke SEO Auditor. Dalam 3 detik Anda tahu apakah title sudah tepat panjangnya, description sudah ada, canonical benar, semua gambar punya alt, dan H1 tepat satu. Fix dulu sebelum publish, hindari malu kena flag SEO tools lain setelah live.

- **Audit kompetitor** - Anda mau rebut keyword "sepeda listrik terbaik 2026" dari kompetitor yang saat ini posisi 1. Audit halaman mereka. Lihat panjang title, jumlah kata, structured data yang mereka pakai. Bandingkan dengan halaman Anda sendiri. Dari gap ini Anda tahu persis apa yang harus ditingkatkan.

- **QA berkala situs klien** - Anda handle 15 situs klien sebagai retainer. Setiap awal bulan, audit homepage dan 5 halaman penting masing-masing klien. Kalau ada regresi (misal klien tiba-tiba hilangkan canonical karena redesign), Anda langsung catch dan lapor.

- **Troubleshoot penurunan traffic organik** - Traffic organik turun 30% minggu lalu. Audit halaman yang biasanya traffic-nya tinggi. Ketemu, canonical-nya sekarang menunjuk ke homepage karena bug template. Fix dalam 10 menit.

- **Training content writer** - Tim content Anda baru, belum terbiasa SEO best practice. Buat workflow: setiap artikel baru harus lulus audit SEO (skor minimal 75) sebelum di-publish. Tool ini jadi quality gate internal yang konsisten.

- **Riset SERP untuk tahu stadard di niche tertentu** - Anda mau masuk niche "review kamera". Audit 10 halaman top SERP. Lihat panjang rata-rata konten, heading yang mereka pakai, structured data yang umum. Pakai data ini sebagai benchmark saat bikin konten sendiri.

## Skor dan severity

SEO Auditor memberikan skor 0 sampai 100. Perhitungannya: mulai dari 100, lalu kurangi bobot untuk setiap isu yang ditemukan.

- Error: potong 15 poin per isu. Contoh: missing title, missing description, missing canonical, zero H1, multiple H1.
- Warning: potong 7 poin per isu. Contoh: panjang title di luar rentang 30-65, panjang description di luar 70-160, ada gambar tanpa alt, missing viewport, atribut lang tidak di-set.
- Info: potong 2 poin per isu. Contoh: tidak ada structured data, tidak ada OG tags, tidak ada favicon.

Skor minimum 0 (tidak bisa negatif). Warna indikator di UI:
- **Hijau teal** (75 sampai 100): halaman sehat, cuma polish-polish kecil
- **Kuning** (50 sampai 74): ada beberapa isu signifikan yang sebaiknya diperbaiki
- **Merah** (0 sampai 49): halaman punya masalah SEO serius, prioritaskan perbaikan

## Apa yang dicek (detail)

Berikut daftar lengkap elemen yang dievaluasi per scan:

| Elemen | Kategori isu | Kondisi trigger |
|--------|--------------|-----------------|
| Title tag | error | Tidak ditemukan sama sekali |
| Title length | warning | Di bawah 30 atau di atas 65 karakter |
| Meta description | error | Tidak ditemukan sama sekali |
| Description length | warning | Di bawah 70 atau di atas 160 karakter |
| Canonical link | error | Tag link rel=canonical tidak ada |
| H1 count | error | Zero H1 atau lebih dari satu H1 |
| Image alt | warning | Ada gambar tanpa atribut alt yang terisi |
| Viewport meta | warning | Tidak ada meta viewport |
| Lang attribute | warning | Tag html tidak punya atribut lang |
| Structured data | info | Tidak ada JSON-LD maupun microdata |
| Open Graph tags | info | Tidak ada OG tag sama sekali |
| Favicon | info | Tidak ada link rel=icon |

Selain issue-based checks, tool juga mencatat data deskriptif:
- Robots meta (index, noindex, nofollow, dst)
- Twitter Card tags (card, title, description, image)
- H2, H3, H4 counts dan daftar teks H1 serta H2
- Total gambar dan total gambar tanpa alt
- Jumlah anchor internal (sama domain) dan eksternal
- Total word count body
- Daftar itemtype structured data

## Pengaturan

### timeout
Batas waktu maksimum (detik) menunggu response server target. Default 20. Rekomendasi naikkan ke 40 atau 60 untuk situs besar yang lambat.

### user_agent_rotation
Boolean dari Settings global. Default mengikuti Settings. Rekomendasi biarkan ON supaya server tidak serve konten versi bot yang beda dari konten browser normal.

### proxy_rotation
Boolean dari Settings global. Rekomendasi aktifkan kalau Anda batch-audit banyak URL dari satu domain dan takut kena rate limit.

## Tips akurasi

- **Audit halaman individual yang kena target keyword, bukan homepage**. Homepage itu etalase, jarang dioptimalkan untuk keyword spesifik. Audit halaman content yang punya judul, H1, dan body jelas.

- **Untuk SPA (React, Vue, tanpa SSR)**, hasil audit mungkin kosong karena HTML server-side hanya skeleton. Tool ini saat ini tidak render JS. Solusinya: audit URL pre-rendered atau pakai snapshot HTML hasil Playwright manual.

- **Kombinasikan dengan tool lain**. SEO on-page cuma satu dimensi. Untuk gambaran lengkap, tambah Tech Stack Detector (lihat platform), Security Headers (lihat hardening), dan Broken Link Checker (lihat integritas).

- **Simpan skor dari waktu ke waktu**. Audit halaman yang sama setiap bulan, catat skor. Kalau turun, investigasi apa yang berubah di HTML antara scan bulan lalu dan sekarang.

## Troubleshooting

### Problem: Skor selalu rendah meski halaman Anda bagus
**Gejala:** Semua audit kasih skor di bawah 50. 
**Penyebab:** Halaman render client-side, HTML yang diterima tool hanya skeleton kosong. 
**Solusi:** Verify manual via `curl -s URL | grep title`. Kalau kosong, halaman memang SPA. Tambahkan SSR atau prerendering.

### Problem: Description terdeteksi padahal Anda yakin tidak ada
**Gejala:** Kolom description ada isinya tapi Anda tidak pernah set manual. 
**Penyebab:** CMS atau framework auto-generate description dari excerpt pertama konten. 
**Solusi:** Normal. Kalau auto-generated tidak sesuai, set manual via CMS.

### Problem: Multiple H1 false positive
**Gejala:** Tool report multiple H1 tapi Anda yakin cuma satu. 
**Penyebab:** Template atau widget (misal sidebar widget judul, footer widget judul) render tag H1 juga. 
**Solusi:** Cek View Source manual, ganti tag widget ke H2 atau H3. Hanya satu H1 per halaman untuk semantic yang tepat.

### Problem: Tidak bisa fetch halaman di belakang login
**Gejala:** Error 401 atau 403 saat audit URL member-only. 
**Penyebab:** Halaman butuh autentikasi. 
**Solusi:** Set Auth Vault profile untuk domain target dengan cookies atau Bearer token yang valid. Tool otomatis pakai.

### Problem: OG tags tidak terdeteksi
**Gejala:** OG section kosong padahal Anda sudah set OG tag. 
**Penyebab:** OG tag pakai atribut `name` bukan `property`. Standar resmi adalah `property`. 
**Solusi:** Ubah semua OG tag Anda ke `<meta property="og:..." content="..." />`.

## Keamanan dan etika

> [!WARNING]
> Audit satu halaman = satu request GET ke server target. Secara legal ini tercatat di log. Hanya audit situs Anda sendiri atau situs yang Anda punya izin untuk audit.

- Satu request per scan, footprint minimal.
- Respect Terms of Service situs target. Scraping masal untuk kompetitor research bisa violate ToS.
- Hasil audit adalah assist, bukan oracle. Validasi manual untuk keputusan penting.

## Related docs

- [Broken Link Checker](broken-links.md) - validasi link di situs yang sama
- [Security Headers Scanner](security-headers.md) - audit header keamanan
- [URL Mapper](/docs/tools/url-mapper.md) - discover halaman dulu sebelum batch audit
- [Bulk Queue](/docs/advanced/bulk-queue.md) - batch audit multi-URL
- [History](/docs/system/history.md) - review audit lama, export hasil
- [Scheduled Jobs](/docs/system/scheduled.md) - jadwalkan audit periodik
