# User-Agent Rotation

> Sistem rotasi User-Agent dengan 6 profil browser lengkap (full header set utuh, bukan hanya UA string) untuk menyamarkan fingerprint request dan menghindari deteksi bot berbasis rule sederhana. Mendukung mode random, round_robin, dan specific.

## Deskripsi

User-Agent Rotation adalah strategi menyamarkan identitas HTTP client dengan mengganti header `User-Agent` dan header browser pendukung lain secara sistematis antar request. Target situs sering memakai header ini sebagai salah satu sinyal pembeda "ini browser asli" dibandingkan "ini bot python-requests dengan default UA". Dengan UA rotation, tiap request keluar dengan signature yang terlihat seperti browser populer seperti Chrome Windows, Firefox Mac, atau Safari, sehingga pattern scraping tidak mudah di-fingerprint oleh rule-based bot detection yang cek UA blacklist.

Implementasi di PyScrapr tidak sekadar random pick dari list 10 UA string seperti library pemula. Kami menggunakan profil full header set: tiap profil browser membawa satu set header lengkap yang konsisten internal: `User-Agent`, `Accept`, `Accept-Language`, `Accept-Encoding`, `Sec-CH-UA` (Chromium hints), `Sec-CH-UA-Mobile`, `Sec-CH-UA-Platform`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site`, `Sec-Fetch-User`, dan `Upgrade-Insecure-Requests`. Alasan full-set penting: bot detection modern seperti Cloudflare Bot Management membandingkan konsistensi antar header. UA bilang "Chrome 120 Windows" tapi `Sec-CH-UA-Platform` bilang "macOS" akan langsung flagged sebagai suspicious. Profil di PyScrapr memastikan semua header align dengan browser yang di-claim.

Enam profil ter-bundled di `ua_rotator.py`: `chrome_win` (Chrome terbaru di Windows 10/11), `chrome_mac` (Chrome di macOS Sonoma), `firefox_win` (Firefox di Windows), `firefox_linux` (Firefox di Ubuntu), `safari_mac` (Safari di macOS), dan `edge_win` (Edge di Windows). Tiap profil di-update manual secara berkala untuk reflect versi browser terkini; maintenance team PyScrapr update saat Chrome atau Firefox major release stabil. Jika Anda butuh profil khusus seperti Chrome Android atau Safari iOS, Anda bisa tambahkan profil custom via setting `ua_custom_profiles` atau edit `services/ua_profiles.json` langsung.

Mode rotasi dikontrol oleh setting `ua_mode`: `random` (pilih acak per request), `round_robin` (cycle sequential), key profil spesifik seperti `chrome_win` (force satu profil), atau implisit disabled jika tidak set (pakai default httpx UA yang identifiable sebagai library Python). Integrasi dilakukan di class `Downloader` via method `_rotated_headers()` yang dipanggil sebelum tiap `httpx.get` atau `httpx.post`, memastikan semua tool yang inherit dari Downloader otomatis benefit tanpa code change di orchestrator.

## Kapan pakai?

1. **Scraping target dengan bot detection ringan** - Rule-based detection yang hanya cek UA akan mudah di-bypass dengan rotation multi-profil.
2. **Menghindari rate limit per-UA** - Beberapa CDN rate limit berdasarkan kombinasi IP plus UA, rotate UA bisa memperluas window quota.
3. **Testing responsive design** - Scrape versi mobile dengan UA `safari_ios` atau `chrome_android` (custom profile) untuk verify content delivery sesuai device.
4. **Avoid honeypot UA** - Default httpx UA seperti `python-httpx/0.27.0` terkenal di blocklist, rotate menghilangkan risiko identifikasi langsung.
5. **Kombinasi dengan Proxy** - UA rotation tanpa proxy artinya IP sama tapi UA beda (suspect pattern). Kombinasi proxy plus UA memberi signature fully variable.
6. **Long-running scheduled jobs** - Tiap fire pakai UA berbeda sehingga pattern traffic lebih natural across time, tidak memicu anomaly detection.
7. **Multi-geographic simulation** - Kombinasi profil OS berbeda mensimulasikan user dari region berbeda untuk test geo-aware content.
8. **Research fingerprinting target** - Test sejauh mana fingerprinting target sophisticated dengan observasi respons rotasi vs static.

## Cara penggunaan

1. Buka Settings > Advanced > UA Rotation section.
2. Dropdown `ua_mode`: pilih mode. Rekomendasi `random` untuk beginner, `round_robin` untuk predictable testing, key spesifik seperti `chrome_win` untuk lock pada satu profil.
3. Jika Anda pilih profil spesifik, tampilan akan menunjukkan preview headers yang akan dikirim.
4. Toggle `ua_include_sec_ch_headers` untuk full-set (default true). Disable hanya untuk target legacy yang confused dengan Sec-CH headers baru.
5. Review field `ua_exclude_profiles` yang berupa list profil untuk di-skip. Misalnya exclude `safari_mac` jika target reject Safari UA consistently.
6. Klik "Save changes" di toolbar Settings.
7. Test via tombol "Test UA" (jika tersedia) yang hit `httpbin.org/headers` untuk verifikasi headers yang actually ter-send.
8. Jalankan job sample di tool manapun. Log server akan menampilkan baris `Selected UA profile: chrome_win` per request atau per job.
9. Monitor respons target. Seharusnya tidak lagi langsung block request yang sebelumnya di-block dengan default UA.
10. Fine-tune exclude list berdasarkan behavior target; jika UA tertentu konsisten 403, exclude saja.
11. Untuk sticky per session, enable `ua_sticky_per_job` agar satu job pakai profil tetap selama eksekusi (bukan rotate per request).
12. Jika target sangat sophisticated, kombinasikan dengan proxy residential dan cookies handling.
13. Untuk tambah profil mobile atau region spesifik, edit `data/settings.json` field `ua_custom_profiles` dengan JSON schema yang sesuai.
14. Pantau log untuk profil yang sering ter-block dan eliminasi dari pool.
15. Update profile secara berkala mengikuti browser release dari Chrome, Firefox, Safari.

## Pengaturan / Konfigurasi

### ua_mode
Enum `off`, `random`, `round_robin`, atau key profil spesifik seperti `chrome_win`. Strategi rotasi. Default `random`. Rekomendasi: `random` untuk crawling besar, key spesifik untuk debugging.

### ua_specific_profile
String profil force jika ua_mode tidak match built-in. Default kosong. Gunakan untuk lock pada custom profile.

### ua_include_sec_ch_headers
Boolean, include Sec-CH-UA dan variant. Default true. Non-Chromium browser (Firefox) idealnya false, tapi PyScrapr auto-handle berdasarkan profil.

### ua_include_sec_fetch_headers
Boolean, include Sec-Fetch-Dest/Mode/Site/User. Default true. Disable hanya untuk target legacy.

### ua_exclude_profiles
Array string profile names untuk skip. Default kosong. Contoh: `["safari_mac", "firefox_linux"]` jika target reject dua itu.

### ua_sticky_per_job
Boolean, konsistensi per job (satu profil selama job) vs per request (rotate tiap call). Default false. Rekomendasi true untuk session-aware target seperti e-commerce.

### ua_custom_profiles
Object dengan struktur `{profile_name: {headers: {...}}}`. Custom profile yang di-append ke 6 built-in. Default kosong.

### ua_chrome_version_override
String optional, lock Chrome profiles ke versi spesifik seperti `"120.0.6099.130"`. Default kosong (pakai versi terbaru di profile JSON). Gunakan jika target expect versi stable.

### ua_randomize_language
Boolean, randomize Accept-Language antar `en-US`, `id-ID`, `en-GB`. Default false. Aktifkan untuk simulasi multi-lingual audience.

### ua_platform_order
Array optional, urutan round_robin mulai dari platform tertentu. Default alphabetical. Gunakan untuk prioritaskan `chrome_win` yang paling umum.

### ua_refresh_profiles_url
String URL optional, jika diset auto-fetch updated profiles dari URL remote (advanced self-hosted profile service). Default kosong.

## Output / Efek

Tidak ada file output. Observable behavior sebagai berikut:

- **Headers terkirim** - Tiap HTTP request carry full profile header set, verifiable via `httpbin.org/headers` endpoint.
- **Log line** - `UA: chrome_win (v120.0.6099.130) selected for https://example.com/` muncul di server log.
- **Response behavior** - Target seharusnya tidak lagi block, atau block dengan pola berbeda yang memberi petunjuk detection layer.
- **Fingerprint consistency** - Verify via `webrtc-fingerprint.com` atau tool fingerprinting lain bahwa headers align.
- **Downloader class integration** - Semua tool HTTP (Harvester, Ripper, Mapper, Scraper) otomatis pakai rotator tanpa code change.

