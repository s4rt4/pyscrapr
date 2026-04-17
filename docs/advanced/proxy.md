# Proxy Rotator

> Sistem rotasi proxy yang dipakai transparan oleh semua tool PyScrapr untuk menyembunyikan IP asli, menghindari rate limit geografis, dan mendistribusikan request melintasi pool proxy yang Anda konfigurasi. Mendukung HTTP, HTTPS, dan SOCKS5.

## Deskripsi

Proxy Rotator adalah layer networking yang duduk di antara PyScrapr dan target situs. Alih-alih tiap request keluar langsung dari IP lokal Anda, request di-route melalui server proxy perantara yang sudah dikonfigurasi. Fitur ini esensial ketika target situs melakukan rate limiting per-IP (habis quota, seluruh scraping berhenti) atau geo-blocking (konten tidak tersedia di region Anda). Dengan pool proxy yang sehat, scraping bisa berjalan lebih panjang tanpa ter-blok dan dengan variasi IP yang membuat pattern traffic terlihat lebih natural ke sisi target.

Secara teknis, Proxy Rotator terimplementasi di `services/proxy_manager.py` sebagai class `ProxyManager`. Class ini membaca setting `proxy_list` (string multiline berisi satu URL proxy per baris) dan `proxy_mode` (enum `round_robin`, `random`, atau `none`). Ketika HTTP client dibuat via factory `http_factory.build_client()`, factory akan meminta ProxyManager untuk next proxy berdasarkan mode dan meng-inject sebagai parameter `proxies` ke instance httpx atau requests. Ini memastikan semua orchestrator tool (Harvester, Ripper, Mapper, Scraper klasik) otomatis mendapat benefit tanpa perlu mengubah kode tool individual. Single point of configuration yang konsisten membuat maintenance jauh lebih mudah.

Format proxy URL mengikuti konvensi standar: `<scheme>://[<user>:<pass>@]<host>:<port>`. Scheme yang didukung adalah `http`, `https`, `socks5`, dan `socks5h` (SOCKS5 dengan DNS resolution melalui proxy). Autentikasi basic-auth diembed inline di URL jika diperlukan. Contoh valid: `http://proxy1.example.com:8080`, `http://user:pass@proxy2.example.com:3128`, `socks5://127.0.0.1:1080`. Untuk mode `round_robin`, ProxyManager menyimpan counter internal dan rotate ke proxy berikutnya setiap kali dipanggil. Untuk mode `random`, ia memilih acak dari pool. Mode `none` menonaktifkan rotator dan request keluar langsung dari IP lokal.

Integrasi dengan yt-dlp (Media Downloader) sedikit berbeda karena yt-dlp punya mekanisme sendiri. PyScrapr meng-inject proxy ke `ydl_opts["proxy"]` di `media_downloader.py` saat menginisialisasi instance yt-dlp, mengambil satu proxy dari ProxyManager sesuai mode. Karena yt-dlp long-running (single video mungkin membutuhkan beberapa menit), proxy dipilih sekali per job bukan per request HTTP individual. Health check proxy (ping sebelum use) bisa diaktifkan opsional untuk skip proxy yang down, namun menambah overhead sekitar 100 ms per request sehingga default off untuk performa.

## Kapan pakai?

1. **Scraping target dengan rate limit ketat** - Cloudflare, Akamai, dan situs enterprise sering memblokir IP yang request terlalu banyak dalam waktu 1 menit.
2. **Akses konten geo-restricted** - Situs streaming atau konten regional yang memblokir IP di luar region tertentu seperti US, UK, atau Jepang.
3. **Menghindari IP ban saat testing** - Saat development scraping logic, Anda banyak trial error; proxy rotator mencegah IP dev Anda ter-flag permanen.
4. **Anonymity untuk research ethical** - Academic research terhadap public content di mana Anda ingin mengurangi jejak IP pribadi dalam log target.
5. **Load distribution untuk target besar** - Spread request ke banyak IP agar tiap IP low-profile dan terlihat seperti user biasa, bukan crawler agresif.
6. **Bypass corporate firewall quota** - Jaringan kantor mungkin membatasi request ke domain tertentu; proxy eksternal mem-bypass batasan ini.
7. **Testing dari IP region berbeda** - Verifikasi apakah konten situs benar-benar sama dari perspektif US, EU, atau Asia sebelum deploy scraper.
8. **Resiliensi saat proxy tunggal mati** - Pool multi-proxy memberi fallback otomatis bila satu node down tanpa intervensi manual.

