# Security Headers Scanner

> Tool audit header keamanan HTTP yang memeriksa 9 header penting (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, dan tiga header Cross-Origin) plus flag cookie (HttpOnly, Secure, SameSite), menghasilkan grade huruf A sampai F dan skor 0 sampai 100, beserta rekomendasi konkret per header yang hilang atau lemah. Cocok untuk audit harden konfigurasi server sebelum launch, due diligence kompetitor, atau compliance checklist.

## Apa itu Security Headers Scanner

Security Headers Scanner adalah modul PyScrapr yang berfokus pada satu dimensi yang sering ter-neglected dalam development: response headers yang dikirim server untuk mitigasi berbagai kelas serangan di sisi browser. Header seperti Content Security Policy bisa mencegah XSS. Header Strict Transport Security memaksa HTTPS dan mencegah downgrade attack. X-Frame-Options mencegah clickjacking. Semua header ini gratis untuk ditambahkan, cuma beberapa baris konfigurasi nginx atau middleware framework, tapi dampaknya signifikan untuk postur keamanan.

Masalahnya, banyak developer tidak tahu header apa yang perlu ada, nilai mana yang aman, atau kapan cookies mereka butuh flag Secure. Security Headers Scanner mengotomatiskan audit ini. Anda paste URL, tool melakukan satu GET request, menangkap semua response headers dan Set-Cookie headers, mengevaluasi masing-masing, lalu return laporan terstruktur dengan grade huruf (A sampai F) yang mirip seperti standard tools komersial (misalnya observatory.mozilla.org atau securityheaders.com), tapi semuanya offline dan terintegrasi dengan workflow PyScrapr Anda.

Grading logic: setiap header punya bobot berdasarkan tingkat kritikalitasnya. HSTS dan CSP paling penting (bobot 20 masing-masing), X-Frame-Options dan X-Content-Type-Options menengah (10 dan 8), sisanya lebih ringan (5-6). Skor total adalah persentase bobot yang "earned" oleh header yang ada dengan nilai yang tepat. Selain cek presence, tool juga validasi kualitas nilai: HSTS tanpa max-age atau max-age=0 dapat penalty, X-Content-Type-Options yang bukan nosniff dapat warning, X-Frame-Options yang bukan DENY atau SAMEORIGIN dapat info flag.

> [!NOTE]
> Scanner ini fokus pada HTTP response headers dan Set-Cookie attributes. Ini bukan tool vulnerability scanner. Tidak probe SQL injection, XSS, atau RCE. Untuk audit komprehensif, kombinasikan dengan SSL Inspector, Tech Fingerprinter, dan penetration testing terpisah.

## Cara pakai (step-by-step)

1. Buka menu **Security Headers** di sidebar PyScrapr.

2. Paste URL target di field `URL target`. Biasanya scan terhadap URL https:// supaya bisa validate HSTS dan cookies Secure. Contoh: `https://app.contoh.com`.

3. Klik `Scan`. Tool buat Job type SECURITY_SCAN, fetch URL sekali, capture response headers dan cookies, evaluasi.

4. Hasil muncul dalam bentuk:
   - **Big grade letter** (A, B, C, D, E, atau F) di lingkaran besar berwarna (teal untuk A, lime B, yellow C, orange D, merah E atau F)
   - **Skor numerik** 0 sampai 100 di sebelahnya
   - **Tabel "Header Ditemukan"** berisi header yang present beserta nilainya
   - **Daftar "Header Hilang"** berisi header yang tidak ada, ditampilkan sebagai badge merah
   - **Tabel Cookie** dengan kolom Nama, HttpOnly, Secure, SameSite, Path. Kolom boolean pakai badge warna.
   - **List rekomendasi** dalam bentuk Alert component, satu per issue, dengan severity dan message yang actionable

5. Hasil tersimpan di History sebagai Job SECURITY_SCAN, bisa di-rerun atau di-diff.

## Contoh kasus pakai

- **Pre-launch security checklist** - Tim dev claim fitur X sudah ready untuk production. Scan production-preview URL. Grade C karena CSP belum ada, HSTS belum ada. Block launch sampai fixed. Ini checklist objective yang menghindari debate subjective.

