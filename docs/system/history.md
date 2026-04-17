# History

> Halaman daftar lengkap semua job yang pernah dijalankan PyScrapr, lengkap dengan filter, export multi-format, dan re-run cepat.

## Deskripsi

History adalah log master semua aktivitas scraping yang pernah Anda lakukan di PyScrapr. Tidak peduli apakah job itu berasal dari Harvester, Ripper, Mapper, Media Downloader, Scraper klasik, utilities kecil, atau dispatch dari Scheduled/Bulk Queue - semuanya tercatat di sini dalam satu tabel terunifikasi. Halaman ini adalah tempat Anda pergi ketika butuh informasi "apa yang terjadi dengan job X", "kapan terakhir kali saya scraping situs Y", atau "export semua hasil ke CSV untuk laporan mingguan".

Secara arsitektur, History di-power oleh tabel `jobs` di database SQLite (atau PostgreSQL kalau Anda migrasi). Tiap row merepresentasikan satu job dengan field utama: `id` (UUID), `tool` (nama tool), `url` (target), `status` (pending/running/done/error/stopped), `config` (JSON dari konfigurasi saat submit), `result` (JSON ringkasan hasil), `created_at`, `started_at`, `completed_at`, dan `source` (manual/schedule/bulk). Halaman frontend memakai TanStack Query dengan auto-refresh setiap 3 detik untuk polling, sehingga status job yang sedang running terupdate realtime tanpa perlu reload manual.

Tabel History menampilkan kolom esensial: Type (badge berwarna per tool), URL (truncated dengan tooltip full URL), Status (colored dot + label), Downloaded Count (angka asset/page di-scrape), Source (ikon kecil: hand untuk manual, clock untuk schedule, stack untuk bulk), dan Time-ago relatif. Di kolom Actions terdapat dua tombol utama: Export (dropdown menu CSV/JSON/Excel) dan Re-run (clone config dan create job baru). Klik row akan membuka detail modal dengan full config, full result JSON, timeline event, dan log execution.

Untuk user baru yang belum punya job sama sekali, History menampilkan empty state dengan ilustrasi dan CTA "Start your first harvest" yang mengarahkan ke Media Downloader (entry tool paling beginner-friendly). Untuk user existing dengan banyak history, filter bar di atas tabel memungkinkan filter berdasarkan tool, status, date range, source, dan search URL. Kombinasi filter tersimpan di URL query string sehingga bisa di-bookmark atau di-share ke tim.

## Kapan pakai?

1. **Audit trail bulanan** - Export semua job bulan lalu ke Excel untuk laporan ke stakeholder atau arsip compliance.
2. **Debugging job gagal** - Filter status=error, klik row untuk lihat stack trace di detail modal dan cari pattern penyebab.
3. **Re-run job dengan config sama** - Ketika butuh ulang hasil job lama tanpa isi form dari nol, tombol Re-run clone config otomatis.
4. **Mencari job spesifik di historis** - Search URL partial untuk lokasi job lama yang Anda lupa tanggal pastinya.
5. **Sumber Diff pair** - Browse History untuk pilih dua job ID yang akan dibandingkan di Diff Detection.
6. **Validasi scheduled runs** - Filter source=schedule, verifikasi bahwa tiap fire sukses dan tidak skip.
7. **Cleanup storage** - Identifikasi job lama yang file-nya memakan disk, lalu delete selektif.
8. **Sharing hasil dengan tim** - Export JSON sebuah job lalu kirim ke kolega yang butuh data hasil scraping.

## Cara penggunaan

1. Akses halaman History via navbar sidebar atau URL `/history`.
2. Tabel default menampilkan semua job diurutkan berdasarkan `created_at` descending (terbaru di atas). Pagination 50 per halaman.
3. Di toolbar atas, ada filter: Tool (multi-select), Status (multi-select), Date Range (range picker), Source (dropdown), Search URL (text input).
4. Pilih filter sesuai kebutuhan. Tabel akan refetch otomatis dengan debounce 500ms setelah filter berubah.
5. Sorting bisa diubah dengan klik header kolom. Indikator arrow menandakan arah (asc/desc).
6. Scan row untuk temukan job yang Anda cari. Badge tool berwarna membantu scanning visual cepat.
7. Klik row untuk buka detail modal. Modal berisi tab: Overview, Config, Result, Timeline, Log.
8. Di tab Overview lihat summary cepat dan tombol action (Re-run, Delete, Open output folder).
9. Tab Config menampilkan JSON mentah konfigurasi saat submit - berguna untuk replicate atau troubleshoot.
10. Tab Result JSON summary dari hasil scraping. Tab Timeline menampilkan timestamped events (started, progress milestones, completed).
11. Untuk export single job, klik tombol "Export" di baris atau di modal detail. Pilih format: CSV, JSON, atau Excel.
12. Untuk bulk operation, centang checkbox multiple rows lalu gunakan toolbar yang muncul (Export Selected, Delete Selected, Re-run Selected).

