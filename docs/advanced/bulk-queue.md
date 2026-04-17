# Bulk URL Queue

> Submisi multiple URL sekaligus sebagai batch yang tiap URL jadi job terpisah di History — ideal untuk ingestion cepat dari daftar URL yang sudah Anda siapkan eksternal.

## Deskripsi

Bulk URL Queue memecah friction utama saat Anda punya 50, 100, atau lebih URL yang ingin di-scrape dengan konfigurasi yang sama. Tanpa fitur ini, Anda harus submit satu per satu via form tool — waktu banyak terbuang di klik berulang. Dengan Bulk Queue, Anda paste seluruh list dalam textarea, pilih tool dan konfigurasinya sekali, lalu submit satu kali. Backend akan mengurai list, validate, dan create job individual untuk tiap URL — semua muncul di History dengan grouping batch yang memudahkan tracking.

Di balik layar, endpoint `POST /api/bulk/submit` menerima payload dengan struktur `{urls: [...], tool: "media", config: {...}}`. Array urls bisa sampai 100 entries per batch (configurable). Untuk tiap URL, modul `bulk._dispatch` memanggil endpoint submit tool yang relevan dengan config yang dishare. Hasilnya adalah N job baru dengan field metadata `bulk_batch_id` (UUID per batch) yang memungkinkan grouping di History view. Scheduled Jobs juga melewati mekanisme dispatch yang sama — `_dispatch` berperan sebagai single entry point yang maintain konsistensi antara bulk manual submit dan automated scheduled trigger.

Saat ini UI Bulk Queue tersedia prominent di halaman Media Downloader, karena use case paling umum adalah download banyak video/playlist sekaligus. Implementasi berupa modal dengan textarea (satu URL per baris, baris kosong dan comment `#` diabaikan), dropdown pemilih tool, form konfigurasi tool yang muncul sesuai pilihan, dan tombol "Queue N jobs" yang menampilkan count URL terdeteksi. Validasi client-side memeriksa URL format valid dan tool compatible sebelum submit ke backend. Backend juga double-check dan reject batch yang invalid, mengembalikan detail error per URL jika ada masalah sebagian.

Arsitektur dispatcher mendukung ekstensi ke tool lain selain Media. Roadmap include enable Bulk Queue di Harvester (ingest banyak gallery URL sekaligus), URL Mapper (crawl banyak sitemap domain), dan Site Ripper (arsipkan banyak blog sekaligus). Saat ini fitur live di Media, tapi endpoint API-nya generic dan bisa dipanggil via HTTP client eksternal untuk tool apapun yang support.

## Kapan pakai?

1. **Download banyak video dari playlist eksternal** — Paste daftar URL YouTube dari spreadsheet/notion ke Bulk Queue, biarkan download sekaligus overnight.
2. **Ingest batch content dari RSS aggregator** — Script eksternal produce daftar URL artikel baru, di-bulk-submit ke Harvester untuk image harvest.
3. **Arsip banyak blog dari bookmark lama** — Bookmark browser Anda ada 50 blog favorit, bulk-rip semuanya ke offline archive.
4. **Mapping banyak subdomain sekaligus** — Security research / SEO audit yang butuh structure map dari banyak domain simultan.
5. **Compare competitor list** — Daftar URL competitor produk di-harvest bareng untuk analisis.
6. **Research academic dataset** — Paper butuh scrape 200 halaman public archive; bulk submit vs 200x klik.
7. **Migration data** — Pindah dari tool lama, export URL list, import ke PyScrapr via Bulk.
8. **Automation pre-scheduled** — Bulk submit list sekaligus untuk warm-up sebelum setup scheduled recurring.

## Cara penggunaan

