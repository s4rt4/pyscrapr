# CAPTCHA Solver

> Integrasi dengan service 2Captcha dan Anti-Captcha untuk auto-solve reCAPTCHA v2/v3, hCaptcha, dan Cloudflare challenges yang muncul saat scraping target sensitif. Gunakan dengan bijak dan hanya pada situs yang sah Anda akses.

## Deskripsi

CAPTCHA Solver adalah fitur opsional yang mengaktifkan kemampuan PyScrapr melewati challenge-response automated-detection yang dipasang situs target. Ketika Harvester, Ripper, atau tool lain mengenali pattern CAPTCHA di HTML response, modul solver akan otomatis mengekstrak challenge data (seperti `site_key` untuk reCAPTCHA atau secret token untuk hCaptcha), mengirim ke service third-party yang memiliki pool manusia atau AI khusus, menunggu hasil token valid, lalu meng-inject token kembali ke form submission atau header request untuk melanjutkan scraping tanpa intervensi manual.

Implementasi di `services/captcha_solver.py` memakai abstract adapter pattern. Ada base class `CaptchaSolver` dengan method abstract `solve_recaptcha_v2(site_key, page_url)` dan `solve_hcaptcha(site_key, page_url)`. Dua konkret adapter di-provide: `AdapterTwoCaptcha` (wrapper 2captcha.com API) dan `AdapterAntiCaptcha` (wrapper anti-captcha.com API). Factory method memilih adapter sesuai setting `captcha_provider` dan menggunakan `captcha_api_key` yang Anda isi di Settings. Menambah provider baru seperti CapMonster atau DeathByCaptcha tinggal implement adapter baru dengan interface yang sama tanpa mengubah kode tool.

Heuristic detection berjalan di layer downloader. Setelah response HTML di-fetch, middleware scan body untuk pattern khas: string `g-recaptcha` atau `src="google.com/recaptcha"` untuk reCAPTCHA, `h-captcha` atau `hcaptcha.com/1/api.js` untuk hCaptcha, dan class name `cf-challenge` atau pesan "Please stand by, while we are checking your browser" untuk Cloudflare. Jika ter-detect, flow scraping dihentikan sementara, data CAPTCHA di-extract via regex atau DOM parse, solver dipanggil dengan site_key dan page_url, polling hasil setiap 5 detik sampai dapat token (typically 5-60 detik), lalu request di-retry dengan token baru ter-inject.

Legal disclaimer penting: fitur ini disediakan murni untuk penggunaan personal, edukasi, dan research ethical. CAPTCHA adalah mekanisme legitimate yang dipasang owner situs; membypass secara massal terhadap target tanpa izin dapat melanggar ToS atau hukum setempat (Computer Fraud and Abuse Act di US, UU ITE di Indonesia untuk konteks merugikan). PyScrapr tidak bertanggung jawab atas misuse. Gunakan solver hanya pada situs yang Anda miliki sendiri atau dengan izin eksplisit dari owner. Biaya service solver sendiri jadi friction natural: sekitar 2,99 USD per 1000 solve untuk 2Captcha, 2 USD per 1000 untuk Anti-Captcha, cukup murah untuk personal tapi accumulate cepat jika disalahgunakan massal. Ada endpoint `GET /api/vault/captcha/balance` untuk cek sisa saldo.

## Kapan pakai?

1. **Scraping situs milik sendiri yang memasang CAPTCHA** - Blog atau tool Anda sendiri dengan CAPTCHA anti-spam yang kebetulan menghalangi scraping legitimate untuk backup atau migrasi data.
2. **Research akademik dengan izin** - Penelitian yang sudah IRB-approved terhadap public data berCAPTCHA dengan dokumentasi legal yang lengkap.
3. **Otomasi account management** - Login ke service Anda sendiri yang memasang reCAPTCHA di form login untuk automation maintenance.
4. **Testing CAPTCHA implementation** - QA engineer yang butuh memastikan CAPTCHA di aplikasi sendiri berfungsi benar saat release testing.
5. **Bypass Cloudflare pada target dengan izin partner** - Situs partner yang mengaktifkan "I'm under attack" mode yang menghalangi crawler legitimate dari pihak yang berhak.
6. **Scheduled monitoring yang sesekali kena challenge** - Schedule harian yang jarang kena CAPTCHA tapi butuh auto-solve agar tidak break automation saat kebetulan terpicu.
7. **Data ingestion enterprise legal** - Kontrak data-sharing dengan penyedia yang menerapkan CAPTCHA untuk rate control bukan prevention.
8. **Demo scraping framework untuk edukasi** - Tutorial atau course tentang web scraping lengkap, termasuk handling CAPTCHA dengan konteks legal yang jelas.

