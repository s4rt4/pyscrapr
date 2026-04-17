# Proxy Rotator

> Sistem rotasi proxy yang dipakai transparan oleh semua tool PyScrapr — menyembunyikan IP asli, menghindari rate limit geografis, dan men-distribute request melintasi pool proxy.

## Deskripsi

Proxy Rotator adalah layer networking yang duduk di antara PyScrapr dan target situs. Alih-alih tiap request keluar langsung dari IP lokal Anda, request di-route melalui server proxy perantara yang Anda konfigurasi. Fitur ini esensial ketika target situs melakukan rate limiting per-IP (habis quota, seluruh scraping berhenti) atau geo-blocking (konten tidak available di region Anda). Dengan pool proxy yang sehat, scraping bisa berjalan lebih panjang tanpa blocked dan dengan variasi IP yang bikin pattern traffic terlihat lebih natural.

Secara teknis, Proxy Rotator terimplementasi di `services/proxy_manager.py` sebagai class `ProxyManager`. Class ini membaca setting `proxy_list` (string multiline berisi satu URL proxy per baris) dan `proxy_mode` (enum: `round_robin`, `random`, `none`). Ketika HTTP client dibuat via factory `http_factory.build_client()`, factory akan ask ProxyManager untuk next proxy (berdasarkan mode) dan inject sebagai parameter `proxies` ke instance httpx/requests. Ini memastikan semua orchestrator tool (Harvester, Ripper, Mapper, Media) otomatis benefit tanpa perlu ubah kode tool individual — single point of configuration.

Format proxy URL mengikuti konvensi standar: `<scheme>://[<user>:<pass>@]<host>:<port>`. Scheme yang didukung: `http`, `https`, `socks5`, `socks5h` (socks5 dengan DNS lewat proxy). Autentikasi basic-auth diembed inline di URL jika diperlukan. Contoh valid: `http://proxy1.example.com:8080`, `http://user:pass@proxy2.example.com:3128`, `socks5://127.0.0.1:1080`. Untuk mode `round_robin`, ProxyManager menyimpan counter internal dan rotate ke proxy berikutnya setiap kali dipanggil. Untuk `random`, memilih acak dari pool. Mode `none` menonaktifkan rotator dan request keluar langsung.

Integrasi dengan yt-dlp (Media Downloader) sedikit berbeda karena yt-dlp punya mekanisme sendiri. PyScrapr meng-inject proxy ke `ydl_opts["proxy"]` saat initialize instance yt-dlp, mengambil satu proxy dari ProxyManager sesuai mode. Karena yt-dlp long-running (single video mungkin beberapa menit), proxy dipilih sekali per job bukan per request. Health check proxy (ping sebelum use) bisa diaktifkan optionally untuk skip proxy yang down — namun menambah overhead, default off.

## Kapan pakai?

1. **Scraping target dengan rate limit ketat** — Cloudflare, Akamai, dan situs enterprise sering block IP yang request terlalu banyak dalam 1 menit.
2. **Akses konten geo-restricted** — Situs streaming atau konten regional yang block IP di luar region tertentu.
3. **Menghindari IP ban saat testing** — Saat development scraping logic, kita banyak trial error — proxy rotator cegah IP dev Anda ter-flag.
4. **Anonymity untuk research ethical** — Academic research terhadap public content dimana Anda ingin mengurangi jejak IP pribadi.
5. **Load distribution untuk target besar** — Spread request ke banyak IP agar tiap IP low-profile dan terlihat seperti user biasa.
6. **Bypass corporate firewall quota** — Jaringan kantor mungkin batasi request ke domain tertentu; proxy external bypass ini.
7. **Testing dari IP region berbeda** — Verifikasi apakah konten situs benar-benar sama dari US, EU, Asia.
8. **Resiliensi saat proxy tunggal mati** — Pool multi-proxy memberi fallback otomatis bila satu down.

## Cara penggunaan