## Cara penggunaan

1. Dapatkan list proxy dari provider komersial seperti Bright Data, Smartproxy, Oxylabs, atau proxy gratis dari publicproxy.com (hati-hati dengan kualitas dan keamanan yang terakhir).
2. Format satu URL proxy per baris, contoh:
```
http://user:pass@proxy1.provider.com:8080
http://user:pass@proxy2.provider.com:8080
socks5://user:pass@proxy3.provider.com:1080
```
3. Buka Settings di aplikasi, scroll ke section Advanced > Proxy.
4. Paste list ke field `proxy_list` (textarea multiline). Baris kosong dan baris yang diawali `#` diabaikan sebagai comment.
5. Pilih `proxy_mode`: `round_robin` untuk cycle sequential, `random` untuk pilih acak per request, atau `none` untuk disable rotator.
6. Toggle `proxy_health_check` jika Anda ingin ProxyManager skip proxy yang tidak responsif (opsional, ada overhead latency).
7. Klik "Save changes" di toolbar Settings.
8. Test koneksi via tombol "Test proxy" (jika tersedia) yang melakukan request ke `httpbin.org/ip` via tiap proxy untuk memverifikasi keluar dari IP yang benar.
9. Jalankan job normal di tool manapun; request otomatis ter-route via proxy sesuai mode.
10. Monitor log server untuk memastikan proxy di-pick benar; baris `Using proxy: <url>` akan muncul per request atau per job.
11. Jika banyak error timeout, evaluasi kualitas proxy; pertimbangkan provider berbeda atau tingkatkan `proxy_timeout`.
12. Sesuaikan pool size: terlalu sedikit menyebabkan rate limit cepat kena lagi, terlalu banyak menyebabkan bayaran berlebih di provider.
13. Untuk yt-dlp di Media Downloader, verifikasi di log yt-dlp line `[debug] Using proxy: ...` muncul.
14. Monitor billing provider mingguan agar tidak surprise bill karena usage tinggi.
15. Dokumentasikan pool proxy dan tanggal expiry credential di password manager untuk rotasi rutin.

## Pengaturan / Konfigurasi

### proxy_list
String multiline berisi list URL proxy, satu per baris. Baris kosong dan comment (prefix `#`) diabaikan. Default kosong. Rekomendasi: minimal 5-10 proxy untuk rotasi efektif pada target agresif.

### proxy_mode
Enum `round_robin`, `random`, atau `none`. Strategi rotasi. Default `none` (disabled). Rekomendasi: `round_robin` untuk predictable distribution, `random` untuk kurangi pattern detection.

### proxy_health_check
Boolean, ping proxy sebelum use untuk filter node yang down. Default false. Overhead sekitar 100 ms per request; enable hanya jika pool sering memiliki node mati.

### proxy_health_check_url
String URL endpoint untuk health check. Default `http://httpbin.org/ip`. Ganti ke endpoint internal jika httpbin tidak accessible dari sisi proxy.

### proxy_timeout
Integer detik, timeout untuk connection ke proxy sebelum dinyatakan down. Default 10. Naikkan jika proxy residential yang memang lambat.

### proxy_retry_on_fail
Boolean, jika proxy gagal respond, coba proxy lain dari pool. Default true. Matikan hanya untuk debugging.

### proxy_max_retries
Integer, jumlah retry dengan proxy berbeda sebelum giveup. Default 2. Naikkan sampai pool size minus 1 untuk exhaustive retry.

### proxy_exclude_domains
Array string, list domain yang bypass proxy. Default `["localhost", "127.0.0.1"]`. Tambahkan domain internal yang memang harus direct.

### proxy_auth_cache
Boolean, cache hasil auth handshake untuk reuse koneksi. Default true. Jangan matikan kecuali debugging auth issue.

### proxy_sticky_per_job
Boolean, jika true, satu job pakai proxy sama untuk semua request internalnya (bukan rotate per request). Default false. Aktifkan untuk target yang session-aware (e-commerce, login flow).

## Output / Efek

Proxy Rotator tidak menghasilkan file output; ia mempengaruhi networking behavior secara transparan. Observasi yang bisa Anda lakukan:

- **Log line per request atau per job** - `Using proxy: http://proxy1.example.com:8080` muncul di server log.
- **IP verification** - Request ke `httpbin.org/ip` akan mengembalikan IP proxy, bukan IP lokal Anda.
- **Target response** - Status 429 (rate limit) seharusnya turun frekuensinya; konten geo-blocked mulai accessible.
- **Health check statistics** - Jika enabled, metric berapa proxy up vs down ter-log di server.
- **Timing profile** - Request sedikit lebih lambat (typically 20-50 persen) karena hop tambahan via proxy server.
- **yt-dlp log** - Line `[debug] Using proxy: ...` saat Media Downloader initialize instance.

## Integrasi dengan fitur lain

- **Semua tool HTTP** - Harvester, Ripper, Mapper, dan Scraper klasik semuanya consume proxy via `http_factory.build_client()` secara otomatis.
- **Media Downloader** - yt-dlp menerima proxy via `ydl_opts["proxy"]` yang di-inject per job saat initialization.
- **UA Rotation** - Kombinasi proxy plus UA rotation menghasilkan signature request yang sangat variatif, bagus untuk menghindari fingerprint detection.
- **CAPTCHA Solver** - Saat CAPTCHA muncul, solver tetap menggunakan proxy yang sama untuk submit balasan agar konsisten dengan session.
- **Webhooks** - Notifikasi dispatch saat banyak proxy failure bisa memberi early warning pool sedang unhealthy.
- **Settings** - Central konfigurasi di section Proxy dengan validation URL format.

## Tips & Best Practices

1. **Pakai residential proxy untuk target yang tough.** Datacenter proxy mudah dideteksi karena IP range-nya known. Residential proxy menyerupai traffic user rumahan dan jauh lebih sulit dibedakan dari user real.

2. **Rotasi per-request di target agresif, per-session di target ramah.** Untuk target yang session-aware, set `proxy_sticky_per_job=true` agar tidak trigger anomaly detection. Untuk target stateless, rotasi per request memberi variasi maksimal.

3. **Monitor health check secara rutin.** Pool 10 proxy dengan 5 mati lebih buruk daripada pool 5 yang semuanya sehat. Jadwalkan audit mingguan untuk replace node mati.

4. **Jangan pakai proxy gratis untuk data sensitif.** Owner proxy gratis bisa intercept traffic HTTP non-TLS dan sering digunakan untuk harvesting credential. Pakai TLS dan provider berbayar untuk anything sensitive.

5. **Beli plan dengan authentication di provider.** Proxy open tanpa auth sering di-abuse banyak orang dan cepat masuk blacklist IP reputation service.

6. **Geographic diversity.** Campurkan proxy dari region berbeda (US, EU, Asia) untuk mengurangi geo-fingerprint ketika target cek konsistensi geografis.

7. **Rotate credential provider secara rutin.** Beberapa provider charge per-GB; monitor usage mingguan agar tidak surprise bill di akhir bulan karena job runaway.

8. **Test sebelum production scheduled.** Jalankan job sample dengan proxy baru sebelum bergantung untuk automation penuh overnight. Satu pool rusak bisa menggagalkan semua schedule.

9. **Kombinasi SOCKS5 dengan Tor untuk anonymity ekstra.** Tor listen di `socks5://127.0.0.1:9050` secara default; bisa dipakai sebagai satu entry dalam pool. Hati-hati ToS target.

10. **Dokumentasikan purpose tiap proxy.** Jika Anda pakai multi-provider, beri comment di list agar tahu mana untuk apa: `# Bright Data residential US`, `# Smartproxy EU datacenter`, dll.

## Troubleshooting

### Problem: Semua request timeout setelah enable proxy
**Gejala:** Job error dengan connection timeout, padahal direct sebelumnya sukses.
**Penyebab:** Credential proxy salah, server proxy down, atau network outbound di-blok firewall lokal.
**Solusi:** Test via curl manual `curl -x http://user:pass@proxy:port http://httpbin.org/ip`. Jika curl juga gagal, masalah ada di proxy atau network, bukan di PyScrapr.

