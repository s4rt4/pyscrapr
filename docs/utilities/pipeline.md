# Custom Python Pipeline

> Editor Python in-browser yang memungkinkan Anda menulis skrip post-processing kustom dan menjalankannya otomatis setelah job scraping selesai. Cocok untuk transformasi data yang tidak tersedia sebagai fitur built-in.

## Deskripsi

Custom Pipeline memberikan Anda backdoor Python penuh di dalam PyScrapr. Anda menulis skrip dalam Monaco Editor (engine yang sama dengan VS Code) dengan syntax highlighting `vs-dark`, autocomplete dasar, dan linting ringan, lalu PyScrapr akan menjalankannya dengan `exec()` di dalam sandbox backend. Script punya akses ke variabel `data` (list of dicts - hasil dari job scraping), `url` (URL target asli jika ada), `job_id` (identifier job yang trigger pipeline), plus pre-imported module: `re`, `json`, `datetime`, `math`, dan `statistics`.

Pipeline dirancang untuk dua mode penggunaan. Mode **manual**: Anda punya dataset, paste ke panel "Test Run" sebagai JSON, jalankan skrip, lihat hasilnya. Mode **auto-run**: set field `auto_run_on` ke salah satu job type (`image_harvester`, `url_mapper`, `site_ripper`, `media_downloader`), dan setiap kali job type itu selesai, `pipeline_listener.py` (yang subscribe ke global `event_bus`) akan memicu pipeline secara otomatis dengan data hasil job sebagai input. Ini enables workflow seperti "setiap kali Image Harvester selesai, langsung filter gambar di bawah 10KB dan hasilkan laporan statistik".

Storage untuk daftar pipeline Anda ada di `data/pipelines.json`. File ini menyimpan semua pipeline: nama, deskripsi, kode, `auto_run_on`, dan metadata. CRUD operations (Create, Read, Update, Delete) diekspos lewat REST API di `app/api/pipelines.py`. Karena storage berbasis file JSON, tidak ada database yang perlu di-setup, tapi juga tidak ada locking kuat - jangan edit pipeline dari dua tab bersamaan.

> [!DANGER]
> **Peringatan keamanan penting**: skrip dieksekusi dengan `exec()` tanpa sandbox. Artinya skrip bisa `import os; os.remove(...)`, membaca file arbitrer, atau membuka koneksi jaringan. Karena PyScrapr adalah tool personal lokal, ini dianggap acceptable - Anda adalah satu-satunya user dan Anda sendiri yang menulis kode. **Jangan** meng-copy-paste skrip Pipeline dari sumber yang tidak tepercaya. Jangan pula share akses PyScrapr Anda ke pihak lain di LAN tanpa otentikasi. Kalau Anda butuh sandbox beneran, pertimbangkan menjalankan PyScrapr di dalam container Docker atau VM.

## Kapan pakai tool ini?

1. **Filter & clean dataset** - drop row dengan field kosong, strip whitespace, lowercase semua email.
2. **Enrichment** - untuk setiap URL di `data`, tambahkan field `domain` dengan `urlparse().netloc` - sekali pakai tanpa perlu tool baru.
3. **Agregasi statistik** - hitung mean/median/stdev harga, distribusi kategori, top-10 keyword - output sebagai dict summary.
4. **Transformasi format** - ubah list flat jadi nested structure untuk export ke JSON hierarkis, atau sebaliknya flatten untuk CSV.
5. **Deduplication kustom** - hapus duplikat berdasarkan kombinasi field (bukan hanya URL), misal `(title, author)` untuk dataset artikel.
6. **Integrasi external API** - kirim hasil scrape ke webhook, Notion API, Airtable, Google Sheets; cukup `import httpx` dan POST.
7. **Auto-workflow** - setiap kali Site Ripper selesai, jalankan pipeline yang generate sitemap.xml dari URL yang diunduh.
8. **Validasi data** - cek apakah semua field required ada, buat laporan error per row.

## Cara penggunaan

