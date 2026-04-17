# REST API Generator

> Endpoint `/api/data/{job_id}` terunifikasi yang menyajikan data hasil scraping dalam format JSON dengan query parameter filter, sort, limit, dan pagination - memungkinkan tool eksternal seperti Zapier, n8n, Grafana, Jupyter, dan dashboard custom mengkonsumsi data PyScrapr secara programmatic tanpa export manual.

## Deskripsi

REST API Generator mengubah PyScrapr dari tool GUI menjadi data service. Setiap job yang selesai di-scrape datanya secara otomatis accessible via endpoint HTTP standar tanpa perlu export manual ke file dulu. Endpoint `GET /api/data/{job_id}` mengembalikan hasil scraping dalam struktur JSON yang konsisten, mendukung query parameter untuk filtering, sorting, limiting, dan pagination, sehingga konsumer (dashboard internal, pipeline ETL, notebook Jupyter, aplikasi mobile custom) dapat mengambil data sesuai kebutuhan tanpa over-fetch yang memboroskan bandwidth dan memori.

Unified endpoint artinya format response sama untuk semua tool: Harvester, Ripper, Mapper, Media Downloader, dan Scraper klasik. Envelope standar berisi field `{job_id, tool, url, status, count, items: [...], meta: {...}}`. Isi array `items` bervariasi per tool: untuk Harvester tiap item adalah object asset `{image_url, width, height, size_kb, hash}`, untuk Mapper berupa `{url, status, depth, parent_url, outbound_links}`, untuk Media Downloader `{file_url, title, duration, format, size_bytes}`, dan untuk Ripper berupa asset nodes dengan tipe (html, image, css, js). Konsumer generic dapat proses envelope dulu, lalu dispatch ke handler per tool berdasarkan field `tool`. Struktur predictable ini mempermudah integration layer.

FastAPI otomatis generate dokumentasi OpenAPI di `/docs` (interactive Swagger UI) dan `/redoc` berdasarkan type hints di endpoint function dan Pydantic models. Ini berarti tiap developer yang akses instance PyScrapr dapat explore API via browser, test request langsung, melihat schema response, dan copy-paste curl command. Catatan nama: ada potensi confusion antara `/docs` API dan `/docs` frontend documentation. PyScrapr memilih path `/docs` API karena standar FastAPI, sementara frontend documentation viewer di-host di `/documentation` atau route terpisah. Fitur auto-generated docs ini mengurangi effort maintenance: selama code di-annotate dengan Pydantic models benar, dokumentasi selalu up-to-date.

Use case utama mencakup dashboard eksternal yang pull data hasil scraping dan visualize di Grafana atau Metabase; pipeline ETL yang fetch data tiap jam dan load ke data warehouse seperti BigQuery atau Snowflake; automation Zapier/IFTTT/n8n yang trigger action berdasarkan hasil scrape (contoh: kirim email saat harga produk turun); Jupyter notebook untuk analisis ad-hoc tanpa copy-paste dari UI; dan mobile app internal yang display subset data. Karena PyScrapr by default hanya listen di localhost, untuk akses remote Anda perlu port forwarding, reverse proxy (nginx), atau deploy ke server dengan auth layer di depan.

## Kapan pakai?

1. **Integrasi dengan data warehouse** - Fetch hasil scraping harian dan load ke BigQuery, Snowflake, atau PostgreSQL via custom ETL job.
2. **Dashboard analytics** - Grafana atau Metabase connection ke API PyScrapr untuk visualize trend data scraped over time.
3. **Notifikasi bersyarat** - Script eksternal yang polling dan trigger alert jika hasil scrape memenuhi kriteria spesifik seperti harga produk di bawah threshold.
4. **Jupyter atau notebook analysis** - Load dataset langsung ke Pandas DataFrame tanpa download file CSV manual dari UI.
5. **Mobile app companion** - Aplikasi iOS atau Android internal yang display subset data dari API untuk monitoring on-the-go.
6. **Cross-tool pipeline** - PyScrapr jadi bagian dari pipeline besar, datanya dikonsumsi oleh tool ML/AI downstream seperti classifier atau LLM.
7. **Automated testing** - Test suite yang verify hasil scrape sesuai expectation lewat API (regression testing untuk scraping logic).
8. **Public data portal** - Expose data selective ke public lewat proxy API dengan auth layer terpisah dan rate limiting ketat.