### Problem: Status 407 Proxy Authentication Required
**Gejala:** Response dari proxy berupa 407 dengan pesan auth.
**Penyebab:** Auth tidak ter-embed di URL, atau format salah misalnya tidak URL-encoded password dengan karakter spesial.
**Solusi:** Pastikan format `http://user:pass@host:port`. URL-encode karakter spesial: `@` jadi `%40`, `:` di password jadi `%3A`.

### Problem: Kadang request keluar dari IP lokal bukan proxy
**Gejala:** Log menunjukkan IP lokal di beberapa request, IP proxy di request lain.
**Penyebab:** Domain tertentu ada di `proxy_exclude_domains`, atau yt-dlp tidak pick up setting proxy.
**Solusi:** Verifikasi exclude list. Untuk yt-dlp, cek log init untuk param `proxy`.

### Problem: Proxy sangat lambat, request lebih dari 30 detik
**Gejala:** Request timeout meski proxy responsif saat tes manual.
**Penyebab:** Proxy overloaded, latency geografis tinggi (misalnya proxy EU dari Asia), atau provider throttling.
**Solusi:** Ganti ke proxy region lebih dekat. Naikkan `proxy_timeout` ke 30. Pertimbangkan upgrade ke provider premium.

### Problem: Error SOCKS5 Authentication failed
**Gejala:** Log error spesifik SOCKS, padahal credential benar.
**Penyebab:** Library httpx tidak native support SOCKS; butuh extra dependency `httpx[socks]` atau `PySocks`.
**Solusi:** Jalankan `pip install httpx[socks]` atau `pip install pysocks`. Restart server.

### Problem: Round robin tidak merata, satu proxy selalu dipakai
**Gejala:** Log menunjukkan proxy pertama terus-menerus selected meskipun mode round_robin.
**Penyebab:** Bug counter reset per request instead of persistent, atau multiple instance ProxyManager (bukan singleton).
**Solusi:** Restart server untuk clear state. Verifikasi `ProxyManager` di-instantiate sebagai singleton global.

### Problem: Health check terus fail padahal proxy bisa curl
**Gejala:** ProxyManager skip semua node meskipun manual test lolos.
**Penyebab:** `proxy_health_check_url` tidak accessible dari sisi proxy (firewall di proxy).
**Solusi:** Ganti health check URL ke endpoint yang universal accessible, misalnya `https://www.google.com/generate_204`.

### Problem: Request berhasil tapi target mendeteksi sebagai bot
**Gejala:** Status 200 dari proxy, tapi content berupa "Access Denied" atau CAPTCHA page.
**Penyebab:** Proxy IP adalah datacenter range yang known, mudah dideteksi.
**Solusi:** Upgrade ke residential proxy. Kombinasikan dengan UA Rotation untuk variasi signature lebih lengkap.

### Problem: Memory leak setelah long-running dengan banyak proxy
**Gejala:** RAM aplikasi naik terus selama beberapa jam.
**Penyebab:** Connection pool tidak ter-close properly di library.
**Solusi:** Restart periodik setiap 24 jam. Upgrade httpx ke versi terbaru yang fix connection leak.

### Problem: yt-dlp tidak pakai proxy meski setting ada
**Gejala:** Media download keluar dari IP lokal.
**Penyebab:** yt-dlp init sebelum ProxyManager ready, atau race condition di startup.
**Solusi:** Verifikasi `media_downloader.py` memanggil `proxy_manager.get_proxy()` sebelum build `ydl_opts`.

## FAQ

**Q: Apakah PyScrapr ship dengan proxy built-in?**
A: Tidak. Anda harus menyediakan pool sendiri baik dari provider berbayar maupun gratis.

**Q: Apakah Tor didukung?**
A: Ya, via SOCKS5 ke `127.0.0.1:9050` (port default Tor). Hati-hati dengan ToS target; banyak situs memblokir Tor exit nodes.

**Q: Berapa proxy ideal dalam pool?**
A: Tergantung rate limit target dan volume job. Mulai 5-10, scale sesuai kebutuhan. Pool terlalu besar hanya buang biaya.

**Q: Apakah proxy memengaruhi download speed?**
A: Ya, biasanya 20-50 persen lebih lambat dari direct. Residential proxy lebih lambat dari datacenter.

**Q: Bisa tiap tool pakai proxy list berbeda?**
A: Tidak default (global pool). Butuh fork code untuk per-tool override; belum ada setting UI untuk itu.

