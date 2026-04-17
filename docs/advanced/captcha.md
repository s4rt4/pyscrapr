# CAPTCHA Solver

> Integrasi dengan service 2Captcha dan Anti-Captcha untuk auto-solve reCAPTCHA, hCaptcha, dan Cloudflare challenges yang muncul saat scraping.

## Deskripsi

CAPTCHA Solver adalah fitur opsional yang mengaktifkan kemampuan PyScrapr untuk melewati challenge-response automated-detection yang dipasang situs target. Ketika Harvester, Ripper, atau tool lain mengenali pattern CAPTCHA di HTML response, modul solver akan otomatis mengekstrak challenge data (site_key untuk reCAPTCHA, secret token untuk hCaptcha), mengirim ke service third-party yang memiliki pool manusia atau AI khusus, menunggu hasil token valid, lalu inject token kembali ke form submission atau header request untuk melanjutkan scraping.

Implementasi di `services/captcha_solver.py` memakai abstract adapter pattern. Ada base class `CaptchaSolver` dengan method abstract `solve_recaptcha(site_key, url)` dan `solve_hcaptcha(site_key, url)`. Dua konkret adapter di-provide: `TwoCaptchaAdapter` (wrap 2captcha.com API) dan `AntiCaptchaAdapter` (wrap anti-captcha.com API). Factory method memilih adapter sesuai setting `captcha_provider` dan menggunakan `captcha_api_key` yang Anda isi di Settings. Menambah provider baru (CapMonster, DeathByCaptcha) tinggal implement adapter baru dengan interface sama.

Heuristic detection berjalan di layer downloader. Setelah GET response HTML, middleware scan body untuk pattern khas: script `src="google.com/recaptcha"` untuk reCAPTCHA, `hcaptcha.com/1/api.js` untuk hCaptcha, dan `Please stand by, while we are checking your browser` untuk Cloudflare. Jika detected, flow scraping dihentikan sementara, CAPTCHA data di-extract via regex/DOM parse, solver dipanggil, dan request di-retry dengan token baru. Proses ini biasanya memakan 10-60 detik tergantung kompleksitas challenge dan load service solver.

Peringatan legal penting: fitur ini disediakan murni untuk penggunaan personal/edukasi dan research ethical. CAPTCHA adalah mekanisme legitimate yang dipasang owner situs; membypassnya secara massal terhadap target tanpa izin dapat melanggar ToS atau hukum setempat (Computer Fraud and Abuse Act di US, contohnya). PyScrapr tidak bertanggung jawab atas misuse. Gunakan solver hanya pada situs yang benar-benar Anda miliki, atau dengan izin eksplisit owner. Biaya service solver pun jadi friction natural: sekitar $2-3 per 1000 solve untuk 2Captcha, $2 untuk Anti-Captcha, cukup murah untuk personal tapi accumulate cepat untuk abuse massal.

## Kapan pakai?

1. **Scraping situs milik sendiri yang pasang CAPTCHA** — Blog/tool Anda sendiri dengan CAPTCHA anti-spam yang kebetulan menghalangi scraping legitimate.
2. **Research akademik dengan izin** — Penelitian yang sudah IRB-approved terhadap public data berCAPTCHA.
3. **Otomasi account management** — Login ke service sendiri yang pasang reCAPTCHA di login form.
4. **Testing CAPTCHA implementation** — QA engineer yang butuh test bahwa CAPTCHA berfungsi benar di aplikasi sendiri.
5. **Bypass Cloudflare pada target dengan izin** — Situs partner yang ada Cloudflare "I'm under attack" mode menghalangi legitimate crawler.
6. **Scheduled monitoring yang kadang kena challenge** — Schedule harian yang sesekali kena CAPTCHA butuh auto-solve agar tidak break automation.
7. **Data ingestion enterprise legal** — Kontrak data-sharing dengan penyedia yang implement CAPTCHA untuk rate control, bukan prevention.
8. **Demo scraping framework untuk edukasi** — Tutorial/course tentang web scraping lengkap termasuk handling CAPTCHA.

## Cara penggunaan

