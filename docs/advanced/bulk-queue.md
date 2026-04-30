# Bulk URL Queue

> Submisi multiple URL sekaligus sebagai batch yang tiap URL jadi job terpisah di History, ideal untuk ingestion cepat dari daftar URL yang sudah Anda siapkan di spreadsheet, Notion, bookmark, atau script eksternal. Mendukung 1 sampai 100 URL per batch dengan shared configuration.

## Deskripsi

Bulk URL Queue memecah friction utama saat Anda punya 50, 100, atau lebih URL yang ingin di-scrape dengan konfigurasi yang sama. Tanpa fitur ini, Anda harus submit satu per satu via form tool, dan waktu banyak terbuang untuk klik berulang. Dengan Bulk Queue, Anda paste seluruh list dalam textarea, pilih tool dan konfigurasinya sekali, lalu submit satu kali. Backend akan mengurai list, validate tiap URL, dan create job individual untuk tiap URL. Semua muncul di History dengan grouping batch yang memudahkan tracking progress dan retry failed job secara granular.

Di balik layar, endpoint `POST /api/bulk/submit` menerima payload dengan struktur `{urls: string[], tool: "media", config: {...}}`. Array `urls` bisa sampai 100 entries per batch secara default (dapat diatur via `bulk_max_urls_per_batch` di Settings). Untuk tiap URL, modul `bulk._dispatch` memanggil endpoint submit tool yang relevan dengan config yang di-share di batch. Hasilnya adalah N job baru dengan field metadata `bulk_batch_id` (UUID per batch) yang memungkinkan grouping di History view. Scheduled Jobs juga melewati mekanisme dispatch yang sama; `_dispatch` berperan sebagai single entry point yang menjamin konsistensi antara bulk manual submit dan automated scheduled trigger.

Saat ini UI Bulk Queue tersedia prominent di halaman Media Downloader, karena use case paling umum adalah download banyak video atau playlist URL sekaligus (copy dari subscription feed atau curated list). Implementasi berupa tombol "Bulk" di toolbar yang membuka modal dengan textarea (satu URL per baris, baris kosong dan comment `#` diabaikan), dropdown pemilih tool, form konfigurasi tool yang muncul sesuai pilihan, dan tombol "Queue N jobs" yang menampilkan count URL terdeteksi real-time. Validasi client-side memeriksa URL format valid dan tool compatibility sebelum submit ke backend. Backend juga double-check dan reject batch yang invalid secara keseluruhan, mengembalikan detail error per URL jika ada masalah pada sebagian entries.

Arsitektur dispatcher mendukung ekstensi ke tool lain selain Media. Tool yang currently supported: `harvester` (ingest banyak gallery URL sekaligus), `mapper` (crawl banyak domain untuk sitemap structure), `ripper` (arsip banyak blog atau static site), dan `media` (download banyak video). Roadmap expansi ke Scraper klasik untuk scenario form submission bulk. Saat ini fitur UI live di Media Downloader, tapi endpoint API-nya generic dan bisa dipanggil via HTTP client eksternal (curl, Python, Postman) untuk tool apapun yang support.

## Kapan pakai?

1. **Download banyak video dari playlist eksternal** - Paste daftar URL YouTube dari spreadsheet atau Notion ke Bulk Queue, biarkan download sekaligus overnight.
2. **Ingest batch content dari RSS aggregator** - Script eksternal produce daftar URL artikel baru, di-bulk-submit ke Harvester untuk image harvest massal.
3. **Arsip banyak blog dari bookmark lama** - Bookmark browser Anda punya 50 blog favorit; bulk-rip semuanya ke offline archive untuk referensi future.
4. **Mapping banyak subdomain sekaligus** - Security research atau SEO audit yang butuh structure map dari banyak domain simultan tanpa klik manual.
5. **Compare competitor list** - Daftar URL product competitor di-harvest bareng untuk analisis harga atau feature parity.
6. **Research academic dataset** - Paper research butuh scrape 200 halaman public archive; bulk submit vs 200 kali klik satu per satu.
7. **Migration data dari tool lama** - Export URL list dari tool scraping sebelumnya, import ke PyScrapr via Bulk untuk konsolidasi.
8. **Automation pre-scheduled warm-up** - Bulk submit list sekaligus untuk test konfigurasi sebelum setup Scheduled recurring.