## Cara penggunaan

1. Jalankan job apapun (Harvester, Mapper, Ripper, Media, Scraper) hingga status `done`. Catat `job_id` dari History atau response body saat submit.
2. Akses endpoint via curl, Postman, atau browser langsung: `GET http://localhost:8000/api/data/<job_id>`.
3. Response default berisi semua items tanpa filter, dengan `limit` default 100. Untuk filter field spesifik, pakai query param `?filter=field:value`.
4. Untuk sorting, pakai `?sort=field` (ascending) atau `?sort=-field` (descending, dengan prefix minus).
5. Untuk pagination, pakai `?limit=100&offset=200` untuk halaman ketiga dengan 100 items per page.
6. Multiple query param dapat dikombinasi: `?filter=width:1920&sort=-size_kb&limit=50`.
7. Untuk explore schema interactive, buka `http://localhost:8000/docs` di browser. Swagger UI memungkinkan trying endpoint langsung dari browser.
8. Copy curl command dari Swagger untuk integrasi ke script atau CI pipeline.
9. Di Python, gunakan `requests.get(url).json()` atau `httpx.get(url).json()` untuk parse response ke dict.
10. Di JavaScript, gunakan `fetch(url).then(r => r.json())` untuk browser environment.
11. Handle error codes: 404 jika job_id tidak ditemukan, 400 jika query param invalid, 500 untuk server error internal.
12. Implement retry logic di konsumer untuk handle transient failure, terutama jika konsumer berjalan di network tidak stabil.
13. Untuk production integration, tambahkan API key middleware; PyScrapr open untuk modifikasi auth.
14. Monitor access log via FastAPI uvicorn default logging untuk debugging atau audit.
15. Untuk workload besar, pakai `format=csv` streaming agar tidak load full JSON ke memori konsumer.

## Pengaturan / Konfigurasi

### job_id (path parameter)
String UUID, required. Job ID dari History atau response submit. Format standar UUID v4.

### filter (query parameter)
String, optional, dapat multiple. Format `field:value` atau `field:value1,value2` untuk OR dalam satu field. Multiple `filter=` param untuk AND across fields. Contoh: `?filter=status:200&filter=depth:2,3`.

### sort (query parameter)
String, optional. Field untuk sort. Prefix `-` untuk descending. Contoh: `?sort=-size_kb` untuk size terbesar dulu.

### limit (query parameter)
Integer, default 100, max 10000. Jumlah maksimum items dalam response. Hard cap dapat diatur via `api_max_limit` di Settings.

### offset (query parameter)
Integer, default 0. Offset untuk pagination. Gunakan dengan limit untuk iterasi melalui dataset besar.

### fields (query parameter)
String comma-separated, optional. Projection field tertentu untuk mengurangi payload size. Contoh: `?fields=url,status` hanya return dua field tersebut di items.

### format (query parameter)
Enum `json` atau `csv`. Default `json`. CSV streamable untuk large dataset tanpa buffer full di memori.

### include_meta (query parameter)
Boolean, default true. Include envelope meta fields seperti `completed_at`, `duration_seconds`, `config_snapshot`.

### flatten (query parameter)
Boolean, default false. Flatten nested object ke dot-notation key, berguna untuk format CSV yang tidak support nested structure.

### api_default_limit (setting)
Integer di Settings, default limit jika query tidak specify. Default 100. Rekomendasi: biarkan sesuai untuk hindari over-fetch.

### api_max_limit (setting)
Integer, hard cap limit untuk prevent overload. Default 10000. Naikkan hanya jika Anda punya infrastruktur dan bandwidth.

### api_enable_cors (setting)
Boolean, enable CORS headers untuk cross-origin consumption dari browser. Default false. Aktifkan hanya dengan origins whitelist.

### api_rate_limit_per_min (setting)
Integer, rate limit per IP. Default 0 berarti unlimited. Set 60-120 untuk production public-facing.

### api_require_key (setting)
Boolean, enforce API key in Authorization header. Default false untuk local use.

### api_key (setting)
String shared secret jika `api_require_key=true`. Generate via UUID atau random 32-char string.

## Output / Efek

Response JSON envelope structure standar:

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

