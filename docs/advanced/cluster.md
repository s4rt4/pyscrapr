# Cluster / Worker Nodes (Distributed Scraping)

> Mode distribusi sederhana yang memungkinkan beberapa instance PyScrapr di mesin berbeda bekerja sama dalam satu sistem scraping. Satu mesin berperan sebagai master yang punya UI dan meng-dispatch job, mesin-mesin lain berperan sebagai worker headless yang menerima job via HTTP dan mengerjakan lokal. Tanpa Redis, tanpa Celery, tanpa message broker; hanya HTTP POST antar process dengan shared token sebagai auth minimal. Cocok untuk skenario paralel berat, rotasi IP lintas jaringan, atau offload CPU-bound task ke mesin yang lebih kuat.

## Apa itu Cluster Mode

PyScrapr awalnya dirancang sebagai single-node offline toolkit. Semua fitur (UI, orchestrator, downloader, database SQLite) jalan di satu process. Ini cukup untuk kebanyakan user personal. Tapi ada use case di mana satu mesin tidak cukup: scraping situs yang rate-limit per IP (butuh rotasi geografis), job besar dengan ribuan URL (butuh paralel multi-machine), atau kombinasi mesin weak (laptop kecil untuk UI) dan mesin strong (desktop GPU untuk Playwright + CLIP).

Solusi tradisional seperti Celery + Redis kelas berat untuk kebutuhan personal. PyScrapr memilih pendekatan minimalis: setiap node adalah PyScrapr instance normal, komunikasi antar node pakai HTTP POST standar, auth pakai shared secret token yang ditaruh di header `X-Auth-Token`. Tidak ada message queue, tidak ada persistent broker. Kalau node mati, job state hilang, jadi ini bukan sistem production HA; lebih tepat disebut "multi-node coordination".

Ada tiga mode operasi:

- `standalone` (default): mode single-node klasik. Tidak ada coordination, semua dikerjakan lokal.
- `master`: mode dengan UI aktif dan orchestrator yang bisa dispatch ke worker. Master tetap bisa eksekusi job lokal juga; worker hanya tambahan kapasitas.
- `worker`: mode headless tanpa UI aktif (UI tetap ada tapi tidak dipakai). Worker listen di port HTTP, terima job submit dari master, eksekusi, dan expose status endpoint.

Master tidak tahu apa yang dikerjakan worker secara detail; hanya tahu `job_id` di worker dan bisa polling status. Worker tidak tahu job lain yang sedang dikerjakan master atau worker lain; setiap node isolated. Koordinasi tingkat tinggi (load balancing, failure retry) dihandle master.

## Setup / Instalasi

### Langkah keseluruhan

1. Pasang PyScrapr di setiap mesin yang ingin ikut cluster. Versi harus sama (minor version match) untuk kompatibilitas API.
2. Pilih satu mesin sebagai master (biasanya yang Anda akses langsung dengan UI), sisanya worker.
3. Konfigurasi shared `worker_auth_token` yang sama di semua node. Token ini adalah kunci keamanan; pilih string random minimal 32 karakter.
4. Di tiap worker, set `worker_mode=worker` dan jalankan server listen di `0.0.0.0` supaya reachable dari master.
5. Di master, set `worker_mode=master`, isi `worker_pool` dengan URL tiap worker, dan toggle `worker_enabled=true`.
6. Test connectivity dengan "Cek worker health" di Settings UI.
7. Dispatch job via API atau UI button.

### Setup worker detail

Di mesin worker, edit `data/settings.json`:

```json
{
  "worker_mode": "worker",
  "worker_auth_token": "a_long_random_shared_secret_token_32chars_min"
}
```

Restart server dengan bind ke semua interface:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> [!WARNING]
> Jangan bind `0.0.0.0` kalau mesin terhubung ke internet tanpa firewall. Token sharing bukan kripto-kuat; anyone yang tahu token bisa submit job. Idealnya cluster hanya di LAN atau VPN.

Test worker health dari master atau browser:

```bash
curl http://worker1.local:8585/api/worker/health
```

Response:

```json
{"status": "ok", "mode": "worker", "version": "1.0.0", "load": 0.1}
```

### Setup master detail

Di mesin master, edit Settings lewat UI (Settings -> Cluster section):

