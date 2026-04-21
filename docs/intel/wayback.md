# Wayback Machine Explorer

> Tool untuk menelusuri arsip historis halaman web via web.archive.org. Lihat tampilan sebuah URL dari 2005, 2010, 2020, semua dalam satu timeline. Submit URL ke Wayback untuk arsipkan on-demand. Ekstrak raw HTML dari snapshot spesifik untuk diff atau analisis.

## Apa itu Wayback Machine Explorer

Wayback Machine Explorer adalah modul PyScrapr yang menjadi UI friendly di atas Wayback Machine CDX API (Internet Archive). Wayback Machine sendiri adalah project Internet Archive yang sejak 1996 mengarsipkan trilyun halaman web, nonprofit, bebas akses publik. Tool ini membantu Anda query arsip tersebut tanpa harus masuk web.archive.org secara manual dan scroll-scroll calendar interface-nya.

Dengan satu URL input, tool menampilkan list semua snapshot yang Wayback punya untuk URL itu, dikelompokkan per tahun, lengkap dengan timestamp presisi, status HTTP saat diambil, ukuran halaman, dan tombol langsung untuk buka snapshot di tab baru. Filter by year range kalau Anda cuma mau lihat periode spesifik. Tombol "Arsipkan sekarang" untuk submit URL terkini ke Wayback supaya versi hari ini ikut tersimpan permanent.

> [!NOTE]
> Modul ini tidak mengkopi arsip ke disk Anda. Semua data streaming langsung dari web.archive.org. Kalau Internet Archive down (jarang, tapi terjadi), modul tidak akan kerja.

Kenapa tool ini berguna? Beberapa alasan: riset historis konten (kompetitor dulu jual apa, pemerintah dulu umumkan apa), forensics ("ini situs dulu beda isinya, buktikan"), recover konten dari situs yang sudah mati, atau sekadar nostalgia melihat tampilan Tokopedia 2012.

## Cara pakai (step-by-step)

1. Buka PyScrapr, navigasi ke **Wayback Explorer** di sidebar. Halaman tampilkan form dengan URL field, range tahun, limit, dan dua tombol.

2. Di field `URL target`, masukkan URL lengkap yang ingin Anda cari snapshot-nya. Bisa homepage (`https://kompas.com`), bisa halaman dalam (`https://kompas.com/read/2019/12/31/xxxxx`). Wildcard tidak didukung di CDX API via mode ini.

3. Opsional, set `Dari tahun` dan `Sampai tahun` kalau Anda cuma mau snapshot dalam rentang waktu tertentu. Contoh: dari 2010, sampai 2015. Kosongkan untuk ambil semua waktu.

4. `Limit` default 200. Naikkan ke 1000-2000 kalau Anda riset situs aktif yang punya ribuan snapshot. Maksimum 10000 per request (hard limit).

5. Klik `Cari`. Backend query CDX API Wayback, parse hasilnya, kelompokkan per tahun. Hasil muncul sebagai kartu per-tahun dengan tabel snapshots di dalamnya.

6. Setiap baris snapshot punya tombol `Lihat`. Klik untuk buka snapshot di tab browser baru. URL-nya format `https://web.archive.org/web/<timestamp>/<original_url>`. Toolbar Wayback akan muncul di atas halaman.

7. Kalau Anda ingin arsipkan URL saat ini (supaya versi hari ini tersimpan permanen di Internet Archive), klik tombol `Arsipkan sekarang`. Backend akan submit ke endpoint `/save/`. Tunggu notifikasi sukses dengan timestamp baru.

## Contoh kasus pakai

- **Riset konten historis untuk artikel** - Anda nulis feature story tentang evolusi media online Indonesia. Scan homepage Detikcom, Kompas, Tempo untuk tahun 2000, 2005, 2010, 2015, 2020, 2024. Screenshot tiap era untuk artikel.

- **Recover blog post yang terhapus** - Sebuah tutorial penting di blog X sudah dihapus pemiliknya. URL masih Anda bookmark, tapi konten sudah 404. Masukkan URL ke Wayback Explorer, cari snapshot terdekat sebelum penghapusan, ambil konten dari sana.

- **Verifikasi klaim "situs saya selalu bilang begini"** - Ada dispute. Seseorang klaim halaman X selalu mengatakan Y. Anda cek Wayback, ternyata tahun lalu halaman tersebut masih mengatakan Z. Bukti visual + timestamp untuk argumentasi.

- **Monitoring migrasi situs** - Situs kompetitor baru migrasi dari WordPress ke Next.js. Lihat di Wayback tampilan lama vs snapshot terbaru. Analisis breaking changes di SEO, struktur URL, content volume.

- **Forensic digital investigation** - Mencari versi lama sebuah press release yang sekarang di-edit ulang. Wayback snapshot tunjukkan teks original. Berguna untuk jurnalisme investigatif.

- **Rebuild situs mati** - Organisasi X bubar, situs mereka (yang punya konten berharga) offline. Pakai Wayback snapshots terakhir sebagai sumber untuk rebuild konten di CMS baru.