Field `count` adalah jumlah items dalam response ini, `total_available` adalah total items di job (untuk pagination UI). Untuk `format=csv`, response berupa stream text CSV dengan header row otomatis dari keys items. Content-Type menjadi `text/csv` dengan `Content-Disposition: attachment` header untuk trigger download di browser.

Contoh konsumsi Python:
```python
import requests
r = requests.get("http://localhost:8000/api/data/abc-123?limit=500&sort=-size_kb")
data = r.json()
for item in data["items"]:
    print(item["image_url"], item["size_kb"])
```

Contoh JavaScript fetch:
```javascript
const res = await fetch("/api/data/abc-123?filter=status:200");
const data = await res.json();
console.log(data.count, data.items);
```

## Integrasi dengan fitur lain

- **History** - Source of truth untuk `job_id` yang valid; setiap record di History accessible via REST API.
- **Diff Detection** - Endpoint terpisah `/api/diff/{job_id}` sebagai bagian dari REST API family.
- **Bulk Queue** - `POST /api/bulk/submit` juga REST API standar dengan schema yang documented di Swagger.
- **Webhooks** - Alternatif push-based (webhook) vs pull-based (REST API) untuk konsumsi data.
- **Scheduled** - Data dari scheduled runs accessible via API dengan metadata schedule source.
- **Settings** - Konfigurasi limit, CORS, auth, rate limit untuk hardening production.

## Tips & Best Practices

1. **Gunakan field projection.** `?fields=url,status` mengurangi payload drastis untuk large dataset. Fetch hanya yang dibutuhkan konsumer agar parsing lebih cepat.

2. **Paginate large data.** Jangan ambil 10000 items sekaligus; iterate dengan offset untuk memory-safe baik di server maupun konsumer.

3. **Cache di sisi konsumer.** Data scraping tidak berubah setelah job `done`; cache dengan TTL panjang (24 jam) aman kecuali Anda re-run job dengan job_id baru.

4. **Monitor via OpenAPI docs.** Swagger UI di `/docs` adalah tool debugging terbaik saat integration; copy curl langsung dari UI.

5. **Aktifkan CORS hanya jika butuh.** Cross-origin access membuka pintu untuk XSS atau CSRF di hosted environment. Whitelist origins spesifik, bukan wildcard.

6. **Tambah API key di production.** Jangan expose endpoint tanpa auth jika accessible dari public network. Rotasi key secara berkala.

7. **Pakai format=csv untuk streaming big download.** CSV streamable vs JSON yang buffer all di memori; untuk dataset 100000 plus items, CSV lebih efisien.

8. **Version API saat breaking change.** Jika format berubah, bump ke `/api/v2/data/...` untuk backward compatibility dengan konsumer lama.

9. **Log access pattern.** FastAPI uvicorn log default sudah memadai untuk audit; tambah middleware custom jika butuh detail per-user.

10. **Handle 429 rate limit di konsumer.** Implement exponential backoff saat response 429 dari rate limit. Baca header `Retry-After` untuk tunggu optimal.

## Troubleshooting

### Problem: 404 Not Found untuk job_id yang valid
**Gejala:** Endpoint return 404 meski job ada di History UI.
**Penyebab:** Job sudah di-archive atau di-delete via retention policy.
**Solusi:** Verifikasi di History dengan filter archived. Cek flag `archived` di database row job.

### Problem: 400 Bad Request untuk filter query
**Gejala:** Response 400 saat pakai `?filter=...`.
**Penyebab:** Syntax filter salah (missing colon), atau field name tidak exist di schema tool tersebut.
**Solusi:** Verifikasi format `field:value`. Cek schema items di `/docs` untuk field names yang valid per tool.

### Problem: Response sangat lambat lebih dari 5 detik
**Gejala:** Request hang sebentar sebelum return.
**Penyebab:** Query tanpa limit di job besar, atau sort on field yang belum ter-index.
**Solusi:** Set `limit` explicit (maksimal 500). Gunakan offset untuk paginate bertahap.

### Problem: CSV response encoding aneh di Excel
**Gejala:** Karakter non-ASCII muncul rusak saat open di Excel.
**Penyebab:** UTF-8 BOM missing; Excel default assume Windows-1252.
**Solusi:** Tambahkan `api_csv_add_bom=true` di Settings. Atau import CSV manual di Excel dengan encoding UTF-8 via Data > From Text.

