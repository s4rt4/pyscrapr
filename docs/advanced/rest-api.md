# REST API Generator

> Endpoint `/api/data/{job_id}` terunifikasi yang menyajikan data hasil scraping dalam format JSON dengan query param filter/sort/limit — memungkinkan tool eksternal konsumsi data PyScrapr secara programmatic.

## Deskripsi

REST API Generator mengubah PyScrapr dari tool GUI menjadi data service. Setiap job yang selesai di-scrape datanya secara otomatis accessible via endpoint HTTP standar, tanpa perlu export manual ke file dulu. Endpoint `GET /api/data/{job_id}` mengembalikan hasil scraping dalam struktur JSON yang konsisten, mendukung query parameter untuk filtering, sorting, limiting, dan pagination — sehingga konsumer (dashboard internal, pipeline ETL, notebook Jupyter, dll) dapat ambil data sesuai kebutuhan tanpa over-fetch.

Unified endpoint artinya format response sama untuk semua tool (Harvester, Ripper, Mapper, Media, Scraper klasik), dengan envelope standar: `{job_id, tool, url, status, count, items: [...], meta: {...}}`. Isi `items` bervariasi per tool — untuk Harvester tiap item adalah `{image_url, width, height, size_kb, hash}`, untuk Mapper `{url, status, depth, parent_url, outbound_links}`, untuk Media `{file_url, title, duration, format, size_bytes}`. Konsumer yang generic dapat proses envelope dulu, lalu dispatch ke handler per tool berdasarkan field `tool`. Struktur ini mempermudah integration layer karena predictable.

FastAPI otomatis generate dokumentasi OpenAPI di `/docs` dan `/redoc` berdasarkan type hints di endpoint function. Ini berarti tiap developer yang akses instance PyScrapr bisa explore API via interactive Swagger UI, test request dari browser, melihat schema response, dan copy-paste curl command. Fitur ini mengurangi effort maintenance dokumentasi — selama code di-annotate dengan Pydantic models benar, dokumentasi always up-to-date.

Use case utama mencakup: (1) dashboard eksternal yang pull data hasil scraping dan visualize di tool analytics favorit; (2) pipeline ETL yang fetch data tiap jam dan load ke data warehouse; (3) automation Zapier/IFTTT/n8n yang trigger action berdasarkan hasil scrape; (4) Jupyter notebook untuk analisis ad-hoc tanpa kopi-paste dari UI; (5) mobile app internal yang display subset data di dashboard custom. Karena PyScrapr by default hanya listen di localhost, untuk akses remote Anda perlu port-forwarding atau deploy ke server (mesin sendiri).

## Kapan pakai?

1. **Integrasi dengan data warehouse** — Fetch hasil scraping harian dan load ke BigQuery/Snowflake via custom ETL job.
2. **Dashboard analytics** — Grafana/Metabase connection ke API PyScrapr untuk visualize trend data scraped.
3. **Notifikasi bersyarat** — Script eksternal yang polling dan trigger alert jika hasil scrape memenuhi kriteria (misal harga produk di bawah target).
4. **Jupyter/notebook analysis** — Load dataset langsung ke DataFrame tanpa download file CSV manual.
5. **Mobile app companion** — App iOS/Android internal yang display subset data dari API.
6. **Cross-tool pipeline** — PyScrapr jadi bagian dari pipeline besar, data-nya dikonsumsi oleh tool ML/AI downstream.
7. **Automated testing** — Test suite yang verify hasil scrape sesuai expectation lewat API.
8. **Public data portal** — Expose data selective ke public lewat proxy API dengan auth layer di depan.

## Cara penggunaan