- **SEO historical analysis** - Lihat bagaimana title tag, meta description, heading structure situs kompetitor berubah dari waktu ke waktu. Clue strategi SEO mereka.

- **Deteksi defacement historis** - Situs institusi pernah di-deface hacker 2019. Lihat snapshot bulan itu untuk konfirmasi event + tanggal persisnya.

## Apa yang dikembalikan

Setiap snapshot punya field berikut:

| Field | Deskripsi | Contoh |
|-------|-----------|--------|
| **timestamp** | Waktu snapshot, format YYYYMMDDHHMMSS | `20240315142030` |
| **url** | URL asli yang di-archive | `https://contoh.com/halaman` |
| **status** | HTTP status code saat snapshot | `200`, `301`, `404` |
| **digest** | SHA-1 hash konten (untuk dedupe) | `AGK...XYZ` |
| **length** | Ukuran response body dalam bytes | `48291` |
| **mimetype** | Content-Type header | `text/html` |
| **snapshot_url** | URL ready-to-click ke snapshot live | `https://web.archive.org/web/20240315142030/...` |

Status 200 artinya snapshot berisi halaman valid. Status 301/302 artinya saat Wayback crawl, URL redirect ke URL lain (ikuti redirect di tab browser untuk cek). Status 404 artinya saat itu halaman sudah dihapus, tapi Wayback tetap record bahwa halaman di-request dan return 404.

## Cara kerja internal (teknis)

### List snapshots

Endpoint: `GET https://web.archive.org/cdx/search/cdx`

Parameter yang dikirim:
- `url`: URL target persis
- `output=json`: minta response array of arrays (row 0 = headers, row 1+ = data)
- `limit`: batas jumlah snapshot (kita cap 10000)
- `from=YYYYMMDD`: tanggal mulai (kita pakai YYYY0101)
- `to=YYYYMMDD`: tanggal akhir (kita pakai YYYY1231)

Response shape:
```
[
  ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"],
  ["com,contoh)/", "20240315142030", "https://contoh.com/", "text/html", "200", "AGK...XYZ", "48291"],
  ...
]
```

Parser iterate dari index 1 (skip header), map field by index, append snapshot_url computed dari template `https://web.archive.org/web/{ts}/{original}`.

### Save on-demand

Endpoint: `GET https://web.archive.org/save/<url>`

Wayback akan fetch URL, archive-kan, lalu redirect ke snapshot URL final. Tool follow redirect otomatis (httpx `follow_redirects=True`), parse final URL untuk extract timestamp. Timeout 60 detik karena save bisa lama untuk halaman besar.

Kalau save gagal (rate-limit, URL robots-blocked, atau Wayback internal error), response tidak akan punya `/web/<ts>/` pattern di final URL. Tool return `{saved: false, error: ...}`.

### Fetch raw content

Endpoint: `GET https://web.archive.org/web/<ts>id_/<url>`

Suffix `id_` (huruf kecil i, huruf d, underscore) artinya "identity mode": Wayback tidak inject toolbar JS/CSS, tidak rewrite link internal, return raw response original. Berguna kalau Anda mau parse HTML snapshot dengan BeautifulSoup atau feed ke tool diff.

Endpoint ini di-expose sebagai `/api/wayback/content?url=...&timestamp=...` yang return PlainTextResponse.

## Pengaturan

### from_year / to_year
Filter range waktu. Kosongkan untuk ambil semua. Format: integer tahun, misal 2018. Tool akan format ke YYYY0101 dan YYYY1231 untuk CDX API.

### limit
Default 200, max 10000. Kalau situs sangat aktif (misal portal berita dengan daily snapshot), bahkan 10000 pun bisa tidak cukup untuk range panjang. Dalam kasus itu, narrow down via year range.

### User-Agent / proxy
Tool pakai `http_factory.build_client()`, artinya otomatis apply UA + proxy settings global Anda. Wayback tidak sensitive soal UA, tapi rate-limit per IP ada.

## Tips akurasi

- **URL harus exact.** Wayback index per exact URL string. `https://contoh.com`, `https://contoh.com/`, dan `https://www.contoh.com` di-index terpisah. Coba beberapa variant kalau hasil tidak sesuai ekspektasi.

- **Subdomain vs wildcard.** Query `https://contoh.com` tidak include snapshot dari `https://blog.contoh.com`. CDX API modem kita pakai tidak support wildcard di mode ini. Query per subdomain.

- **Path spesifik lebih bersih.** Query URL root punya ratusan snapshot per tahun yang mostly near-duplicate. Kalau Anda cari konten spesifik, query URL halaman-nya langsung supaya hasil lebih relevan.

- **Snapshot di awal dan akhir tahun biasanya paling representatif.** Wayback crawler datang beberapa kali setahun untuk mayoritas situs, tapi pattern crawl tidak uniform. Untuk "apa tampilan tahun 2015", ambil snapshot awal 2016 (yang capture akhir 2015 state).