- `worker_mode`: `master`
- `worker_enabled`: true
- `worker_auth_token`: same shared token
- `worker_pool`: list URL worker, satu per baris atau comma-separated:

```
http://worker1.local:8585
http://worker2.local:8585
http://192.168.1.50:8585
```

- `worker_dispatch_strategy`: `round_robin`, `random`, atau `least_loaded`

Klik Save, kemudian klik "Cek worker health" untuk verifikasi. Response menampilkan daftar worker dengan status up/down dan load metric.

## Cara pakai

1. Pastikan semua worker sudah running dan terdaftar di master pool.
2. Buka salah satu tool di UI master, misalnya Image Harvester.
3. Isi URL dan config seperti biasa.
4. Di section Advanced, cari toggle "Dispatch ke worker" (UI saat ini minimal; mungkin lewat API terlebih dahulu).
5. Submit job. Master akan pilih worker berdasarkan strategy, POST config ke endpoint worker, dan simpan mapping `local_job_id -> {worker_url, remote_job_id}`.
6. Progress di UI master polled dari worker tiap beberapa detik via `GET /api/worker/status/{remote_job_id}`.
7. Saat worker selesai, result file tetap di worker (master hanya simpan metadata).
8. Untuk ambil file hasil, master expose endpoint proxy: `GET /api/cluster/remote-job/{worker_url}/{job_id}/files` yang stream file dari worker.
9. Atau akses langsung worker UI di `http://worker1.local:8585/history` dan download dari sana.

### Dispatch via API

```bash
curl -X POST http://master.local:8585/api/cluster/dispatch \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "image-harvester",
    "config": {"url": "https://example.com", "max_images": 100},
    "worker_url": "http://worker1.local:8585"
  }'
```

Jika `worker_url` dihilangkan, master pilih sesuai `worker_dispatch_strategy`.

Response:

```json
{
  "status": "dispatched",
  "worker_url": "http://worker1.local:8585",
  "remote_job_id": "uuid-at-worker",
  "local_job_id": "uuid-at-master"
}
```

### Cek health semua worker

```bash
curl http://master.local:8585/api/cluster/workers
```

Response:

```json
{
  "workers": [
    {"url": "http://worker1.local:8585", "status": "up", "load": 0.3, "version": "1.0.0"},
    {"url": "http://worker2.local:8585", "status": "down", "error": "connection refused"}
  ]
}
```

## Contoh skenario

### Skenario 1: Rotasi IP via worker di lokasi berbeda

Seorang researcher butuh scrape situs yang block IP tertentu. Dia setup 3 worker: satu di rumah (ISP A), satu di kantor (ISP B), satu di VPS cloud (datacenter). Master di laptop personal pilih worker secara round-robin, jadi request terdistribusi dari 3 IP berbeda. Situs target tidak deteksi pattern karena IP bervariasi.

### Skenario 2: Paralel large Harvester job

Tim data perlu scrape 500 galeri dari marketplace. Satu mesin akan butuh 10 jam. Dengan 5 worker, master split 500 URL jadi 5 batch @ 100, dispatch ke masing-masing worker. Total waktu ~2 jam. Setelah selesai, file di-aggregate dari tiap worker ke folder master via script rsync.

### Skenario 3: Offload Playwright ke mesin kuat

Laptop tipis user adalah master; Playwright di laptop bikin kipas ngamuk dan RAM full. Dia punya desktop tower RTX 3090 di ruangan lain. Install PyScrapr di tower, set sebagai worker, aktifkan Playwright di worker. Master dispatch job rendering-heavy ke tower, laptop tetap adem untuk UI dan job ringan.

## Pengaturan detail

### worker_mode

String, nilai: `standalone` (default), `master`, `worker`. Menentukan peran node. Restart server wajib setelah ubah.

### worker_enabled

Boolean, default `false`. Master switch untuk cluster mode. Ketika `false`, master tetap mode standalone meski `worker_mode=master`.

### worker_auth_token

String shared secret. Default kosong. **Harus diisi** sebelum production use; kosong berarti open endpoint (bahaya). Minimal 32 karakter random, gunakan password generator.

### worker_pool