## Integrasi dengan fitur lain

- **Downloader base class** - Semua tool HTTP consume via `_rotated_headers()` secara transparan.
- **Proxy Rotator** - Kombinasi untuk signature variation penuh (IP plus header diversity).
- **CAPTCHA Solver** - UA harus konsisten selama solve; `ua_sticky_per_job=true` sangat disarankan.
- **Media Downloader** - yt-dlp accept header set override via `http_headers` parameter yang di-populate dari rotator.
- **Settings** - Section UA Rotation dengan preview headers.
- **Site Ripper** - Asset download pakai UA konsisten dengan HTML request untuk hindari integrity flag.

## Tips & Best Practices

1. **Pakai sticky_per_job untuk e-commerce.** Session-based detection akan anggap suspicious jika UA berubah di tengah sesi checkout atau browse. Satu profil per job lebih natural.

2. **Random per-request untuk crawl besar stateless.** Ripper dengan ribuan halaman benefit dari variasi tinggi karena tiap halaman independen tanpa session state.

3. **Exclude profil yang tidak relevan.** Jika target hanya support Chrome/Edge, exclude Firefox dan Safari untuk hindari request yang selalu ter-reject.

4. **Kombinasikan dengan proxy.** IP diversity plus UA diversity jauh lebih efektif dari hanya salah satu. Sophistication target menentukan perlu kombinasi berapa layer.