## Cara penggunaan

1. Buka halaman Media Downloader (atau tool lain yang sudah support Bulk, cek badge "Bulk" di toolbar).
2. Cari tombol "Bulk Queue" atau "Bulk" di toolbar atas halaman, biasanya di kanan dekat tombol Submit.
3. Klik tombol untuk membuka modal Bulk Queue. Modal menampilkan textarea besar di tengah layar.
4. Paste list URL, satu per baris. Counter "Detected: N URLs" di pojok textarea update real-time saat Anda mengetik atau paste.
5. Line comment dengan prefix `#` diabaikan. Baris kosong juga diabaikan. Berguna untuk annotate section dalam list (misalnya `# Tech channels`, `# Food vlogs`).
6. Pilih tool dari dropdown (default sesuai halaman aktif; di Media Downloader default adalah `media`).
7. Isi konfigurasi tool di form di bawah textarea. Config ini akan dipakai untuk SEMUA URL dalam batch ini.
8. Review URL list. Indikator merah muncul untuk URL yang invalid format (tidak http atau https) atau duplicate dengan URL lain di textarea.
9. Review setting opsional: `dedupe`, `priority`, `dispatch_delay_ms` di advanced section modal.
10. Klik tombol "Queue N jobs" (N adalah count detected). Modal menampilkan progress "Submitting..." dengan spinner.
11. Setelah selesai, toast hijau muncul dengan summary: "Queued 47 jobs (3 skipped duplicate)". Modal auto-close setelah 2 detik.
12. Navigate ke halaman History untuk melihat semua job. Gunakan filter `bulk_batch_id` untuk menampilkan hanya job dari batch spesifik.
13. Monitor progress bulk via indikator count per status (pending, running, done, error) di History filter bar.
14. Retry failed jobs per individu via tombol Re-run di row History, atau collect failed URL lalu submit ulang sebagai batch baru.
15. Export result semua job dalam batch via REST API `/api/data/{job_id}` looping atau satu-shot via query batch_id di endpoint future.

## Pengaturan / Konfigurasi

### urls (payload field)
Array of string, required. Daftar URL untuk di-submit. Max 100 per request default, dapat diatur via `bulk_max_urls_per_batch` di Settings.

### tool (payload field)
String, required. Nama tool target: `media`, `harvester`, `ripper`, `mapper`, atau `scraper`. Invalid value return 400.

### config (payload field)
Object, required. Config sesuai schema tool yang dipilih. Validated di backend via Pydantic model tool yang relevan.

### tags (payload field)
Array of string, optional. Labels untuk seluruh batch yang akan di-inherit ke tiap job. Berguna untuk filter di History.

### priority (payload field)
Enum `low`, `normal`, atau `high`. Default `normal`. Priority di worker queue; `high` akan dikerjakan sebelum `normal` dan `low`.

### dedupe (payload field)
Boolean, default true. Skip URL yang sudah pernah di-job dengan tool sama dalam X hari terakhir (dedupe window).

### dedupe_window_days (payload field)
Integer, default 7. Window lookup untuk dedupe dalam hari. Set 0 untuk disable effective dedupe tanpa mengubah flag.

### fail_fast (payload field)
Boolean, default false. Jika true, abort seluruh batch saat URL pertama gagal validate. Rekomendasi false untuk batch besar agar partial success tidak lost.

### dispatch_delay_ms (payload field)
Integer, default 100. Jeda antar dispatch dalam milidetik untuk menghindari worker overwhelmed. Naikkan ke 500-1000 untuk target sensitif rate limit.

### notify_on_batch_done (payload field)
Boolean, default false. Trigger webhook khusus saat semua job dalam batch selesai (bukan per-job notification).

### bulk_max_urls_per_batch (setting)
Integer global, default 100. Hard cap URL per request. Naikkan untuk use case besar, tapi hati-hati memory backend.