- **Length field bisa misleading.** Ini ukuran response archived (termasuk JavaScript, CSS, images kadang di-inline). Tidak selalu = ukuran halaman aktual.

- **Gunakan raw content untuk parsing.** Kalau Anda mau BeautifulSoup HTML snapshot untuk ekstrak data terstruktur, pakai endpoint `id_` (raw) bukan snapshot URL biasa. Toolbar Wayback akan ikut ter-parse dan mengotori hasil.

## Troubleshooting

### Problem: "Tidak ada snapshot untuk URL ini"
**Gejala:** count: 0, list kosong. 
**Penyebab:** URL tidak pernah di-crawl Wayback, atau di-robots-block oleh situs pemilik, atau URL slight off (tambah/kurang trailing slash). 
**Solusi:** Coba variant URL (http vs https, with/without www, with/without trailing slash). Kalau masih kosong, URL memang tidak di-index. Klik Arsipkan sekarang untuk trigger Wayback crawl pertama.

### Problem: "HTTP 429" atau response lambat
**Gejala:** CDX API return 429 Too Many Requests. 
**Penyebab:** Rate-limit Wayback per IP. Anda baru saja query banyak URL berurutan. 
**Solusi:** Tunggu 5-10 menit. Kalau Anda butuh batch, masukkan delay 2-3 detik antar request via Bulk Queue + rate-limit setting.

### Problem: Save button gagal dengan "could not extract timestamp"
**Gejala:** Notifikasi error setelah klik Arsipkan sekarang. 
**Penyebab:** Wayback save kadang return halaman error / challenge, bukan redirect ke snapshot. Bisa karena robots-blocked, rate-limit, atau maintenance. 
**Solusi:** Tunggu beberapa menit, retry. Cek manual di `https://web.archive.org/save/<url>` di browser untuk melihat pesan error spesifik.

### Problem: Snapshot yang dibuka tidak load styling/images
**Gejala:** Halaman snapshot lama mengalami layout broken. 
**Penyebab:** Wayback tidak selalu arsipkan semua sub-resource (CSS, JS, image). Snapshot HTML root ada, tapi dependencies mungkin cuma sebagian. 
**Solusi:** Ini intrinsic ke Wayback archive, bukan bug tool. Coba snapshot dengan timestamp berbeda (beberapa menit sebelum/sesudah), mungkin yang itu lebih lengkap.

### Problem: Content endpoint return HTML dengan Wayback toolbar HTML tetap ada
**Gejala:** Anda pakai `/api/wayback/content` tapi hasilnya tetap mengandung `<script>` Wayback toolbar. 
**Penyebab:** URL path salah, belum pakai `id_` suffix. 
**Solusi:** Pastikan timestamp param 14 digit dan URL param percent-encoded. Tool backend sudah pakai id_ otomatis, kalau Anda lihat toolbar berarti ada issue di path constructor; report sebagai bug.

## Keamanan / etika

> [!WARNING]
> Internet Archive adalah nonprofit dengan bandwidth donasi. Pakai dengan bijak.

- **Jangan hammer CDX API.** Kalau Anda butuh scan banyak URL, insert delay. Batch 100 URL dengan 2 detik interval lebih baik daripada 100 parallel.

- **Save on-demand adalah resource intensive.** Setiap save trigger crawl baru di sisi Wayback. Jangan save URL random massive hanya untuk "seru-seruan". Save URL yang benar-benar penting untuk disave.

- **Hormati robots.txt logic Wayback.** Kalau situs pemilik men-set `X-Robots-Tag: noarchive` atau masukkan Wayback crawler di robots.txt disallow, Wayback tidak akan arsipkan. Ini oleh desain. Jangan workaround dengan cara aneh.

- **Konten di Wayback tidak selalu bisa Anda republish.** Copyright original owner tetap berlaku. Wayback memberi akses untuk riset dan historical reference, bukan lisensi bebas pakai.

- **Privacy concerns.** Kadang halaman personal (blog pribadi, profil kecil) tidak sadar di-archive. Kalau pemilik minta takedown ke Archive.org, itu hak mereka. Jangan jadikan Wayback sumber untuk doxing atau stalking.

- **Jangan submit URL yang berisi data sensitif.** Save endpoint akan arsipkan URL tersebut permanen. Jangan submit URL admin panel dengan session token di query string, halaman password reset, atau URL signed (S3 presigned dll).

## Related docs

- [Domain Intel](/docs/intel/domain.md) - lookup WHOIS + DNS + subdomain untuk target riset
- [Sitemap Analyzer](/docs/intel/sitemap.md) - enumerate URL publik untuk candidate scan snapshot
- [Diff Detection](/docs/system/diff.md) - bandingkan dua versi snapshot untuk tracking perubahan
- [URL Mapper](/docs/tools/url-mapper.md) - crawl situs live, hasilnya bisa di-submit ke Wayback batch
- [Site Ripper](/docs/tools/site-ripper.md) - alternatif offline kalau Anda butuh clone komplit, bukan snapshot historis