1. **Buka halaman Custom Pipeline** - dari sidebar pilih `Custom Pipeline`. Ekspektasi: tabel daftar pipeline yang sudah ada (kosong kalau belum pernah buat).
2. **Klik `New pipeline`** - modal editor muncul. Ekspektasi: editor Monaco terisi kode template dengan komentar.
3. **Isi metadata** - `Name` (bebas), `Description` (opsional tapi sangat disarankan), `Auto-run on job type` (None/Image Harvester/URL Mapper/Site Ripper/Media Downloader). Ekspektasi: field tersimpan di state lokal.
4. **Tulis skrip di Monaco Editor** - atau pilih preset di dropdown `Load preset snippet`: `Filter by size`, `RegEx: strip tracking params`, `Extract domain from URL`, `Aggregate to summary stats`. Ekspektasi: editor terisi kode starter dengan komentar penjelasan.
5. **Gunakan variabel yang tersedia** - `data` berisi list-of-dicts, biasanya hasil job upstream. Modifikasi in-place (`data[:] = [...]`) atau assign ke variable baru bernama `output`. Ekspektasi: IntelliSense tidak full tapi syntax highlighting aktif.
6. **Pilih sumber data untuk `Test run`** - di panel bawah: (a) isi `Job ID (optional)` dari job yang sudah selesai, pipeline akan load hasil job itu; atau (b) paste sample JSON manual ke field `Or paste sample data (JSON array)`. Ekspektasi: validasi JSON otomatis, error merah jika malformed.
7. **Klik `Run`** - skrip dieksekusi di backend. Ekspektasi: loading spinner 0.5-5 detik, lalu panel hasil muncul dengan stdout capture (dari `print()`) + hasil `data`/`output` final.
8. **Iterasi** - ubah skrip, klik `Run` lagi. Tidak perlu save dulu.
9. **Save pipeline** - klik tombol `Create` (pipeline baru) atau `Update` (edit). Ekspektasi: entry baru/update di `data/pipelines.json`, toast "Saved".
10. **Aktifkan Auto Run (opsional)** - kembali ke form, set `Auto-run on job type` ke job type yang diinginkan, save lagi. Ekspektasi: setelah ini, setiap job type terkait yang completed akan memicu pipeline.
11. **Monitor hasil auto-run** - di panel "Recent Runs", atau cek `data/pipeline_runs/{job_id}_{pipeline_id}.json` di disk.
12. **Disable / hapus jika tidak perlu** - edit dan matikan toggle `Enabled`, atau klik ikon trash (tooltip `Delete`) di tabel.

## Pengaturan / Konfigurasi

### Name

Nama pipeline (string, required). Muncul di tabel dan di log. Gunakan nama deskriptif seperti `filter_small_images` atau `notion_export`.

### Description

Deskripsi bebas (string, opsional). Muncul sebagai subtitle. Tulis tujuan pipeline + input/output yang diharapkan, akan membantu Anda sendiri 3 bulan lagi saat lupa.

### Code

Body skrip Python. Tidak ada shebang, tidak perlu `def main():` - langsung statement top-level. Anda bisa define function di dalamnya lalu panggil, atau tulis flat script. Monaco Editor mendukung Ctrl+F untuk search, Ctrl+/ untuk comment toggle.

### Auto Run On

Enum: `None` (manual only), `image_harvester`, `url_mapper`, `site_ripper`, `media_downloader`. Saat di-set ke value non-None, `pipeline_listener.py` akan mendaftarkan callback ke `event_bus`. Ketika job type itu emit event `job_completed`, semua pipeline yang match akan dijalankan secara sekuensial (bukan parallel, untuk menghindari race condition pada file system).

### Variables tersedia di script

- `data` - list of dicts, output job upstream. Untuk Image Harvester biasanya `[{"url": "...", "alt": "...", "size": ...}]`; untuk URL Mapper `[{"url": "...", "depth": N, "title": "..."}]`; dst.
- `url` - URL target asli job (string atau None).
- `job_id` - ID job yang trigger pipeline (string).
- `output` - assign variable ini untuk override hasil akhir. Jika tidak di-assign, `data` hasil modifikasi yang dipakai.

### Pre-imported modules

`re`, `json`, `datetime`, `math`, `statistics`. Modul lain bisa Anda import sendiri (`import urllib.parse`, `import httpx`, dll) - tapi pastikan sudah ter-install di venv backend.

### Test Run: job_id vs sample_data

Prioritas: jika `job_id` diisi dan valid, sample_data diabaikan. Jika `job_id` kosong atau tidak ditemukan, fallback ke `sample_data` JSON. Jika keduanya kosong, `data = []`.

### Preset Snippets

- **filter_size** - loop `data`, keep hanya entry dengan `item.get('size', 0) > threshold`.
- **regex_clean** - `re.sub()` untuk membersihkan pola (misal strip query string dari URL).
- **extract_domain** - tambahkan field `domain` dari `urlparse(item['url']).netloc`.
- **aggregate_stats** - pakai `statistics.mean/median/stdev` untuk laporan numerik.

## Output

**Test Run**: output muncul inline di UI - tidak disimpan ke disk.