1. Jalankan job apapun hingga status `done`. Catat job_id dari History atau response submit.
2. Akses endpoint via curl, Postman, atau browser: `GET http://localhost:8000/api/data/<job_id>`.
3. Response default berisi semua items tanpa filter. Untuk filter field spesifik, pakai query param `?filter=field:value`.
4. Untuk sorting, pakai `?sort=field` (ascending) atau `?sort=-field` (descending).
5. Untuk paging, pakai `?limit=100&offset=200` untuk halaman ke-3 dengan 100 per halaman.
6. Multiple query param bisa dikombinasi: `?filter=width:1920&sort=-size_kb&limit=50`.
7. Untuk explore schema, buka `/docs` di browser. Swagger UI akan interactive.
8. Copy curl command dari Swagger untuk integrasi script.
9. Di code Python, gunakan `requests.get(url).json()` untuk parse response.
10. Handle errors: 404 jika job_id tidak ada, 400 jika query param invalid, 500 untuk server error.
11. Implement retry logic di konsumer untuk handle transient failure.
12. Untuk production integration, tambah API key middleware (PyScrapr open untuk modifikasi).

## Pengaturan / Konfigurasi

Endpoint `/api/data/{job_id}` mendukung query parameter:

- **job_id** (path, string UUID, required) — Job ID dari History.
- **filter** (query, string, optional, multiple) — Format `field:value` atau `field:value1,value2` untuk OR. Bisa multiple `filter=` untuk AND. Contoh: `?filter=status:200&filter=depth:2,3`.
- **sort** (query, string, optional) — Field untuk sort. Prefix `-` untuk descending. Contoh: `?sort=-size_kb`.
- **limit** (query, int, default 100, max 10000) — Max items dalam response.
- **offset** (query, int, default 0) — Offset untuk pagination.
- **fields** (query, string comma-separated, optional) — Projection field tertentu untuk reduce payload. Contoh: `?fields=url,status`.
- **format** (query, enum `json`, `csv`, default `json`) — Format response. CSV stream untuk large dataset.
- **include_meta** (query, boolean, default true) — Include meta envelope fields.
- **flatten** (query, boolean, default false) — Flatten nested object ke dot-notation key (useful untuk CSV).

Settings relevant di halaman Settings (tidak banyak karena endpoint stateless):

- **api_default_limit** (int, default 100) — Default limit jika query tidak specify.
- **api_max_limit** (int, default 10000) — Hard cap limit untuk prevent overload.
- **api_enable_cors** (boolean, default false) — Enable CORS headers untuk cross-origin consumption.
- **api_rate_limit_per_min** (int, default 0 = unlimited) — Rate limit per IP.
- **api_require_key** (boolean, default false) — Enforce API key in Authorization header.
- **api_key** (string, if require_key=true) — Shared secret API key.

## Output

Response JSON envelope structure:

```json
{
  "job_id": "uuid-string",
  "tool": "harvester",
  "url": "https://example.com/gallery",
  "status": "done",
  "count": 147,
  "total_available": 512,
  "limit": 100,
  "offset": 0,
  "items": [
    {
      "image_url": "https://example.com/img/001.jpg",
      "width": 1920,
      "height": 1080,
      "size_kb": 234,
      "hash": "sha256-hex..."
    }
  ],
  "meta": {
    "completed_at": "2026-04-17T03:15:42Z",
    "duration_seconds": 83,
    "config_snapshot": {...}
  }
}
```

Untuk format=csv, response berupa stream text CSV dengan header row otomatis dari keys items.

## Integrasi dengan fitur lain

- **History** — Source of truth untuk job_id yang valid.
- **Diff Detection** — Endpoint terpisah `/api/diff`, bagian dari REST API.
- **Bulk Queue** — `/api/bulk/submit` juga REST API standar.
- **Webhooks** — Alternatif push-based vs pull-based REST API.
- **Scheduled** — Data dari scheduled runs accessible via API.
- **Settings** — Konfig limit, CORS, auth.

## Tips & Best Practices

1. **Gunakan field projection** — `?fields=url,status` kurangi payload drastis untuk large dataset.
2. **Paginate large data** — Jangan ambil 10000 items sekaligus; iterate dengan offset untuk memory-safe.
3. **Cache di konsumer** — Data scraping tidak berubah setelah done; cache dengan TTL panjang.
4. **Monitor di OpenAPI docs** — Swagger UI tool debugging terbaik saat integration.
5. **Aktifkan CORS hanya jika butuh** — Cross-origin access buka pintu untuk XSS/CSRF di hosted env.
6. **Tambah API key di production** — Jangan expose endpoint tanpa auth jika accessible dari public.
7. **Pakai format=csv untuk streaming** — Untuk big download, CSV streamable vs JSON yang buffer all.
8. **Version API** — Jika breaking change ke format, bump ke `/api/v2/data/...` untuk backward compat.