1. Dapatkan list proxy dari provider (Bright Data, Smartproxy, Oxylabs, atau proxy gratis dari publicproxy.com — hati-hati kualitas).
2. Format satu URL proxy per baris, contoh:
```
http://user:pass@proxy1.provider.com:8080
http://user:pass@proxy2.provider.com:8080
socks5://user:pass@proxy3.provider.com:1080
```
3. Buka Settings > Advanced > Proxy section.
4. Paste list ke field `proxy_list` (textarea multiline).
5. Pilih `proxy_mode`: `round_robin` (cycle sequential), `random` (pilih acak), atau `none` (disable).
6. Toggle `proxy_health_check` jika Anda ingin ProxyManager skip proxy yang tidak responsif (opsional, ada overhead).
7. Klik "Save changes".
8. Test koneksi via tombol "Test proxy" (jika tersedia) yang hit httpbin.org/ip via tiap proxy untuk verify keluar dari IP benar.
9. Jalankan job normal di tool mana saja — otomatis ter-route via proxy.
10. Monitor di log server untuk pastikan proxy di-pick benar (line `Using proxy: <url>` muncul per request).
11. Jika banyak error timeout, evaluasi kualitas proxy; pertimbangkan provider berbeda.
12. Adjust pool size — too few = rate limit cepat kena lagi; too many = bayaran berlebih.

## Pengaturan / Konfigurasi

Field Settings > Proxy section:

- **proxy_list** (string multiline) — List URL proxy, satu per baris. Baris kosong dan comment (prefix `#`) diabaikan.
- **proxy_mode** (enum `round_robin`, `random`, `none`, default `none`) — Strategi rotasi.
- **proxy_health_check** (boolean, default false) — Ping proxy sebelum use. Overhead ~100ms per request.
- **proxy_health_check_url** (string URL, default `http://httpbin.org/ip`) — Endpoint untuk health check.
- **proxy_timeout** (int detik, default 10) — Timeout untuk koneksi ke proxy sebelum dinyatakan down.
- **proxy_retry_on_fail** (boolean, default true) — Jika proxy fail, coba proxy lain dari pool.
- **proxy_max_retries** (int, default 2) — Jumlah retry dengan proxy berbeda sebelum giveup.
- **proxy_exclude_domains** (array string, optional) — Domain yang bypass proxy (misal `localhost`, `127.0.0.1`).
- **proxy_auth_cache** (boolean, default true) — Cache hasil auth handshake untuk reuse.
- **proxy_sticky_per_job** (boolean, default false) — Jika true, satu job pakai proxy yang sama untuk semua request (bukan rotate per request).

## Output

Proxy Rotator tidak menghasilkan file; ia mempengaruhi networking behavior. Observasi yang bisa Anda lakukan:

- **Log line** — `Using proxy: http://proxy1.example.com:8080` per job atau per request.
- **IP verification** — Request ke `httpbin.org/ip` akan return IP proxy, bukan IP lokal.
- **Target response** — Status 429 seharusnya turun frekuensinya; geo-blocked content mulai accessible.
- **Health check stats** — Jika enabled, metric berapa proxy up vs down terlog.

## Integrasi dengan fitur lain

- **Semua tool HTTP** — Harvester, Ripper, Mapper, Scraper klasik consume via `http_factory.build_client`.
- **Media Downloader** — yt-dlp menerima proxy via `ydl_opts["proxy"]`.
- **UA Rotation** — Kombinasi proxy + UA rotation = signature request sangat variatif.
- **CAPTCHA Solver** — Saat CAPTCHA muncul, solver tetap pakai proxy untuk kirim balasan.
- **Webhooks** — Notifikasi saat banyak proxy failure (health check integrated).
- **Settings** — Central config di section Proxy.

## Tips & Best Practices

1. **Pakai residential proxy untuk target tough** — Datacenter proxy mudah dideteksi; residential menyerupai traffic user biasa.
2. **Rotasi per-request di target agresif; per-session di target ramah** — `proxy_sticky_per_job=true` untuk situs yang deteksi session change.
3. **Monitor health check** — Pool 10 proxy dengan 5 mati lebih buruk daripada pool 5 yang sehat.
4. **Jangan pakai proxy gratis untuk sensitive data** — Owner proxy bisa intercept traffic HTTP non-TLS.
5. **Beli authentication di provider** — Proxy open (tanpa auth) sering di-abuse dan di-blacklist.
6. **Geographic diversity** — Campurkan proxy dari region berbeda agar reduce geo-fingerprint.
7. **Rotate credential provider rutin** — Beberapa provider charge per-GB; monitor usage agar tidak surprise bill.
8. **Test sebelum production scheduled** — Jalankan job sample dengan proxy baru sebelum rely untuk automation penuh.

## Troubleshooting