5. **Update profiles rutin.** Browser version lama seperti Chrome 100 sangat mencolok di 2026; update saat Chrome atau Firefox major release.

6. **Hindari UA eksotis.** Profile obscure seperti browser mining coin atau IE11 lebih mencolok daripada common Chrome. Stick to mainstream.

7. **Test fingerprint di target.** Beberapa target juga cek TLS JA3 fingerprint, yang tidak ter-cover UA rotation. Gunakan `curl_cffi` jika perlu TLS spoof.

8. **Log profil per-job untuk audit.** Trail mana profil paling sering ter-block memberi insight untuk tuning exclude list.

9. **Accept-Language match dengan target region.** Target Indonesia mungkin serve konten berbeda untuk `en-US` vs `id-ID`. Randomize atau lock sesuai behavior yang Anda inginkan.

10. **Maintain profil custom terpisah.** Jangan edit built-in profiles langsung; pakai `ua_custom_profiles` agar update PyScrapr tidak overwrite perubahan Anda.

## Troubleshooting

### Problem: Request tetap block walaupun UA rotation aktif
**Gejala:** Status 403 atau 429 persisten meski log menunjukkan rotasi UA berjalan.
**Penyebab:** Target cek sinyal lain seperti TLS fingerprint, behavior pattern, atau JS execution.
**Solusi:** Kombinasikan dengan Proxy Rotator. Untuk target sophisticated, pertimbangkan headless browser solution di luar PyScrapr scope.

### Problem: Sec-CH-UA header value tidak match target expectation
**Gejala:** Target reject dengan indikasi UA hint missing atau invalid.
**Penyebab:** Target expect `Sec-CH-UA-Full-Version-List` yang belum di-implement di profile default.
**Solusi:** Update profile JSON dengan header tambahan. Atau disable `ua_include_sec_ch_headers` jika target legacy.

### Problem: yt-dlp tidak pakai UA rotation
**Gejala:** Log yt-dlp menunjukkan default UA yt-dlp, bukan profil dari rotator.
**Penyebab:** yt-dlp punya internal UA yang override kecuali explicit set.
**Solusi:** Verifikasi `ydl_opts["http_headers"]` di-populate dari UA rotator di `media_downloader.py`.