## Pengaturan / Konfigurasi

Beberapa aspek halaman History dikontrol oleh Settings global:

- **history_page_size** (int, default 50) - Jumlah row per halaman pagination. Nilai lebih tinggi (100, 200) untuk layar besar; lebih rendah (25) untuk mobile.
- **history_refresh_interval** (int ms, default 3000) - Interval polling TanStack Query. Di-share dengan Dashboard.
- **history_default_sort** (string, default `created_at:desc`) - Sort default saat halaman dibuka pertama kali.
- **history_default_filter** (object, optional) - Filter default yang auto-apply. Misal `{"status": ["done", "error"]}` untuk exclude running.
- **history_show_archived** (boolean, default false) - Apakah job di-archive muncul di list default. Toggle di toolbar.
- **history_url_truncate_length** (int, default 60) - Karakter URL sebelum dipotong "..." dengan tooltip full.
- **export_include_config** (boolean, default true) - Apakah export CSV menyertakan kolom config JSON.
- **export_include_result** (boolean, default true) - Apakah export menyertakan result JSON.
- **export_filename_template** (string) - Template nama file export. Default `pyscrapr_history_{date}.{ext}`.
- **delete_confirmation_required** (boolean, default true) - Apakah delete selalu minta konfirmasi atau langsung.
- **rerun_edit_before_submit** (boolean, default false) - Apakah Re-run langsung submit atau buka form pre-filled untuk edit dulu.

Semua setting di atas berlaku cross-session dan tersimpan di `data/settings.json`.

## Output

Halaman History sendiri tidak menghasilkan file otomatis, tapi menyediakan tiga format export on-demand:

- **CSV** - Plain comma-separated untuk Excel atau Google Sheets. Kolom: id, tool, url, status, created_at, completed_at, downloaded_count, source, config (stringified JSON), result (stringified JSON).
- **JSON** - Array objek untuk konsumsi programmatic. Struktur lengkap dengan nested config dan result object.
- **Excel (.xlsx)** - Dengan formatting: header bold, auto-width kolom, conditional color pada kolom status. Powered oleh library openpyxl di backend.

File export di-download langsung ke folder Downloads browser dengan nama sesuai `export_filename_template`. Untuk bulk export (banyak job selected), satu file berisi multi-row. Untuk single job export, filename menyertakan job ID untuk identifikasi.

## Integrasi dengan fitur lain

- **Dashboard** - Recent 5 jobs di Dashboard adalah subset tersort dari tabel History.
- **Diff Detection** - Tombol "Diff vs previous" di row History pre-fill Diff picker.
- **Scheduled Jobs** - Job dari schedule muncul dengan source=schedule dan icon clock.
- **Bulk Queue** - Job dari bulk muncul dengan source=bulk dan grouped oleh `bulk_batch_id`.
- **Webhooks** - Job yang trigger webhook menampilkan indikator webhook di detail modal.
- **Re-run** - Fitur clone config ke job baru lewat modul submit tool masing-masing.
- **Settings** - Banyak UI behavior dikontrol dari Settings.
- **REST API** - Endpoint `/api/jobs` adalah sumber data yang sama untuk integrasi eksternal.

## Tips & Best Practices

1. **Bookmark filter kombinasi yang sering dipakai** - URL query string otomatis reflect filter state, jadi bookmark view "error today" cukup satu klik.
2. **Archive daripada delete** - Untuk job lama, gunakan archive flag agar tetap bisa di-restore. Delete hanya untuk yang benar-benar junk.
3. **Export JSON untuk backup** - Weekly export full History JSON sebagai backup offsite yang bisa di-restore.
4. **Pakai date range untuk report** - Isi date range untuk export hanya periode tertentu, bukan seluruh database yang besar.
5. **Perhatikan source filter** - Pisahkan analisis manual vs scheduled untuk pemahaman lebih akurat tentang automation efficacy.
6. **Cleanup periodik** - Bulanan sekali scan History untuk delete atau archive job yang tidak relevan; storage disk akan berterima kasih.
7. **Gunakan search URL untuk trace domain** - Cari partial domain untuk lihat semua job terhadap domain spesifik (audit trail per-target).
8. **Verifikasi sebelum bulk delete** - Selalu double-check selected rows sebelum bulk delete; operasi ini tidak reversible.

## Troubleshooting

**Problem: Tabel History kosong walaupun sudah banyak job dijalankan.**
Cause: Filter default tersembunyi yang exclude semua, atau DB corrupt.
Solution: Reset filter (tombol "Clear filters"). Verifikasi DB file exist dan bisa dibuka (sqlite browser).

