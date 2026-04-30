# Dashboard

> Halaman beranda PyScrapr yang memberikan ringkasan satu-layar untuk seluruh aktivitas scraping, statistik penggunaan, dan akses cepat ke semua tool.

## Deskripsi

Dashboard adalah pintu masuk utama (landing page) ketika Anda membuka PyScrapr melalui URL root `/`. Halaman ini dirancang sebagai command center yang memadatkan informasi paling penting dari seluruh sistem ke dalam satu viewport, sehingga Anda tidak perlu melompat-lompat antar halaman hanya untuk mengetahui status job, kapasitas disk, atau tool mana yang paling sering digunakan. Prinsip desainnya adalah "glance-ability" - artinya dalam waktu kurang dari tiga detik setelah halaman dimuat, pengguna sudah bisa menjawab pertanyaan dasar seperti "ada job yang gagal tadi malam?" atau "masih cukup disk untuk job besar hari ini?".

Secara arsitektur, Dashboard bukanlah halaman statis. Ia adalah React component yang memakai TanStack Query untuk polling endpoint aggregation setiap beberapa detik, sehingga angka counter selalu sinkron dengan state aktual di backend. Layout terbaru menampilkan grid tile **P1 sampai P8** (Image Harvester, URL Mapper, Site Ripper, Media Downloader, AI Tagger, Tech Fingerprinter, Screenshotter, Threat Scanner) di baris atas, diikuti baris **Audit & Intel** untuk SEO Auditor, Broken Link Checker, Security Headers, SSL Inspector, Domain Intel, Wayback Explorer, dan Sitemap Analyzer. Tiap tile mengambil counter dari endpoint `/api/stats/{tool}` yang menghitung job berdasarkan status phase - `pending`, `running`, `done`, `error`, dan `stopped`.

Selain grid tile, Dashboard sekarang dibekali komponen visual dari `@mantine/charts`: **AreaChart 14 hari** untuk tren aktivitas job harian, dan **DonutChart distribusi job** per tool. Data chart datang dari endpoint `/api/system/dashboard/timeseries`. Semua agregasi dilakukan di backend agar frontend ringan dan tidak perlu mengiterasi ratusan record job di browser. Palet warna tile selaras dengan ikon berwarna di sidebar sehingga ada continuity visual saat berpindah halaman.

Dashboard juga menjalankan peran pedagogis: bagi pengguna baru yang belum pernah menjalankan job sekalipun, tampilan default akan menampilkan quick action buttons besar yang mengarahkan mereka ke Media Downloader, URL Mapper, atau Site Ripper, lengkap dengan deskripsi singkat "apa yang dilakukan tool ini". Untuk pengguna existing, quick action tetap ada namun diposisikan lebih subtle dan digeser oleh daftar "Recent 5 jobs" yang lebih relevan untuk kebutuhan sehari-hari.

Dari sisi implementasi, halaman ini mengkonsumsi beberapa endpoint aggregation sekaligus dan menggunakan Mantine Grid + Card components untuk layout responsif. Grid P1-P8 mengisi baris pertama (4 kolom di desktop, 2 di tablet, 1 di mobile), diikuti grid Audit/Intel (juga 4 kolom desktop), kemudian dua kolom chart, dan terakhir tabel "Recent jobs". Warna badge status konsisten dengan tema design system: hijau untuk done, merah untuk error, biru untuk running, abu-abu untuk pending, dan kuning untuk warning seperti disk space hampir penuh.

## Kapan pakai?

1. **Morning check-in** - Membuka PyScrapr pertama kali di pagi hari untuk melihat apakah scheduled jobs yang berjalan semalam selesai dengan baik atau ada yang error.
2. **Monitoring cepat di sela pekerjaan** - Ketika job besar sedang berjalan di background, Anda ingin sekilas memastikan progress tanpa harus masuk ke halaman History detail.
3. **Audit penggunaan disk** - Sebelum memulai Site Ripper pada domain besar, cek progress bar disk usage di Dashboard untuk memastikan ada ruang cukup.
4. **Navigasi cepat** - Gunakan tile tool sebagai shortcut ke halaman tool masing-masing; satu klik dari Dashboard langsung masuk ke form Media Downloader, Harvester, atau lainnya.
5. **Debugging awal** - Saat ada report "job gagal", buka Dashboard dulu untuk melihat tool mana yang punya error counter tinggi sebelum drill-down ke History.
6. **Onboarding user baru** - Ketika memperkenalkan PyScrapr ke orang lain, Dashboard berfungsi sebagai peta visual seluruh kemampuan aplikasi dalam satu screen.
7. **Weekly reporting** - Ambil screenshot Dashboard pada akhir minggu untuk dokumentasi statistik penggunaan (total jobs completed, data harvested, dan sebagainya).
8. **Kapasitas planning** - Melihat tren jumlah job dan disk usage selama beberapa hari untuk memprediksi kapan perlu upgrade storage atau cleaning folder downloads.