1. Buka halaman Media Downloader (atau tool lain yang sudah support Bulk).
2. Cari tombol "Bulk Queue" di toolbar atas halaman (biasanya di kanan dekat tombol Submit).
3. Klik tombol untuk buka modal Bulk Queue.
4. Modal menampilkan textarea besar di tengah. Paste list URL, satu per baris.
5. Line comment dengan prefix `#` diabaikan. Baris kosong juga diabaikan. Useful untuk annotate list.
6. Counter "Detected: N URLs" di pojok textarea update realtime saat Anda mengetik/paste.
7. Pilih tool dari dropdown (default sesuai halaman aktif; misal di Media Downloader, default adalah `media`).
8. Isi konfigurasi tool di form di bawah textarea. Config ini akan dipakai untuk SEMUA URL dalam batch.
9. Review URL list. Indikator merah muncul untuk URL yang invalid format (tidak http/https) atau duplicate.
10. Klik tombol "Queue N jobs" (N = count detected). Modal menampilkan progress "Submitting...".
11. Setelah selesai, toast hijau muncul dengan summary: "Queued 47 jobs (3 skipped duplicate)". Modal auto-close.
12. Navigate ke History untuk lihat semua job. Filter `bulk_batch_id` menampilkan job dari batch spesifik.

## Pengaturan / Konfigurasi

Field di payload `POST /api/bulk/submit`:

- **urls** (array of string, required) — Daftar URL. Max 100 per request default.
- **tool** (string, required) — Nama tool target: `media`, `harvester`, `ripper`, `mapper`, `scraper`.
- **config** (object, required) — Config sesuai schema tool yang dipilih. Validated di backend.
- **tags** (array of string, optional) — Labels untuk seluruh batch. Diturunkan ke tiap job.
- **priority** (enum `low`, `normal`, `high`, default `normal`) — Priority di worker queue.
- **dedupe** (boolean, default true) — Skip URL yang sudah pernah di-job dengan tool sama dalam X hari terakhir.
- **dedupe_window_days** (int, default 7) — Window untuk dedupe lookup.
- **fail_fast** (boolean, default false) — Jika true, abort seluruh batch saat URL pertama gagal validate.
- **dispatch_delay_ms** (int, default 100) — Jeda antar dispatch untuk menghindari worker overwhelmed.
- **notify_on_batch_done** (boolean, default false) — Trigger webhook khusus batch completion (bukan per job).

Settings global terkait:

- **bulk_max_urls_per_batch** (int, default 100) — Hard cap per request.
- **bulk_max_concurrent_batches** (int, default 3) — Concurrent batch yang boleh running.
- **bulk_default_dedupe** (boolean, default true) — Default dedupe flag.
- **bulk_default_priority** (enum, default `normal`) — Default priority.
- **bulk_ui_show_duplicates** (boolean, default true) — Tampilkan warning duplicate di modal.

## Output

Response POST `/api/bulk/submit`:

```json
{
  "batch_id": "uuid-batch-string",
  "submitted_count": 47,
  "skipped_count": 3,
  "skipped_reasons": [
    {"url": "...", "reason": "duplicate"},
    {"url": "...", "reason": "invalid_scheme"}
  ],
  "job_ids": ["uuid1", "uuid2", "..."],
  "queued_at": "2026-04-17T10:00:00Z"
}
```

Side effect: N row baru di tabel jobs dengan `source=bulk` dan `bulk_batch_id=<uuid>`. Job individual melewati flow normal tool masing-masing (pending → running → done/error).

## Integrasi dengan fitur lain

- **Scheduled** — Pakai dispatcher yang sama (`bulk._dispatch`); batch scheduled juga track-able.
- **History** — Filter by `bulk_batch_id` untuk isolate batch.
- **Webhooks** — `notify_on_batch_done` fires khusus saat semua job dalam batch selesai.
- **REST API** — Endpoint `/api/bulk/submit` standar REST.
- **Settings** — Default behavior per-batch.
- **Media Downloader** — UI prominent integration.
- **Diff Detection** — Job dalam batch yang sama bisa di-diff antar satu sama lain.

## Tips & Best Practices

1. **Validate URL eksternal dulu** — Sebelum paste, cek format di tool validator agar tidak banyak skip.
2. **Gunakan comment baris** — Prefix `#` untuk annotate section dalam textarea (agar reviewable).
3. **Test batch kecil dulu** — Submit 5 URL untuk verify config benar sebelum 100.
4. **Aktifkan dedupe** — Hindari re-scrape URL yang baru saja dijalankan untuk hemat resource.
5. **Set priority bijak** — `high` untuk urgent batch (latar belakang worker prioritize); `low` untuk background ingestion.
6. **Monitor worker load** — 100 concurrent submit bisa overwhelm worker jika tidak ada `dispatch_delay_ms`.
7. **Pair dengan Scheduled** — Batch recurring disarankan pakai Scheduled; Bulk untuk one-time.
8. **Export batch list** — Simpan URL list sebagai file `.txt` untuk re-submit di masa depan.