String atau list URL worker. Format: comma-separated `http://w1:8585,http://w2:8585` atau newline-separated di UI textarea. URL harus include scheme (http/https) dan port.

### worker_dispatch_strategy

String, nilai: `round_robin` (default), `random`, `least_loaded`.

- `round_robin`: rotate dispatch ke worker berurutan. Fair tapi tidak aware beban.
- `random`: pilih acak. Sederhana, cocok untuk pool homogen.
- `least_loaded`: pilih worker dengan metric load terendah (dilihat dari `/health` endpoint). Butuh extra round-trip health check tapi lebih efisien untuk mesin heterogen.

### worker_health_interval_sec

Integer, default 30. Master polling `/health` tiap interval untuk update status worker. Turunkan jadi 10 untuk deteksi failure lebih cepat; naikkan jadi 60 untuk hemat traffic.

### worker_timeout_sec

Integer, default 10. Timeout HTTP request master ke worker. Naikkan untuk link lambat atau worker sibuk.

### worker_fallback_to_local

Boolean, default `true`. Jika `true`, ketika semua worker down, master jalankan job lokal sebagai fallback. Jika `false`, job error dengan status "no worker available".

### worker_ssl_verify

Boolean, default `true`. Untuk worker lewat HTTPS dengan self-signed cert, set `false`. Hanya pakai di LAN trusted.

## Tips & best practices

1. **Gunakan token random panjang.** Password generator 40 karakter minimum. Token pendek atau dictionary word bisa di-brute force kalau endpoint terekspos.

2. **Pisahkan cluster network dari internet.** Idealnya worker di LAN private atau VPN (Tailscale, WireGuard). Eksposisi ke WAN butuh HTTPS dan firewall ketat.

3. **Monitor worker health rutin.** Setup job cron atau external monitoring yang curl `/api/cluster/workers` setiap 5 menit. Alert kalau ada worker down.

4. **Version sync antar node.** Master dan worker harus versi major sama. API schema bisa berubah antar minor version dan menyebabkan deserialize error.

5. **Dokumentasi worker pool.** Simpan list URL worker di knowledge base internal, siapa owner mesin, lokasi fisik, dan spec. Memudahkan troubleshooting saat satu worker tiba-tiba down.

6. **Test failover.** Sengaja matikan satu worker, cek apakah master re-dispatch ke worker lain dengan benar. Simulasi failure sebelum terjadi di production.

7. **Jangan dispatch CPU-heavy ke laptop kecil.** Kalau worker laptop tipis, dispatch hanya job ringan (URL Mapper, small Harvester). Beri strong machine untuk Playwright, CLIP, yt-dlp.

8. **Rotasi token berkala.** Tiap 3-6 bulan, generate token baru dan update di semua node secara tandem. Hindari token static selama bertahun-tahun.

9. **Isolasi output folder.** Worker simpan hasil di disk lokal. Jangan asumsi output bisa diakses dari master secara langsung kecuali ada share mount (SMB, NFS). Pakai endpoint proxy untuk transfer file.

10. **Batching URL supaya efisien.** Daripada dispatch 1 URL per job, batch 50-100 URL per job ke worker. Overhead HTTP dispatch jadi amortize.

## Troubleshooting

### Problem: Worker status down padahal server jalan

**Gejala:** `/api/cluster/workers` menampilkan worker "down" dengan error "connection refused" atau "timeout".

**Penyebab:** Firewall di mesin worker block inbound port 8000, atau worker bind `127.0.0.1` saja (tidak `0.0.0.0`), atau URL salah.

**Solusi:** Di worker, verifikasi `uvicorn` di-start dengan `--host 0.0.0.0`. Di firewall, allow inbound port 8000 dari IP master. Test dari master: `curl http://worker.local:8585/api/worker/health`. Jika gagal, fix di worker dulu.

### Problem: 401 Unauthorized saat dispatch

**Gejala:** Master dapat response 401 saat POST `/api/worker/submit`.

**Penyebab:** Token master dan worker beda, atau worker belum baca setting terbaru.

**Solusi:** Pastikan `worker_auth_token` persis sama di kedua node. Restart worker setelah ubah token. Verifikasi dengan curl plus header:

```bash
curl -H "X-Auth-Token: <token>" http://worker.local:8585/api/worker/health
```

