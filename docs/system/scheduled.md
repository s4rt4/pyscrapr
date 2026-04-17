# Scheduled Jobs

> Sistem penjadwalan recurring job berbasis APScheduler dengan cron expression, sehingga PyScrapr bisa menjalankan harvest, ripper, atau media download secara otomatis tanpa intervensi manual.

## Deskripsi

Scheduled Jobs adalah fitur yang mengubah PyScrapr dari sekadar on-demand scraper menjadi automation platform. Alih-alih menekan tombol Submit setiap kali Anda butuh data terbaru dari situs tertentu, Anda cukup mendefinisikan jadwal dalam format cron (misal setiap hari jam 3 pagi, atau setiap 6 jam), dan sistem akan secara otomatis mendispatch job sesuai konfigurasi yang telah disimpan. Fitur ini sangat cocok untuk use case monitoring perubahan konten, backup harian, atau ingestion data berkala.

Di balik layar, Scheduled Jobs memanfaatkan library APScheduler (Advanced Python Scheduler) yang berjalan sebagai background scheduler di proses FastAPI. Setiap schedule yang Anda buat tersimpan dalam dua tempat: dictionary in-memory `_schedules` yang menyimpan metadata (nama, cron expr, konfigurasi tool, enable flag) dan APScheduler job store internal yang mengelola timing actual. Ketika trigger cron-nya cocok dengan waktu sekarang, APScheduler akan memanggil callback yang meneruskan request ke modul `bulk._dispatch`, modul yang sama yang juga dipakai oleh Bulk URL Queue. Dengan cara ini, baik bulk submission maupun scheduled trigger melewati jalur eksekusi yang konsisten.

Format cron expression yang dipakai adalah standard 5-field Unix cron: `minute hour day month weekday`. Field satu per satu diisi dengan angka literal, range (misal `1-5`), list (`1,3,5`), step (`*/2`), atau wildcard `*`. Misalnya ekspresi `0 3 * * *` berarti "menit ke-0, jam ke-3, tiap hari, tiap bulan, tiap hari dalam minggu" — yang artinya jam 3 pagi tiap hari. Ekspresi `0 */6 * * *` berarti tiap 6 jam mulai jam 0 (sehingga fires di jam 0, 6, 12, 18). PyScrapr tidak menambahkan field detik atau tahun seperti beberapa implementasi cron lain; kami sengaja mempertahankan standar 5-field agar familiar bagi admin Linux.

Karena schedules disimpan in-memory (bukan di database persistent), restart server akan kehilangan state. Namun PyScrapr melakukan dump ke `data/schedules.json` saat shutdown graceful dan restore saat startup, sehingga dalam praktik jadwal tetap persisten kecuali crash mendadak. Untuk production use case yang butuh HA, Anda dapat mengkonfigurasi APScheduler job store berbasis database (SQLAlchemyJobStore) — namun default-nya memory store cukup untuk tool personal.

## Kapan pakai?

1. **Content monitoring harian** — Scrape situs berita kompetitor atau forum komunitas setiap pagi agar selalu punya snapshot konten terbaru.
2. **Backup recurring situs sendiri** — Jalankan Site Ripper setiap minggu untuk arsip offline blog atau dokumentasi Anda.
3. **Tracking harga e-commerce** — Harvester terhadap listing produk setiap 6 jam untuk mendeteksi perubahan harga via Diff Detection.
4. **Ingestion RSS/sitemap** — URL Mapper terhadap sitemap.xml setiap hari agar punya graph struktur situs yang up-to-date.
5. **Media collection** — Media Downloader terhadap channel YouTube atau playlist tertentu setiap hari untuk grab video baru otomatis.
6. **Compliance & audit** — Scraping halaman yang wajib diaudit (misal terms-of-service situs partner) secara berkala untuk deteksi perubahan.
7. **Research longitudinal** — Data akademik yang butuh snapshot konsisten setiap hari, minggu, atau bulan untuk analisis time-series.
8. **Warming cache & prefetch** — Jalankan job kecil menjelang peak time agar data yang Anda konsumsi sudah fresh saat dibutuhkan.

## Cara penggunaan

