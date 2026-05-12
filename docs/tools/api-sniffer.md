# API Sniffer

> API Sniffer adalah tool tier P12 di PyScrapr untuk reverse engineer REST atau GraphQL endpoint dari Single Page Application (SPA) via Playwright network interception. Anda paste URL target, optionally script interaksi (klik, scroll, input form), tool akan jalankan headless Chromium dengan stealth, subscribe ke event `page.on("request")` dan `page.on("response")`, capture semua request yang dibuat halaman, dan group per (host, method, path) jadi `ApiEndpoint` yang rapi. Tool deteksi GraphQL operation otomatis dan group by `operationName`. Output: tab Endpoints dengan table grouped per host, tab GraphQL (kalau ada), timing chart request over time, dan stats summary. Export ke OpenAPI 3.0.3 JSON atau Postman v2.1 collection untuk import ke Swagger UI atau Postman app.

## Apa itu API Sniffer

Banyak situs modern adalah SPA: frontend Reach/Vue/Angular yang fetch data dari API backend lewat XHR/fetch. API itu sering tidak punya dokumentasi publik (internal use saja), tapi semua request flow lewat browser Anda saat Anda berinteraksi dengan situs. Buka DevTools Network tab, Anda lihat. Tapi Network tab di-design untuk debug satu request, bukan reverse engineering 200 request jadi spec API yang ter-organize.

API Sniffer otomatisasi proses ini. Jalankan headless browser, navigate ke URL target, biarkan halaman load + interact (opsional dengan script), capture semua network event dengan metadata lengkap (request method, URL, headers, body, response status, response headers, response body kalau JSON), lalu group per endpoint. Hasil: table yang menjawab "ini situs pakai API mana saja, untuk operasi apa, dengan auth method apa".

Positioning di sidebar Tools (warna indigo, route `/sniffer`, ikon antenna). Use case primary: dokumentasi API internal, integrasi situs yang tidak ada public API resmi, QA test suite dari capture browse session, security audit endpoint yang accidentally exposed.

> [!WARNING]
> Tool ini powerful. Tujuan etis: dokumentasi situs Anda sendiri, integrasi yang Anda butuh untuk personal automation, atau audit dengan izin. Lihat section Etika & Legal sebelum scan situs pihak ketiga.

Beda API Sniffer dengan mitmproxy atau Burp Suite Proxy: tool ini browser-based (Playwright), tidak butuh setup proxy/cert manual di browser host. Lebih portable, lebih cepat di-spin-up. Trade-off: tidak handle native mobile app traffic atau non-browser HTTP client (untuk itu, pakai mitmproxy).

## Cara kerja

Flow eksekusi:

1. **Spawn headless Chromium** via Playwright dengan stealth plugin aktif (kalau toggle on). Browser context bersih (tidak ada cookies dari session Anda).
2. **Subscribe network events**: `page.on("request", handler)` dan `page.on("response", handler)`. Tiap request tertangkap dengan: timestamp, method, URL parsed, headers, body (kalau ada), resource type.
3. **Navigate ke URL target** via `page.goto(url, wait_until="networkidle")`. Browser load HTML, execute JS, fetch XHR/fetch ke API.
4. **(Opsional) jalankan interaksi script** kalau Anda set: scroll, klik selector, input form, wait. Lihat section Interaksi di bawah.
5. **Wait strategy** decide kapan stop capture:
   - **2s idle silence**: kalau tidak ada request baru selama 2 detik berturut, anggap sudah selesai (default).
   - **wait_seconds hard timeout**: cap waktu maximum (default 30s).
   - **max_requests cap**: kalau jumlah request mencapai limit (default 500).
6. **Group + analyze**: post-process semua captured request. Group per (host, method, path). GraphQL detection (lihat di bawah). Filter aset statis kalau toggle on.
7. **Sanitize**: mask sensitive headers (Cookie, Authorization, X-API-Key) untuk display. Original tetap di internal storage untuk export.
8. **Render output**: tabs Endpoints, GraphQL, Timing, Stats. Plus tombol Export OpenAPI dan Export Postman.

## Cara pakai

Buka menu **API Sniffer** di sidebar Tools (warna indigo, ikon antenna). Halaman: form input di atas, tabs hasil di bawah.

### Langkah 1: Setup target

1. Field `URL` di header. Paste URL halaman target (homepage atau page yang trigger API call yang Anda incar).
2. (Opsional) Set:
   - **Wait seconds**: hard timeout (default 30s).
   - **Max requests**: cap jumlah request (default 500).
   - **Filter static assets**: skip `.js`, `.css`, gambar, font, woff (default on, biasanya Anda hanya peduli API).
   - **Stealth mode**: pakai Playwright Stealth plugin untuk evade anti-bot detection (default on).