## Troubleshooting

**Problem: "Batch limit exceeded" error saat submit.**
Cause: URL count > `bulk_max_urls_per_batch`.
Solution: Split batch jadi beberapa request, atau naikkan limit di Settings.

**Problem: Banyak URL skipped dengan reason "duplicate".**
Cause: Dedupe aktif dan URL ini baru di-scrape dalam window.
Solution: Disable dedupe di batch, atau naikkan window.

**Problem: Submit sukses tapi job tidak muncul di History.**
Cause: Dispatcher async, butuh beberapa detik. Atau worker belum pick up.
Solution: Wait 5-10 detik. Refresh History. Cek worker log.

**Problem: Semua job dalam batch error dengan pesan sama.**
Cause: Config shared invalid untuk semua URL (misal depth terlalu tinggi).
Solution: Fix config dan re-submit. Cek error message detail.

**Problem: Modal Bulk Queue tidak muncul / tombol tidak klik-able.**
Cause: Tool saat ini tidak support Bulk (Bulk belum enabled di halaman ini).
Solution: Pindah ke Media Downloader. Untuk tool lain pakai API direct.

**Problem: Progress hang saat submit banyak URL.**
Cause: Backend process terlalu banyak secara paralel.
Solution: Naikkan `dispatch_delay_ms`. Split batch smaller.

**Problem: Batch counter di History tidak akurat.**
Cause: Race condition di dispatcher pertama kali.
Solution: Restart server. Cek `bulk_batch_id` manual di DB.

**Problem: `skipped_reasons` return "invalid_url" untuk URL yang tampak benar.**
Cause: Whitespace tersembunyi (tab, zero-width space) dari paste.
Solution: Bersihkan dengan tool online trimmer. Paste sebagai plain text.

**Problem: Webhook batch done tidak fires.**
Cause: Job individual masih pending, batch belum full completion.
Solution: Wait semua job done. Cek webhook settings separate dari per-job.

## FAQ

**Q: Berapa max URL per batch?**
A: Default 100, configurable via Settings.

**Q: Apakah dedupe scope hanya URL atau URL+config?**
A: Default URL+tool. Jika config beda, re-dispatch.

**Q: Bisa bulk submit untuk tool berbeda dalam satu request?**
A: Tidak. Satu batch = satu tool. Submit multi-batch untuk multi-tool.

**Q: Apakah bulk submit bisa dibatalkan setelah queued?**
A: Individual jobs bisa di-stop via History. Batch-level cancel belum ada.

**Q: Bagaimana order eksekusi batch?**
A: FIFO default, adjust via priority field.

**Q: Apakah batch_id persistent setelah DB cleanup?**
A: Ya, disimpan di field job sampai job ter-delete.

**Q: Bisa bulk submit dari CLI?**
A: Ya via curl / script ke endpoint `/api/bulk/submit`.

**Q: Apakah batch progress bisa dimonitor realtime?**
A: Via polling `/api/jobs?bulk_batch_id=<id>` untuk hitung status.

**Q: Batch besar butuh disk besar?**
A: Ya, kalkulasi per-job lalu kali N. Monitor Dashboard disk bar.

**Q: Retry failed jobs dalam batch?**
A: Re-submit URL yang gagal via Bulk baru, atau klik Re-run per job di History.

## Keterbatasan

- Max 100 URL per batch default (adjust via Settings).
- Satu tool per batch (no mixed).
- Tidak ada batch cancel built-in (harus per-job).
- UI baru prominent di Media Downloader (tool lain via API).
- Dedupe window fixed per request (tidak per-URL granular).
- Progress batch-level via polling (no push notification).
- Tidak ada batch retry group.
- Config shared untuk semua URL (no per-URL override).

## Related docs

- [Scheduled Jobs](../system/scheduled.md) — Menggunakan dispatcher yang sama.
- [History](../system/history.md) — Filter by bulk_batch_id.
- [Webhooks](./webhooks.md) — Notifikasi batch done.
- [REST API](./rest-api.md) — Endpoint /api/bulk/submit.
- [Media Downloader](../tools/media-downloader.md) — UI prominent.
