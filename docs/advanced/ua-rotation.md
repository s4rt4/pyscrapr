# User-Agent Rotation

> Sistem rotasi User-Agent dengan 6 profil browser lengkap (header set utuh, bukan hanya UA string) untuk menyamarkan fingerprint request dan menghindari deteksi bot sederhana.

## Deskripsi

User-Agent Rotation adalah strategi menyamarkan identitas client HTTP dengan mengganti header `User-Agent` dan header browser-pendukung lain secara sistematis antar request. Target situs sering memakai header ini sebagai salah satu sinyal pembeda "ini browser asli" vs "ini bot python-requests". Dengan UA rotation, tiap request keluar dengan signature yang terlihat seperti browser populer (Chrome Windows, Firefox Mac, Safari iPhone, dll), sehingga pattern scraping tidak mudah di-fingerprint oleh rule-based bot detection.

Implementasi di PyScrapr tidak sekadar random-pick dari list 10 UA string seperti library pemula. Kami menggunakan profil "full header set" — artinya tiap profil browser membawa satu set header lengkap yang konsisten: `User-Agent`, `Accept`, `Accept-Language`, `Accept-Encoding`, `Sec-CH-UA` (Chromium hints), `Sec-CH-UA-Mobile`, `Sec-CH-UA-Platform`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site`, `Sec-Fetch-User`, dan `Upgrade-Insecure-Requests`. Mengapa? Karena bot detection modern seperti Cloudflare Bot Management membandingkan konsistensi antar-header. UA bilang "Chrome 120 Windows" tapi `Sec-CH-UA-Platform` bilang "macOS" → langsung flagged. Profil full-header di PyScrapr memastikan internal consistency per browser.

Enam profil yang ter-bundled: `chrome_win` (Chrome terbaru di Windows 10/11), `chrome_mac` (Chrome di macOS Sonoma), `firefox_win` (Firefox di Windows), `firefox_linux` (Firefox di Ubuntu), `safari_mac` (Safari di macOS), dan `edge_win` (Edge di Windows). Tiap profil di-update manual secara berkala untuk reflect versi browser terkini (maintenance team PyScrapr update saat Chrome/Firefox mayor release). Jika Anda punya kebutuhan khusus (misal Chrome Android), Anda bisa tambah profil custom via modifikasi `services/ua_profiles.json`.

Mode rotasi dikontrol oleh setting `ua_mode`: `random` (pilih acak per request), `round_robin` (cycle sequential), `specific:<profile_name>` (force satu profil), atau `off` (pakai default httpx/requests UA yang identifiable sebagai library). Integrasi dilakukan di class `Downloader` via method `_rotated_headers()` yang dipanggil sebelum tiap `httpx.get/post`, memastikan semua tool yang subclass Downloader otomatis benefit tanpa code change.

## Kapan pakai?

1. **Scraping target dengan bot detection ringan** — Rule-based detection yang hanya cek UA akan mudah di-bypass dengan rotation.
2. **Menghindari rate limit per-UA** — Beberapa CDN rate limit berdasarkan UA string, rotate UA = bypass.
3. **Testing responsive design** — Scrape versi mobile dengan UA safari_ios atau chrome_android (custom profile).
4. **Avoid honeypot UA** — Default httpx UA terkenal di blocklist, rotate menghilangkan risiko ini.
5. **Kombinasi dengan Proxy** — UA rotation tanpa proxy = IP sama tapi UA beda (suspect); kombinasi = signature fully variabel.
6. **Long-running scheduled jobs** — Tiap fire pakai UA berbeda sehingga pattern traffic lebih natural across time.
7. **Multi-geographic simulation** — Kombinasi profil OS berbeda simulate user dari region berbeda.
8. **Research fingerprinting** — Test sejauh mana fingerprinting target sophisticated dengan observasi rotasi vs static.

## Cara penggunaan

1. Buka Settings > Advanced > UA Rotation section.
2. Dropdown `ua_mode`: pilih mode. `random` untuk beginner, `round_robin` untuk predictable, `specific:chrome_win` untuk lock, `off` untuk disable.
3. Jika `specific`, pilih profil dari dropdown `ua_specific_profile`.
4. Toggle `ua_include_sec_ch_headers` untuk full-set (default true). Disable untuk minimal UA only jika target legacy yang confused dengan Sec-CH.
5. Review field `ua_exclude_profiles` — list profil yang di-skip. Misal exclude `safari_mac` jika target reject Safari.
6. Klik "Save changes".
7. Test via tombol "Test UA" (jika tersedia) yang hit httpbin.org/headers untuk verify headers sent.
8. Jalankan job sample. Log akan menampilkan `Selected UA profile: chrome_win` per request.
9. Monitor target response — seharusnya tidak lagi langsung block request yang sebelumnya di-block.
10. Fine-tune exclude list berdasarkan behavior target.
11. Untuk sticky per session, enable `ua_sticky_per_job` agar satu job pakai profil tetap (bukan rotate per request).
12. Jika target sangat sophisticated, kombinasikan dengan proxy residential dan cookies handling.

## Pengaturan / Konfigurasi

Field Settings > UA Rotation section:

- **ua_mode** (enum `off`, `random`, `round_robin`, `specific`, default `random`) — Strategi rotasi.
- **ua_specific_profile** (string, conditional) — Profil force jika mode specific.
- **ua_include_sec_ch_headers** (boolean, default true) — Include Sec-CH-UA* headers.
- **ua_include_sec_fetch_headers** (boolean, default true) — Include Sec-Fetch-* headers.
- **ua_exclude_profiles** (array string, optional) — Profile names untuk skip.
- **ua_sticky_per_job** (boolean, default false) — Konsistensi per job vs per request.
- **ua_custom_profiles** (object, optional) — Profile custom yang di-append ke built-in 6.
- **ua_chrome_version_override** (string, optional) — Lock Chrome ke versi spesifik (jika butuh stable fingerprint).
- **ua_randomize_language** (boolean, default false) — Randomize Accept-Language antar `en-US`, `id-ID`, dll.
- **ua_platform_order** (array, optional) — Urutan round_robin mulai dari platform tertentu.
- **ua_refresh_profiles_url** (string URL, optional) — Jika diset, auto-fetch updated profiles dari URL remote (advanced, self-hosted profile service).

## Output

Tidak ada file output. Observable behavior:

- **Headers terkirim** — Tiap request carry full profile header set.
- **Log line** — `UA: chrome_win (v120.0.6099.130) selected for https://example.com/`.
- **Response behavior** — Target seharusnya tidak lagi block, atau block dengan pola berbeda.
- **Fingerprint consistency** — Verify via `webrtc-fingerprint.com` atau httpbin.org/headers.

