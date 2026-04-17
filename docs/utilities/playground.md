# Selector Playground

> Tester CSS/XPath selector live yang fetch halaman target lalu menjalankan selector Anda di server, menampilkan elemen yang match beserta teks dan atribut. Ideal untuk menyusun selector sebelum dipakai di Image Harvester, Site Ripper, atau pipeline.

## Deskripsi

Selector Playground menjawab pertanyaan yang selalu muncul saat scraping: "apakah selector ini sudah benar sebelum saya hardcode ke job?". Anda masukkan URL, pilih jenis selector (CSS atau XPath), ketik selector string, klik Run, dan PyScrapr akan fetch halaman di backend (menggunakan httpx dengan user-agent yang reasonable), parse dengan BeautifulSoup + lxml, menjalankan selector, lalu mengembalikan daftar elemen yang match - masing-masing dengan teks bersih, atribut, dan truncated outerHTML preview.

Di balik layar, CSS selector menggunakan `soup.select(selector_string)` lewat BeautifulSoup - backend lxml untuk speed. XPath menggunakan `lxml.etree.HTML(html).xpath(selector)` karena BeautifulSoup sendiri tidak support XPath native. Hasil di-normalize ke format seragam: list of `{text, attrs, html, tag}` agar UI bisa render konsisten. HTML yang di-fetch di-truncate ke **50KB** untuk menghindari payload berat di browser - jika halaman target jauh lebih besar, selector masih berjalan di full HTML server-side, tapi preview di UI terpotong.

Playground dirancang sebagai "scratchpad" iteratif. Tidak ada persistence - setiap refresh halaman, input hilang (kecuali Anda copy manual). Ini disengaja agar Anda tidak sungkan eksperimen. Begitu selector ketemu, click tombol `Use in Harvester` untuk navigate ke halaman Image Harvester dengan URL pre-filled, atau copy selector ke clipboard untuk paste ke tool lain.

Quick Examples panel menyediakan beberapa selector umum (`h1`, `a[href]`, `img`, `meta[name="description"]`) sebagai titik awal untuk pemula yang belum familiar dengan CSS selector syntax. Untuk selector yang invalid (misal `div..class` - double dot typo), backend mengembalikan error specific, dan UI menampilkan notifikasi merah dengan pesan dari library parser - memudahkan debug.

## Kapan pakai tool ini?

1. **Sebelum setup Image Harvester** - pastikan selector `img.product` benar-benar match di halaman target sebelum start job yang crawl 10 halaman.
2. **Reverse engineering layout situs** - coba berbagai selector untuk memahami struktur DOM: `article > header > h1` vs `h1.post-title`.
3. **Debug selector yang berhenti jalan** - situs baru saja redesign, selector lama return 0 hasil; Playground menunjukkan struktur baru.
4. **Eksplorasi XPath kompleks** - `//a[contains(@class,'btn') and text()='Next']` - Playground menampilkan match instan.
5. **Compare CSS vs XPath** - kadang satu pendekatan lebih robust. Test keduanya side-by-side.
6. **Verifikasi pagination link** - cek apakah selector next-page link match tepat satu elemen yang benar.
7. **Ekstraksi attribut spesifik** - misal `meta[property="og:image"]` → `content`; Playground menampilkan semua atribut.
8. **Teach yourself selector syntax** - visual feedback langsung membantu belajar CSS/XPath lebih cepat daripada trial-error di scraper.

## Cara penggunaan