1. Buka menu Scheduled dari navbar sidebar atau akses langsung `/scheduled`.
2. Di halaman utama, Anda akan melihat tabel daftar schedules existing dengan kolom: Name, Tool, Cron Expression, Next Run, Last Run, Status (enabled/disabled), dan Actions.
3. Untuk membuat schedule baru, klik tombol "+ New Schedule" di pojok kanan atas halaman.
4. Modal form muncul. Isi field Name dengan label deskriptif seperti "Daily news scrape" atau "Weekly backup rip".
5. Pilih Tool dari dropdown: Harvester, Ripper, Mapper, Media, atau Scraper klasik. Field konfigurasi yang muncul menyesuaikan tool.
6. Isi konfigurasi tool sebagaimana Anda mengisinya di halaman tool masing-masing — URL target, depth, filters, dan seterusnya. Ini akan menjadi preset yang dipakai tiap kali schedule fires.
7. Masukkan Cron Expression. Tersedia preset dropdown (Hourly, Daily, Weekly, Custom) atau ketik langsung 5-field expression.
8. Gunakan tombol "Validate" di sebelah input cron untuk memastikan expression valid dan preview next 3 run times sebelum save.
9. Klik Save. Schedule langsung registered ke APScheduler dan tabel diupdate dengan row baru.
10. Untuk toggle enable/disable, klik switch di kolom Status pada row. Disable akan menghentikan future triggers tanpa menghapus schedule.
11. Untuk edit, klik icon pencil di kolom Actions. Modal terbuka dengan nilai existing; ubah lalu Save.
12. Untuk delete, klik icon trash. Konfirmasi dialog muncul — setelah delete, schedule hilang dari memory dan job store APScheduler.

## Pengaturan / Konfigurasi

Form create/edit schedule terdiri dari field berikut:

- **name** (string, required) — Label human-readable untuk schedule. Tidak perlu unik tapi sebaiknya deskriptif. Maksimal 100 karakter.
- **tool** (enum, required) — Salah satu dari `harvester`, `ripper`, `mapper`, `media`, `scraper`. Menentukan endpoint submit mana yang dipanggil saat fires.
- **url** (string, required) — Target URL. Validasi basic scheme (http/https) dilakukan di frontend dan backend.
- **cron_expr** (string, required) — Expression 5-field. Contoh valid: `0 3 * * *`, `*/15 * * * *`, `0 9 * * 1-5` (weekday jam 9).
- **config** (object, optional) — Object JSON berisi tool-specific options. Struktur mengikuti schema submit endpoint tool (misal harvester punya `depth`, `image_filter`; ripper punya `max_pages`, `respect_robots`).
- **enabled** (boolean, default true) — Jika false, schedule tetap tersimpan tapi tidak akan fires sampai di-toggle true.
- **timezone** (string, optional) — IANA timezone seperti `Asia/Jakarta` atau `UTC`. Default mengikuti server timezone. Cron expression di-interpret dalam timezone ini.
- **max_instances** (int, default 1) — Jumlah maksimum instansi job yang boleh running bersamaan dari schedule yang sama. Default 1 mencegah overlap jika job sebelumnya belum selesai ketika trigger berikutnya datang.
- **coalesce** (boolean, default true) — Jika beberapa trigger terlewat (misal server down), apakah APScheduler merge jadi satu trigger atau fires semua yang tertinggal. True = merge.
- **misfire_grace_time** (int, default 60) — Detik toleransi keterlambatan sebelum trigger dianggap missed. Berguna jika server busy dan tidak bisa fires tepat waktu.
- **tags** (array of string, optional) — Label untuk grouping dan filter di tabel. Misal `["daily", "high-priority"]`.
- **on_fire_webhook** (boolean, default false) — Jika true, webhook akan dipicu tiap kali schedule fires (bukan hanya saat job done/error). Berguna untuk monitoring schedule health.

Semua field tersimpan di-memory dan didump ke `data/schedules.json` saat shutdown. File ini plain JSON array yang bisa Anda edit manual jika perlu (lalu restart untuk reload).

## Output

Scheduled sendiri tidak menghasilkan file output langsung. Yang dihasilkan adalah side-effect berupa job baru yang ter-create di History setiap kali schedule fires. Job tersebut mengikuti flow normal masing-masing tool:

- **Job record** — Tercatat di DB job dengan field `source: "schedule"` dan `schedule_id` mengacu ke ID schedule parent.
- **Files** — Output file (HTML, media, manifest) tersimpan di folder downloads sesuai tool, sama seperti job manual.
- **Logs** — Fire events (trigger fired, dispatch success/fail) tertulis ke application log.
- **Next run info** — Setelah fires, tabel schedules diupdate dengan `last_run` timestamp dan `next_run` kalkulasi baru.

Jika Anda butuh notifikasi saat schedule fires, aktifkan `on_fire_webhook` atau gunakan Webhooks level global dengan trigger "on job done".

## Integrasi dengan fitur lain

- **Bulk Queue** — Schedules menggunakan `bulk._dispatch` internally, jadi struktur payload dispatch konsisten dengan bulk submission manual.
- **Webhooks** — Pair dengan Webhooks untuk notifikasi Discord/Telegram tiap kali schedule fires atau job hasilnya error.
- **Diff Detection** — Schedule repeat untuk URL yang sama menghasilkan run berurutan — perfect case untuk Diff comparing run A vs run B.
- **History** — Semua scheduled runs muncul di History dengan filter `source: schedule` untuk isolasi dari manual jobs.
- **Settings** — Default timezone dan misfire_grace_time global diatur di Settings.
- **Dashboard** — Widget "Upcoming Scheduled" menampilkan 3 next-fire dari dashboard homepage.
- **REST API Generator** — Data hasil scheduled runs dapat langsung di-serve via `/api/data/{job_id}`.

## Tips & Best Practices

1. **Jangan set interval terlalu agresif** — Setiap menit (`* * * * *`) jarang dibutuhkan dan membebani target situs serta disk lokal. Mulai dari jam-an atau harian.
2. **Gunakan waktu off-peak** — Untuk recurring daily, pilih jam 2-5 pagi agar target situs tidak terbebani dan bandwidth Anda bebas.
3. **Beri nama dengan konvensi** — Prefix nama dengan tool (`[MEDIA] Daily YouTube`, `[RIPPER] Weekly Blog`) agar filter dan scan tabel mudah.
4. **Test manual dulu sebelum schedule** — Pastikan konfigurasi tool bekerja benar via submit manual sekali; baru kemudian buat schedule dengan konfigurasi yang sama.
5. **Aktifkan webhook on_fire untuk schedule kritikal** — Agar tahu kalau schedule tidak fires (misal karena server down) melalui absence of webhook.
6. **Batasi max_instances ke 1** — Untuk mencegah overlap yang bisa merusak file karena dua job menulis ke path yang sama.
7. **Review tabel schedules bulanan** — Disable atau delete schedule yang sudah tidak relevan untuk menghemat resource.
8. **Backup file schedules.json** — Simpan salinan file `data/schedules.json` agar bisa restore cepat jika DB/app rusak.

## Troubleshooting

**Problem: Schedule dibuat tapi tidak pernah fires.**
Cause: APScheduler scheduler belum start di backend, atau enabled=false tidak sengaja.
Solution: Cek log startup apakah "Scheduler started" muncul. Toggle enabled di UI untuk memastikan true. Restart server jika perlu.

**Problem: Cron expression ditolak dengan error "invalid format".**
Cause: Syntax 5-field tidak benar, misal penggunaan `?` seperti Quartz cron atau 6-field dengan detik.
Solution: Gunakan format standard Unix cron. Test dulu via `crontab.guru` online, kemudian paste ke PyScrapr.

**Problem: Job fires dua kali dalam waktu sangat dekat.**
Cause: Dua schedule dengan config hampir sama, atau `coalesce=false` dengan misfire membuat trigger doubled.
Solution: Cari duplikat di tabel. Set coalesce=true. Set max_instances=1.

**Problem: Last run timestamp tidak terupdate walaupun job sebenarnya running.**
Cause: Bug di callback update atau race condition antara APScheduler dan state writer.
Solution: Cek log untuk exception dalam callback. Manual refresh halaman Scheduled. Restart server sebagai last resort.

**Problem: Schedule hilang setelah restart server.**
Cause: File `data/schedules.json` tidak ter-write (crash sebelum shutdown graceful).
Solution: Selalu stop server dengan Ctrl+C (bukan kill -9). Backup file ini secara berkala. Untuk HA, pindah ke SQLAlchemyJobStore.