**Problem: Halaman sangat lambat dimuat dengan History yang besar (>10000 rows).**
Cause: Pagination tidak efficient di backend (query all then slice), atau index DB kurang.
Solution: Pastikan index pada `created_at`, `tool`, `status`. Arsipkan job lama. Turunkan `history_page_size`.

**Problem: Status job stuck di "running" padahal sudah lama.**
Cause: Worker crash tanpa update status ke error, atau long-running job yang memang belum selesai.
Solution: Cek log untuk stack trace. Manual update status ke stopped via API jika yakin hung. Restart worker.

**Problem: Re-run menghasilkan job dengan config salah (field hilang).**
Cause: Schema config berubah (field baru required) tapi config lama tidak punya field itu.
Solution: Ubah setting `rerun_edit_before_submit: true` agar form pre-filled dan bisa edit sebelum submit.

**Problem: Export CSV Excel tidak bisa dibuka, error corrupted.**
Cause: Karakter khusus (comma, newline) di URL atau config tidak di-escape benar.
Solution: Gunakan export JSON sebagai alternatif. Untuk CSV, set quoting mode ke QUOTE_ALL di backend.

**Problem: Auto-refresh tidak jalan, harus manual F5.**
Cause: TanStack Query disabled di production build, atau tab browser throttled karena idle.
Solution: Cek Devtools Network untuk lihat polling request. Fokus tab agar tidak throttled.

**Problem: Delete job tidak menghapus file output di disk.**
Cause: Default behavior hanya delete DB record; file management terpisah.
Solution: Cek opsi "Delete files too" di konfirmasi dialog. Atau cleanup manual di file system.

**Problem: Detail modal tab Config kosong.**
Cause: Config tidak tersimpan saat submit (bug lama atau import dari migration).
Solution: Re-run dengan config baru akan fix going forward. Untuk job lama, terima saja data-less.

**Problem: Filter date range tidak bekerja dengan benar.**
Cause: Timezone mismatch antara picker (local) dan DB (UTC).
Solution: Verifikasi server timezone. Explicitly set timezone di picker (feature flag).

## FAQ

**Q: Berapa lama job disimpan di History?**
A: Selamanya (tidak ada auto-expire default). Anda bisa setup cleanup script manual jika butuh policy retention.

**Q: Apakah bisa hide kolom tertentu dari tabel?**
A: Ada column visibility toggle di toolbar. Preference tersimpan di localStorage browser.

**Q: Apakah re-run menciptakan job baru atau overwrite lama?**
A: Selalu job baru dengan ID berbeda. Job lama tetap utuh sebagai record histori.

**Q: Apakah bulk export ada limit jumlah?**
A: Default max 5000 rows per export untuk prevent timeout. Pakai date range untuk split jika lebih besar.

**Q: Apakah History bisa di-sync antar device/user?**
A: Tidak built-in (PyScrapr adalah tool personal offline). Untuk multi-user, pakai DB server-based (PostgreSQL).

**Q: Bagaimana cara hapus semua job sekaligus?**
A: Filter all, select all, bulk delete. Atau truncate tabel `jobs` manual di SQLite.

**Q: Apakah bisa comment atau tag job?**
A: Fitur tag tersedia di detail modal (free-text tags). Comment belum ada (feature request).

**Q: Apakah detail log tersimpan selamanya?**
A: Log tersimpan di field `log_snippet` sampai 10000 karakter. Full log di file external yang bisa expire via log rotation.

**Q: Apakah export include metadata folder output?**
A: JSON export menyertakan `output_folder` path. CSV tidak (keep lean).

**Q: Apakah ada fitur "compare jobs side-by-side"?**
A: Untuk comparison, gunakan Diff Detection. Side-by-side detail modal adalah feature request.

## Keterbatasan

- Tidak ada fitur comment built-in (hanya tag).
- Pagination offset-based (bukan cursor), bisa slow untuk skip page terakhir dari DB besar.
- Tidak ada export PDF langsung (harus via Excel → PDF manual).
- Bulk operation maksimum 500 rows per action untuk prevent timeout.
- Detail modal load full config+result per klik, tidak di-cache.
- Tidak ada fitur "restore archived" di UI default (harus via API endpoint).
- Timezone handling date range bergantung browser setting.
- Tidak ada fitur audit "siapa delete apa kapan" (PyScrapr single-user).

## Related docs

- [Dashboard](./dashboard.md) - Entry point cepat sebelum drill ke History.
- [Diff Detection](./diff.md) - Bandingkan 2 job dari History.
- [Scheduled Jobs](./scheduled.md) - Filter source=schedule untuk audit.
- [Bulk Queue](../advanced/bulk-queue.md) - Filter source=bulk untuk batch runs.
- [REST API](../advanced/rest-api.md) - Endpoint /api/jobs untuk akses programmatic.
- [Settings](./settings.md) - Tune behavior dan pagination default.