- **Audit kompetitor untuk benchmark** - Anda mau lihat seberapa serius kompetitor soal keamanan. Scan homepage mereka. Ketahuan pakai grade A dengan CSP yang ketat. Ini indikasi tim engineering mereka matang.

- **Compliance audit internal** - Perusahaan Anda ikut ISO 27001 atau SOC 2. Bagian audit minta bukti bahwa situs public pakai standar security. Scan, screenshot laporan, lampirkan.

- **Regresi check setelah redeploy** - Setelah redeploy ke Kubernetes baru, scan lagi untuk pastikan tidak ada header yang hilang karena konfigurasi ingress berubah. Bandingkan dengan scan sebelum deploy di History.

- **Training security awareness developer** - Tunjukkan ke developer junior: sebelum dan sesudah mereka tambah CSP. Grade naik dari D ke B. Visual dampak satu konfigurasi.

- **SaaS vendor evaluation** - Anda evaluasi 3 SaaS vendor. Scan situs masing-masing. Yang paling tidak serius soal header adalah signal soal engineering discipline vendor.

## Header yang di-check

| Header | Severity saat hilang | Bobot | Fungsi |
|--------|----------------------|-------|--------|
| Strict-Transport-Security | error | 20 | Paksa HTTPS, cegah downgrade attack |
| Content-Security-Policy | error | 20 | Kebijakan konten, mitigasi XSS dan injection |
| X-Frame-Options | warning | 10 | Cegah clickjacking via iframe |
| X-Content-Type-Options | warning | 8 | Cegah MIME sniffing (nilai nosniff) |
| Referrer-Policy | warning | 6 | Kontrol informasi referrer |
| Permissions-Policy | info | 5 | Kontrol akses fitur browser (kamera, mikrofon, dll) |
| Cross-Origin-Opener-Policy | info | 5 | Isolasi browsing context |
| Cross-Origin-Embedder-Policy | info | 5 | Kontrol embed resource |
| Cross-Origin-Resource-Policy | info | 5 | Kontrol resource yang boleh di-embed lintas origin |

## Cookie flags yang di-check

Untuk setiap Set-Cookie yang dikirim server:

- **HttpOnly**: JavaScript tidak bisa akses cookie. Mencegah pencurian via XSS. Warning kalau tidak ada.
- **Secure**: Cookie hanya dikirim via HTTPS. Mencegah leak via HTTP plaintext. Warning kalau tidak ada.
- **SameSite**: Kontrol pengiriman cookie saat cross-site request. Nilai Strict atau Lax untuk sebagian besar kasus. Info kalau tidak ada.

## Grading

Grade huruf ditentukan dari skor numerik:
- A: 90 sampai 100
- B: 75 sampai 89
- C: 60 sampai 74
- D: 45 sampai 59
- E: 30 sampai 44
- F: 0 sampai 29

Skor dihitung dari persentase bobot yang di-earn. Contoh: situs punya HSTS (20) + CSP (20) + X-Frame-Options (10) + X-Content-Type-Options (8) = 58 dari total 84 bobot = 69%. Skor 69, grade C.

Penalty tambahan untuk nilai lemah: HSTS tanpa max-age proper memotong setengah bobot HSTS. X-Content-Type-Options selain nosniff kasih warning tapi tidak potong bobot.

## Pengaturan

### timeout
Batas waktu maksimum (detik) fetch URL. Default 20.

### user_agent_rotation
Boolean dari Settings. Default mengikuti Settings. Beberapa WAF serve header berbeda untuk bot vs browser.

### proxy_rotation
Boolean dari Settings.

Tool ini tidak punya opsi khusus selain timeout. Semua bobot dan threshold saat ini di-hardcode berdasarkan best practice industri 2025.

## Tips akurasi

- **Scan URL yang punya cookie session**, bukan homepage static. Homepage biasanya tidak set cookie. Login-kan dulu (pakai Auth Vault), lalu scan halaman member area.

- **Pastikan target HTTPS**. Scanner tidak akan evaluasi HSTS dengan benar kalau URL-nya http://. HSTS memang hanya berarti di HTTPS.

- **Scan endpoint API juga**. Banyak tim hardening hanya frontend, lupa API. Scan `https://api.contoh.com/v1/ping` untuk lihat.