**Problem: Next run time tampil "in past".**
Cause: Timezone mismatch antara server dan client browser, atau cron interpretasi dalam UTC tapi ditampilkan dalam local time.
Solution: Set `timezone` di schedule ke IANA yang Anda inginkan. Verifikasi server clock sinkron (NTP).

**Problem: Schedule fires tapi job-nya error "Invalid config".**
Cause: Config tool berubah (field baru required), tapi config tersimpan schedule masih format lama.
Solution: Edit schedule, isi ulang field baru, save. Atau hapus dan recreate.

**Problem: Tampilan tabel schedule lambat dimuat.**
Cause: Terlalu banyak schedule (> 500) dan polling interval pendek.
Solution: Archive atau delete schedule lama. Tingkatkan polling interval di Settings.

**Problem: Webhook on_fire tidak terkirim walaupun job fires.**
Cause: Webhook config kosong atau URL webhook invalid; event bus listener tidak terhubung.
Solution: Test webhook di Settings (tombol "Send test"). Verifikasi `on_fire_webhook: true` di schedule config.

## FAQ

**Q: Apakah bisa menjalankan schedule saat server baru dihidupkan jika ada yang terlewat?**
A: Ya, dengan `coalesce=true` dan `misfire_grace_time` cukup besar, APScheduler akan merge missed triggers dan fires sekali saat startup.

**Q: Berapa maksimum schedules yang bisa didaftarkan?**
A: Tidak ada hard limit dari APScheduler. Praktikal limit sekitar 1000 sebelum performance UI menurun.

**Q: Bagaimana cara menjalankan schedule sekali lalu otomatis terhapus?**
A: Gunakan cron yang spesifik tanggal (misal `0 3 15 4 *` untuk 15 April jam 3 pagi) lalu delete manual setelah fires. Atau gunakan fitur one-shot yang berbeda (Bulk Queue delayed).

**Q: Bisakah schedule dipicu manual di luar cron?**
A: Ya, ada tombol "Run now" di row yang men-trigger dispatch langsung tanpa menunggu cron.

**Q: Apakah waktu eksekusi schedule akurat ke detik?**
A: APScheduler fires di awal menit cron, dengan akurasi 1-2 detik tergantung beban server.

**Q: Apakah schedule bisa dependen satu sama lain (chain)?**
A: Tidak built-in. Untuk dependency chain, gunakan webhook dari job A untuk trigger endpoint yang submit job B.

**Q: Apakah config schedule bisa dinamis (misal tanggal di URL berubah)?**
A: Tidak di UI, tapi jika edit langsung `schedules.json` Anda bisa pakai variable substitution custom (butuh modifikasi kode).

**Q: Bagaimana schedule menangani daylight saving time?**
A: APScheduler DST-aware jika timezone IANA diisi. UTC tidak kena DST.

**Q: Bisakah saya pause semua schedules sekaligus?**
A: Ya, ada tombol "Pause all" di toolbar yang set enabled=false untuk semua rows sekaligus.

**Q: Apakah schedule berjalan jika komputer sleep?**
A: Tidak. APScheduler butuh proses aktif. Jika laptop sleep, schedule yang terlewat akan miss atau di-coalesce saat wake.

## Keterbatasan

- Tidak ada GUI builder visual untuk cron expression (harus paham notasi); walau ada preset, custom tetap text-based.
- Storage in-memory default tidak HA; butuh konfigurasi manual untuk DB job store.
- Tidak ada dependency chain antar schedule (harus via webhook workaround).
- Maksimal 1 instance per schedule default (bisa dinaikkan tapi sering berbahaya).
- Tidak ada built-in retry policy per schedule (retry diatur di level job, bukan schedule).
- History untuk audit schedule changes (siapa edit kapan) tidak tersedia.
- Tidak ada fitur "run once at future date" khusus (harus pakai cron one-time atau tool eksternal).

## Related docs

- [Bulk Queue](../advanced/bulk-queue.md) — Dispatcher yang sama, untuk one-time multiple URLs.
- [Webhooks](../advanced/webhooks.md) — Notifikasi saat schedule fires atau job hasil.
- [Diff Detection](./diff.md) — Bandingkan hasil antar run dari schedule yang sama.
- [History](./history.md) — Filter `source: schedule` untuk audit runs.
- [Settings](./settings.md) — Konfigurasi global timezone dan default misfire.