1. Register akun di 2captcha.com atau anti-captcha.com dan top-up balance (minimum biasanya $5-10).
2. Dari dashboard provider, copy API key.
3. Buka Settings > Advanced > CAPTCHA section.
4. Pilih provider di dropdown `captcha_provider`: `twocaptcha` atau `anticaptcha`.
5. Paste API key ke field `captcha_api_key`.
6. Toggle `captcha_auto_solve` ke true untuk aktifkan auto-detection dan solve.
7. Klik "Save changes".
8. Klik tombol "Test CAPTCHA" (jika tersedia) untuk submit test puzzle dan verify credential valid.
9. Jalankan job pada target yang mengandung CAPTCHA. Observe log untuk indikator "CAPTCHA detected" diikuti "CAPTCHA solved in Xs".
10. Monitor balance provider akun. Setiap solve decrement balance.
11. Jika banyak solve gagal, ganti tipe CAPTCHA priority atau hubungi support provider.
12. Adjust timeout dan retry settings di advanced config jika default tidak cukup.

## Pengaturan / Konfigurasi

Field Settings > CAPTCHA section:

- **captcha_provider** (enum `none`, `twocaptcha`, `anticaptcha`, default `none`) — Provider aktif.
- **captcha_api_key** (string, encrypted at rest) — API key dari provider dashboard.
- **captcha_auto_solve** (boolean, default false) — Enable auto-detection dan dispatch.
- **captcha_timeout** (int detik, default 120) — Max tunggu solve sebelum abort.
- **captcha_poll_interval** (int detik, default 5) — Interval polling hasil ke provider.
- **captcha_max_retries** (int, default 2) — Retry jika solve gagal.
- **captcha_soft_fail** (boolean, default true) — Jika true, lanjut job tanpa CAPTCHA solved (log warning). Jika false, abort job.
- **captcha_types_enabled** (array, default `["recaptcha_v2", "hcaptcha", "cloudflare"]`) — Tipe yang di-handle.
- **captcha_fallback_manual** (boolean, default false) — Jika solver fail, prompt user manual solve via UI.
- **captcha_detection_patterns** (object, optional) — Custom regex untuk detect CAPTCHA baru.
- **captcha_budget_usd** (float, default 10.0) — Soft limit total solve cost; warning jika tercapai.

## Output

Solver tidak menghasilkan file tapi side-effect sebagai berikut:

- **Token terselesaikan** — Dicapture dan di-inject ke request; tidak di-persist di disk.
- **Log entries** — `CAPTCHA detected: recaptcha_v2 on https://example.com/login` diikuti `Solved in 23s, cost $0.003`.
- **History field** — Job detail menampilkan `captcha_encounters: 2, captcha_solved: 2, captcha_cost: $0.006`.
- **Balance update** — Akun provider decrement; usage dashboard provider tracks.
- **Warning** — Jika budget tercapai, webhook warning fires.

## Integrasi dengan fitur lain

- **Downloader middleware** — Detection terjadi di layer HTTP client.
- **Proxy Rotator** — Solve pakai proxy yang sama dengan request originalnya.
- **Webhooks** — Warning budget, report solve statistics.
- **Settings** — Config terpusat.
- **History** — Statistik per-job captcha encounters.
- **UA Rotation** — Harus konsisten UA saat solve agar token valid.

## Tips & Best Practices

1. **Mulai dengan small balance** — Test dulu $5 sebelum top-up besar untuk pastikan setup bekerja.
2. **Monitor budget mingguan** — Solve accumulate cepat jika target sering challenge.
3. **Kombinasikan dengan proxy residential** — Target sering skip CAPTCHA untuk IP residential, kurangi solve cost.
4. **Gunakan UA Rotation konsisten** — Ganti UA tengah sesi picu CAPTCHA; sticky UA reduce encounters.
5. **Jangan enable pada target unknown** — Bisa surprise bill jika target agresif spam CAPTCHA.
6. **Review legal setiap target** — Solver pada situs tanpa izin berisiko legal.
7. **Pakai captcha_soft_fail=true untuk monitoring** — Agar absence CAPTCHA solve tidak break pipeline data.
8. **Log semua encounter** — Sebagai audit trail untuk compliance review.

## Troubleshooting

**Problem: CAPTCHA terdeteksi tapi solver tidak dispatch.**
Cause: `captcha_auto_solve=false` atau provider=none.
Solution: Verify Settings. Enable auto_solve.

**Problem: Solve gagal dengan "ERROR_WRONG_CAPTCHA".**
Cause: Site_key extraction salah, atau challenge expire sebelum solve submit.
Solution: Kurangi `captcha_poll_interval`. Update pattern extraction jika situs ubah struktur.