### Problem: Round_robin selalu pick profil sama
**Gejala:** Log menunjukkan profil pertama terus selected.
**Penyebab:** Counter state tidak persistent setelah restart server, atau multiple instance.
**Solusi:** Accept behavior (random seed pada startup, lalu sequential). Atau pakai `random` mode untuk menghindari.

### Problem: Custom profile tidak di-load
**Gejala:** Setting `ua_custom_profiles` tidak muncul di rotation.
**Penyebab:** JSON syntax error di settings atau field mismatch.
**Solusi:** Validasi JSON via `jsonlint.com`. Pastikan schema match expected: `{name: {headers: {...}}}`. Restart server untuk reload.

### Problem: Accept-Language selalu en-US walau target Indonesia
**Gejala:** Target serve konten English padahal ingin Indonesia.
**Penyebab:** Default profile header `Accept-Language: en-US,en;q=0.9`.
**Solusi:** Enable `ua_randomize_language` atau override Accept-Language di custom profile dengan `id-ID,id;q=0.9,en;q=0.8`.

### Problem: Memory usage naik setelah lama rotate
**Gejala:** RAM naik linear selama jam-jam running.
**Penyebab:** Connection pool tidak reuse karena header berbeda per request.
**Solusi:** Enable `ua_sticky_per_job` untuk pool reuse. Atau accept overhead untuk security variance.

### Problem: Target deteksi "User-Agent doesn't match TLS fingerprint"
**Gejala:** Error spesifik menyebut TLS.
**Penyebab:** UA claim Chrome, tapi library httpx TLS fingerprint berbeda dengan real Chrome.
**Solusi:** Gunakan `curl_cffi` library yang fake TLS fingerprint. Butuh integration code custom.

### Problem: Profile list di UI kosong
**Gejala:** Dropdown profil tidak menampilkan opsi.
**Penyebab:** File `services/ua_profiles.json` corrupt atau path salah.
**Solusi:** Restore dari backup git. Verifikasi file ada di app directory dengan permission read.

### Problem: Sticky per job malah tidak konsisten antar request
**Gejala:** Walau sticky aktif, masih ada UA berbeda dalam satu job.
**Penyebab:** Bug caching job_id di rotator, atau request bypass via library third-party.
**Solusi:** Verifikasi semua HTTP call melewati Downloader base class. Cek `curl_cffi` atau urllib fallback yang mungkin tidak melewati rotator.

## FAQ

**Q: Apakah UA rotation cukup untuk bypass semua bot detection?**
A: Tidak. Cloudflare Bot Management, Akamai, PerimeterX butuh kombinasi proxy, UA, TLS fingerprint, dan JS execution yang valid.

**Q: Bisa tambah profile Android atau iOS?**
A: Ya, via `ua_custom_profiles` atau edit `ua_profiles.json` langsung dengan schema header set yang sesuai browser mobile.

**Q: UA mana paling aman untuk scraping generik?**
A: `chrome_win` paling umum di traffic internet dengan market share lebih dari 60 persen. Statistik netral membuat blend in lebih baik.

**Q: Apakah rotation per request lebih baik dari per job?**
A: Tergantung target. Session-based target prefer sticky per job. Stateless target prefer rotate per request.

**Q: Apakah Sec-CH-UA header mandatory?**
A: Tidak strictly mandatory, tapi tanpa itu browser Chromium-era tampak mencurigakan. Modern target expect header ini ada.

**Q: Bagaimana target deteksi UA tidak authentic?**
A: Cross-check dengan Sec-CH-UA, TLS JA3 fingerprint, JS `navigator.userAgent`, dan behavior patterns seperti mouse movement.

**Q: Bisa spoof lebih lanjut untuk lewati Cloudflare?**
A: PyScrapr menyediakan UA rotation dasar. Untuk Cloudflare sophisticated, butuh tools seperti `undetected-chromedriver` atau `curl_cffi`.

**Q: Apakah profile di-update otomatis saat Chrome update?**
A: Tidak otomatis. PyScrapr maintainer update manual berkala. Custom profile bisa fetch remote via `ua_refresh_profiles_url`.