### Problem: 429 Rate Limit Exceeded
**Gejala:** Konsumer dapat 429 setelah beberapa request cepat.
**Penyebab:** Rate limit per IP tercapai.
**Solusi:** Naikkan `api_rate_limit_per_min` atau implement backoff exponential di konsumer. Distribute dari multiple IP jika perlu volume besar.

### Problem: 401 Unauthorized
**Gejala:** Response 401 meski URL benar.
**Penyebab:** `api_require_key=true` tapi request tidak include header Authorization.
**Solusi:** Tambah header `Authorization: Bearer <key>` di konsumer. Verifikasi key di Settings cocok.

### Problem: Filter multiple value tidak bekerja seperti diharapkan
**Gejala:** Query `?filter=field:v1&filter=field:v2` return data tidak match.
**Penyebab:** Syntax comma untuk OR dalam satu field, multiple param untuk AND cross field.
**Solusi:** Pakai `?filter=field:v1,v2` untuk OR dalam satu field. Multiple `filter=` param berbeda field untuk AND.

### Problem: Items array kosong padahal job sukses dengan data
**Gejala:** Response count=0 padahal History tunjukkan job berhasil.
**Penyebab:** Filter eksklusif terlalu ketat, atau offset lebih besar dari total_available.
**Solusi:** Remove filter untuk debug. Cek `total_available` di response untuk verifikasi.

### Problem: CORS error di browser client
**Gejala:** Browser console error "CORS policy blocked".
**Penyebab:** `api_enable_cors=false` atau origin konsumer tidak ada di whitelist.
**Solusi:** Enable di Settings. Verifikasi allowed origins configurable dan match origin browser.

### Problem: OpenAPI schema tidak reflect change terbaru
**Gejala:** Swagger UI masih tunjukkan schema lama setelah update code.
**Penyebab:** Browser cache atau server belum restart setelah code change.
**Solusi:** Hard refresh browser (Ctrl-Shift-R). Restart FastAPI server untuk regenerate schema.

## FAQ

**Q: Apakah endpoint butuh auth default?**
A: Default false (local tool). Enable via `api_require_key=true` untuk production deployment.

**Q: Berapa rate limit default?**
A: Unlimited default untuk local use. Set threshold 60-120 per minute jika expose ke public.

**Q: Bisa akses data job yang masih running?**
A: Ya, tapi `items` bisa partial. Rekomendasi wait status done untuk data lengkap.

**Q: Apakah response cached server-side?**
A: Tidak default. Tambah Redis cache via middleware custom jika butuh performa lebih.

**Q: Bisa pakai POST untuk complex filter dengan body JSON?**
A: Saat ini hanya GET. Complex filter via multiple query param atau fetch all lalu filter di konsumer.

**Q: Apakah OpenAPI schema exportable?**
A: Ya, akses `/openapi.json` untuk raw spec, bisa di-import ke Postman atau code generator.

**Q: Versioning API?**
A: Saat ini v1 implisit. Future breaking change akan pakai versi eksplisit `/api/v2/...`.

**Q: Bisa subscribe ke stream Server-Sent Events?**
A: Tidak built-in. Webhook alternatif push-based untuk real-time notification.

**Q: Apakah API expose sensitive data?**
A: `config_snapshot` di meta include konfigurasi termasuk credentials jika ada. Filter `?include_meta=false` untuk exclude.

**Q: Log access endpoint disimpan di mana?**
A: FastAPI uvicorn log access default ke stdout. Tambah middleware custom untuk audit log ke file atau syslog.

**Q: Bisa akses endpoint dari luar network lokal?**
A: Butuh port forwarding, reverse proxy seperti nginx, atau tunnel service seperti ngrok untuk dev testing.

**Q: Bagaimana integrate dengan Zapier?**
A: Gunakan Zapier "Webhooks by Zapier" trigger dengan GET ke endpoint PyScrapr, atau terima push dari PyScrapr webhook.

## Keterbatasan

