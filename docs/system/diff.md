# Diff Detection

> Fitur perbandingan dua run job yang mendeteksi item baru, item hilang, dan perubahan status antar snapshot - sangat berguna untuk monitoring perubahan situs dari waktu ke waktu.

## Deskripsi

Diff Detection adalah tool analitik yang mengambil dua job hasil scraping terhadap URL yang sama (atau berbeda) dan menghitung selisih antara keduanya. Bayangkan Anda menjalankan Harvester terhadap halaman listing e-commerce pagi ini, lalu menjalankan lagi sore ini. Apa yang berubah? Produk baru yang muncul? Produk yang hilang dari listing? Dengan Diff Detection, jawaban tersebut disajikan dalam bentuk visual terstruktur dengan panel new/removed yang berwarna-warni, tanpa Anda perlu export kedua dataset ke Excel lalu melakukan VLOOKUP manual.

Secara konsep, diff bekerja dengan mengekstrak "item identifier" dari tiap job - untuk Harvester/Ripper/Media itu adalah URL asset (image URL, media URL); untuk URL Mapper itu adalah node dalam crawl graph (URL halaman yang di-visit). Kedua set ini kemudian diproses dengan operasi set theory sederhana: `B - A` menghasilkan item baru, `A - B` menghasilkan item hilang, dan `A ∩ B` menghasilkan item unchanged. Untuk Mapper secara khusus, ada kategori tambahan `status_changed` yang mendeteksi node yang URL-nya sama antara A dan B tapi HTTP status berubah (misal sebelumnya 200 OK, sekarang 404 Not Found).

Endpoint API `GET /api/diff?job_a=X&job_b=Y` adalah jantung fitur ini. Parameter `job_a` dan `job_b` adalah ID job yang ingin dibandingkan. Backend akan memuat data kedua job, menormalisasi ke set identifier, menghitung diff, dan mengembalikan response JSON yang mengandung empat kategori: `new` (array identifier baru), `removed` (array yang hilang), `unchanged_count` (hanya jumlah, tidak list), dan untuk mapper, `status_changed` (array object dengan url + old_status + new_status). Untuk mencegah response payload yang terlalu besar, tiap kategori list dibatasi 500 item; jika lebih, response menyertakan flag `truncated: true` dan saran untuk export detail ke CSV.

UI Diff Detection adalah halaman dengan dual job picker dropdown di atas (pilih job A, pilih job B) dan tombol Compare. Setelah klik, panel hasil muncul di bawah dengan tiga kolom: panel teal untuk "new", panel merah untuk "removed", dan panel kuning untuk "status_changed" (hanya untuk mapper). Tiap panel menampilkan list item dengan link clickable yang membuka URL di tab baru. Panel unchanged hanya menampilkan angka count tanpa list untuk menjaga fokus pada perbedaan. Ada juga summary card di bagian atas yang menunjukkan persentase similarity antara dua job - berguna untuk quick assessment "seberapa banyak berubah".

## Kapan pakai?

1. **Monitoring perubahan konten situs** - Bandingkan run harian terhadap situs berita untuk lihat artikel apa saja yang baru di-publish hari ini.
2. **Deteksi dead links** - Compare dua mapper runs untuk identifikasi halaman yang dulunya 200 sekarang 404 akibat restructuring situs target.
3. **Audit inventory e-commerce** - Bandingkan listing produk antar hari untuk lihat produk mana yang habis/dihapus vs yang baru ditambahkan.
4. **Compliance monitoring** - Cek apakah terms-of-service atau privacy policy berubah dengan membandingkan mapper output minggu ini vs minggu lalu.
5. **Validasi output scheduled job** - Setelah setup schedule harian, pakai Diff untuk sanity check bahwa tiap run memang menghasilkan konten fresh dan bukan cached yang identik.
6. **Research arkeologi situs** - Lihat evolusi struktur situs dari snapshot historis dengan compare antar tanggal.
7. **QA sebelum migration** - Bandingkan scraping dari situs lama vs staging environment baru untuk memastikan semua konten ter-migrate.
8. **Investigasi hilangnya data** - Ketika user komplain "kemarin masih ada link X, sekarang hilang", diff langsung memberi bukti obyektif.