**Q: Bisa set UA per-tool berbeda?**
A: Tidak default (global). Butuh fork code untuk per-tool override.

**Q: UA rotation compatible dengan cookies?**
A: Ya, cookies jar independen dari UA header. Cookies tetap persist sesuai session config.

**Q: Apakah profile bisa custom Accept-Encoding?**
A: Ya, semua header di profile fully customizable termasuk encoding.

**Q: Bagaimana test efektivitas rotasi?**
A: Scrape ke `httpbin.org/headers` atau `useragentstring.com` dan verify headers yang received match dengan expected profile.

## Keterbatasan

- Tidak mengatasi TLS fingerprinting (butuh library `curl_cffi` terpisah).
- Tidak mengatasi JS-based detection (butuh headless browser solution).
- 6 profil built-in terbatas ke desktop mainstream; mobile harus via custom profile.
- Update profile manual, tidak auto dari browser release feed.
- Tidak ada per-tool config default; global untuk semua tool.
- Round_robin state in-memory (reset saat restart server).
- Tidak bundle `curl_cffi` integration out of the box.
- Accept-Language sederhana, tidak full locale negotiation dengan weighting.
- Tidak ada mode real-time fetch dari `useragents.me` atau service similar.
- Custom profile butuh edit JSON manual, belum ada UI editor.

## Studi kasus penggunaan nyata

**Skenario 1: News aggregator crawling 50 source berbeda.** Aggregator news harian hit 50 situs berita besar. Sebelum UA rotation, 15 dari 50 situs block PyScrapr karena default httpx UA terdaftar di blocklist mereka. Setelah aktifkan `random` mode dengan 6 profil browser, 48 dari 50 situs sukses. Dua sisanya butuh proxy plus UA kombinasi karena deteksi lebih sophisticated.

**Skenario 2: E-commerce monitoring session-aware.** Target e-commerce deteksi anomali saat UA berubah di tengah sesi browsing (rate 429 atau redirect ke homepage). Set `ua_sticky_per_job=true` membuat satu job selalu pakai profil konsisten. Result: job sukses end-to-end, tidak ada session loss.

**Skenario 3: Mobile-first web verification.** Developer perlu verify bahwa mobile version situs load dengan benar. Tambah custom profile `safari_ios` di `ua_custom_profiles` dengan UA string iPhone Safari. Scraping dengan profil ini mengembalikan HTML mobile, verifikasi responsive design tanpa emulator browser.

**Skenario 4: Bypass basic rate limit via UA diversity.** CDN target rate limit 100 request per UA per jam. Dengan 6 profil, effective rate 600 per jam dari satu IP. Untuk use case small-scale legitimate, ini cukup tanpa perlu proxy.

**Skenario 5: Accept-Language testing multi-locale.** Situs retail global serve konten berbeda per Accept-Language. Enable `ua_randomize_language` dengan pool `[en-US, id-ID, ja-JP]`. Scrape 300 halaman: 100 versi Indonesia (harga rupiah), 100 versi US (dollar), 100 versi Japan (yen). Analisis pricing strategy bisa di-compare head-to-head.

## Maintenance profile long-term

Browser release cycle 4-6 minggu (Chrome) artinya profile bisa stale dalam hitungan bulan. Pedoman maintenance:

1. **Audit kuartalan.** Setiap 3 bulan, cek latest Chrome dan Firefox version. Update Chrome version dan `Sec-CH-UA` string di profile jika selisih lebih dari 5 version.

2. **Subscribe ke release notes.** Ikuti Chrome Release Blog dan Firefox Release Notes untuk heads-up perubahan major di header semantics.

3. **Testing script untuk detect anomaly.** Buat script yang scrape `useragentstring.com` atau `httpbin.org/headers` dan assert output matches profile expected. Jalankan weekly, alert jika diverge.

4. **Version override untuk stability.** Untuk production scheduled yang butuh fingerprint stabil (supaya target tidak curiga UA terus berubah tiap release), pakai `ua_chrome_version_override` lock ke versi LTS atau stable populer.

5. **Fetch dinamis dari remote.** `ua_refresh_profiles_url` bisa point ke endpoint internal yang serve fresh profile JSON. Maintainer team update JSON di satu tempat, semua instance PyScrapr auto-pull.