1. **Buka Selector Playground** - sidebar `Selector Playground`. Ekspektasi: form dengan field `URL to inspect`, toggle CSS/XPath, dan field `Selector`.
2. **Tempel URL di field `URL to inspect`** - format lengkap dengan protokol `https://example.com/products`. Ekspektasi: input text tidak memvalidasi URL sebelum submit; invalid URL akan error saat `Fetch`.
3. **Klik tombol `Fetch`** untuk menarik HTML halaman. Ekspektasi: badge status code muncul, plus ukuran HTML.
4. **Pilih Selector Type** lewat SegmentedControl `CSS` atau `XPath`. Default CSS. Ekspektasi: placeholder field `Selector` berubah sesuai jenis (`div.content > h2, img.hero` untuk CSS, `//div[@class='content']//h2` untuk XPath).
5. **Tulis selector di field `Selector`** - atau klik salah satu preset di card `Quick examples` sebelum fetch.
6. **Klik `Test`** - backend parse + eksekusi selector. Ekspektasi: loading spinner singkat lalu tabel match muncul.
7. **Review match count di atas tabel result** - misal badge "3 matches".
8. **Lihat detail tiap row** - kolom `Tag`, `Text content`, `Attributes` ditampilkan per match.
9. **Refine selector jika tidak sesuai** - misal dapat 0 match, tambah wildcard; dapat terlalu banyak, tambah class prefix.
10. **Klik `Use in Harvester` jika sudah yakin` - redirect ke halaman Image Harvester dengan field URL dan optionally selector sudah terisi. Ekspektasi: URL param `?url=...` terbawa.
11. **Atau copy selector manual** - untuk pemakaian di Custom Pipeline atau AI Extract. Ekspektasi: tidak ada tombol copy otomatis untuk selector, pakai keyboard.
12. **Ganti URL untuk test lain** - Playground tidak stateful, ganti URL lalu klik `Fetch` lagi.
13. **Close tab tanpa save** - tidak ada data yang hilang karena memang tidak disimpan.

## Pengaturan / Konfigurasi

### URL

Alamat lengkap halaman target. HTTPS dan HTTP keduanya didukung. Tidak ada proxy/vault integration di playground - fetch dilakukan plain. Jika situs membutuhkan cookie/auth, Playground saat ini tidak akan berhasil (lihat Keterbatasan).

### Selector Type

- **CSS** - syntax BeautifulSoup `soup.select`. Support: `tag`, `.class`, `#id`, `[attr]`, `[attr=value]`, `parent > child`, `ancestor descendant`, pseudo-class terbatas (`:nth-of-type`, `:not(...)`, `:contains` custom BS).
- **XPath** - syntax lxml. Support penuh XPath 1.0: `//`, `/`, predicate `[...]`, fungsi `contains()`, `starts-with()`, `normalize-space()`, axis `following-sibling::`, dll.

### Selector (string)

Field text. Tidak ada autocomplete. Multi-line tidak didukung (single selector per run). Whitespace di awal/akhir otomatis di-trim.

### Truncation Limit

Hardcoded 50KB di backend. Tidak diekspos di UI. Jika Anda bekerja dengan halaman sangat besar dan butuh preview penuh, edit `app/services/selector_service.py`.

### Parser

BeautifulSoup default pakai `lxml` parser (lebih cepat dan toleran terhadap HTML invalid). Jika Anda ingin html.parser (stdlib), harus edit di backend.

### Quick Examples

Preset statis: `h1`, `a[href]`, `img[src]`, `meta[name="description"]`, `title`, `.content`. Klik untuk auto-fill selector.

### HTTP Headers

Playground mengirim user-agent default httpx (Python/x.y.z). Beberapa situs block UA ini. Tidak ada UI untuk custom headers - ini limitation yang disengaja agar Playground tetap sederhana. Untuk situs yang butuh header custom, gunakan Image Harvester atau Site Ripper yang terintegrasi Auth Vault.

## Output

Tidak ada file output. Hasil hanya live di UI, tidak disimpan ke `data/`. Jika Anda ingin record selector yang bagus, copy manual ke note Anda atau ke Description field di Custom Pipeline / Harvester config.

Format result di UI per-match:
```
Tag: <img>
Text: "Product photo"  (cleaned, trimmed)
Attrs: {"src": "https://...", "alt": "...", "class": "..."}
HTML: <img src="..." alt="..." class="..."/>  (truncated)
```

## Integrasi dengan fitur lain

1. **Image Harvester** - tombol `Use in Harvester` langsung redirect dengan URL pre-fill, saving setup time.
2. **AI Extract** - pakai Playground untuk mengisolasi blok HTML relevan (misal `#product-info`), salin outerHTML ke AI Extract Input Text sebagai context yang lebih sempit dan akurat.
3. **Custom Pipeline** - verifikasi selector sebelum hardcode `soup.select('...')` di pipeline script.
4. **Site Ripper** - test selector untuk `link_rewrite_pattern` atau `allow_selector` sebelum run crawler besar.
5. **Link Bypass (tidak langsung)** - jika situs bypass punya link target yang bisa di-extract lewat CSS, Playground bisa verify pattern-nya sebelum tulis adapter bypass baru.