- **Bandingkan dengan scan sebelumnya** via History. Regresi header kadang terjadi saat redeploy karena konfigurasi server berubah tanpa sengaja.

## Troubleshooting

### Problem: Semua header hilang meski Anda yakin sudah set
**Gejala:** Grade F, semua 9 header missing. 
**Penyebab:** Server behind CDN yang strip header, atau konfigurasi nginx tidak apply ke path itu. 
**Solusi:** Cek di CDN dashboard apakah header forward policy benar. Test manual via `curl -I URL`.

### Problem: HSTS ada tapi masih dapat warning
**Gejala:** Grade turun karena HSTS. 
**Penyebab:** Value HSTS pakai max-age=0 (artinya non-aktif) atau tidak ada max-age sama sekali. 
**Solusi:** Set value ke `max-age=31536000; includeSubDomains; preload` untuk best practice.

### Problem: Cookie Secure warning tapi domain memang HTTP
**Gejala:** Situs HTTP, cookie tidak Secure, dapat warning. 
**Penyebab:** Expected, situs HTTP tidak boleh set Secure. 
**Solusi:** Migrasi ke HTTPS. Skenario HTTP legitimate di production sudah sangat jarang di 2026.

### Problem: CSP ada tapi dapat penalty
**Gejala:** Header CSP ditemukan tapi masih ada issue. 
**Penyebab:** Tool cek presence saja untuk CSP, tidak deep-validate directive. CSP validation kompleks dan butuh tool khusus. 
**Solusi:** Pakai CSP evaluator eksternal (misalnya Google CSP Evaluator) untuk deep check.

### Problem: Scan target di balik Cloudflare return hasil beda dari expected
**Gejala:** Header Anda set di origin tapi tool lihat header Cloudflare saja. 
**Penyebab:** Cloudflare override atau inject header. 
**Solusi:** Verify di Cloudflare dashboard apakah HTTP Response Header Modification rules aktif. Kadang Cloudflare strip HSTS kalau SSL mode Flexible.

### Problem: Cookie tidak terdeteksi padahal browser menyimpannya
**Gejala:** Tool report 0 cookies, padahal browser Network tab jelas ada Set-Cookie. 
**Penyebab:** Cookie di-set via JavaScript di client, bukan Set-Cookie header. 
**Solusi:** Tool ini hanya baca header. Cookie dari JS tidak terdeteksi. Kalau perlu audit, rewrite ke server-side Set-Cookie.

## Keamanan dan etika

> [!WARNING]
> Scanner ini adalah audit ringan. Hasil grade A tidak berarti situs "aman". Header bukan satu-satunya aspek keamanan. Tetap butuh pentest untuk evaluation komprehensif.

- Satu GET request per scan, footprint minimal di log server.
- Tool tidak probe vulnerability. Tidak test SQLi, XSS payload, atau path traversal. Itu domain pentest.
- Jangan publish hasil scan kompetitor sebagai "exposure". Info header adalah public-by-design, tapi etika tetap.

## Quick reference nilai header yang direkomendasikan

Berikut contoh nilai header yang umumnya dinilai aman untuk 2026. Sesuaikan dengan kebutuhan aplikasi Anda, terutama CSP yang harus spesifik per situs:

- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()`
- `Cross-Origin-Opener-Policy: same-origin`
- `Cross-Origin-Embedder-Policy: require-corp`
- `Cross-Origin-Resource-Policy: same-origin`

Perhatikan bahwa CSP yang terlalu ketat bisa break inline script dan style yang legit. Rollout bertahap dengan CSP-Report-Only dulu disarankan untuk situs besar.

## Related docs

- [SSL Certificate Inspector](ssl.md) - audit TLS certificate, complementary
- [Tech Fingerprinter](/docs/tools/tech-detector.md) - deteksi web server + framework untuk konteks header
- [SEO Auditor](seo.md) - audit on-page SEO
- [Broken Link Checker](broken-links.md) - validasi integritas link
- [Scheduled Jobs](/docs/system/scheduled.md) - jadwalkan scan security periodik
- [Webhooks](/docs/advanced/webhooks.md) - notify kalau grade turun
