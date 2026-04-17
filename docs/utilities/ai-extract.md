# AI Extract

> Alat ekstraksi data terstruktur berbasis Large Language Model (LLM) lokal via Ollama. Cocok untuk mengubah teks mentah yang berantakan menjadi JSON rapi tanpa perlu menulis parser rumit.

## Deskripsi

AI Extract adalah jembatan antara PyScrapr dan instance Ollama lokal yang berjalan di mesin Anda pada `http://localhost:11434`. Tool ini membaca teks mentah apapun — HTML yang sudah di-clean, transcript, email, artikel, bahkan dump log — lalu menggunakan model bahasa (LLM) untuk mengekstrak entitas atau field yang Anda deskripsikan dalam bentuk schema. Hasilnya selalu berupa JSON valid karena request dikirim dengan flag `format=json` pada Ollama API, sehingga Anda tidak perlu lagi bergulat dengan regex panjang atau parser BeautifulSoup yang rapuh.

Secara arsitektural, AI Extract tidak menyimpan model atau melakukan training. Ia hanya berperan sebagai client: membangun prompt (instruksi sistem + schema description + input text), memanggil endpoint `/api/generate` atau `/api/chat` Ollama, menunggu respons, lalu membersihkan output dari kemungkinan markdown code fence (`` ```json ... ``` ``) yang kadang tetap muncul meskipun json_mode aktif. Temperature di-set ke `0.1` agar output deterministik — dua panggilan dengan input yang sama cenderung menghasilkan JSON yang sama, yang penting untuk workflow reproducible.

Karena Ollama berjalan 100% lokal, tidak ada data yang dikirim ke cloud. Anda bisa bekerja dengan dokumen sensitif (invoice internal, transcript meeting, data klien) tanpa kekhawatiran kebocoran. Trade-off-nya adalah Anda perlu menyediakan hardware sendiri: model kecil seperti `llama3.2:1b` butuh ~2GB VRAM/RAM, sementara `llama3.1:8b` butuh ~8GB, dan `llama3.3:70b` butuh setidaknya 40GB. PyScrapr tidak memverifikasi spec hardware — jika model tidak muat, Ollama sendiri yang akan mengembalikan error OOM.

PyScrapr menyediakan empat preset template yang siap pakai: **Product** (extract nama, harga, SKU, deskripsi, stok dari halaman e-commerce), **Article** (judul, author, tanggal publish, isi, tag dari artikel berita/blog), **Entities** (ekstraksi named-entity: person, organization, location, date, event dari teks bebas), dan **Contact** (nama, email, telepon, alamat, website dari halaman "tentang kami" atau business card). Anda bisa memilih preset sebagai titik awal lalu memodifikasi schema sesuai kebutuhan — preset bukan hardcoded, hanya starter JSON.

## Kapan pakai tool ini?

1. **Halaman tanpa struktur konsisten** — ketika setiap produk di satu situs punya layout berbeda dan CSS selector tidak bisa digeneralisasi, LLM bisa "memahami" isi halaman secara semantik.
2. **Ekstraksi entitas dari teks bebas** — misalnya daftar nama perusahaan dan jabatan dari notulen rapat, atau nama obat dan dosis dari resep yang di-OCR.
3. **Normalisasi data yang heterogen** — harga ditulis sebagai "Rp 1.250.000", "IDR 1,250,000", "1.25jt", atau "one point two five million" — LLM bisa menyamakan semuanya menjadi `1250000` dengan satu prompt.
4. **Post-processing hasil scraper** — setelah Site Ripper mengunduh ribuan halaman, jalankan AI Extract dalam loop untuk mengubah HTML menjadi dataset terstruktur tanpa perlu menulis parser per-template.
5. **Klasifikasi cepat tanpa training** — apakah artikel ini tentang politik, olahraga, atau teknologi? Zero-shot classification lewat prompt + schema `{"category": "..."}` sudah cukup untuk prototipe.
6. **Summarization terstruktur** — ringkas transcript meeting satu jam menjadi JSON `{"topik_utama": [...], "action_items": [...], "keputusan": [...]}`.
7. **Parsing invoice/kwitansi** — ekstrak line items, total, tax, vendor, tanggal dari PDF yang sudah di-OCR ke text.
8. **Eksperimen prompt engineering** — UI-nya ringan sehingga cocok sebagai playground untuk menguji schema dan prompt sebelum dipakai di Custom Pipeline production.