## Cara penggunaan

1. Buka halaman Diff Detection dari navbar sidebar atau akses `/diff`.
2. Di bagian atas halaman, ada dua dropdown job picker: "Job A (baseline)" di kiri dan "Job B (comparison)" di kanan.
3. Klik dropdown Job A. List job akan tampil dengan format: `[tool_badge] URL (timestamp) - status`. Pilih job yang akan jadi baseline perbandingan.
4. Klik dropdown Job B. Biasanya Anda memilih job dengan URL yang sama atau mirip tapi dari timestamp berbeda. Tool juga disarankan sama (tidak mix harvester dengan mapper).
5. Verifikasi summary di atas panel bahwa kedua job kompatibel untuk di-diff. Jika tool berbeda, warning merah muncul.
6. Klik tombol "Compare" di tengah. Loading spinner muncul sementara backend menghitung diff.
7. Setelah selesai (biasanya 1-3 detik untuk job < 1000 item), panel hasil muncul di bawah.
8. Review panel teal "New items": ini adalah asset/node yang ada di Job B tapi tidak di Job A. Jumlah ditampilkan di header panel.
9. Review panel merah "Removed items": asset/node yang ada di Job A tapi hilang di Job B. Berguna untuk deteksi broken/deleted.
10. Jika kedua job adalah mapper, review panel kuning "Status changed": URL yang sama tapi HTTP status berubah. Format row: `URL: 200 → 404`.
11. Panel summary menampilkan total unchanged count dan persentase similarity. Similarity tinggi (>95%) menunjukkan perubahan minor.
12. Klik item di panel untuk buka URL di tab baru dan verifikasi secara manual. Atau klik tombol "Export diff" di toolbar untuk download CSV dengan semua kategori.

## Pengaturan / Konfigurasi

Diff Detection tidak punya settings khusus di halaman Settings karena fungsinya stateless (compute on-demand). Namun beberapa query parameter endpoint `/api/diff` bisa digunakan untuk fine-tuning:

- **job_a** (string, required) - ID job baseline. Diambil dari DB job; harus existed dan status `done`.
- **job_b** (string, required) - ID job comparison. Sama requirement dengan job_a.
- **limit** (int, default 500, max 5000) - Maksimum item per kategori dalam response. Jika limit terlampaui, flag truncated=true.
- **offset** (int, default 0) - Untuk pagination jika ingin iterate seluruh set item yang lebih besar dari limit.
- **include_unchanged** (boolean, default false) - Jika true, response menyertakan list URL unchanged (bukan hanya count). Default false untuk hemat bandwidth.
- **identifier_field** (string, auto-detect) - Field mana yang dipakai sebagai identifier unik. Auto-detect berdasarkan tool: `image_url` untuk harvester, `file_url` untuk media, `url` untuk mapper/ripper. Bisa dioverride untuk case advanced.
- **case_sensitive** (boolean, default true) - Apakah identifier comparison case-sensitive. Set false untuk URL yang scheme-nya inkonsisten (http vs HTTP).
- **normalize_url** (boolean, default true) - Apakah identifier URL dinormalisasi (strip trailing slash, lowercase host, remove default port) sebelum comparison. Default true.
- **status_changed_only** (boolean, default false, mapper only) - Jika true, skip kalkulasi new/removed dan fokus hanya pada status changes untuk speed up.
- **diff_algorithm** (enum: `set`, `myers`, default `set`) - Algoritma diff. Set theory untuk item independen; Myers untuk perbandingan ordered sequences (jarang dipakai, experimental).

Semua parameter di atas tersedia sebagai advanced options di UI (toggle expandable panel) atau dapat dipassing langsung via URL query string jika integrasi dengan tool eksternal.

## Output

Response dari endpoint `/api/diff` berbentuk JSON dengan struktur berikut:

```json
{
  "job_a": "uuid-a",
  "job_b": "uuid-b",
  "tool": "mapper",
  "new": ["https://example.com/page-x", "..."],
  "removed": ["https://example.com/old-page", "..."],
  "status_changed": [
    {"url": "https://example.com/foo", "old_status": 200, "new_status": 404}
  ],
  "unchanged_count": 1523,
  "similarity": 0.94,
  "truncated": false,
  "computed_at": "2026-04-17T10:15:30Z"
}
```

UI merender response ini menjadi panel visual. Ada juga tombol "Export diff" yang convert ke CSV dengan kolom `category,url,old_status,new_status`. CSV ini cocok di-import ke Excel untuk sharing ke tim non-teknis.

## Integrasi dengan fitur lain

- **Scheduled Jobs** - Schedule harian menghasilkan series runs yang perfect untuk diff comparison antar tanggal.
- **Webhooks** - Jika jumlah diff melampaui threshold (configurable), trigger webhook "on_diff_significant" yang kirim notifikasi Discord/Telegram.
- **History** - Tombol "Diff vs previous" di row history otomatis pre-fill job picker dengan job sebelumnya dari URL/tool yang sama.
- **REST API** - Endpoint diff adalah bagian dari REST API dan bisa dipanggil oleh tool eksternal untuk integrasi custom.
- **Dashboard** - Indikator Δ di Recent Activity row berasal dari quick-diff calculation terhadap run sebelumnya.
- **Settings** - Default `normalize_url` dan threshold untuk webhook significant diff diatur di Settings global.

## Tips & Best Practices

1. **Compare job dengan tool yang sama** - Diff antar tool berbeda (misal harvester vs mapper) tidak bermakna karena struktur identifier berbeda.
2. **Gunakan scheduled pairs** - Setup schedule dengan frequency yang konsisten (daily) untuk punya "bahan" diff yang bersih dan rapi.
3. **Normalisasi URL jika target punya trailing slash inkonsisten** - Banyak situs generate `/page` dan `/page/` bergantian; tanpa normalisasi diff akan false positive.
4. **Export CSV untuk sharing** - Tampilan UI cocok untuk quick review; untuk reporting ke stakeholder non-teknis, export CSV lebih accessible.
5. **Threshold similarity untuk alert** - Tetapkan threshold (misal similarity < 80%) sebagai trigger webhook, sehingga perubahan besar ter-notif otomatis.
6. **Archive job lama tapi jangan delete** - Diff butuh kedua job exist di DB. Archive dengan flag tapi jangan hard delete agar historical diff tetap bisa.
7. **Perhatikan truncation** - Untuk site besar, 500 item bisa terlampaui. Naikkan limit atau gunakan offset pagination jika butuh full picture.
8. **Buat bookmark diff pair penting** - Anda bisa bookmark URL `/diff?job_a=X&job_b=Y` untuk quick access diff yang rutin direview.

## Troubleshooting

**Problem: Dropdown job picker kosong padahal ada banyak job di History.**
Cause: Filter backend hanya list job dengan status `done`; job running/error tidak muncul.
Solution: Tunggu job selesai dulu sebelum diff. Atau disable filter status di advanced settings.

**Problem: Diff menghasilkan "new" dan "removed" yang sangat banyak padahal URL mirip.**
Cause: URL tidak ternormalisasi - beda trailing slash, scheme, atau query string membuat dianggap berbeda.
Solution: Aktifkan `normalize_url: true`. Untuk case khusus query string, custom normalization perlu ditambahkan di kode.

**Problem: Similarity 100% tapi user yakin ada perubahan.**
Cause: Tool yang dipakai tidak capture field yang berubah (misal harvester tidak capture harga, hanya URL gambar).
Solution: Gunakan tool yang lebih tepat (misal scraper klasik dengan selector custom) untuk capture konten yang relevan.

**Problem: Endpoint 500 error saat compare.**
Cause: Salah satu job corrupt di DB (JSON field tidak bisa di-parse) atau field identifier tidak ada.
Solution: Cek log server. Re-run salah satu job untuk regenerate data. Validasi schema DB.