- Hanya GET method untuk data retrieval; no POST query body untuk complex filter.
- Filter sederhana (exact match, OR in field, AND across fields); no regex atau range queries.
- No aggregation (sum, avg, count_distinct); raw items only.
- Pagination offset-based (deep pages bisa lambat di dataset besar).
- Tidak ada subscription atau streaming (SSE atau WebSocket).
- API key global, tidak per-user atau per-scope.
- Rate limiting sederhana per-IP, tidak per-key.
- No GraphQL option untuk flexible query.
- Tidak ada endpoint untuk delete atau modify data (read-only by design).
- Config snapshot di meta bisa leak credential jika tidak di-mask.

## Studi kasus penggunaan nyata

**Skenario 1: Grafana dashboard untuk monitor harga produk.** Pengguna scrape harga 50 produk competitor harian. Data-source Grafana di-set ke PyScrapr REST API dengan plugin JSON. Grafana polling setiap jam, fetch data terbaru, plot trend line untuk tiap produk. Visual dashboard dengan alert ketika price drop lebih dari 10 persen. Zero kode integration custom, semua config via Grafana UI.

**Skenario 2: ETL ke BigQuery via Airflow.** Data engineer build DAG Airflow yang fetch hasil scraping PyScrapr harian via API, transform dengan pandas, load ke BigQuery. Endpoint `/api/data/{job_id}?format=csv` di-stream langsung ke BigQuery loader. Pipeline end-to-end berjalan 10 menit per batch, vs sebelumnya 1 jam manual export plus upload.

**Skenario 3: Jupyter notebook untuk ad-hoc analysis.** Analyst buka notebook, `import requests`, fetch endpoint API PyScrapr, load ke DataFrame, lakukan analysis statistik atau ML. Cycle eksperimen cepat: run job PyScrapr, refresh cell notebook, dapat hasil. Tidak perlu download CSV dan re-import setiap iterasi.

**Skenario 4: Mobile companion app untuk monitoring.** Developer build iOS app internal yang tampilkan latest scrape result di home screen widget. App polling endpoint REST API setiap 15 menit, tampilkan top 10 items. Notifikasi push jika ada item match kriteria user. Simple, low maintenance, very useful untuk team operations on-the-go.

**Skenario 5: Zapier automation saat ada data baru.** Zapier Zap trigger pada schedule 1 jam, GET ke endpoint PyScrapr, filter items yang match kondisi (contoh: price turun 20 persen), post ke Slack channel plus email marketing team. End-to-end automation tanpa coding server, murah di plan Zapier starter.

## Security hardening untuk production

Jika PyScrapr di-expose beyond localhost, beberapa langkah hardening wajib:

1. **Enable API key authentication.** `api_require_key=true` di Settings. Generate key random 32+ karakter, simpan di password manager. Rotate quarterly.

2. **Gunakan reverse proxy dengan TLS.** Nginx atau Caddy di depan PyScrapr untuk terminate TLS, enable HTTP/2, dan memberi layer tambahan untuk rate limit plus IP filtering.

3. **Whitelist origin untuk CORS.** Jangan pakai wildcard `*`. Specify exact origins dari konsumer browser yang legitimate.

4. **Set rate limit reasonable.** Untuk consumer internal, 60-120 request per menit cukup. Lebih ketat jika endpoint publik.

5. **Log access untuk audit.** Middleware custom untuk log IP, API key hash, endpoint, status, dan timestamp ke file terpisah untuk audit trail.

6. **Disable `/docs` dan `/redoc` di production.** OpenAPI UI bisa expose schema ke attacker. Set `docs_url=None` di FastAPI app init untuk production build.

7. **Filter sensitive field dari response.** Default `include_meta=false` untuk request eksternal agar config_snapshot tidak expose.

8. **Monitor anomaly traffic.** Spike tiba-tiba di endpoint bisa signal abuse atau leak API key. Alert via webhook ke ops channel.

## Integrasi code examples lanjutan

**Python dengan pagination:**
```python
import requests
def fetch_all(job_id):
    offset = 0
    all_items = []
    while True:
        r = requests.get(f"http://localhost:8000/api/data/{job_id}",
                         params={"limit": 500, "offset": offset})
        data = r.json()
        all_items.extend(data["items"])
        if len(data["items"]) < 500: break
        offset += 500
    return all_items
```

**Node.js dengan streaming CSV:**
```javascript
const fetch = require('node-fetch');
const fs = require('fs');
const res = await fetch('http://localhost:8000/api/data/abc?format=csv');
res.body.pipe(fs.createWriteStream('output.csv'));
```