### bulk_max_concurrent_batches (setting)
Integer, default 3. Concurrent batch yang boleh running simultaneously. Melebihi ini batch baru masuk queue.

### bulk_default_dedupe (setting)
Boolean, default true. Default dedupe flag jika payload tidak specify.

### bulk_default_priority (setting)
Enum, default `normal`. Default priority jika payload tidak specify.

### bulk_ui_show_duplicates (setting)
Boolean, default true. Tampilkan warning visual di modal saat ada URL duplicate dalam textarea.

## Output / Efek

Response POST `/api/bulk/submit`:

```json
{
  "batch_id": "uuid-batch-string",
  "submitted_count": 47,
  "skipped_count": 3,
  "skipped_reasons": [
    {"url": "https://duplicate.com/video1", "reason": "duplicate"},
    {"url": "ftp://invalid.com/file", "reason": "invalid_scheme"},
    {"url": "not-a-url", "reason": "invalid_url"}
  ],
  "job_ids": ["uuid1", "uuid2", "..."],
  "queued_at": "2026-04-17T10:00:00Z"
}
```

Side effect: N row baru di tabel jobs dengan `source=bulk` dan `bulk_batch_id=<uuid>`. Job individual melewati flow normal tool masing-masing (pending, running, done atau error). UI History menampilkan badge "Bulk" di row job yang berasal dari batch. Filter `?bulk_batch_id=<uuid>` di History atau REST API mengembalikan hanya job dalam batch tersebut.

Contoh submit via curl:
```bash
curl -X POST http://localhost:8585/api/bulk/submit \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://youtube.com/watch?v=abc", "https://youtube.com/watch?v=def"],
    "tool": "media",
    "config": {"format": "mp4", "quality": "720p"}
  }'
```

Contoh Python:
```python
import requests
payload = {
    "urls": urls_list,
    "tool": "harvester",
    "config": {"max_depth": 2, "filters": {"min_width": 800}}
}
r = requests.post("http://localhost:8585/api/bulk/submit", json=payload)
batch = r.json()
print(f"Batch {batch['batch_id']}: {batch['submitted_count']} queued")
```

## Integrasi dengan fitur lain

- **Scheduled Jobs** - Menggunakan dispatcher yang sama (`bulk._dispatch`); batch scheduled juga trackable via `bulk_batch_id`.
- **History** - Filter by `bulk_batch_id` untuk isolate job batch spesifik, berguna untuk audit dan retry.
- **Webhooks** - `notify_on_batch_done` fires khusus saat seluruh job dalam batch selesai (bukan per-job notification).
- **REST API** - Endpoint `/api/bulk/submit` adalah REST API standar; bisa dipanggil dari script eksternal atau CI.
- **Settings** - Default behavior per-batch (dedupe, priority, max_urls) configurable global.
- **Media Downloader** - UI prominent integration dengan tombol Bulk di toolbar.
- **Diff Detection** - Job dalam batch yang sama bisa di-diff antar run untuk track perubahan.

## Tips & Best Practices

1. **Validate URL eksternal dulu.** Sebelum paste, cek format via tool validator atau regex agar tidak banyak skip. URL copy-paste dari browser biasanya sudah benar, tapi dari spreadsheet sering kotor.

2. **Gunakan comment baris.** Prefix `#` untuk annotate section dalam textarea agar reviewable. Contoh: `# ---- Music channels ----` sebelum 20 URL YouTube music.

3. **Test batch kecil dulu.** Submit 5 URL untuk verify config benar sebelum 100. Batch 100 yang gagal semua karena config wrong membuang banyak resource.

4. **Aktifkan dedupe.** Hindari re-scrape URL yang baru dijalankan untuk hemat resource. Dedupe window 7 hari default biasanya cukup.

5. **Set priority bijak.** `high` untuk urgent batch yang butuh hasil cepat (worker prioritize); `low` untuk background ingestion overnight yang bisa nunggu.

6. **Monitor worker load.** 100 concurrent submit bisa overwhelm worker jika tidak ada `dispatch_delay_ms` minimal 100 ms. Naikkan jika Anda lihat spike CPU.