### Langkah 2: (Opsional) script interaksi

Beberapa API hanya trigger setelah user action. Klik tombol "Load more", scroll ke bawah, submit form. Tool support interaksi script via field **Interaction script**.

Format: satu aksi per baris, format `action:target`. Tool eksekusi berurutan setelah page load awal selesai.

```
wait:2000
scroll:bottom
wait:1000
click:#load-more-button
wait:2000
click:button[aria-label="Next page"]
wait:1500
fill:input[name="q"]:hello world
press:Enter
wait:3000
```

Aksi yang didukung:

| Aksi | Argumen | Efek |
|------|---------|------|
| `wait` | milliseconds | Sleep |
| `scroll` | `top`, `bottom`, atau angka pixel | Scroll page |
| `click` | CSS selector | Click element |
| `fill` | selector:value | Fill input |
| `press` | key name | Press keyboard key |
| `goto` | URL | Navigate ke URL baru |
| `hover` | selector | Hover element |

### Langkah 3: Run capture

Klik **Start capture**. Tool spawn job, progress streaming. UI menampilkan counter request real-time. Anda lihat angka naik saat halaman load + interact.

Setelah wait strategy terpenuhi, capture stop, tool process. UI switch ke tabs hasil.

### Langkah 4: Eksplorasi hasil

**Tab Endpoints**: table grouped by host. Per host, list endpoint dengan kolom Method, Path, Count, Status. Click row untuk expand: detail headers (request + response), body samples (request + response, kalau JSON di-pretty print), timing.

**Tab GraphQL** (kalau ada): list operation dengan kolom Operation name, Type (Query/Mutation), Count. Click untuk lihat query body, variables sample, response sample.

**Tab Timing**: chart line request count over time (X axis: detik sejak start, Y axis: requests/second). Useful untuk identify burst (lazy load) vs steady (polling).

**Tab Stats**: total requests, unique endpoints, response type breakdown (JSON, HTML, image, dst), total bytes downloaded, total time captured.

### Langkah 5: Export

Tombol **Export OpenAPI** dan **Export Postman** di kanan atas.

## Endpoint grouping & GraphQL detection

### Grouping logic

Tool group requests pakai tuple (host, method, normalized_path). Path normalization:

- Path parameter angka diganti `{id}`: `/users/123/posts` jadi `/users/{id}/posts`.
- UUID diganti `{uuid}`: `/items/abc-def-...` jadi `/items/{uuid}`.
- Filename dengan extension dianggap distinct: `/avatar.png` tidak di-merge dengan `/cover.png`.

Hasilnya: 50 request `/users/{id}` jadi 1 endpoint dengan count 50, bukan 50 endpoint terpisah.

### GraphQL detection

GraphQL endpoint biasanya semua POST ke single URL (`/graphql`). Tanpa grouping khusus, semua call jadi 1 endpoint dengan body berbeda-beda - tidak informative. Tool detect dengan rule:

1. URL path mengandung `/graphql` atau `/gql`, atau
2. Request body adalah JSON dengan field `query` (atau `query` + `variables`).

Kalau match, request masuk ke GraphQL tab (bukan Endpoints tab), di-group by `operationName` (field di body atau auto-extract dari query string).

```graphql
query GetUserProfile($id: ID!) {
  user(id: $id) {
    id
    name
    email
  }
}
```

`operationName` di sini `GetUserProfile`, count per panggilan dengan operationName sama di-aggregate.

## Export OpenAPI 3.0.3

Output JSON sesuai spec OpenAPI 3.0.3. Struktur skeleton:

```json
{
  "openapi": "3.0.3",
  "info": {
    "title": "API Sniffer Capture: example.com",
    "version": "1.0.0",
    "description": "Auto-generated from PyScrapr API Sniffer capture at 2026-05-12T10:30:00Z"
  },
  "servers": [
    {"url": "https://api.example.com"}
  ],
  "paths": {
    "/users/{id}": {
      "get": {
        "summary": "GET /users/{id}",
        "parameters": [...],
        "responses": {
          "200": {
            "description": "OK",
            "content": {
              "application/json": {
                "schema": { ... auto-inferred from sample response ... }
              }
            }
          }
        }
      }
    }
  }
}
```

Schema response di-infer dari sample JSON yang ter-capture, pakai JSON-to-schema converter built-in. Tipe primitive (string, integer, boolean) di-detect dari first sample. Nested object jadi `$ref` ke schema component.