**Problem: Response truncated di 500 item.**
Cause: Job besar dengan >500 diff items per kategori.
Solution: Tingkatkan parameter `limit` (max 5000) atau iterate dengan `offset` pagination.

**Problem: Status_changed kosong walaupun tool mapper dan yakin ada status perubahan.**
Cause: Field status tidak tersimpan di data job mapper (mungkin versi lama sebelum field ini added).
Solution: Re-run mapper job dengan versi terbaru. Status field now auto-captured.

**Problem: Compare sangat lambat (>30 detik) untuk job besar.**
Cause: Job dengan puluhan ribu items, set comparison di Python single-threaded.
Solution: Optimize dengan batch processing (feature request). Sementara, split job besar ke beberapa job kecil.

**Problem: Export CSV diff berisi karakter aneh.**
Cause: Encoding mismatch (URL dengan karakter non-ASCII).
Solution: Buka CSV dengan encoding UTF-8 explicit di Excel (via Data > From Text). Atau gunakan text editor seperti Notepad++ untuk verify.

**Problem: Panel status_changed tidak muncul walaupun tool mapper.**
Cause: Kedua job dipilih tapi tidak ada node dengan URL sama - mungkin kedua crawl menelusuri cabang berbeda.
Solution: Perluas max_depth mapper di kedua run agar cabang lebih overlap.

## FAQ

**Q: Apakah bisa diff lebih dari 2 job (triple compare)?**
A: Tidak di UI standard. Untuk multi-way comparison, chain diff (A vs B, lalu B vs C) atau gunakan script external yang pakai endpoint REST API.

**Q: Apakah diff bekerja untuk URL target berbeda?**
A: Secara teknis bisa, tapi hasilnya tidak bermakna karena identifier sets kemungkinan disjoint total.

**Q: Berapa lama data diff disimpan?**
A: Diff computation on-demand, tidak disimpan di DB. Tiap klik Compare compute ulang. Untuk caching, pakai external layer.

**Q: Apakah diff memperhitungkan ordering?**
A: Default algoritma set theory tidak care ordering. Untuk ordered sequences pakai `diff_algorithm: myers` experimental.

**Q: Bisa diff dipakai untuk compare file sizes atau kontent body?**
A: Saat ini hanya identifier. Untuk content-level diff, butuh feature fork yang expand scope.

**Q: Apakah diff bisa di-schedule?**
A: Tidak secara langsung, tapi bisa via eksternal script yang panggil API diff setelah scheduled job fires.

**Q: Bagaimana handle job yang di-delete?**
A: Diff akan 404 jika salah satu job ID tidak ditemukan. Pastikan kedua job masih exist sebelum compare.

**Q: Apakah diff case-sensitive untuk URL?**
A: Default true, tapi bisa diubah via `case_sensitive: false` untuk target situs yang URL-nya mixed case.

**Q: Bisa diff mapper dengan harvester?**
A: Secara UI tidak disarankan. Field identifier berbeda jadi hasil meaningless.

**Q: Apakah ada visualisasi graph untuk diff mapper?**
A: Saat ini hanya list. Visualisasi graph merge adalah feature request mendatang.

## Keterbatasan

- Maksimum 500 items per kategori dalam response default (bisa dinaikkan via limit parameter hingga 5000).
- Tidak ada content-level diff (hanya identifier-level).
- Tidak ada multi-way diff (lebih dari 2 job) built-in.
- Computation stateless dan tidak di-cache; job besar akan re-compute tiap klik.
- Algoritma Myers experimental, tidak direkomendasikan untuk production.
- Tidak ada visualisasi graph untuk mapper diff.
- Export terbatas ke CSV; JSON dan Excel butuh parse manual dari response API.

## Related docs

- [Scheduled Jobs](./scheduled.md) - Source dari run pairs untuk diff.
- [History](./history.md) - Pilih job ID untuk diff dari sini.
- [Webhooks](../advanced/webhooks.md) - Notifikasi significant diff.
- [REST API](../advanced/rest-api.md) - Endpoint diff untuk integrasi eksternal.
- [URL Mapper](../tools/url-mapper.md) - Tool yang menghasilkan diff dengan status_changed.