### Problem: Job dispatch tapi tidak ada progress update

**Gejala:** Master menampilkan status "dispatched" selamanya, tidak pernah jadi "running" atau "done".

**Penyebab:** Polling endpoint gagal (mungkin network blip) atau worker crash saat eksekusi tanpa notifikasi.

**Solusi:** Akses UI worker langsung di browser, cek History. Jika job ada di worker dengan status done, master kehilangan koneksi polling saja; fix connectivity. Jika job tidak ada di worker, dispatch gagal, retry.

### Problem: Load balancer stuck di satu worker

**Gejala:** Dengan `round_robin`, semua job selalu masuk worker pertama.

**Penyebab:** Worker lain down dan master hanya pakai yang up. Atau state round-robin counter rusak.

**Solusi:** Cek health, pastikan minimal 2 worker up. Untuk `least_loaded`, inspect endpoint health untuk pastikan load metric di-report (bukan selalu 0).

### Problem: File output di worker, tidak di master

**Gejala:** Job selesai tapi file hasil tidak muncul di folder `data/output/` master.

**Penyebab:** Arsitektur cluster memang simpan file di worker lokal. Master hanya simpan metadata.

**Solusi:** Akses file via `/api/cluster/remote-job/{worker_url}/{job_id}/files` di master. Atau SSH/share folder manual. Atau setup auto-sync rsync antar node. Ini by-design; PyScrapr belum punya transfer otomatis.

### Problem: Version mismatch error

**Gejala:** Error `API schema mismatch: master 1.0.0, worker 0.9.0`.

**Penyebab:** Upgrade master tapi lupa upgrade worker.

**Solusi:** Update semua node ke versi yang sama. PyScrapr check version compat saat dispatch dan refuse kalau beda major.

### Problem: Worker CPU maxed out, master tidak tahu

**Gejala:** Worker di-dispatch terus padahal CPU 100%.

**Penyebab:** `worker_dispatch_strategy` bukan `least_loaded`, atau metric load dari `/health` tidak akurat.

**Solusi:** Switch ke `least_loaded`. Verifikasi endpoint health return load number realistic (0 sampai 1). Atau tambah logic cap max concurrent job per worker di config.

## Keamanan / batasan

- Shared token adalah secret sederhana, bukan kripto-kuat. Jangan pakai untuk deployment public internet tanpa HTTPS dan firewall tambahan.
- Token kosong = siapapun bisa submit job. PyScrapr akan warn di log startup; jangan ignore.
- Tidak ada end-to-end encryption payload antara master dan worker kecuali pakai HTTPS. Setup reverse proxy Caddy atau Nginx dengan TLS untuk WAN.
- Tidak ada job persistence lintas restart; kalau master restart saat job di worker masih jalan, master lose track dan butuh manual recovery via worker history.
- Tidak ada retry otomatis antar worker. Kalau worker crash, job di-dispatch di situ akan jadi zombie; master tidak otomatis pindah ke worker lain.
- File output stay di worker lokal; tidak ada otomatis transfer ke master. Integrasi file system manual.
- Tidak ada sandboxing worker; job arbitrary bisa eksekusi Python pipeline di worker. Jangan terima dispatch dari master yang tidak terpercaya.
- Tidak ada rate limiting di endpoint worker; master bisa banjiri worker dengan job tanpa back-pressure.
- Load metric simplistic (running job count); tidak aware CPU, RAM, atau disk real.
- UI cluster management masih minimal; banyak operasi hanya lewat API saat ini.
- Koneksi worker harus accessible dari master; tidak ada reverse-connect mode untuk worker di belakang NAT tanpa port forward.

## Related docs

- [REST API](/docs/advanced/rest-api.md) - Endpoint cluster dispatch dan status terintegrasi dengan REST API umum.
- [Settings](/docs/system/settings.md) - Section Cluster untuk konfigurasi terpusat.
- [Webhooks](/docs/advanced/webhooks.md) - Worker bisa fires webhook sendiri; atau master aggregate webhook.
- [History](/docs/system/history.md) - Remote job indicator di History menampilkan worker asal.
- [Proxy Rotation](/docs/advanced/proxy.md) - Tiap worker bisa punya proxy berbeda untuk rotasi IP level cluster.