7. **Pair dengan Scheduled.** Batch recurring disarankan pakai Scheduled Jobs; Bulk untuk one-time ingestion ad-hoc.

8. **Export batch list.** Simpan URL list sebagai file `.txt` di folder backup untuk re-submit di masa depan atau audit trail.

9. **Fail fast untuk batch kritikal.** Untuk batch yang semua URL saling tergantung (misalnya set dokumen paper), set `fail_fast=true` agar partial success tidak menyesatkan.

10. **Review error reasons dengan cermat.** Setelah submit, cek `skipped_reasons` di response untuk tahu pola error (banyak duplicate? banyak invalid format?) dan perbaiki source list.

## Troubleshooting

### Problem: Batch limit exceeded error saat submit
**Gejala:** Response 400 dengan pesan "Batch size exceeds maximum allowed".
**Penyebab:** URL count melebihi `bulk_max_urls_per_batch` setting.
**Solusi:** Split batch menjadi beberapa request lebih kecil, atau naikkan limit di Settings (perhatikan memory footprint).

### Problem: Banyak URL skipped dengan reason duplicate
**Gejala:** `submitted_count` jauh lebih kecil dari `submitted_count + skipped_count` dengan mayoritas duplicate.
**Penyebab:** Dedupe aktif dan URL ini baru di-scrape dalam window 7 hari.
**Solusi:** Set `dedupe: false` di payload batch, atau naikkan `dedupe_window_days` ke 30 jika ingin keep filter.

### Problem: Submit sukses tapi job tidak muncul di History
**Gejala:** Response 200 dengan job_ids, tapi History kosong untuk batch_id.
**Penyebab:** Dispatcher async, butuh beberapa detik untuk persist ke DB. Atau worker belum pick up.
**Solusi:** Wait 5-10 detik. Refresh History. Cek worker log untuk error startup.

### Problem: Semua job dalam batch error dengan pesan sama
**Gejala:** Batch submit 50 URL, semua status error dengan message identik.
**Penyebab:** Config shared invalid untuk semua URL (misalnya depth terlalu tinggi, output path tidak writable).
**Solusi:** Cek error message detail di satu job sample, fix config, dan re-submit batch dengan config yang benar.

### Problem: Modal Bulk Queue tidak muncul atau tombol tidak klikabel
**Gejala:** Klik tombol Bulk tidak respond.
**Penyebab:** Tool saat ini tidak support Bulk (belum enabled untuk halaman ini).
**Solusi:** Pindah ke Media Downloader atau halaman tool yang sudah support. Untuk tool lain pakai API langsung.

### Problem: Progress hang saat submit banyak URL
**Gejala:** Spinner "Submitting..." berjalan lama lebih dari 30 detik.
**Penyebab:** Backend memproses terlalu banyak secara paralel, bottleneck di validation atau insert DB.
**Solusi:** Naikkan `dispatch_delay_ms`. Split batch menjadi yang lebih kecil (50 per batch).

### Problem: Batch counter di History tidak akurat
**Gejala:** Filter `bulk_batch_id` menunjukkan count lebih kecil dari `submitted_count` di response.
**Penyebab:** Race condition di dispatcher pertama kali, beberapa job gagal insert.
**Solusi:** Restart server. Cek `bulk_batch_id` manual di DB untuk rekonsiliasi.

### Problem: skipped_reasons return invalid_url untuk URL yang tampak benar
**Gejala:** URL tampak valid tapi di-reject sebagai invalid.
**Penyebab:** Whitespace tersembunyi seperti tab, zero-width space, atau BOM dari paste.
**Solusi:** Bersihkan list via tool online trimmer atau paste sebagai "plain text" (Ctrl-Shift-V di browser).

### Problem: Webhook batch done tidak fires
**Gejala:** `notify_on_batch_done=true` tapi tidak ada webhook masuk.
**Penyebab:** Job individual masih pending atau error, batch belum full completion (semua harus done, error saja masih transient).
**Solusi:** Wait semua job reach terminal state. Cek webhook settings untuk `batch.done` event subscription.