**Auto Run**: hasil disimpan ke `data/pipeline_runs/{job_id}_{pipeline_id}.json` dengan struktur:
```json
{
  "pipeline_id": "...",
  "job_id": "...",
  "started_at": "2026-04-17T10:00:00",
  "finished_at": "2026-04-17T10:00:02",
  "stdout": "...",
  "output": [...] atau {...},
  "error": null
}
```

File terpisah per run, tidak overwrite. Anda bisa list dan diff versi lama.

## Integrasi dengan fitur lain

1. **Image Harvester** - set `auto_run_on: image_harvester` untuk otomatis filter/resize/export setiap kali harvest selesai.
2. **URL Mapper** - pipeline bisa transform site map jadi sitemap.xml, atau filter URL by pattern untuk seed ke Site Ripper.
3. **Site Ripper** - post-process HTML files, ekstrak field via BeautifulSoup di dalam pipeline (perlu `import bs4`).
4. **AI Extract** - panggil endpoint `/api/ai-extract/run` lewat `httpx` di dalam pipeline, loop per-item, kumpulkan field LLM-extracted.
5. **Auth Vault** - pipeline bisa baca `data/auth_vault.json` langsung untuk enrichment credentials (misal lookup header per-domain).

## Tips & Best Practices

1. **Gunakan `print()` untuk debug** - stdout di-capture dan ditampilkan di Result panel. Sprinkle `print(f"row {i}: {item}")` saat iterasi.
2. **Jangan modifikasi `data` saat iterasi** - bikin copy: `for item in list(data): ...`. Atau build list baru dan assign ke `output`.
3. **Handle missing keys** - selalu `item.get('field', default)` bukan `item['field']` untuk menghindari KeyError yang menghentikan run.
4. **Idempotent** - skrip seharusnya bisa jalan 2x dengan input sama tanpa duplicate efek samping (terutama untuk auto-run).
5. **Commit script di luar UI** - copy kode Pipeline yang penting ke file `.py` di Git repo terpisah sebagai backup, karena `pipelines.json` tidak di-version-control default.
6. **Test dengan data kecil** - sample_data 5 row cukup untuk validasi logic. Jangan Test Run dengan 100k row tiap iterasi.
7. **Timeout diri sendiri** - pipeline tidak punya hard timeout; skrip infinite loop akan hang worker. Tambah `if i > 10000: break` sebagai safety.
8. **Audit sebelum Auto Run** - jalankan manual 2-3 kali sukses dulu sebelum enable auto-run, karena error di auto-run lebih susah di-debug.

## Troubleshooting

### Problem: Script tidak jalan saat job selesai (auto-run tidak trigger)
- **Symptom**: pipeline punya `auto_run_on: image_harvester`, tapi setelah harvest selesai, tidak ada entry di `data/pipeline_runs/`.
- **Cause**: `pipeline_listener.py` tidak ter-start, atau event_bus belum di-wire ke job yang bersangkutan.
- **Solution**: restart backend (`uvicorn`). Cek log startup untuk pesan "Pipeline listener registered". Jika tidak ada, cek `app/main.py` apakah listener di-initialize.

### Problem: NameError 'data' is not defined
- **Symptom**: Test Run gagal dengan "name 'data' is not defined".
- **Cause**: sample_data JSON kosong atau tidak valid, dan job_id tidak disediakan.
- **Solution**: paste minimal `[]` (list kosong) atau JSON valid ke sample_data textarea.

### Problem: Syntax error di Monaco tidak kelihatan
- **Symptom**: Run Test → error, tapi editor tidak highlight line yang bermasalah.
- **Cause**: Monaco linting untuk Python terbatas (tidak full pyright). Missing colon atau indent salah kadang lolos.
- **Solution**: baca pesan error di Result panel - line number diberikan. Fix manual. Alternatif: copy-paste skrip ke VS Code / PyCharm untuk linting penuh, lalu paste balik.

### Problem: ModuleNotFoundError saat import
- **Symptom**: `import pandas` → "No module named 'pandas'".
- **Cause**: paket tidak ter-install di venv backend PyScrapr.
- **Solution**: aktifkan venv backend, `pip install pandas`, restart backend. Atau pakai stdlib alternatif.

### Problem: Pipeline mengubah `data` tapi output tidak berubah
- **Symptom**: `data.append(...)` dijalankan tapi result kosong.
- **Cause**: Anda assign variable baru `data = [...]` (rebind, bukan mutate). Reference original hilang.
- **Solution**: gunakan `data[:] = new_list` (slice assignment, mutate in-place) atau assign ke `output` variable eksplisit.