**Q: Apakah HTTPS di-inspect oleh proxy?**
A: Tidak untuk forward proxy standar. HTTPS end-to-end encrypted, proxy hanya relay bytes. MITM proxy butuh cert installation di klien.

**Q: Bisa kombinasi proxy rotator dengan VPN?**
A: Bisa, tapi hati-hati karena dual-hop latency akan tinggi dan troubleshooting jadi kompleks.

**Q: Apakah ada auto-failover saat proxy mati mendadak?**
A: Ya, dengan `proxy_retry_on_fail=true` (default). PyScrapr akan coba proxy lain dari pool otomatis.

**Q: Bagaimana handle proxy yang tiba-tiba minta CAPTCHA?**
A: Integrasi dengan CAPTCHA Solver (settings terpisah). CAPTCHA biasanya dari target, bukan dari proxy.

**Q: Legal untuk pakai proxy untuk scraping?**
A: Tergantung yurisdiksi dan ToS target situs. Konsultasi legal untuk use case komersial.

**Q: Apakah proxy auth tersimpan encrypted?**
A: `data/settings.json` plaintext secara default. Untuk encryption at rest, gunakan disk encryption OS level.

**Q: Bisa monitor traffic proxy in-app?**
A: Tidak, PyScrapr tidak expose statistik proxy detail. Cek dashboard provider untuk usage breakdown.

## Keterbatasan

- Tidak ada auto-discovery proxy; harus manual config via Settings.
- Health check sederhana (hanya ping URL, bukan full integration test dengan target).
- Tidak ada per-tool proxy pool; semua tool pakai global pool.
- SOCKS5 butuh extra dependency install (`httpx[socks]`).
- Tidak ada built-in proxy marketplace atau provider integration.
- Performance overhead 20-50 persen vs direct connection.
- HTTPS inspection tidak didukung tanpa MITM setup manual di klien.
- Tidak ada rotasi otomatis based on response code (misalnya skip proxy yang 403 terus).
- Monitoring statistik proxy (usage, error rate) minim di UI.
- Credential tersimpan plaintext di settings.json.

## Studi kasus penggunaan nyata

**Skenario 1: Scraping marketplace dengan rate limit IP-based.** Pengguna melakukan harvest ribuan listing dari marketplace dengan rate limit 100 request per menit per IP. Tanpa proxy, job 5000 listing butuh 50 menit minimum dan sering kena 429. Dengan 10 residential proxy di pool mode `round_robin`, effective rate naik ke 1000 request per menit dan job selesai dalam 5 menit tanpa 429. Cost proxy masih sekitar 1 USD untuk bandwidth yang terpakai.

**Skenario 2: Akses konten geo-restricted.** Pengguna di Indonesia perlu scrape konten yang hanya available di US (contoh: artikel news site dengan paywall regional). Proxy residential US di-set sebagai single-entry pool dengan mode `round_robin`. Semua request keluar dari IP US, konten terakses normal. Alternatif: VPN system-wide, tapi proxy memberi granularity per-job tanpa memengaruhi traffic lain di laptop.

**Skenario 3: Testing dari region berbeda.** Developer perlu verify apakah homepage situs serve konten berbeda untuk user US vs UK vs ID. Tiga profil pool proxy berbeda region, tiap run pakai satu region, lalu bandingkan hasil HTML via Diff Detection. Temuan: banner promosi berbeda, pricing berbeda, bahkan layout navigasi berubah sesuai region.

**Skenario 4: Tor untuk anonimitas research.** Researcher privacy pakai Tor SOCKS5 sebagai single entry di pool. Semua request route via Tor network, IP keluar bervariasi dari exit node global. Overhead latency 2-5 detik per request, tapi untuk research ethical yang butuh anonimitas source, trade-off acceptable.

**Skenario 5: Fail-over otomatis untuk production scheduled.** Pool 5 proxy dari 2 provider berbeda (Bright Data dan Smartproxy). `proxy_retry_on_fail=true` dengan `proxy_max_retries=4`. Saat satu provider mengalami outage (kejadian nyata 1-2 kali per bulan), job masih sukses via fallback ke provider kedua. Uptime meningkat dari 98 persen ke 99.9 persen.

## Optimasi biaya proxy

Residential proxy bisa mahal jika dipakai serampangan. Beberapa teknik untuk menekan cost tanpa sacrifice efektivitas:

1. **Cache aggresif di sisi aplikasi.** Jika Anda scrape halaman yang rarely change, cache HTML di local filesystem dengan TTL 24 jam. Request yang di-cache tidak hit proxy sama sekali.

2. **Filter dulu, fetch kemudian.** Gunakan sitemap.xml atau RSS untuk discover URL target, lalu fetch hanya yang delta. Bandwidth proxy untuk discovery biasanya datacenter (murah), fetch konten pakai residential (mahal tapi perlu).

3. **Monitor bandwidth per job.** Provider charge per GB. Disable image download di Harvester untuk job yang hanya butuh metadata akan menghemat 90 persen bandwidth.

4. **Switch mode sesuai kebutuhan.** `proxy_sticky_per_job=true` untuk target e-commerce menghemat overhead handshake per request. Per-request rotation hanya untuk stateless crawl.

5. **Negosiasi kontrak volume dengan provider.** Pay-as-you-go mahal. Bulk plan dengan commit 50-100 GB per bulan diskon 30-50 persen dari standard rate.

## Provider proxy yang populer

Berikut beberapa provider proxy populer yang biasa dipakai komunitas scraping, dengan karakteristik masing-masing:

1. **Bright Data (sebelumnya Luminati).** Provider premium dengan pool residential terbesar di industri (72 juta plus IP). Harga tinggi (sekitar 12 USD per GB residential), tapi kualitas sangat reliable untuk target tough seperti Amazon atau Google. Cocok untuk enterprise.

2. **Smartproxy.** Mid-range, harga sekitar 8 USD per GB residential, pool 40 juta IP. Performance bagus untuk target umum, dashboard user-friendly, dokumentasi lengkap. Sweet spot untuk personal dan small team.

3. **Oxylabs.** Alternatif Bright Data dengan harga kompetitif. Pool besar, uptime tinggi. Fokus di enterprise plus developer-friendly dengan integration SDK.

4. **IPRoyal.** Budget-friendly, sekitar 7 USD per GB residential. Kualitas decent untuk target non-sophisticated. Bagus untuk personal scraping atau test environment.

5. **ProxyScrape.** Gratis dan berbayar, pool datacenter dan residential. Gratis tier useful untuk eksperimen tapi tidak reliable untuk production.

6. **Webshare.** Affordable ($3.50 per GB), 30 juta IP. Support SOCKS5 dan HTTP. Bagus untuk hobbyist dan startup.

7. **Tor (gratis).** Network public, free. Latency tinggi (2-5 detik per hop) dan banyak exit node di-blacklist. Hanya untuk research anonymity, bukan production scraping.

Pilih berdasarkan: budget, target yang di-scrape (tough atau ramah), volume bandwidth bulanan, dan kebutuhan geographic coverage. Mulai dengan trial gratis beberapa provider untuk bandingkan sebelum commit.

## Monitoring dan observability pool

Untuk pool yang panjang umur dan reliable, observability penting:

1. **Track success rate per proxy.** Log per request: proxy URL, status code, latency. Aggregate mingguan, proxy dengan success rate di bawah 80 persen kandidat replace.

2. **Alert saat pool degradasi.** Set webhook fires jika `proxy_retry_on_fail` trigger lebih dari 20 persen request dalam 1 jam. Indikasi pool unhealthy.

3. **Dashboard provider integration.** Provider besar expose API untuk usage stats (GB consumed, success rate, top domains). Integrate ke dashboard internal untuk visibility cost.

4. **Rotate pool berkala.** Bahkan tanpa masalah explicit, rotate pool setiap 3-6 bulan ke provider berbeda untuk hindari pattern detection long-term.

5. **Split pool per use case.** Pool residential untuk high-stakes target, pool datacenter untuk discovery. Reduce cost dan maintain performance.

## Related docs

- [UA Rotation](/docs/advanced/ua-rotation.md) - Pair dengan proxy untuk disguise lengkap.
- [CAPTCHA Solver](/docs/advanced/captcha.md) - Handle challenge saat proxy ter-flag.
- [Settings](/docs/system/settings.md) - Section Proxy untuk konfigurasi pool.
- [Media Downloader](/docs/tools/media-downloader.md) - Integrasi yt-dlp proxy injection.
- [Webhooks](/docs/advanced/webhooks.md) - Alert saat pool proxy unhealthy.