## Troubleshooting

**Problem: 404 Not Found untuk job_id yang valid.**
Cause: Job sudah di-archive atau delete.
Solution: Verify di History. Cek archive flag di DB.

**Problem: 400 Bad Request untuk filter query.**
Cause: Syntax filter salah (missing colon, invalid field name).
Solution: Verify format `field:value`. Cek schema di /docs untuk field names valid.

**Problem: Response sangat lambat (>5 detik).**
Cause: Query tanpa limit di job besar, atau sort on un-indexed field.
Solution: Set `limit` explicit. Gunakan offset untuk paginate.

**Problem: CSV response encoding aneh di Excel.**
Cause: UTF-8 BOM missing.
Solution: Set `api_csv_add_bom` di Settings. Atau import CSV manual dengan encoding UTF-8.

**Problem: 429 Rate Limit Exceeded.**
Cause: Konsumer polling terlalu cepat.
Solution: Naikkan `api_rate_limit_per_min` atau implement backoff di konsumer.

**Problem: 401 Unauthorized.**
Cause: `api_require_key=true` tapi request tidak include header.
Solution: Tambah header `Authorization: Bearer <key>` di konsumer.

**Problem: Filter multiple value tidak bekerja.**
Cause: Syntax comma vs multiple param.
Solution: Pakai `?filter=field:v1,v2` untuk OR dalam satu field, atau multi `filter=` param untuk AND.

**Problem: Items array kosong padahal job sukses dengan data.**
Cause: Filter eksklusif terlalu ketat, offset lebih besar dari total.
Solution: Remove filter untuk debug. Cek `total_available`.

**Problem: CORS error di browser client.**
Cause: `api_enable_cors=false`.
Solution: Enable di Settings. Verify allowed origins configurable.

## FAQ

**Q: Apakah endpoint butuh auth default?**
A: Default false (local tool). Enable via Settings untuk production.

**Q: Berapa rate limit default?**
A: Unlimited default (local use). Set threshold jika expose publicly.

**Q: Bisa akses data job yang masih running?**
A: Ya, tapi `items` bisa partial. Recommend wait status=done.

**Q: Apakah response cached server-side?**
A: Tidak default. Tambah Redis cache via middleware jika butuh.

**Q: Bisa pakai POST untuk complex filter (body JSON)?**
A: Saat ini hanya GET. Complex filter via multiple query param.

**Q: Apakah OpenAPI schema exportable?**
A: Ya, akses `/openapi.json` untuk raw spec.

**Q: Versioning API?**
A: Saat ini v1 implisit. Future breaking change akan versi eksplisit.

**Q: Bisa subscribe ke stream (Server-Sent Events)?**
A: Tidak built-in. Webhook alternatif push-based.

**Q: Apakah API expose sensitive data?**
A: Config snapshot di meta include kredensial jika ada. Filter `?include_meta=false` untuk exclude.

**Q: Log access endpoint?**
A: FastAPI uvicorn log access default. Tambah middleware untuk audit log custom.

## Keterbatasan

- Hanya GET method untuk data retrieval.
- Filter sederhana (exact match, OR in field, AND across fields); no regex atau range.
- No aggregation (sum, avg, count_distinct); raw items only.
- Pagination offset-based (bisa lambat untuk deep pages).
- Tidak ada subscription/streaming (SSE/WebSocket).
- API key global, tidak per-user.
- Rate limiting sederhana per-IP.
- No GraphQL option.

## Related docs

- [History](../system/history.md) — Source job_id.
- [Diff Detection](../system/diff.md) — Endpoint diff terkait.
- [Bulk Queue](./bulk-queue.md) — Endpoint submit bulk.
- [Webhooks](./webhooks.md) — Push alternatif.
- [Settings](../system/settings.md) — Konfig CORS, rate limit.