### Problem: Pipeline hang, tidak pernah selesai
- **Symptom**: spinner berputar 5+ menit, bahkan untuk data kecil.
- **Cause**: infinite loop, atau external HTTP request tanpa timeout.
- **Solution**: kill backend process, cek skrip untuk `while True` tanpa break. Tambah `timeout=30` ke semua `httpx.get/post`. Restart backend.

### Problem: File `pipelines.json` corrupt / tidak bisa di-load
- **Symptom**: halaman Pipeline kosong meskipun sebelumnya ada entri; error log "JSONDecodeError".
- **Cause**: race condition saat 2 save bersamaan, atau edit manual dengan syntax salah.
- **Solution**: restore dari backup jika ada; atau edit manual `data/pipelines.json` untuk perbaiki syntax. Minimal valid: `[]`.

### Problem: stdout terlalu panjang, UI freeze
- **Symptom**: skrip `print()` dalam loop 100k kali; halaman browser hang.
- **Cause**: result panel render semua stdout sekaligus tanpa virtualization.
- **Solution**: limit print ke sample (`if i % 100 == 0: print(...)`), atau redirect ke file (`open('log.txt','w').write(...)`).

### Problem: Pipeline auto-run sukses tapi hasil tidak sesuai ekspektasi di kedua kali run
- **Symptom**: run pertama output correct, run kedua duplikat atau missing.
- **Cause**: skrip tidak idempotent - mungkin `data.extend()` atau side-effect ke global state.
- **Solution**: refactor agar skrip selalu build output baru dari input, tidak tergantung state sebelumnya.

## FAQ

**Q: Apakah Custom Pipeline aman?**
A: Tidak disandbox. Untuk tool personal lokal, ini trade-off demi fleksibilitas. Jangan paste skrip dari sumber asing.

**Q: Bisa pakai async/await?**
A: Ya, tapi harus `import asyncio` dan `asyncio.run(main())` di akhir, karena exec context-nya sync.

**Q: Bisa akses database eksternal (PostgreSQL, MongoDB)?**
A: Bisa - install driver (`psycopg2`, `pymongo`) ke venv, lalu import. PyScrapr tidak membatasi network.

**Q: Bagaimana schedule pipeline (cron)?**
A: Tidak built-in. Pakai Windows Task Scheduler / cron untuk panggil endpoint `POST /api/pipelines/{id}/run` via curl.

**Q: Bisa chain 2 pipeline?**
A: Tidak ada UI chaining. Workaround: dalam skrip pipeline A, panggil endpoint pipeline B lewat httpx.

**Q: Batas ukuran script?**
A: Tidak ada hard limit, tapi Monaco mulai laggy di >5000 baris. Pecah jadi fungsi modular.

**Q: Apakah `data` di-deep-copy?**
A: Tidak. Modifikasi in-place akan mengubah reference yang sama. Jika ingin safety, `import copy; data = copy.deepcopy(data)` di awal.

**Q: Support Python 3.12+ features?**
A: Tergantung versi Python yang jalankan backend. Cek `python --version` di venv.

**Q: Log run di-rotate otomatis?**
A: Tidak. `data/pipeline_runs/` akan membengkak seiring waktu. Bersihkan manual atau tulis pipeline cleanup.

**Q: Bisa mengakses state antar-run?**
A: Tidak via variable global. Pakai file (`open('data/state.json')`) untuk persistence sederhana.

## Keterbatasan

- **Tidak ada sandbox** - skrip punya akses penuh ke filesystem dan network.
- **Tidak ada debugger interaktif** - no breakpoint; harus print-debug.
- **Monaco linting Python terbatas** - tidak selevel PyCharm/VS Code dengan pylance.
- **Tidak ada version history** - save = overwrite. Backup manual jika perlu.
- **Tidak parallel** - auto-run sekuensial untuk hindari race.
- **Tidak ada test harness formal** - Test Run hanya eksekusi ad-hoc, tidak ada assert framework.
- **Variabel `data` bisa besar** - untuk job dengan 100k row, load penuh ke memory mungkin lambat.

## Related docs

- [AI Extract](./ai-extract.md) - bisa dipanggil dari pipeline untuk ekstraksi terstruktur batch.
- [Selector Playground](./playground.md) - eksplorasi CSS/XPath sebelum di-coding ke pipeline.
- [Event bus architecture](/docs/advanced/webhooks.md) - detail teknis pipeline_listener.
- [Auth Vault](./vault.md) - baca credentials per-domain dari pipeline.
- [Index dokumentasi](../index.md) - navigasi utama.