## Cara penggunaan

1. Register akun di 2captcha.com atau anti-captcha.com. Proses verifikasi email biasanya cepat.
2. Top-up balance minimum (biasanya 5-10 USD), bisa via PayPal, kartu kredit, atau crypto.
3. Dari dashboard provider, copy API key di section "Account" atau "API".
4. Buka Settings > Advanced > CAPTCHA section di PyScrapr.
5. Pilih provider di dropdown `captcha_provider`: `twocaptcha` atau `anticaptcha`.
6. Paste API key ke field `captcha_api_key`. Key akan di-mask di UI untuk privasi.
7. Toggle `captcha_auto_solve` ke true untuk aktifkan auto-detection dan dispatch.
8. Klik "Save changes" di toolbar Settings.
9. Klik tombol "Test CAPTCHA" (jika tersedia) untuk submit test puzzle dan memverifikasi credential valid. Hasil sukses dalam 10-30 detik.
10. Cek saldo via endpoint `GET /api/vault/captcha/balance` atau dashboard provider. Balance harus ter-decrement setelah test.
11. Jalankan job pada target yang mengandung CAPTCHA. Observasi log server untuk indikator `CAPTCHA detected: recaptcha_v2` diikuti `CAPTCHA solved in 23s, cost $0.003`.
12. Monitor balance provider akun mingguan. Setiap solve decrement balance.
13. Jika banyak solve gagal, ganti tipe CAPTCHA priority di dashboard provider atau hubungi support.
14. Adjust timeout dan retry settings di advanced config jika default tidak cukup untuk tipe CAPTCHA spesifik (misalnya Enterprise).
15. Dokumentasikan use case dan target yang di-solve untuk compliance audit internal.

## Pengaturan / Konfigurasi

### captcha_provider
Enum `none`, `twocaptcha`, atau `anticaptcha`. Provider aktif. Default `none`. Rekomendasi: coba 2Captcha dulu untuk akurasi reCAPTCHA, Anti-Captcha untuk hCaptcha.

### captcha_api_key
String API key dari dashboard provider. Masked di UI. Default kosong. Treat as password; jangan commit ke Git.

### captcha_auto_solve
Boolean, enable auto-detection dan dispatch ke solver saat CAPTCHA terdeteksi. Default false. Aktifkan hanya setelah test credential sukses.

### captcha_timeout
Integer detik, max tunggu solve sebelum abort request. Default 120. Naikkan sampai 180 untuk Enterprise CAPTCHA yang lebih lambat.

### captcha_poll_interval
Integer detik, interval polling hasil ke provider. Default 5. Turunkan ke 3 untuk latency lebih rendah dengan overhead API call sedikit lebih banyak.

### captcha_max_retries
Integer, retry jika solve gagal (token invalid atau timeout). Default 2. Naikkan ke 3-4 untuk reliability di production.

### captcha_soft_fail
Boolean, jika true maka job lanjut tanpa CAPTCHA solved dengan warning log. Jika false, job abort. Default true. Untuk monitoring pipeline pakai true; untuk data-critical pakai false.

### captcha_types_enabled
Array tipe yang di-handle. Default `["recaptcha_v2", "hcaptcha", "cloudflare"]`. Kurangi ke tipe yang memang target hadapi untuk hindari false positive detection.

### captcha_fallback_manual
Boolean, jika solver gagal, prompt user untuk manual solve via UI modal. Default false. Aktifkan untuk interactive session, tidak cocok untuk automation overnight.

### captcha_detection_patterns
Object optional, custom regex untuk deteksi CAPTCHA baru yang belum di-support. Default built-in patterns. Edit untuk target yang pakai custom CAPTCHA.

### captcha_budget_usd
Float, soft limit total solve cost dalam USD. Default 10.0. Jika tercapai, webhook warning fires dan auto_solve di-disable sementara.

## Output / Efek