**Problem: Balance provider nol tapi setting belum warn.**
Cause: Budget tracking local out-of-sync dengan actual provider balance.
Solution: Sinkronisasi manual via dashboard provider. Set budget lebih konservatif.

**Problem: Token solve valid tapi target tetap 403.**
Cause: Target juga cek cookie atau fingerprint lain selain CAPTCHA token.
Solution: Handle cookies jar manual. Kombinasikan dengan browser-cookie3 import.

**Problem: Timeout walau provider tidak terlalu lambat.**
Cause: Polling interval terlalu panjang, miss window completion.
Solution: Turunkan `captcha_poll_interval` ke 3-5s.

**Problem: Cloudflare challenge tidak terdeteksi.**
Cause: Pattern detection tidak match HTML (Cloudflare sering update template).
Solution: Update `captcha_detection_patterns` dengan regex terbaru.

**Problem: Cost per solve lebih tinggi dari iklan.**
Cause: Tipe CAPTCHA spesifik (reCAPTCHA v3, hCaptcha Enterprise) charge premium.
Solution: Verify dengan dashboard provider. Pertimbangkan provider berbeda untuk tipe spesifik.

**Problem: API key invalid error walau baru buat.**
Cause: Key belum activated (butuh top-up minimum), atau salah paste.
Solution: Cek dashboard provider apakah key active. Re-copy tanpa whitespace trailing.

**Problem: Concurrent solve menggantung semua request.**
Cause: Provider rate limit concurrent solve per account.
Solution: Serialkan solve di ProxyManager level. Upgrade plan provider jika butuh parallel.

## FAQ

**Q: Legal di Indonesia pakai CAPTCHA solver?**
A: Belum ada regulasi eksplisit, namun dapat melanggar ToS target dan UU ITE jika untuk tujuan merugikan. Konsultasi hukum untuk use case komersial.

**Q: Apakah solver aman (tidak leak data)?**
A: Provider legitimate tidak menyimpan challenge content lama. Namun data transit via service — hindari jika target mengandung sensitive info.

**Q: Berapa akurasi solve?**
A: 2Captcha claim 95%+; Anti-Captcha 97%+. reCAPTCHA v3 dan hCaptcha Enterprise lebih rendah (~85%).

**Q: Bisa offline/self-host solver?**
A: PyScrapr tidak support self-host AI solver built-in. Bisa integrate via adapter custom.

**Q: Apakah Google/hCaptcha bisa deteksi solver?**
A: Ya, mereka evolusi terus. Solver populer kadang ter-flag; pakai kombinasi dengan fingerprinting sophisticated.

**Q: Bisa pakai kedua provider sekaligus untuk failover?**
A: Tidak default (satu aktif). Butuh code fork untuk chain failover.

**Q: Bagaimana handle CAPTCHA baru yang belum ter-support?**
A: Update `captcha_types_enabled` dan tambah adapter logic untuk tipe baru.

**Q: Apakah solver bekerja di Media Downloader (yt-dlp)?**
A: Tidak langsung. yt-dlp punya mekanisme sendiri untuk YouTube age gate, tidak terkait.

**Q: Bagaimana jika target pasang custom CAPTCHA (bukan reCAPTCHA)?**
A: Butuh pattern extraction custom dan submit via "normal CAPTCHA" API provider (image recognition).

**Q: Apakah solve cost bisa di-claim tax?**
A: Tergantung yurisdiksi dan purpose. Consultasi akuntan.

## Keterbatasan

- Tidak support semua tipe CAPTCHA (terbatas reCAPTCHA v2/v3, hCaptcha, Cloudflare basic).
- Biaya akumulatif bisa mahal untuk volume besar.
- Dependency pada service eksternal (downtime = scraping stop).
- Legal gray area di banyak yurisdiksi.
- Detection heuristic bisa false positive/negative.
- Tidak ada local/offline solver option.
- Concurrent solve limited oleh provider plan.
- Custom CAPTCHA (non-standard) butuh manual integration.

## Related docs

- [Proxy](./proxy.md) — Kombinasi untuk reduce CAPTCHA encounters.
- [UA Rotation](./ua-rotation.md) — Konsistensi UA saat solve.
- [Settings](../system/settings.md) — Section CAPTCHA config.
- [Webhooks](./webhooks.md) — Warning budget alerts.