## Cara penggunaan

1. **Install Ollama lebih dulu** — buka [ollama.com](https://ollama.com), download installer untuk OS Anda, jalankan. Setelah terinstall, Ollama otomatis start sebagai service di background pada port `11434`. Ekspektasi: icon llama muncul di system tray (Windows) atau menu bar (macOS).
2. **Pull minimal satu model** — buka terminal, jalankan `ollama pull llama3.2`. Unduhan pertama bisa 2-5 menit tergantung koneksi (ukuran ~2GB untuk 3B params). Ekspektasi: progress bar sampai 100%, lalu pesan `success`.
3. **Buka halaman AI Extract di PyScrapr** — dari sidebar pilih "AI Extract". Ekspektasi: status card di atas langsung melakukan health-check ke Ollama dan menampilkan badge hijau "Connected" plus jumlah model yang tersedia.
4. **Pilih model dari dropdown** — biasanya `llama3.2:latest` atau model lain yang sudah Anda pull. Ekspektasi: dropdown terisi otomatis dari response `/api/tags` Ollama.
5. **Pilih preset atau tulis schema kustom** — klik salah satu dari tombol preset (Product, Article, Entities, Contact) untuk auto-fill schema textarea, atau tulis sendiri dalam format deskripsi JSON seperti `{"nama": "nama lengkap orang", "umur": "umur dalam tahun (integer)"}`. Ekspektasi: textarea terisi dengan schema starter.
6. **Tempelkan teks input** — paste HTML yang sudah di-clean, artikel, atau teks mentah apapun ke textarea "Input Text". Batas praktis ~8000 karakter untuk model 3B-7B agar tidak truncate context. Ekspektasi: counter karakter (jika ada) menunjukkan jumlah.
7. **Klik tombol Extract** — tunggu loading spinner. Durasi bervariasi: 2-5 detik untuk model kecil di GPU, 10-30 detik untuk model besar di CPU. Ekspektasi: spinner aktif, tombol disabled.
8. **Review hasil di JSON Viewer** — hasil muncul sebagai tree collapsible di panel kanan. Ekspektasi: JSON valid, sesuai schema, tanpa field ekstra.
9. **Copy atau download hasil** — gunakan tombol "Copy JSON" untuk clipboard, atau simpan manual. Ekspektasi: toast "Copied!" muncul.
10. **Iterasi schema jika perlu** — jika field tidak lengkap atau format salah, perjelas deskripsi field (misalnya `"harga": "harga dalam rupiah sebagai integer tanpa separator"`), lalu klik Extract lagi.
11. **Ganti model jika kualitas kurang** — jika `llama3.2:1b` terlalu "pelupa", upgrade ke `llama3.1:8b` atau `qwen2.5:7b`. Pull dulu via CLI lalu refresh halaman.
12. **Simpan hasil untuk pipeline** — copy JSON hasil ke Custom Pipeline jika ingin post-process lebih lanjut, atau langsung export ke CSV via tool lain.

## Pengaturan / Konfigurasi

### Base URL Ollama

Default `http://localhost:11434`. Bisa diubah di backend `app/services/ollama_client.py` atau via environment variable `OLLAMA_BASE_URL` jika Anda menjalankan Ollama di mesin lain (misalnya desktop dengan GPU sementara PyScrapr di laptop). Hati-hati: jika pakai IP LAN, pastikan firewall Windows/Linux mengizinkan port 11434, dan Ollama di-start dengan `OLLAMA_HOST=0.0.0.0` agar listen di semua interface.

### Model

Dropdown menampilkan semua model yang sudah di-`pull`. Rekomendasi per use-case:
- **Teks pendek, latency-sensitive**: `llama3.2:1b` atau `qwen2.5:0.5b` — cepat tapi kurang akurat untuk schema kompleks.
- **Use-case umum, balance**: `llama3.2:3b` atau `llama3.1:8b` — sweet spot antara kecepatan dan akurasi.
- **Schema kompleks, multi-entity**: `qwen2.5:14b`, `llama3.1:70b`, atau `mistral-nemo:12b` — butuh hardware kuat.
- **Khusus JSON**: `gemma2:9b` atau model yang di-tune untuk structured output.

### Schema Description

Textarea utama tempat Anda mendefinisikan "apa yang mau diekstrak". Format bebas tapi yang paling reliable adalah JSON-like dengan deskripsi per-field. Contoh:
```
{
  "product_name": "nama produk lengkap, string",
  "price_idr": "harga dalam rupiah, integer tanpa separator",
  "in_stock": "boolean, true jika tersedia"
}
```
Semakin eksplisit deskripsi (termasuk tipe data dan format), semakin akurat LLM.

### Input Text

Teks mentah yang akan dianalisis. Tidak ada validasi format — boleh HTML kotor, markdown, plain text, atau campuran. Tips: bersihkan dulu tag `<script>` dan `<style>` agar tidak membuang context window.

### Temperature (hidden, hardcoded)

Di-set `0.1` di backend untuk konsistensi. Tidak diekspos ke UI karena untuk ekstraksi deterministik, temperature tinggi hampir selalu memburukkan hasil. Jika Anda butuh variasi (misal untuk brainstorming), edit `app/services/ollama_client.py`.

### JSON Mode

Flag `format: "json"` dikirim ke Ollama API, memaksa model untuk menghasilkan string yang parseable sebagai JSON. Tidak bisa dimatikan lewat UI (memang tujuannya JSON output).

### Timeout

Default 120 detik per request. Diatur di httpx client. Untuk model besar di CPU, mungkin perlu dinaikkan di `ollama_client.py`.

## Output

Output muncul di panel kanan sebagai JSON tree viewer dan tidak otomatis disimpan ke disk. Jika Anda ingin persistence, salin manual atau integrasikan ke Custom Pipeline yang menulis ke `data/ai_extracts/{timestamp}.json`.

Format output selalu JSON valid (setelah fence stripping). Struktur mengikuti schema yang Anda berikan — tidak ada field `meta` atau wrapper tambahan dari PyScrapr. Jika LLM menambahkan field yang tidak diminta, itu bukan bug PyScrapr melainkan "kreativitas" model; tightening schema description biasanya menyelesaikan.

## Integrasi dengan fitur lain

1. **Site Ripper → AI Extract** — setelah Ripper mengunduh ratusan halaman, loop setiap file HTML, kirim body-nya ke AI Extract, kumpulkan JSON hasilnya sebagai dataset.
2. **Custom Pipeline** — panggil endpoint `/api/ai-extract/run` dari script pipeline untuk otomatisasi batch. Pipeline punya akses ke `data` (list dicts) yang bisa di-enrich dengan field hasil LLM.
3. **Selector Playground** — gunakan Playground untuk isolasi blok HTML yang relevan (misal `div.product-details`), lalu kirim hanya blok itu ke AI Extract agar context lebih fokus dan akurasi naik.
4. **Image Harvester alt-text enrichment** — setelah Harvester kumpulkan URL gambar + alt text, kirim alt-text ke AI Extract untuk klasifikasi (produk/orang/pemandangan) atau ekstraksi brand.
5. **Auth Vault (tidak langsung)** — karena AI Extract tidak melakukan fetch URL (hanya proses teks), Auth Vault tidak relevan. Gunakan Playground/Harvester dulu untuk fetch, lalu teksnya ke AI Extract.

## Tips & Best Practices

1. **Mulai dari model kecil** — prototipe schema dengan `llama3.2:3b` dulu. Jika akurasinya cukup, stop di situ — tidak perlu model 70B yang lambat.
2. **Deskripsi field = kontrak** — tulis deskripsi seperti Anda menjelaskan ke junior engineer. "harga" ambigu; "harga retail akhir dalam rupiah sebagai integer, tanpa titik/koma separator" jauh lebih reliable.
3. **Contoh dalam schema** — tambahkan `"example"` di schema jika format harus sangat spesifik, misalnya `"date": "tanggal dalam format YYYY-MM-DD, contoh: 2026-04-17"`.
4. **Potong input yang terlalu panjang** — jika teks >10k token, pecah per-section dan jalankan bertahap lalu merge di pipeline, daripada truncate otomatis oleh Ollama yang bisa menghilangkan info penting.
5. **Simpan schema yang bagus** — gunakan Custom Pipeline atau file `.md` catatan pribadi untuk menyimpan schema yang terbukti jalan, agar tidak trial-error ulang.
6. **Verifikasi dengan sampel** — jalankan schema di 5-10 sampel beragam dulu sebelum batch 1000 dokumen. LLM bisa bias terhadap pola yang tidak Anda antisipasi.
7. **Jangan percaya buta** — LLM bisa halusinasi (mengisi field dengan tebakan). Untuk data kritis (harga, kontrak), cross-check dengan regex atau selector tradisional.
8. **Monitor GPU/RAM** — buka Task Manager saat generate. Jika swap ke disk, turunkan ukuran model atau batch size.

## Troubleshooting

### Problem: Status card merah "Ollama offline"
- **Symptom**: badge merah, tombol Extract disabled, error toast "Ollama tidak merespon".
- **Cause**: service Ollama belum jalan, atau port 11434 di-block firewall.
- **Solution**: (1) cek system tray untuk icon Ollama; jika tidak ada, buka aplikasi Ollama secara manual. (2) di terminal, `curl http://localhost:11434/api/tags` — harus return JSON. Jika timeout, start Ollama: `ollama serve` (Linux/macOS) atau restart aplikasi (Windows). (3) cek Windows Defender Firewall, pastikan Ollama.exe allowed.

### Problem: Dropdown model kosong
- **Symptom**: status card hijau tapi dropdown "Model" kosong atau hanya menampilkan placeholder.
- **Cause**: Anda belum pernah menjalankan `ollama pull <name>`.
- **Solution**: buka terminal, jalankan `ollama pull llama3.2`. Tunggu selesai. Refresh halaman PyScrapr. Dropdown akan terisi.

### Problem: Error "model not found"
- **Symptom**: toast error "model 'llama3.2:latest' not found" padahal dropdown menampilkannya.
- **Cause**: cache dropdown stale; model sudah di-remove lewat `ollama rm` tapi UI belum refresh.
- **Solution**: refresh halaman (F5), atau restart Ollama service untuk sinkronisasi.

### Problem: JSON output tidak valid / parse error
- **Symptom**: panel result menampilkan raw string, bukan tree. Console error "Unexpected token".
- **Cause**: model terlalu kecil untuk json_mode (biasanya <1B params), atau sempat timeout di tengah generate.
- **Solution**: (1) upgrade model ke minimal 3B params. (2) cek apakah output diawali ``` ```json ``` — fence stripping PyScrapr sudah handle ini, tapi jika ada teks naratif sebelum JSON, edit prompt di backend. (3) simplify schema — terlalu banyak field nested bisa membingungkan model kecil.

### Problem: Response sangat lambat (>60 detik)
- **Symptom**: spinner berputar lama, kadang timeout.
- **Cause**: (a) model jalan di CPU bukan GPU; (b) model terlalu besar untuk RAM/VRAM sehingga swap; (c) input text terlalu panjang.
- **Solution**: (1) `ollama ps` — lihat kolom `PROCESSOR`. Jika `100% CPU`, install GPU driver (CUDA untuk NVIDIA, ROCm untuk AMD). (2) pakai model yang muat di VRAM Anda: 8GB VRAM → max 7B, 12GB → 13B. (3) pendekkan input di bawah 4000 karakter.

### Problem: Output JSON selalu sama tidak peduli input berbeda
- **Symptom**: ekstraksi 3 artikel berbeda menghasilkan JSON identik.
- **Cause**: prompt accidentally ter-cache, atau model ukurannya kecil sekali dan bias ke satu output.
- **Solution**: (1) restart Ollama service untuk clear KV cache. (2) pastikan Input Text benar-benar beda (bukan placeholder lama). (3) pakai model minimal 3B.

### Problem: Field integer dikembalikan sebagai string ("123" bukan 123)
- **Symptom**: Pipeline downstream gagal karena type mismatch.
- **Cause**: LLM sering default ke string di JSON kecuali dipaksa.
- **Solution**: perjelas deskripsi: `"price": "harga sebagai number/integer, bukan string dalam quotes"`. Atau post-process: `int(result["price"])` di Python Pipeline.

### Problem: Bahasa Indonesia di-translate ke Inggris otomatis
- **Symptom**: input artikel Bahasa Indonesia, tapi field `title` dan `content` keluar dalam Bahasa Inggris.
- **Cause**: model multilingual kecil kadang bias ke English sebagai "default professional language".
- **Solution**: tambahkan instruksi eksplisit di schema: `"title": "judul artikel, PERTAHANKAN bahasa asli dari input, jangan translate"`. Atau pakai model yang lebih multilingual seperti `qwen2.5` atau `aya`.

### Problem: Ollama crash / OOM saat generate
- **Symptom**: Ollama service mati, Windows Event Log menunjukkan crash, atau error "ollama runner process has terminated".
- **Cause**: model lebih besar dari available VRAM+RAM.
- **Solution**: (1) tutup aplikasi lain yang makan RAM (Chrome, IDE). (2) set `OLLAMA_NUM_PARALLEL=1` di env var untuk limit concurrent requests. (3) downgrade ke model lebih kecil. (4) di Linux, add swap file 16GB sebagai safety net.

## FAQ

**Q: Apakah saya butuh koneksi internet?**
A: Hanya saat pertama install Ollama dan pull model. Setelah itu AI Extract jalan 100% offline.

**Q: Data saya aman? Tidak dikirim ke Anthropic/OpenAI?**
A: Aman. Ollama adalah server LLM lokal open-source. PyScrapr tidak memanggil API eksternal apapun dari fitur AI Extract. Anda bisa verifikasi dengan Wireshark.

**Q: Model mana yang paling bagus?**
A: Tergantung hardware dan use-case. Secara umum `qwen2.5:7b` atau `llama3.1:8b` adalah sweet spot untuk tugas ekstraksi. `gemma2:9b` kadang lebih bagus untuk JSON.

**Q: Bisa pakai GPT-4 / Claude / Gemini?**
A: Tidak langsung lewat UI ini. AI Extract dirancang spesifik untuk Ollama. Jika Anda ingin cloud API, tulis Custom Pipeline yang memanggil SDK masing-masing provider.

**Q: Berapa biaya per ekstraksi?**
A: Gratis — hanya listrik. Tidak ada token billing seperti cloud API.

**Q: Apakah hasilnya deterministik? Run 2x dapat output sama?**
A: Mendekati — dengan `temperature=0.1` dan input sama, ~95% output akan identik. 5% variasi tetap ada karena sampling stochastic.

**Q: Bagaimana handle PDF?**
A: AI Extract tidak parse PDF. Konversi ke text dulu (tools lain atau `pdftotext`), baru paste ke Input Text.

**Q: Berapa panjang input maksimum?**
A: Dibatasi context window model. `llama3.2` = 128k token, tapi praktis 8-16k untuk latency wajar. Potong input panjang.

**Q: Bisa ekstrak image (vision)?**
A: Butuh model vision seperti `llava` atau `llama3.2-vision`. Fitur ini belum diekspos di UI PyScrapr saat ini — hanya text input.

**Q: Hasil kadang beda padahal input sama, kenapa?**
A: Temperature 0.1 masih memungkinkan sampling variasi kecil. Untuk full determinism, backend perlu di-set `temperature=0` dan `seed=fixed`.

## Keterbatasan

- **Butuh hardware yang layak** — laptop 4GB RAM tanpa GPU akan sangat lambat atau tidak bisa sama sekali.
- **Kualitas bervariasi per model** — model kecil sering halusinasi atau miss field. Tidak ada "one size fits all".
- **Tidak ada batch UI** — ekstrak 100 dokumen manual via UI tidak praktis; pakai Custom Pipeline untuk otomasi.
- **Tidak ada fine-tuning hook** — PyScrapr tidak menyediakan cara train/fine-tune model untuk domain spesifik; Anda harus pakai tool Ollama eksternal (`ollama create` dengan Modelfile).
- **Context window terbatas** — dokumen >100 halaman harus dipotong manual.
- **Tidak ada caching response** — setiap klik Extract memanggil LLM dari awal; jika input sama, tetap bayar waktu inference.
- **Tidak ada schema validation di sisi PyScrapr** — output tidak dicek melawan JSON Schema formal; trust dari output model.

## Related docs

- [Custom Pipeline](./pipeline.md) — otomatisasi AI Extract batch lewat script Python.
- [Selector Playground](./playground.md) — isolasi blok HTML sebelum dikirim ke LLM.
- [Site Ripper](../tools/site-ripper.md) — sumber HTML massal untuk diproses AI Extract.
- [System requirements](../system/requirements.md) — spec hardware minimum untuk model LLM.
- [Index dokumentasi](../index.md) — navigasi lengkap dokumentasi PyScrapr.