Solver tidak menghasilkan file tapi menghasilkan side-effect berikut:

- **Token terselesaikan** - Di-capture dan di-inject ke request; tidak di-persist di disk untuk keamanan.
- **Log entries** - Baris seperti `CAPTCHA detected: recaptcha_v2 on https://example.com/login` diikuti `Solved in 23s, cost $0.003`.
- **History field** - Detail job menampilkan `captcha_encounters: 2, captcha_solved: 2, captcha_cost: $0.006` untuk audit trail.
- **Balance update** - Akun provider ter-decrement; usage dashboard provider tracks detail per solve.
- **Warning webhook** - Jika budget tercapai, webhook warning fires ke channel yang configured.
- **Metric endpoint** - `GET /api/vault/captcha/balance` return `{balance_usd: 7.50, provider: "twocaptcha"}`.

## Integrasi dengan fitur lain

- **Downloader middleware** - Detection terjadi di layer HTTP client universal, jadi semua tool benefit otomatis.
- **Proxy Rotator** - Solve call menggunakan proxy yang sama dengan request original untuk konsistensi IP.
- **Webhooks** - Warning budget, report solve statistics, alert saat balance rendah.
- **Settings** - Konfigurasi terpusat termasuk provider selection dan budget tracking.
- **History** - Statistik per-job captcha encounters untuk audit dan cost analysis.
- **UA Rotation** - UA harus konsisten sepanjang solve agar token tetap valid di sisi target; sticky_per_job disarankan.

## Tips & Best Practices

1. **Mulai dengan small balance.** Test dulu dengan 5 USD sebelum top-up besar untuk memastikan setup bekerja dan provider cocok dengan tipe CAPTCHA target Anda.

2. **Monitor budget mingguan.** Solve cost accumulate cepat jika target sering challenge. Set `captcha_budget_usd` konservatif dan terima warning webhook untuk intervensi manual.

3. **Kombinasikan dengan proxy residential.** Target sering skip CAPTCHA untuk IP residential. Kombinasi residential proxy plus UA natural bisa mengurangi solve cost sampai 80 persen.

4. **Gunakan UA Rotation konsisten.** Ganti UA di tengah sesi memicu CAPTCHA baru. Sticky UA per job mengurangi encounters signifikan.

5. **Jangan enable pada target unknown.** Target agresif bisa spam CAPTCHA dan menguras balance. Test dulu satu job kecil untuk lihat frekuensi challenge.

6. **Review legal tiap target.** Solver pada situs tanpa izin berisiko hukum. Maintain daftar target yang Anda sudah punya izin untuk audit.

7. **Pakai captcha_soft_fail=true untuk monitoring pipeline.** Agar absence CAPTCHA solve tidak break pipeline data; log warning cukup untuk trigger investigasi manual.

8. **Log semua encounter.** Sebagai audit trail untuk compliance review, terutama jika ada tanya legal nanti.

9. **Rotate provider saat satu underperform.** Jika 2Captcha akurasi rendah di target spesifik, coba Anti-Captcha. Maintain akun di keduanya untuk failover manual.

10. **Jangan hardcode API key di script eksternal.** Selalu baca dari Settings atau environment variable agar mudah rotasi.

## Troubleshooting

### Problem: CAPTCHA terdeteksi tapi solver tidak dispatch
**Gejala:** Log menampilkan detection tapi tidak ada solve attempt.
**Penyebab:** `captcha_auto_solve=false` atau `captcha_provider=none`.
**Solusi:** Verifikasi Settings. Enable `captcha_auto_solve`. Pastikan provider sudah dipilih dan API key valid.

### Problem: Solve gagal dengan ERROR_WRONG_CAPTCHA
**Gejala:** Token di-submit tapi target reject dengan "captcha salah".
**Penyebab:** Site_key extraction salah, challenge expire sebelum submit, atau target rotate site_key.
**Solusi:** Kurangi `captcha_poll_interval` ke 3 detik. Update pattern extraction jika situs ubah struktur HTML.

### Problem: Balance provider nol tapi setting belum warn
**Gejala:** Solve gagal dengan "insufficient funds" padahal budget tracker tidak fires warning.
**Penyebab:** Budget tracking local out-of-sync dengan actual balance provider.
**Solusi:** Sinkronisasi manual via dashboard provider. Set `captcha_budget_usd` lebih konservatif (misalnya separuh dari top-up).