## Tips & Best Practices

1. **Mulai dari selector spesifik, longgarkan bertahap** - `article.post h1.title` dulu, kalau 0 match baru coba `h1.title`.
2. **Gunakan DevTools browser sebagai referensi** - right-click element → "Copy selector" di Chrome untuk starting point, tapi hampir selalu perlu dirapikan (Chrome sering generate `:nth-child(3) > div > span`).
3. **Prefer CSS untuk sederhana, XPath untuk kondisi teks** - CSS tidak bisa match "element yang teksnya berisi 'Beli'"; XPath bisa dengan `//button[contains(text(),'Beli')]`.
4. **Hindari `:nth-child` jika bisa** - fragile terhadap perubahan layout. Prefer class/attribute selector.
5. **Test di 2-3 halaman mirip** - selector yang jalan di product page pertama belum tentu jalan di halaman lain dari situs yang sama karena layout bervariasi.
6. **Simpan selector bagus di catatan** - Playground tidak persist; Anda akan menyesal setelah refresh kalau tidak copy.
7. **Perhatikan whitespace** - teks yang muncul di UI sudah di-`strip()`. Jangan heran kalau " Hello World " muncul sebagai "Hello World".
8. **XPath `text()` vs `string()`** - `text()` return hanya direct child text node (exclude teks anak elemen), `string()` return all nested text. Untuk "ambil semua teks" pakai `string(.)` atau di UI pakai field Text (sudah flattened).

## Troubleshooting

### Problem: "0 matches found" padahal elemen jelas ada di browser
- **Symptom**: selector benar di DevTools, tapi Playground return 0.
- **Cause**: halaman rendered oleh JavaScript client-side. Playground fetch raw HTML (SSR output), bukan HTML setelah JS execute.
- **Solution**: (1) lihat "View Source" di browser (Ctrl+U) - kalau elemen tidak ada di source, itu JS-rendered. (2) pakai tool yang support JS rendering (Playwright-based), atau cari JSON API yang halaman itu panggil (inspect Network tab), fetch API langsung.

### Problem: 403 Forbidden / 401 Unauthorized saat fetch
- **Symptom**: error "HTTP 403" atau similar, tidak ada hasil.
- **Cause**: situs block user-agent default httpx, atau butuh cookie auth.
- **Solution**: Playground tidak support custom header/auth. Workaround: gunakan Image Harvester/Site Ripper yang bisa read dari Auth Vault. Atau test selector di Playground pakai mirror halaman (save HTML manually, host local).

### Problem: Cloudflare / Captcha halaman
- **Symptom**: HTML yang di-fetch berisi "Checking your browser..." bukan content real.
- **Cause**: anti-bot challenge.
- **Solution**: tidak ada solusi di Playground. Gunakan browser automation tool eksternal untuk bypass, simpan HTML, lalu test selector di HTML lokal (tidak didukung Playground, ini limitation).

### Problem: XPath error "Invalid expression"
- **Symptom**: notifikasi merah "XPath error: Invalid expression".
- **Cause**: syntax salah, misalnya `//div[class='x']` (missing `@` untuk atribut).
- **Solution**: koreksi jadi `//div[@class='x']`. XPath wajib `@` untuk attribute.

### Problem: CSS selector error "SelectorSyntaxError"
- **Symptom**: error "Expected selector".
- **Cause**: syntax invalid, misalnya `div:.class` (harusnya `div.class`).
- **Solution**: cek dokumentasi selector BeautifulSoup atau soupsieve.

### Problem: Hasil match terlalu banyak, tidak spesifik
- **Symptom**: selector `div` return 200 elemen, UI lambat render.
- **Cause**: selector terlalu umum.
- **Solution**: tambah kualifikasi: `div.product-card`, atau naikkan spesifisitas via parent: `#products-grid div`.