## Cara penggunaan

1. Buka browser dan akses URL PyScrapr (default `http://localhost:8585/`). Dashboard otomatis dimuat sebagai route `/`.
2. Tunggu 1-2 detik sampai semua tile terisi data. Indikator loading skeleton akan berubah menjadi angka actual begitu endpoint aggregation merespons.
3. Scan baris atas yang berisi "Overall Stats" - Total Jobs, Completed, Error Rate, dan Storage Used. Angka ini adalah agregat dari seluruh tool.
4. Pindai grid tile tool di bawahnya. Tiap tile menampilkan nama tool, icon, counter total/done/error, dan link "Open tool".
5. Perhatikan jika ada tile dengan badge merah menandakan error rate tinggi - klik tile tersebut untuk masuk ke halaman tool dan lihat detail.
6. Scroll ke bagian "Recent Activity" yang berisi 5 job terbaru dari semua tool, diurutkan berdasarkan created_at descending.
7. Tiap row recent job menampilkan: tool badge berwarna, URL (truncated dengan tooltip full URL), status dot, dan time-ago relatif ("5 min ago", "2 hours ago").
8. Klik row job untuk membuka detail job di halaman History atau tool yang bersangkutan.
9. Cek progress bar "Disk Usage" di sidebar atau footer Dashboard. Bar ini menampilkan rasio folder downloads vs total free disk.
10. Jika warna progress bar berubah kuning (>70%) atau merah (>90%), pertimbangkan cleanup folder downloads lewat File Explorer atau Settings.
11. Gunakan tombol Quick Action di bagian atas atau bawah (tergantung state user) untuk memulai job baru langsung dari Dashboard.
12. Biarkan halaman tetap terbuka di tab browser sebagai monitoring pasif; auto-refresh akan memperbarui angka tanpa perlu reload manual.

## Pengaturan / Konfigurasi

Dashboard tidak memiliki halaman konfigurasi tersendiri, namun beberapa aspek perilakunya dipengaruhi oleh setting global di halaman Settings:

- **ui_refresh_interval** - Angka dalam detik yang menentukan seberapa sering TanStack Query melakukan refetch ke endpoint aggregation. Default 3 detik. Nilai lebih rendah (1-2 detik) memberikan update lebih realtime namun sedikit menambah beban server. Nilai lebih tinggi (5-10 detik) cocok untuk mesin low-resource.
- **dashboard_recent_count** - Jumlah job yang ditampilkan di bagian Recent Activity. Default 5. Bisa diubah ke 10 atau 20 jika ingin melihat lebih banyak histori singkat di Dashboard.
- **disk_warning_threshold** - Persentase disk usage yang memicu warna kuning pada progress bar. Default 70%.
- **disk_critical_threshold** - Persentase yang memicu warna merah dan peringatan overlay. Default 90%.
- **downloads_path** - Path folder yang dihitung sebagai "Storage Used". Default `data/downloads/` relatif ke root app.
- **show_quick_actions** - Boolean toggle untuk menampilkan/menyembunyikan panel quick actions. User berpengalaman mungkin lebih suka tampilan minimalis tanpa CTA.
- **default_tool_order** - Array string yang mengatur urutan tile tool di grid. Misalnya `["media", "ripper", "mapper", "harvester", "scraper"]` akan menaruh Media Downloader di posisi pertama.
- **stats_include_stopped** - Apakah job dengan status `stopped` (dihentikan manual oleh user) dihitung sebagai error atau dikecualikan dari total. Default false (tidak dihitung sebagai error).

Semua field di atas dapat diedit dari halaman Settings. Perubahan tersimpan di `data/settings.json` dan Dashboard akan mengambil nilai baru pada refresh berikutnya tanpa perlu restart server.

## Output

Dashboard tidak menghasilkan file output karena sifatnya read-only. Namun ia "memproduksi" informasi visual berikut:

- **Numerical counters**: angka integer yang diupdate realtime untuk total jobs, completed, error, dan disk bytes.
- **Progress bars**: visual representation persentase disk usage dan, opsional, progress running jobs individual.
- **Colored badges**: indikator status pada tiap recent job row (hijau/merah/biru/abu/kuning).
- **Time-ago strings**: format relatif seperti "just now", "5 min ago", "3 hours ago", "yesterday", "3 days ago".
- **Click-through links**: setiap tile dan row adalah anchor yang mengarahkan ke halaman detail; bukan output data tapi output navigasi.