6. **Test di target critical sebelum roll out.** Setelah update profile, jalankan sample job di target produksi untuk verify masih sukses. Rollback jika ada regression.

## Detail 6 profile bundled

Berikut detail ringkas untuk tiap profile built-in:

1. **chrome_win.** Chrome versi terbaru stable di Windows 10/11. UA string contoh: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`. Sec-CH-UA konsisten dengan Chromium. Accept-Language default en-US. Paling umum di internet, terbaik untuk blend in.

2. **chrome_mac.** Chrome di macOS Sonoma. UA similar tapi Win64 diganti `Macintosh; Intel Mac OS X 10_15_7`. Sec-CH-UA-Platform `"macOS"`. Bagus untuk target yang curiga dengan Windows-only traffic.

3. **firefox_win.** Firefox terbaru di Windows. UA string `Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0`. Sec-CH-UA tidak included (Firefox tidak implement). Accept header berbeda dari Chrome.

4. **firefox_linux.** Firefox di Ubuntu. UA `X11; Linux x86_64; rv:122.0`. Niche market (sekitar 2 persen traffic) tapi legitimate untuk developer audience.

5. **safari_mac.** Safari di macOS. UA `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15`. Tidak include Sec-CH headers. Safari-specific Accept format.

6. **edge_win.** Edge (Chromium-based) di Windows. UA mirip Chrome tapi dengan `Edg/120.0.0.0` di akhir. Sec-CH-UA brand mention Edge. Market share sekitar 5 persen, niche tapi representasi valid.

Tiap profile juga membawa Accept, Accept-Language, Accept-Encoding, Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site, Sec-Fetch-User, dan Upgrade-Insecure-Requests yang konsisten dengan browser yang di-claim.

## Menambah profile custom

Untuk use case khusus (mobile, browser regional), add custom profile via Settings field `ua_custom_profiles` dengan JSON:

```json
{
  "chrome_android": {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
    "Sec-CH-UA": "\"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\", \"Not=A?Brand\";v=\"24\"",
    "Sec-CH-UA-Mobile": "?1",
    "Sec-CH-UA-Platform": "\"Android\""
  }
}
```

Setelah save Settings, restart server agar profile di-register di pool. Verifikasi via log line `Loaded custom profile: chrome_android`. Pakai via `ua_mode=chrome_android` atau include di random pool (default behavior).

## Detection layer lanjutan yang tidak ter-cover

UA Rotation adalah layer pertama. Sophisticated bot detection melihat sinyal lain:

1. **TLS JA3 fingerprint.** Signature library TLS yang dipakai client. httpx default berbeda dari Chrome real. Fix dengan `curl_cffi` library yang fake TLS stack.

2. **JavaScript execution.** Challenge JS yang harus dieksekusi (Cloudflare turnstile). Tidak bisa dihandle tanpa browser real atau V8 engine.

3. **Canvas fingerprinting.** Rendering canvas yang unique per device. Butuh headless browser dengan stealth plugin.

4. **Behavioral analysis.** Mouse movement, timing, scroll pattern. Pure request-based scraping tidak bisa simulate.

5. **Cookie dan session consistency.** Target track cookies lintas request. PyScrapr maintain cookies via session object; verify tidak reset.

6. **HTTP/2 fingerprinting.** Order dan prioritization HTTP/2 frame bisa leak library identity. Advanced detection layer.

Jika target pakai lebih dari 2 layer di atas, UA Rotation saja tidak cukup. Pertimbangkan Playwright atau Puppeteer dengan stealth plugins sebagai supplementary tool.

## Related docs

- [Proxy](/docs/advanced/proxy.md) - Kombinasi untuk disguise complete IP plus header.
- [CAPTCHA Solver](/docs/advanced/captcha.md) - Konsistensi UA penting saat solve challenge.
- [Settings](/docs/system/settings.md) - Section UA Rotation untuk konfigurasi.
- [Site Ripper](/docs/tools/site-ripper.md) - UA penting untuk asset integrity consistency.
- [Media Downloader](/docs/tools/media-downloader.md) - yt-dlp UA injection via http_headers.