### Problem: Token solve valid tapi target tetap 403
**Gejala:** Solver return sukses, tapi request dengan token tetap ditolak.
**Penyebab:** Target juga cek cookie atau fingerprint lain selain CAPTCHA token.
**Solusi:** Handle cookies jar manual, persist session antar request. Kombinasikan dengan browser-cookie3 import untuk pakai cookies dari browser real.

### Problem: Timeout walau provider tidak terlalu lambat
**Gejala:** Log timeout padahal dashboard provider menunjukkan solve sukses.
**Penyebab:** Polling interval terlalu panjang, miss window completion.
**Solusi:** Turunkan `captcha_poll_interval` ke 3-5 detik.

### Problem: Cloudflare challenge tidak terdeteksi
**Gejala:** Response HTML berisi Cloudflare page tapi tidak ada detection log.
**Penyebab:** Pattern detection tidak match (Cloudflare sering update template).
**Solusi:** Update `captcha_detection_patterns` dengan regex terbaru atau tambahkan class name yang Cloudflare gunakan saat ini.

### Problem: Cost per solve lebih tinggi dari iklan
**Gejala:** Usage dashboard menunjukkan charge lebih tinggi dari harga standar.
**Penyebab:** Tipe CAPTCHA spesifik (reCAPTCHA v3, hCaptcha Enterprise) charge premium.
**Solusi:** Verifikasi breakdown di dashboard provider. Pertimbangkan provider berbeda untuk tipe spesifik.

### Problem: API key invalid error walau baru dibuat
**Gejala:** Error 401 dari provider pada request pertama.
**Penyebab:** Key belum activated (butuh top-up minimum), atau paste dengan whitespace trailing.
**Solusi:** Cek dashboard provider apakah key active dan balance sufficient. Re-copy tanpa whitespace.

### Problem: Concurrent solve menggantung semua request
**Gejala:** Banyak job stuck di "awaiting CAPTCHA" bersamaan.
**Penyebab:** Provider rate limit concurrent solve per account.
**Solusi:** Serialkan solve di ProxyManager level. Upgrade plan provider jika butuh parallel solve tinggi.

### Problem: Solve sukses tapi selanjutnya masih CAPTCHA lagi
**Gejala:** Loop tak berujung dari solve-retry-solve.
**Penyebab:** Target mendeteksi bot melalui signal lain dan re-challenge setelah solve pertama.
**Solusi:** Kombinasikan dengan proxy residential dan UA rotation. Pertimbangkan headless browser untuk target sophisticated.

## FAQ

**Q: Legal di Indonesia pakai CAPTCHA solver?**
A: Belum ada regulasi eksplisit, namun dapat melanggar ToS target dan UU ITE jika tujuannya merugikan. Konsultasi hukum untuk use case komersial atau publik.

**Q: Apakah solver aman dan tidak leak data?**
A: Provider legitimate tidak menyimpan challenge content lama (mereka punya retention policy). Namun data transit via service pihak ketiga; hindari jika target mengandung sensitive info.

**Q: Berapa akurasi solve?**
A: 2Captcha klaim 95 persen plus; Anti-Captcha 97 persen plus. reCAPTCHA v3 dan hCaptcha Enterprise lebih rendah sekitar 85 persen.

**Q: Bisa offline atau self-host solver?**
A: PyScrapr tidak support self-host AI solver built-in. Bisa integrate via adapter custom jika Anda punya model sendiri.

**Q: Apakah Google atau hCaptcha bisa deteksi solver?**
A: Ya, mereka evolusi terus. Solver populer kadang ter-flag. Kombinasikan dengan fingerprinting sophisticated dan residential proxy.

**Q: Bisa pakai kedua provider sekaligus untuk failover?**
A: Tidak default (satu aktif). Butuh code fork untuk chain failover antar provider.

**Q: Bagaimana handle CAPTCHA baru yang belum ter-support?**
A: Update `captcha_types_enabled` dan tambahkan adapter logic untuk tipe baru. Atau submit ke "normal CAPTCHA" image recognition API.

**Q: Apakah solver bekerja di Media Downloader (yt-dlp)?**
A: Tidak langsung. yt-dlp punya mekanisme sendiri untuk YouTube age gate, tidak melalui PyScrapr solver.