### Problem: Worker hanya proses beberapa job, sisanya stuck pending
**Gejala:** Batch 100 URL, hanya 10 yang running simultan.
**Penyebab:** Worker concurrency limit di Settings.
**Solusi:** Naikkan `worker_max_concurrent` di Settings. Atau tunggu batch pertama selesai sebelum worker pick up sisanya.

## FAQ

**Q: Berapa max URL per batch?**
A: Default 100, configurable via `bulk_max_urls_per_batch` di Settings hingga 1000 plus untuk infra kuat.

**Q: Apakah dedupe scope hanya URL atau URL plus config?**
A: Default URL plus tool. Jika config berbeda meski URL sama, tetap di-dispatch sebagai job baru.

**Q: Bisa bulk submit untuk tool berbeda dalam satu request?**
A: Tidak. Satu batch sama dengan satu tool. Submit multiple request untuk multi-tool scenario.

**Q: Apakah bulk submit bisa dibatalkan setelah queued?**
A: Individual jobs bisa di-stop via History per row. Batch-level cancel belum tersedia.

**Q: Bagaimana order eksekusi batch?**
A: FIFO default dalam same priority level. Adjust via field `priority` payload.

**Q: Apakah batch_id persistent setelah DB cleanup?**
A: Ya, disimpan di field `bulk_batch_id` di job row sampai job itu sendiri ter-delete.

**Q: Bisa bulk submit dari CLI?**
A: Ya via curl atau script ke endpoint `/api/bulk/submit`; contoh payload ada di section Output di atas.

**Q: Apakah batch progress bisa dimonitor realtime?**
A: Via polling `/api/jobs?bulk_batch_id=<id>` untuk hitung status count per terminal state.

**Q: Batch besar butuh disk besar?**
A: Ya, kalkulasi per-job disk usage lalu kali N. Monitor Dashboard disk bar selama batch besar running.

**Q: Retry failed jobs dalam batch?**
A: Re-submit URL yang gagal via Bulk baru (collect failed URL dulu), atau klik Re-run per job di History.

**Q: Bulk queue memengaruhi rate limit di target?**
A: Ya, parallelisme tinggi bisa trigger rate limit. Gunakan `dispatch_delay_ms` dan proxy rotation untuk mitigate.

**Q: Bisa mixed scheduled dan bulk dalam pipeline?**
A: Ya, keduanya menggunakan dispatcher yang sama sehingga behavior konsisten. Kombinasi ideal untuk recurring plus ad-hoc workload.

## Keterbatasan

- Max 100 URL per batch default (adjust via Settings, perhatikan memory).
- Satu tool per batch; no mixed-tool dalam satu request.
- Tidak ada batch cancel built-in; harus per-job via History.
- UI prominent hanya di Media Downloader; tool lain via API direct.
- Dedupe window fixed per request, tidak per-URL granular.
- Progress batch-level via polling; no push notification real-time.
- Tidak ada batch retry group; retry manual per-job.
- Config shared untuk semua URL di batch; no per-URL override.
- Tidak ada preview hasil sebelum final submit.
- Rate limit handling per-target bergantung pada Proxy dan UA Rotation.

## Studi kasus penggunaan nyata

**Skenario 1: Download playlist YouTube bulanan.** Content curator subscribe ke 30 channel YouTube favorit, export URL video baru bulanan ke spreadsheet. Copy 200 URL ke Bulk Queue Media Downloader dengan config mp4 720p, submit sekali, dapat 200 job di History. Worker proses 5 concurrent, selesai dalam 3 jam overnight. Total interaksi manual: satu klik.

**Skenario 2: Batch harvest image dari 50 gallery.** Photographer butuh backup asset dari 50 public gallery teman yang tersebar di berbagai situs. Copy URL gallery ke Bulk Queue Harvester dengan config filter minimum 1920x1080 resolution. Submit, 50 job auto-run, hasil asset di folder archive terorganisir per domain.

**Skenario 3: SEO audit multi-client.** SEO agency melayani 20 client. Bulk Queue Mapper dengan 20 root URL domain client, config depth 3. Dapat 20 sitemap structure hasil crawl untuk deliverable laporan mingguan.