Jika Anda butuh output tabular yang bisa di-export, gunakan halaman History yang memiliki fitur Export CSV/JSON/Excel. Dashboard sendiri tidak menyediakan tombol export karena posisinya sebagai overview, bukan reporting tool formal.

## Integrasi dengan fitur lain

- **History** - Klik tombol "View all" atau row recent job untuk drill-down ke halaman History dengan filter tool yang sama.
- **Settings** - Beberapa konfigurasi (refresh interval, thresholds) diambil dari Settings. Link langsung ke Settings tersedia di icon gear di navbar.
- **Webhooks** - Jika suatu event memicu webhook, indikator "webhook fired" bisa muncul di Recent Activity row (opsional, tergantung setting).
- **Scheduled Jobs** - Upcoming scheduled jobs ditampilkan di widget Dashboard (jika enabled), dengan link ke halaman Scheduled untuk edit.
- **Diff Detection** - Jika ada job yang memiliki diff notable vs run sebelumnya, indikator Δ akan muncul di row job.
- **Tool pages** - Setiap tile adalah shortcut ke halaman tool masing-masing (Harvester, Ripper, Mapper, Media, Scraper klasik).
- **Bulk Queue** - Ketika ada batch bulk aktif, counter dedicated muncul di Dashboard dengan progress group.

## Tips & Best Practices

1. **Jadikan tab pinned** - Pin tab Dashboard di browser Anda agar selalu satu klik dari mana saja; auto-refresh akan membuatnya tetap up-to-date tanpa usaha.
2. **Monitor disk usage secara preventif** - Jangan tunggu sampai merah. Ketika bar kuning muncul, luangkan 5 menit untuk cleanup folder downloads lama.
3. **Gunakan Recent Activity sebagai audit trail cepat** - Sebelum panik karena "data hilang", cek dulu di Dashboard apakah job sempat running atau tidak.
4. **Tuning refresh interval sesuai kebutuhan** - Jika Anda multitasking dengan banyak tab, naikkan interval ke 5-10 detik untuk hemat bandwidth browser.
5. **Manfaatkan quick actions untuk job one-shot** - Untuk task satu kali cepat (misal download satu video), quick action dari Dashboard lebih efisien daripada navigasi manual.
6. **Perhatikan error rate trend** - Jika suatu tool konsisten menunjukkan error rate > 20%, ada pattern masalah yang perlu ditelusuri (misal target situs punya anti-bot baru).
7. **Kombinasikan dengan Scheduled** - Set jadwal, lalu Dashboard menjadi tempat cek apakah jadwal berjalan semestinya.
8. **Bookmark filter view** - Jika Anda sering melihat subset tertentu (misal hanya error), gunakan History dengan filter, bukan Dashboard yang bersifat agregat.

## Troubleshooting

**Problem: Angka counter di Dashboard tidak berubah walaupun sudah ada job baru.**
Cause: TanStack Query cache belum invalidate, atau polling interval terlalu lama.
Solution: Refresh halaman manual dengan F5, atau turunkan `ui_refresh_interval` di Settings. Pastikan juga backend berjalan dengan memeriksa `/api/health`.

**Problem: Disk usage progress bar menunjukkan 0% padahal folder downloads penuh.**
Cause: Path `downloads_path` di Settings salah atau tidak dapat diakses oleh proses server (permission issue pada Windows).
Solution: Verifikasi path di Settings benar dan folder exist. Pada Windows, pastikan proses uvicorn punya read permission ke folder tersebut.

**Problem: Recent Activity kosong padahal baru saja menjalankan job.**
Cause: Job masih di phase pending dan belum tercatat sebagai recent, atau sorting bug terkait timezone.
Solution: Tunggu 3-5 detik dan cek lagi. Jika tetap kosong, buka History langsung - masalah kemungkinan di query aggregation yang exclude pending jobs.

**Problem: Tile tool menampilkan error "Failed to load stats".**
Cause: Endpoint `/api/stats/{tool}` 500 error di backend, umumnya karena DB lock atau model mismatch setelah schema update.
Solution: Cek log server untuk stack trace. Restart backend. Jika persisten, hapus file DB sementara (setelah backup) untuk trigger recreate schema.

**Problem: Halaman lambat dimuat, lebih dari 5 detik.**
Cause: Terlalu banyak job history sehingga query aggregation lambat, atau disk usage calculation lambat untuk folder yang sangat besar.
Solution: Arsipkan job lama via Settings > Maintenance. Untuk disk calculation, pertimbangkan caching di backend dengan TTL 60 detik.

**Problem: Quick action buttons tidak muncul untuk user baru.**
Cause: Setting `show_quick_actions` di-toggle off, atau logic "new user detection" mendeteksi ada > 0 job di DB padahal sebenarnya semua job test.
Solution: Set ulang `show_quick_actions` ke true di Settings, atau hapus job dummy di History.