**Q: Bagaimana jika target pasang custom CAPTCHA non-standard?**
A: Butuh pattern extraction custom dan submit via "normal CAPTCHA" API provider (image recognition dengan screenshot).

**Q: Apakah solve cost bisa di-claim pajak?**
A: Tergantung yurisdiksi dan purpose. Konsultasi akuntan.

**Q: Berapa concurrent solve yang aman?**
A: Provider basic plan biasanya 10-20 concurrent. Upgrade ke plan lebih tinggi untuk volume produksi.

**Q: Bagaimana cek saldo tanpa buka dashboard?**
A: Endpoint `GET /api/vault/captcha/balance` return saldo real-time dari provider aktif.

## Keterbatasan

- Tidak support semua tipe CAPTCHA; terbatas pada reCAPTCHA v2/v3, hCaptcha, dan Cloudflare basic.
- Biaya akumulatif bisa mahal untuk volume besar.
- Dependency pada service eksternal; provider downtime berarti scraping stop.
- Legal gray area di banyak yurisdiksi.
- Detection heuristic bisa false positive atau false negative.
- Tidak ada local atau offline solver option.
- Concurrent solve limited oleh plan provider.
- Custom CAPTCHA non-standard butuh manual integration code.
- yt-dlp tidak terintegrasi dengan solver PyScrapr.
- Tidak ada failover antar provider otomatis.

## Studi kasus penggunaan nyata

**Skenario 1: Monitoring harga produk di marketplace dengan CAPTCHA sesekali.** Pengguna tracking harga 100 produk di satu marketplace besar. Marketplace kadang munculkan reCAPTCHA v2 saat akses agresif (sekitar 5 persen request). Dengan 2Captcha integration dan `captcha_soft_fail=true`, job tetap berjalan; request yang CAPTCHA di-solve otomatis dalam 20 detik rata-rata, request lain lanjut normal. Cost solve: sekitar 15 sen per run harian, masih murah untuk value data yang didapat.

**Skenario 2: Login automation ke tool internal.** Company tool lama pakai reCAPTCHA v2 di form login sebagai anti-spam. QA engineer butuh automation test login flow 20 kali per deploy. Anti-Captcha di-integrate untuk auto-solve CAPTCHA saat test run. Solve cost 0.02 USD per 10 test = 0.002 USD per test, ekonomis untuk CI/CD.

**Skenario 3: Archive public government data.** Situs government buka data publik tapi pasang reCAPTCHA untuk rate control. Researcher butuh scrape 50000 halaman arsip publik. Izin dari government sudah ada tertulis. Budget CAPTCHA: 50000 * 0.003 = 150 USD total, dikerjakan selama 2 minggu dengan scheduled overnight. Hasil: dataset siap untuk analisis.

**Skenario 4: Bypass Cloudflare partner site.** Partner B2B pasang Cloudflare "I'm under attack" mode yang memicu challenge ke semua request. Agreement sudah mengizinkan scraping. Anti-Captcha plugin untuk Cloudflare challenge di-enable, solve rate 90 persen, sisanya retry. Job stable running daily.

**Skenario 5: Test CAPTCHA implementation sendiri.** Tim developer baru implement reCAPTCHA di form kontak situs company. Pakai 2Captcha untuk automated test bahwa CAPTCHA benar-benar protect endpoint (submission tanpa token valid di-reject, submission dengan token di-accept). Biaya test suite per deploy: 0.30 USD, nominal untuk dev workflow.

## Ethical considerations dan best practices legal

Penggunaan CAPTCHA solver berada di area gray secara legal dan ethical. Berikut pedoman yang disarankan:

1. **Dapatkan izin tertulis.** Sebelum solve CAPTCHA di situs pihak ketiga, pastikan ada perjanjian atau minimal response positif dari admin situs. Screenshot email untuk audit trail.

2. **Hormati rate limit situs.** CAPTCHA muncul biasanya karena rate terlalu tinggi. Solver bukan lisensi untuk scraping agresif; pelan-pelan lebih sopan.

3. **Jangan target situs yang explicit melarang.** Robots.txt dan ToS yang eksplisit melarang automated access harus dihormati meski secara teknis Anda bisa bypass.