### Problem: Atribut `data-*` tidak muncul di Attrs
- **Symptom**: `data-product-id` ada di DOM tapi tidak tampil.
- **Cause**: seharusnya muncul semua attrs - kalau tidak, element yang match bukan yang Anda kira.
- **Solution**: inspect HTML preview - verifikasi elemen benar. Tambahkan atribut ke selector untuk target specific: `div[data-product-id]`.

### Problem: Fetch sangat lambat (>20 detik)
- **Symptom**: spinner lama untuk halaman biasa.
- **Cause**: situs lambat, atau redirect chain panjang.
- **Solution**: test URL di browser dulu - kalau browser juga lambat, memang situs-nya. Kalau browser cepat tapi Playground lambat, mungkin rate limit server-side; tunggu beberapa menit.

### Problem: Truncation 50KB memotong bagian yang saya mau
- **Symptom**: content di bagian bawah halaman tidak muncul di HTML preview.
- **Cause**: limit 50KB untuk UI.
- **Solution**: Playground selektor tetap jalan di full HTML, hanya preview di UI yang dipotong. Jika selector Anda target elemen yang secara struktural ada di bagian akhir halaman, hasilnya tetap muncul sebagai match. Jika Anda butuh full HTML preview, edit limit di backend.

## FAQ

**Q: Bisa test selector di local file HTML?**
A: Saat ini tidak - URL field wajib URL HTTP/HTTPS. Workaround: serve file lokal via `python -m http.server` lalu pakai `http://localhost:8000/file.html`.

**Q: Apakah Playground pakai Auth Vault?**
A: Tidak. Playground plain fetch tanpa cookie/header custom. Untuk halaman auth-gated gunakan Harvester/Ripper.

**Q: Bisa JS-rendered pages?**
A: Tidak. HTTP fetch tanpa browser engine.

**Q: Bisa simpan session / history?**
A: Tidak. Playground stateless, by design.

**Q: XPath 2.0 / 3.0 features?**
A: Hanya XPath 1.0 (batas lxml built-in).

**Q: Support `:has()` pseudo-class CSS?**
A: Tergantung versi soupsieve. Update BS4 terbaru harusnya support. Test manual.

**Q: Batas ukuran halaman?**
A: Tidak ada hard limit untuk fetch, tapi preview UI dibatasi 50KB. Parser lxml bisa handle puluhan MB, meski lambat.

**Q: Bisa ekspor hasil ke CSV?**
A: Tidak di Playground. Pakai Custom Pipeline jika butuh export.

**Q: Hasil deterministik?**
A: Tergantung halaman. Situs yang konten-nya berubah tiap fetch (ads, timestamp) akan memberi match yang slightly berbeda.

**Q: Bagaimana kalau HTML-nya invalid/malformed?**
A: lxml sangat toleran - akan parse best-effort. Hasil selector mungkin sedikit berbeda dari browser, tapi biasanya cukup dekat.

## Keterbatasan

- **Tidak JS-aware** - halaman SPA (React/Vue/Angular) yang render konten client-side tidak akan berisi konten di HTML mentah.
- **Tanpa auth support** - tidak integrate Auth Vault; hanya fetch anonim.
- **Tanpa proxy** - tidak bisa set HTTP proxy untuk test via tunnel.
- **Tanpa persistence** - semua input hilang saat refresh.
- **Preview truncated 50KB** - halaman besar tidak full-render di UI.
- **XPath 1.0 only** - fitur XPath 2.0+ (regex `matches()`, aggregation) tidak tersedia.
- **Single selector per run** - tidak bisa test 10 selector parallel.
- **Tidak ada screenshot** - tidak render visual halaman.

## Related docs

- [Image Harvester](../tools/image-harvester.md) - target utama output Playground.
- [Site Ripper](../tools/site-ripper.md) - gunakan selector yang sudah divalidasi.
- [Custom Pipeline](./pipeline.md) - hardcode selector tested ke skrip.
- [AI Extract](./ai-extract.md) - alternatif saat selector tradisional tidak cukup.
- [Index dokumentasi](../index.md) - navigasi utama.