## Integrasi dengan fitur lain

- **Downloader base class** — Semua tool HTTP consume via `_rotated_headers`.
- **Proxy Rotator** — Kombinasi untuk signature variation penuh.
- **CAPTCHA Solver** — UA harus konsisten selama solve; sticky_per_job=true disarankan.
- **Media Downloader** — yt-dlp accept header_set override via `http_headers`.
- **Settings** — Section UA Rotation.
- **Site Ripper** — Asset download pakai UA konsisten dengan HTML request.

## Tips & Best Practices

1. **Pakai sticky_per_job untuk e-commerce** — Session-based detection akan suspicious dengan UA change mid-session.
2. **Random per-request untuk crawl besar** — Ripper dengan ribuan pages benefit dari variasi tinggi.
3. **Exclude profil yang tidak relevan** — Jika target hanya support Chrome, exclude Firefox/Safari.
4. **Kombinasikan dengan proxy** — IP + UA diversity > hanya salah satu.
5. **Update profiles rutin** — Browser version lama (Chrome 100) mencolok di 2026.
6. **Hindari UA eksotis** — Profile obscure (browser mining coin) lebih mencolok daripada common Chrome.
7. **Test fingerprint di target** — Beberapa target cek TLS fingerprint juga, yang tidak tercover UA rotation.
8. **Log profil per-job** — Audit trail mana profil paling sering ter-block untuk tuning.

## Troubleshooting

**Problem: Request tetap block walaupun UA rotation aktif.**
Cause: Target cek sinyal lain (TLS fingerprint, behavior, JS execution).
Solution: Kombinasikan dengan Proxy, atau pakai headless browser (outside PyScrapr scope).