4. **Disclosure di research paper.** Untuk academic research, disclose metodologi termasuk penggunaan solver di paper. Reviewer akademik menghargai transparansi.

5. **Budget conservative.** High-volume solving adalah red flag buat abuse. Personal use biasanya di bawah 100 solve per hari.

6. **Hindari login automation di akun orang lain.** Automate login ke akun milik Anda sendiri OK; automate login ke akun orang lain (bahkan kerabat) problematik secara legal dan etik.

## Perbandingan provider CAPTCHA

Tidak semua provider sama. Berikut perbandingan quick antara 2Captcha dan Anti-Captcha untuk membantu memilih:

| Aspek | 2Captcha | Anti-Captcha |
|-------|----------|--------------|
| Harga reCAPTCHA v2 | 2.99 USD per 1000 | 2.00 USD per 1000 |
| Harga hCaptcha | 2.99 USD per 1000 | 2.00 USD per 1000 |
| Harga reCAPTCHA v3 | 2.99 USD per 1000 | 2.00 USD per 1000 |
| Avg solve time v2 | 15-30 detik | 10-25 detik |
| Akurasi claim | 95 persen plus | 97 persen plus |
| API dokumentasi | Sangat lengkap | Lengkap |
| Minimum top-up | 1 USD | 1 USD |
| Support payment | PayPal, crypto, kartu | PayPal, crypto, kartu |
| Concurrent solve basic | 60 | 100 |

Rekomendasi: coba Anti-Captcha dulu untuk cost efficiency. Fallback ke 2Captcha untuk target spesifik yang akurasi Anti-Captcha rendah. Maintain akun di keduanya untuk failover manual saat satu provider outage.

## Integrasi custom provider

PyScrapr support menambah provider lain selain 2Captcha dan Anti-Captcha. Pattern integrasi:

1. **Create new adapter class.** Inherit dari `CaptchaSolver` base class di `services/captcha_solver.py`.
2. **Implement method abstract.** `solve_recaptcha_v2(site_key, page_url)` dan `solve_hcaptcha(site_key, page_url)` dengan logic panggil API provider.
3. **Register di factory.** Tambah case di factory method yang instantiate adapter berdasarkan `captcha_provider` setting.
4. **Update enum setting.** Tambah value baru di `captcha_provider` enum di Pydantic schema settings.
5. **Test dengan sample.** Run test unit dengan mock API response sebelum production use.

Provider alternatif yang bisa diintegrasi: CapMonster (AI-based, lebih murah untuk reCAPTCHA v3), DeathByCaptcha (pionir industri, stable), atau self-hosted seperti Buster browser extension (free tapi perlu browser real).

## Monitoring cost dan budget management

CAPTCHA cost bisa membengkak jika tidak di-monitor. Strategi manage budget:

1. **Dashboard provider check harian.** Login ke dashboard provider, cek spending hari sebelumnya. Spike tiba-tiba = investigate target baru atau bug.

2. **Webhook alert budget threshold.** Set `captcha_budget_usd` konservatif (50 persen dari top-up). Webhook fires saat reach, manual top-up atau pause job.

3. **Per-job cost tracking.** History detail job tampilkan `captcha_cost`. Identify job dengan cost tinggi untuk tuning (misalnya target yang challenge 5 kali per URL).

4. **Cap per-batch.** Di Bulk Queue, bisa tambah field `max_captcha_cost` yang abort batch saat total cost tercapai.

5. **Monthly report.** Generate laporan bulanan CAPTCHA spending by target domain untuk business justification atau optimisasi.

6. **Switch provider saat rate naik.** Jika target ganti tipe CAPTCHA ke Enterprise yang lebih mahal (10-20 USD per 1000), evaluate apakah still worth. Mungkin cari alternative data source.

## Related docs

- [Proxy](/docs/advanced/proxy.md) - Kombinasi untuk mengurangi CAPTCHA encounters.
- [UA Rotation](/docs/advanced/ua-rotation.md) - Konsistensi UA saat solve agar token valid.
- [Settings](/docs/system/settings.md) - Section CAPTCHA untuk konfigurasi provider.
- [Webhooks](/docs/advanced/webhooks.md) - Alert budget dan balance rendah.
- [Vault](/docs/utilities/vault.md) - Endpoint balance dan secret storage.