**Skenario 4: Migration dari tool lain.** Tim pindah dari scraping tool lama ke PyScrapr. Export list 500 URL yang sebelumnya recurring di tool lama, import via Bulk dengan config sesuai tool baru. Setelah verifikasi hasil match, re-create scheduled di PyScrapr untuk recurring.

**Skenario 5: Academic paper dataset collection.** PhD student butuh 300 halaman arsip public government untuk analisis. Bulk submit Ripper dengan list 300 URL dari paper reference. Semua archived offline untuk reproducibility research.

## Advanced patterns dan scripting

Bulk Queue jadi sangat powerful saat digabung dengan script wrapper. Beberapa pattern:

**Pattern 1: Generate URL list dari query dinamis.** Script Python baca list product ID dari DB internal, generate URL template `https://marketplace.com/product/{id}`, POST ke bulk API. Automated discovery plus submit.

**Pattern 2: Chain multiple batches dengan jeda.** Script submit batch 1 (100 URL), wait selesai via polling `/api/jobs?bulk_batch_id=<id>`, submit batch 2 (100 URL berikutnya). Hindari overload worker dan rate limit target.

**Pattern 3: Filter pre-submit dengan validator URL.** Sebelum submit, script validasi URL via HEAD request untuk cek alive. Filter out yang 404 atau redirect unexpected. Hemat worker resource.

**Pattern 4: Retry failed jobs otomatis.** Script query History filter `status=error bulk_batch_id=<id>`, collect URL yang gagal, submit sebagai batch retry baru dengan config yang mungkin lebih conservative (depth rendah, delay tinggi).

**Pattern 5: Export batch result gabungan.** Script query semua `job_id` dari batch, fetch data per job via REST API, merge ke single output JSON atau CSV. Satu batch report untuk konsumen downstream.

**Contoh Python wrapper lengkap:**
```python
import requests, time

def submit_bulk(urls, tool, config, chunk_size=50):
    batch_ids = []
    for i in range(0, len(urls), chunk_size):
        chunk = urls[i:i+chunk_size]
        r = requests.post("http://localhost:8585/api/bulk/submit",
                         json={"urls": chunk, "tool": tool, "config": config})
        batch_ids.append(r.json()["batch_id"])
        time.sleep(2)  # jeda antar submit
    return batch_ids

urls = [f"https://site.com/page/{i}" for i in range(1, 501)]
batches = submit_bulk(urls, "harvester", {"max_depth": 1})
print(f"Submitted {len(batches)} batches totaling {len(urls)} URLs")
```

## Monitoring batch progress

Setelah submit, monitor progress via beberapa cara:

1. **UI History dengan filter.** Filter bar di History input `bulk_batch_id=<uuid>` tampilkan hanya job batch. Badge count per status (pending, running, done, error) update real-time.

2. **Polling via REST API.** Endpoint `/api/jobs?bulk_batch_id=<id>` return list jobs; script bisa count per status untuk dashboard custom.

3. **Webhook batch done.** `notify_on_batch_done=true` di payload fires saat semua job reach terminal state. Alert di Discord channel kapan batch complete.

4. **Log server real-time.** Tail log untuk lihat dispatch per job. Debug visibility tinggi.

5. **Dashboard aggregate.** Batch summary card di halaman Dashboard (future roadmap) akan tampilkan progress bar per batch aktif.

## Related docs

- [Scheduled Jobs](/docs/system/scheduled.md) - Menggunakan dispatcher yang sama untuk konsistensi.
- [History](/docs/system/history.md) - Filter by bulk_batch_id untuk audit batch.
- [Webhooks](/docs/advanced/webhooks.md) - Notifikasi batch done via `notify_on_batch_done`.
- [REST API](/docs/advanced/rest-api.md) - Endpoint `/api/bulk/submit` dan `/api/data/{job_id}` untuk data fetching.
- [Media Downloader](/docs/tools/media-downloader.md) - UI prominent tempat Bulk Queue paling sering digunakan.