### Import ke Swagger UI

1. Save file `openapi.json` dari tombol export.
2. Buka [editor.swagger.io](https://editor.swagger.io).
3. File > Import file, pilih `openapi.json`.
4. Visualize, test request (kalau auth handled), generate client SDK.

### Import ke openapi-generator

CLI tool untuk generate client di banyak bahasa.

```bash
openapi-generator-cli generate \
  -i openapi.json \
  -g python \
  -o ./client-python
```

Output: package Python siap pakai dengan typed function untuk tiap endpoint.

> [!NOTE]
> Spec auto-generated adalah baseline. Untuk production use, review manual: deskripsi endpoint, contoh response, security schemes, error response 4xx/5xx (kemungkinan tidak ter-capture kalau tidak ada error saat capture).

## Export Postman v2.1

Output JSON sesuai schema Postman Collection v2.1.

```json
{
  "info": {
    "name": "API Sniffer: example.com",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "GET /users/{id}",
      "request": {
        "method": "GET",
        "header": [...],
        "url": {
          "raw": "https://api.example.com/users/123",
          "host": ["api", "example", "com"],
          "path": ["users", "123"]
        }
      }
    }
  ]
}
```

### Import ke Postman app

1. Buka Postman app.
2. Klik **Import** di kiri atas.
3. Drag file `postman_collection.json` atau klik Upload Files.
4. Collection muncul di sidebar. Setiap request bisa di-click, edit, send.

Postman akan auto-extract environment variable kalau ada base URL repeat di banyak request. Anda bisa set variable global (`{{base_url}}`, `{{token}}`) lewat menu Environment.

### Test calls

Untuk endpoint yang butuh auth, paste token Anda di header `Authorization` (Postman GUI). Jalankan request, lihat response. Useful untuk verify endpoint masih work setelah capture (situs target tidak deploy breaking change).

## Filter aset statis + stealth mode

### Filter aset

Toggle "Filter static assets" (default on). Saat on, tool skip request dengan resource type `script`, `stylesheet`, `image`, `font`, `media`. Yang capture cuma `xhr`, `fetch`, `document`, `other` (biasanya API).

Matikan toggle ini kalau Anda mau audit comprehensive (mis. detect tracking script atau third-party CDN). Tapi output akan jadi noisy.

### Stealth mode

Toggle "Stealth mode" (default on). Aktifkan Playwright Stealth plugin yang patch:

- `navigator.webdriver` (set false, default true di headless)
- `navigator.plugins` (populate dengan plugin list realistic)
- `navigator.languages` (set ke realistic locale)
- WebGL fingerprint
- Permissions API
- Chrome runtime properties

Banyak situs pakai Cloudflare, Akamai, DataDome, atau PerimeterX. Stealth tidak guaranteed bypass (vendor itu update detection terus), tapi raise success rate dari 30% jadi 80% untuk situs anti-bot standard.

Matikan stealth kalau Anda scan situs Anda sendiri tanpa anti-bot, ada overhead ~200ms per page load.

## Sanitization

Header sensitif yang biasanya bawa secret di-mask di UI display:

| Header | Display | Export OpenAPI | Export Postman |
|--------|---------|----------------|----------------|
| `Cookie` | `<masked, N bytes>` | omit (default) atau masked | included as-is |
| `Authorization` | `<masked: Bearer ...>` | omit (default) | included as-is |
| `X-API-Key` | `<masked>` | omit | included |
| `X-Auth-Token` | `<masked>` | omit | included |
| Custom header dengan substring `key`/`token`/`secret` | `<masked>` | omit | included |

Alasan beda treatment di export:

- **OpenAPI**: spec is meant to be shared / public. Default omit secret untuk avoid bocor saat Anda share file ke team / publish.
- **Postman**: collection biasanya untuk Anda atau team Anda sendiri (untuk test). Secret di-include supaya request langsung bisa di-send. **Jangan share Postman collection ke pihak ketiga tanpa review.**

> [!DANGER]
> Postman export include raw secret kalau ada di request. Sebelum share file `postman_collection.json` ke kolega atau commit ke repo, manual review dan hapus header sensitif, atau set ke environment variable placeholder. Tool akan kasih peringatan saat export dengan warning ini.

## Contoh skenario

### 1. Reverse engineer dashboard kompetitor untuk audit posisi sendiri

Tim product cek apakah kompetitor punya feature yang advertisement claim tapi belum di-implement actual. Mereka punya akun trial gratis, login, browse dashboard. API Sniffer capture semua request: lihat endpoint apa saja yang dipanggil. Bisa infer arsitektur backend.

Setup: paste URL dashboard kompetitor (setelah login manual di browser, copy session cookie ke Playwright via Auth Vault), capture 60s, interaksi script scroll + klik beberapa menu. Output: 80 unique endpoint. Tim engineer review, identify pattern (mis. ada `/api/v2/realtime/...` yang suggest realtime feature yang advertised). Action: revise positioning produk sendiri.

> [!IMPORTANT]
> Use case ini legal kalau untuk competitive intelligence non-attacking (read-only API call dengan akun legitimate Anda sendiri), bukan untuk exploit endpoint atau credential stuffing. Konsultasi legal sebelum publikasi finding ke marketing.

### 2. Dokumentasi API internal yang tidak ada OpenAPI spec

Startup punya backend yang grown organic, 200 endpoint tanpa documentation. Engineer baru on-board butuh ketahui apa saja yang ada.

Setup: jalankan frontend internal di localhost, navigate semua halaman utama, capture session 5 menit dengan interaksi script complete. Export OpenAPI. Import ke Swagger UI internal. New engineer punya peta endpoint dalam 2 jam, bukan 2 hari reading source code.

### 3. Integrasi situs yang tidak expose public API resmi

Anda butuh data dari situs publik (mis. pricing competitor, public statistik) yang tidak punya public API. UI Anda bisa browse, jadi pasti ada API backend.

Setup: capture beberapa halaman target. Identify endpoint yang return data yang Anda butuh (mis. `/api/products?page=1`). Document, replikasi request di kode integrasi Anda (dengan headers, auth). Sekarang Anda punya integration tanpa public API.

> [!WARNING]
> Practice ini sering bertentangan dengan ToS situs target. Sebelum Anda automate scraping endpoint kompetitor di production, baca ToS-nya. Banyak situs explicit forbid "automated access except via designated API". Risiko: IP block, account ban, atau legal action.

### 4. QA testing: capture semua endpoint sekali browse, jadikan test suite Postman

Tim QA brand baru join, butuh setup test suite untuk regression. Manual buat 200 request di Postman akan butuh 2 minggu.

Setup: setup browser session, capture session lengkap (login, browse, add to cart, checkout sandbox). Export Postman collection. Tim QA import ke Postman, organize folder, tambah assertion (response status 200, body contains field X). Test suite siap dalam 1 hari.

### 5. Security audit: cari endpoint yang accidentally exposed

Internal app pre-production. Security team audit network traffic untuk identify endpoint yang seharusnya admin-only tapi expose di frontend non-admin.

Setup: login sebagai user normal (non-admin), capture session 5 menit full interaction. Output: list endpoint yang dipanggil. Compare dengan list endpoint yang seharusnya allow user-role (dari authorization matrix internal). Yang muncul tapi tidak di whitelist = bug security yang perlu di-fix.

## Tips

- **Start small.** First time test di situs kecil (homepage personal blog) untuk validate setup. Setelah confident, scale ke target serius.

- **Interaksi script penting untuk SPA dengan lazy load.** Tanpa scroll/click, tool cuma capture request initial page load (mungkin 5-10 endpoint). Dengan interaksi script complete, capture bisa 100+ endpoint.

- **Bandingkan capture pre dan post change.** Save Postman collection sebelum deploy. Capture lagi setelah deploy. Diff: endpoint baru, endpoint hilang, perubahan signature. Catatan release internal.

- **Manfaatkan Auth Vault.** Untuk situs yang butuh login, login manual sekali di Auth Vault, simpan cookie. API Sniffer pakai cookie itu saat spawn browser. Lihat [Auth Vault docs](/docs/utilities/vault.md).

- **GraphQL operationName eksplisit.** Kalau Anda dev frontend, biasakan kasih nama operasi GraphQL (`query GetUserProfile`). Tool tergantung itu untuk grouping clean.

## Troubleshooting

### Problem: Playwright not installed atau browser not found

**Gejala:** Error "Executable doesn't exist at ...".
**Penyebab:** Browser chromium belum di-download.
**Solusi:** Run `playwright install chromium` di terminal aplikasi. Atau via Settings > Playwright > Install browser.

### Problem: Stealth tidak cukup, situs detect bot

**Gejala:** Halaman load tapi kosong, atau muncul Cloudflare challenge page.
**Penyebab:** Anti-bot vendor (Cloudflare, DataDome) detect Playwright signature.
**Solusi:** Coba User Agent rotation di Settings. Coba interaksi script tambahan untuk simulate human (mouse move, scroll lambat). Untuk situs anti-bot serius, mungkin butuh CAPTCHA solver atau manual session via Auth Vault. Lihat [CAPTCHA Solver docs](/docs/advanced/captcha.md).

### Problem: 0 request captured walaupun page load

**Gejala:** Halaman terlihat load (screenshot OK), tapi count 0.
**Penyebab:** Halaman static (server-render full), atau semua API call terjadi setelah wait window tutup.
**Solusi:** Naikkan `wait_seconds`. Tambah interaksi script untuk trigger API. Pastikan halaman target memang SPA (bukan static HTML).

### Problem: Sensitive data muncul di Postman export

**Gejala:** Setelah export Postman, terlihat Authorization Bearer token full di field header.
**Penyebab:** By design, Postman export tidak mask supaya request langsung bisa di-replay.
**Solusi:** Manual edit `postman_collection.json` sebelum share, replace token dengan `{{token}}`. Atau setup environment variable di Postman setelah import.

### Problem: GraphQL operation tidak ter-detect

**Gejala:** Banyak POST ke `/graphql`, tapi semua jadi 1 endpoint di tab Endpoints (tidak ter-pisah per operation).
**Penyebab:** Body tidak ada `operationName` (anonymous query), atau body bukan JSON valid.
**Solusi:** Tool fallback grouping by hash query string. Tidak rapi, tapi tetap distinct. Untuk improvement, request frontend kasih operationName eksplisit.

## Etika & legal

> [!IMPORTANT]
> API Sniffer adalah tool yang bisa dipakai untuk reverse engineer infrastruktur situs lain. Patuhi aturan berikut.

- **Situs Anda atau izin tertulis.** Jalankan capture di situs Anda sendiri, situs klien dengan kontrak audit, atau bug bounty target yang in-scope.

- **Jangan distribusi finding sebagai serangan.** Endpoint yang Anda discover via API Sniffer di situs pihak ketiga - kalau ada bug security (mis. endpoint admin exposed), report ke vendor responsibly, jangan tweet atau publish blog "lihat kompetitor punya bug".

- **Hormati rate limit.** Capture single session biasanya tidak masalah. Scripted automation untuk repeat capture di situs sama 100x = traffic abuse, kemungkinan IP block atau legal action.

- **Jangan reverse engineer untuk attack.** Practice "saya capture API, lalu saya credential-stuff atau brute-force endpoint" = pidana di banyak yurisdiksi. Tool ini documenting, bukan exploitation framework.

- **Postman export = potential credential leak.** File yang Anda export berisi sample request termasuk header auth. Jangan commit ke git public repo. Jangan share di Slack tanpa redact.

- **ToS situs target.** Beberapa situs ToS explicit forbid "reverse engineering". Kalau Anda staff perusahaan yang scan situs kompetitor untuk product research, konsultasi legal dulu.

- **Bug bounty: baca scope.** Beberapa program allow API enumeration, beberapa explicit forbid. Kalau in-scope, document semua via API Sniffer adalah cara efisien. Kalau out of scope, jangan.

## Pengaturan teknis

| Key | Tipe | Default | Keterangan |
|-----|------|---------|------------|
| `api_sniffer_enabled` | boolean | true | Master switch tool |
| `api_sniffer_wait_seconds_default` | integer | 30 | Default hard timeout capture |
| `api_sniffer_max_requests_default` | integer | 500 | Default cap jumlah request |
| `api_sniffer_idle_silence_seconds` | integer | 2 | Idle threshold sebelum auto-stop |
| `api_sniffer_filter_static_default` | boolean | true | Default toggle filter aset |
| `api_sniffer_stealth_default` | boolean | true | Default toggle stealth mode |
| `api_sniffer_user_agent_rotation` | boolean | false | Rotate UA setiap session |
| `api_sniffer_mask_secret_in_openapi` | boolean | true | Mask secret di OpenAPI export |
| `api_sniffer_mask_secret_in_postman` | boolean | false | Mask secret di Postman export (off, by design) |

## Related docs

- [Playwright Rendering](/docs/advanced/playwright.md) - detail Playwright engine yang dipakai
- [Auth Vault](/docs/utilities/vault.md) - simpan session cookie untuk situs auth
- [Tech Fingerprinter](/docs/tools/tech-detector.md) - identifikasi backend stack sebelum sniff
- [URL Mapper](/docs/tools/url-mapper.md) - peta URL situs sebelum decide page mana untuk sniff
- [OSINT Harvester](/docs/tools/osint-harvester.md) - cari endpoint expose di HTML source (complement sniff)
- [Settings](/docs/system/settings.md) - semua flag API Sniffer