**Problem: Semua request timeout setelah enable proxy.**
Cause: Proxy credential salah, atau proxy server down.
Solution: Test via curl manual `curl -x http://user:pass@proxy:port http://httpbin.org/ip`. Fix credential atau ganti proxy.

**Problem: Status 407 Proxy Authentication Required.**
Cause: Auth tidak ter-embed di URL atau format salah.
Solution: Pastikan format `http://user:pass@host:port`. Special character di password butuh URL encoding.

**Problem: Kadang keluar dari IP lokal bukan proxy.**
Cause: Domain tertentu di `proxy_exclude_domains`, atau yt-dlp tidak pick up proxy setting.
Solution: Verifikasi exclude list. Cek log yt-dlp init untuk `proxy` param.

**Problem: Proxy sangat lambat, request > 30 detik.**
Cause: Proxy overloaded, atau latency geografis tinggi.
Solution: Ganti ke proxy region lebih dekat. Naikkan `proxy_timeout`. Atau upgrade ke provider premium.

**Problem: Error SOCKS5 "Authentication failed".**
Cause: Library httpx tidak native support SOCKS — butuh package `httpx[socks]` atau `PySocks`.
Solution: Install `pip install httpx[socks]`. Restart server.

**Problem: Round robin tidak merata, satu proxy selalu dipakai.**
Cause: Bug counter reset per request instead of persistent.
Solution: Restart server untuk clear state. Verifikasi ProxyManager singleton.

**Problem: Health check terus fail padahal proxy bisa curl.**
Cause: `proxy_health_check_url` tidak accessible dari proxy (firewall di sisi proxy).
Solution: Ganti health check URL ke endpoint yang universally accessible.

**Problem: Request berhasil tapi target mendeteksi sebagai bot.**
Cause: Proxy IP datacenter, bukan residential, mudah dideteksi.
Solution: Upgrade ke residential proxy. Kombinasikan dengan UA Rotation.

**Problem: Memory leak setelah long-running dengan banyak proxy.**
Cause: Connection pool tidak ter-close properly.
Solution: Restart periodik. Upgrade httpx ke versi terbaru.

## FAQ

**Q: Apakah PyScrapr ship dengan proxy built-in?**
A: Tidak. Anda harus provide pool sendiri (beli/gratis).

**Q: Apakah TOR didukung?**
A: Ya via SOCKS5 ke `127.0.0.1:9050` (TOR default). Hati-hati dengan ToS target.

**Q: Berapa proxy ideal dalam pool?**
A: Tergantung rate limit target dan volume job. Start 5-10, scale sesuai kebutuhan.

**Q: Apakah proxy mempengaruhi download speed?**
A: Ya, biasanya lebih lambat 20-50% dari direct. Residential proxy lebih lambat dari datacenter.

**Q: Bisa tiap tool pakai proxy list berbeda?**
A: Tidak default (global pool). Butuh fork code untuk per-tool override.

**Q: Apakah HTTPS di-inspect oleh proxy?**
A: Tidak untuk forward proxy standar (HTTPS end-to-end encrypted). MITM proxy butuh cert install.

**Q: Bisa kombinasi proxy rotator dengan VPN?**
A: Bisa, tapi hati-hati karena dual-hop latency tinggi.

**Q: Apakah ada auto-failover?**
A: Ya dengan `proxy_retry_on_fail=true`.

**Q: Bagaimana handle proxy yang tiba-tiba minta captcha?**
A: Integrasi dengan CAPTCHA Solver (settings terpisah).

**Q: Legal untuk pakai proxy untuk scraping?**
A: Tergantung yurisdiksi dan ToS target. Konsultasi legal untuk use case komersial.

## Keterbatasan

- Tidak ada auto-discovery proxy (harus manual config).
- Health check sederhana (hanya ping URL, bukan full test).
- Tidak per-tool proxy pool.
- SOCKS5 butuh extra dependency install.
- Tidak ada built-in proxy marketplace integration.
- Performance overhead 20-50% vs direct.
- HTTPS inspection tidak didukung (perlu MITM setup manual).

## Related docs

- [UA Rotation](./ua-rotation.md) — Pair dengan proxy untuk disguise lengkap.
- [CAPTCHA Solver](./captcha.md) — Handle challenge saat proxy ter-flag.
- [Settings](../system/settings.md) — Section Proxy.
- [Media Downloader](../tools/media-downloader.md) — yt-dlp proxy injection.