**PowerShell untuk Windows automation:**
```powershell
$data = Invoke-RestMethod "http://localhost:8000/api/data/abc-123?limit=100"
$data.items | Export-Csv output.csv -NoTypeInformation
```

## Performance tuning untuk workload besar

Untuk dataset besar (100000+ items), default settings mungkin tidak optimal. Tuning recommended:

1. **Index database columns yang sering di-filter atau sort.** Jika workload sering query `?filter=status:200&sort=-size_kb`, tambah index composite di kolom status dan size_kb. Query time turun dari detik ke milidetik.

2. **Gunakan CSV streaming untuk export besar.** Endpoint `format=csv` stream row-by-row, memory footprint konstan independen dari total rows. JSON buffer full di memori, bisa OOM untuk dataset besar.

3. **Kurangi include_meta untuk batch API call.** Jika Anda loop 1000 job_id dan fetch data masing-masing, `include_meta=false` kurangi payload 20-30 persen, mempercepat total loop.

4. **Cache aggressive di konsumer.** Data scraping immutable setelah job done. Cache hasil dengan TTL 24 jam di Redis atau memory. Reduce load ke PyScrapr server.

5. **Parallel fetch tapi dengan rate limit.** Jika butuh fetch banyak job_id bersamaan, pakai asyncio atau threading, tapi respect `api_rate_limit_per_min`.

6. **Shard by time range.** Untuk data historical, split query berdasarkan range waktu. Query per-hari vs query semua 1 tahun jauh lebih manageable.

## Common integration recipes

**Google Sheets auto-update via Apps Script:**
```javascript
function updatePyScrapr() {
  const url = "http://your-server/api/data/latest-job-id";
  const response = UrlFetchApp.fetch(url);
  const data = JSON.parse(response.getContentText());
  const sheet = SpreadsheetApp.getActiveSheet();
  sheet.clear();
  sheet.appendRow(Object.keys(data.items[0]));
  data.items.forEach(item => sheet.appendRow(Object.values(item)));
}
```

**Metabase custom question dengan HTTP data source:**
Metabase Enterprise support HTTP JSON source. Point URL ke endpoint PyScrapr, schema auto-detected, dashboard builder bisa visualize langsung.

**Discord bot dengan data real-time:**
```python
import discord, requests
class Bot(discord.Client):
    async def on_message(self, m):
        if m.content.startswith("!scraper"):
            data = requests.get("http://localhost:8000/api/data/latest").json()
            await m.channel.send(f"Count: {data['count']}")
```

**iOS Shortcut untuk quick fetch:**
Shortcut "Get Contents of URL" pointed to endpoint PyScrapr, output JSON, "Get Dictionary from Input" parse, "Show Alert" display result. Zero code app Apple.

## Versi masa depan dan roadmap API

Roadmap REST API untuk versi mendatang:

1. **GraphQL endpoint.** Alternatif REST untuk query flexible tanpa over-fetch. Target Phase 5.

2. **WebSocket untuk real-time update.** Subscribe ke job progress stream. Useful untuk UI dashboard custom.

3. **Cursor-based pagination.** Replace offset-based untuk performa stabil di deep pages.

4. **Aggregation endpoint.** `/api/data/{job_id}/aggregate?by=field&op=count` untuk summary tanpa fetch full items.

5. **Bulk fetch endpoint.** `POST /api/data/batch` dengan body array of job_ids untuk reduce roundtrip.

6. **Write endpoint terbatas.** PATCH untuk update tag atau archive flag. Currently read-only by design.

7. **Webhook subscription management via API.** CRUD webhook config tanpa UI Settings.

Saat ini semua masih backlog; feedback user membantu prioritize. Submit issue atau PR di repository untuk advokasi feature tertentu.

## Related docs

- [History](/docs/system/history.md) - Source of truth untuk job_id yang accessible via API.
- [Diff Detection](/docs/system/diff.md) - Endpoint `/api/diff/{job_id}` terkait untuk perubahan antar run.
- [Bulk Queue](/docs/advanced/bulk-queue.md) - Endpoint `/api/bulk/submit` untuk batch submission.
- [Webhooks](/docs/advanced/webhooks.md) - Push-based alternative untuk notifikasi real-time.
- [Settings](/docs/system/settings.md) - Konfigurasi CORS, rate limit, API key.