**Problem: Sec-CH-UA header value tidak match target expectation.**
Cause: Target Expect `Sec-CH-UA-Full-Version-List` yang belum di-implement di profile.
Solution: Update profile JSON dengan header tambahan. Atau disable sec_ch_headers jika legacy target.

**Problem: yt-dlp tidak pakai UA rotation.**
Cause: yt-dlp punya internal UA yang override kecuali explicit set.
Solution: Verify `ydl_opts["http_headers"]` di-populate dari UA rotator.

**Problem: Round_robin selalu pick profil sama.**
Cause: Counter state tidak persistent setelah restart.
Solution: Accept behavior (random on startup then sequential). Atau pakai mode random.

**Problem: Custom profile tidak di-load.**
Cause: JSON syntax error di `ua_custom_profiles`.
Solution: Validate JSON. Restart server untuk reload.

**Problem: Accept-Language selalu en-US walau target Indonesia.**
Cause: Default profile header en-US; target mungkin serve konten berbeda.
Solution: Enable `ua_randomize_language` atau override profile Accept-Language.

**Problem: Memory usage naik setelah lama rotate.**
Cause: Connection pool tidak reuse karena header berbeda per request.
Solution: Enable sticky_per_job untuk pool reuse. Atau accept overhead untuk security.

**Problem: Target deteksi "User-Agent doesn't match TLS".**
Cause: UA claim Chrome, tapi httpx library TLS fingerprint berbeda dengan real Chrome.
Solution: Gunakan `curl_cffi` library yang fake TLS fingerprint (butuh integration code).

**Problem: Profile list di UI kosong.**
Cause: File `services/ua_profiles.json` corrupt atau path salah.
Solution: Restore dari backup. Verifikasi file exist di app directory.

## FAQ

**Q: Apakah UA rotation cukup untuk bypass semua bot detection?**
A: Tidak. Cloudflare, Akamai, PerimeterX butuh kombinasi proxy + UA + TLS fingerprint + JS execution.

**Q: Bisa tambah profile Android/iOS?**
A: Ya via `ua_custom_profiles` atau edit `ua_profiles.json` langsung.

**Q: UA mana paling aman untuk scraping generik?**
A: `chrome_win` paling umum di traffic internet (>60% market share).

**Q: Apakah rotation per request lebih baik dari per job?**
A: Tergantung target. Session-based target prefer sticky; stateless prefer rotate.

**Q: Apakah Sec-CH-UA header mandatory?**
A: Tidak, tapi tanpa itu Chromium-era browser tampak mencurigakan.

**Q: Bagaimana target deteksi UA tidak authentic?**
A: Cross-check dengan Sec-CH-UA, TLS JA3 fingerprint, JS navigator.userAgent, behavior patterns.

**Q: Bisa spoof lebih lanjut untuk lewati Cloudflare?**
A: PyScrapr menyediakan UA rotation dasar. Untuk Cloudflare sophisticated, butuh tools seperti undetected-chromedriver.

**Q: Apakah profile di-update otomatis saat Chrome update?**
A: Tidak otomatis. PyScrapr maintainer update manual berkala. Custom profile bisa fetch remote via `ua_refresh_profiles_url`.

**Q: Bisa set UA per-tool berbeda?**
A: Tidak default (global). Butuh code fork.

**Q: UA rotation compatible dengan cookies?**
A: Ya, cookies jar independen dari UA header.

## Keterbatasan

- Tidak mengatasi TLS fingerprinting (butuh library curl_cffi).
- Tidak mengatasi JS-based detection (butuh headless browser).
- 6 profil built-in terbatas ke desktop mainstream; mobile harus custom.
- Update profile manual, tidak auto dari browser release.
- Tidak per-tool config default.
- Round_robin state in-memory (reset saat restart).
- Tidak bundle curl_cffi integration.
- Accept-Language sederhana (tidak full locale negotiation).

## Related docs

- [Proxy](./proxy.md) — Kombinasi untuk disguise complete.
- [CAPTCHA Solver](./captcha.md) — Konsistensi UA saat solve.
- [Settings](../system/settings.md) — Section UA Rotation.
- [Site Ripper](../tools/site-ripper.md) — UA penting untuk asset integrity.