**Problem: Time-ago string menunjukkan "in 3 hours" (future).**
Cause: Timezone mismatch antara backend (UTC) dan client browser (local).
Solution: Verifikasi `timezone` setting di backend. Ideally store semua timestamp di UTC dan konversi ke local hanya di frontend.

**Problem: Klik tile tool tidak navigasi kemana-mana.**
Cause: JavaScript error di React Router, biasanya karena route definition berubah setelah update.
Solution: Buka console developer (F12) untuk lihat error. Clear cache browser. Pastikan frontend build up-to-date.

**Problem: Progress bar disk usage flickering antara dua angka berbeda.**
Cause: Race condition antara dua polling yang hit endpoint disk secara paralel, atau file sedang ditulis saat dihitung.
Solution: Naikkan debounce di backend untuk disk calculation. Ini issue kosmetik, tidak mempengaruhi fungsionalitas.

## FAQ

**Q: Apakah Dashboard bisa dicustomize layoutnya?**
A: Saat ini tidak ada drag-drop widget builder. Urutan tile bisa diubah via `default_tool_order` di Settings, tapi struktur utama (stats atas, tile grid, recent activity) fixed.

**Q: Berapa lama data Recent Activity disimpan?**
A: Recent Activity hanya menampilkan 5 job terbaru tanpa batas waktu. Data job itu sendiri tersimpan di DB selamanya kecuali Anda delete manual via History.

**Q: Apakah bisa mengatur Dashboard agar hanya menampilkan tool tertentu?**
A: Tidak langsung. Namun Anda bisa hide tool lewat CSS custom atau modifikasi komponen React (PyScrapr open untuk local modification).

**Q: Apakah Dashboard otomatis refresh ketika job baru selesai?**
A: Ya, dengan polling interval default 3 detik. Tidak menggunakan WebSocket saat ini, jadi ada slight delay maksimal sesuai interval.

**Q: Mengapa total count di Dashboard kadang berbeda dengan jumlah row di History?**
A: Dashboard total biasanya exclude job yang di-archive atau soft-deleted. History full view bisa include dengan filter "show archived".

**Q: Bagaimana cara reset counter statistik?**
A: Tidak ada tombol reset karena counter berasal dari query live. Hapus job di History untuk mengurangi count, atau arsipkan via Settings > Maintenance.

**Q: Apakah Dashboard menyimpan snapshot historis per hari?**
A: Tidak. Dashboard hanya menampilkan snapshot current state. Untuk historical tracking, lihat History dengan date filter.

**Q: Bisakah Dashboard di-embed ke dashboard eksternal seperti Grafana?**
A: Tidak langsung sebagai iframe, tapi data aggregation tersedia via endpoint `/api/stats/*` yang bisa di-scrape oleh Grafana atau tool lain.

**Q: Apakah aman membuka Dashboard di mobile?**
A: Ya, layout responsif. Namun beberapa tombol quick action optimal di desktop karena flow lanjutannya (form isi URL, konfigurasi) lebih enak di layar besar.

**Q: Apa yang terjadi jika backend down saat Dashboard terbuka?**
A: TanStack Query akan retry dengan exponential backoff. Setelah beberapa kegagalan, tile akan menampilkan error state dengan tombol "Retry". Halaman tidak crash.

## Keterbatasan

- Dashboard tidak mendukung real-time WebSocket push; update bergantung pada polling interval.
- Tidak ada customization layout drag-drop; struktur tile fixed (walau urutan bisa diatur).
- Time-ago calculation berbasis client clock; jika jam client salah, tampilan akan menyesatkan.
- Disk usage hanya mengukur folder downloads default; folder custom per-tool tidak diagregasi.
- Tidak ada notifikasi native browser dari Dashboard; untuk itu gunakan Webhooks atau integrasi eksternal.
- Widget scheduled jobs preview terbatas menampilkan 3 upcoming; selebihnya harus buka halaman Scheduled.
- Tidak tersedia export statistik Dashboard ke PDF/PNG built-in; gunakan screenshot manual.
- Disk threshold warning hanya visual, tidak memblokir submission job baru walaupun merah.

## Related docs

- [History](./history.md) - Daftar lengkap semua job dengan filter dan export.
- [Scheduled Jobs](./scheduled.md) - Atur recurring jobs yang muncul di widget Dashboard.
- [Settings](./settings.md) - Konfigurasi refresh interval, thresholds, dan urutan tile.
- [Webhooks](../advanced/webhooks.md) - Notifikasi eksternal bila Anda tidak ingin selalu buka Dashboard.
- [Diff Detection](./diff.md) - Indikator Δ yang muncul di Recent Activity berasal dari sini.
