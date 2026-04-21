# AI Tagger

> Klasifikasi gambar zero-shot dengan model CLIP ViT-B/32 dari OpenCLIP - cukup provide label sembarang dalam bahasa natural, tool langsung beri confidence score per label tanpa perlu training data.

## Deskripsi

AI Tagger adalah modul kecerdasan buatan PyScrapr yang membawa kapabilitas state-of-the-art computer vision ke desktop user biasa, tanpa perlu GPU, tanpa perlu cloud API key, tanpa biaya subscription. Di jantungnya adalah **CLIP** (Contrastive Language-Image Pre-training) - model yang dikembangkan OpenAI tahun 2021 dan kemudian di-open-source-ulang oleh LAION sebagai OpenCLIP. PyScrapr memakai varian `ViT-B/32` dengan pretrained weight `laion2b_s34b_b79k` - artinya backbone Vision Transformer Base dengan patch size 32x32, ditraining pada dataset LAION-2B (2 miliar pair image-text) selama 34 miliar samples seen.

Kenapa CLIP? Karena model ini "mengerti" gambar dan text dalam satu embedding space yang sama. Anda bisa memberi label sembarang dalam bahasa natural - misal `["foto pernikahan outdoor", "foto produk studio", "screenshot software", "selfie dalam ruangan"]` - dan CLIP akan menghitung kemiripan antara setiap gambar dengan text setiap label. Tidak perlu training data. Tidak perlu fine-tuning. Ini disebut **zero-shot classification** dan merupakan terobosan besar yang membuat image classification jadi accessible untuk non-ML engineer.

Secara teknis implementasi: saat user submit job classification, backend load model CLIP sekali ke RAM (ukuran ~350MB, auto-download dari HuggingFace Hub pada run pertama dan cache di `~/.cache/huggingface/`). Setiap label text di-encode jadi vector 512-dim via text encoder. Setiap gambar (dari hasil Image Harvester) di-preprocess (resize 224x224, normalize) dan di-encode via vision encoder jadi vector 512-dim juga. Similarity dihitung via dot product, lalu di-softmax untuk jadikan probability distribution. Hasilnya: setiap gambar dapat score 0-1 per label, total sum = 1.

PyScrapr menjalankan semua ini di CPU pakai PyTorch 2.11 - CUDA tidak wajib. Kecepatan inference rata-rata ~1 detik per gambar di CPU modern (i5/Ryzen 5 up). Untuk batch 1000 gambar, expect ~15-20 menit. Kalau GPU NVIDIA tersedia dan CUDA toolkit terinstall, tool otomatis detect dan pindah ke GPU untuk speedup 20-50x. Tapi desain deliberately CPU-first agar bisa jalan di laptop biasa.

Positioning vs market: Google Vision API dan AWS Rekognition berbayar per-request ($1.5 per 1000 images). Azure Computer Vision juga subscription. Self-hosted alternative seperti Clarifai atau Roboflow masih butuh cloud account atau training custom model. AI Tagger PyScrapr gratis, offline (setelah download model sekali), zero training, dan terintegrasi langsung ke ekosistem - klasifikasi hasil Harvester, filter via tag chip, export hasil dengan label embedded.

## Kapan pakai tool ini?

- **Auto-tagging library foto pribadi** - klasifikasi 10.000 foto di laptop ke kategori `["beach", "mountain", "family", "food", "pet", "travel"]` untuk organization.
- **Moderasi konten user-uploaded** - filter gambar `["safe for work", "adult content", "violence", "text heavy"]` di platform yang Anda kelola.
- **Kategorisasi scraped product images** - hasil Image Harvester dari e-commerce ke label `["clothing", "electronics", "furniture", "food"]` untuk analisis katalog.
- **Dataset curation untuk training model lain** - filter gambar yang sesuai untuk dataset spesifik sebelum fine-tuning model downstream.
- **Visual search di local library** - label semua foto dengan query natural, lalu filter by label untuk temukan "semua foto pantai saat sunset" dari ribuan file.
- **Quality control dropshipping images** - klasifikasi `["studio quality", "amateur", "stock photo", "watermarked"]` untuk filter supplier berkualitas.
- **Content analysis competitor** - jalankan pada hasil harvest Instagram kompetitor untuk dapatkan distribution content type mereka.
- **Automated alt-text generation precursor** - klasifikasi awal sebelum generate caption detail via model lain (BLIP, dll).

## Cara penggunaan

1. Klik menu `AI Tagger` di sidebar. Halaman berisi form kiri (input job) dan panel kanan (hasil + filter).

2. Di field `Select Image Harvester job`, pilih job Image Harvester sebelumnya dari dropdown (sudah completed). Tool akan scan dan tampilkan count gambar yang valid di tiap opsi.

3. Masukkan `Labels for classification` - ketik label lalu tekan Enter untuk tiap label. Contoh:
 ```
   foto pemandangan alam
   foto kota malam hari
   foto makanan close-up
   foto orang potret
   foto produk dengan background putih
   ```
 Tidak ada batas jumlah label (practical: 20 maksimum untuk interpretability). Label boleh dalam Bahasa Indonesia atau Inggris - CLIP multilingual meski bias ke English.

4. (Opsi threshold confidence dan single-label mode tersedia di advanced settings, lihat bagian Pengaturan.)

5. Klik `Start tagging`. Pada run pertama, tool download model CLIP (~350MB) - progress bar muncul. Download ini sekali saja, setelahnya cached.

6. Setelah model loaded, classification mulai. Panel kanan menampilkan progress: `X / Y images processed, ETA Zmin`. Setiap gambar processing ~1 detik di CPU.

7. Selama running, hasil populate incrementally sebagai grid. Setiap card berisi thumbnail + confidence bars per label (colored progress bar dengan percent).

8. Setelah selesai, section `Tag distribution` muncul dengan badge chip per label. Klik chip untuk filter grid hanya tampilkan gambar yang match label tersebut.

9. Klik thumbnail untuk modal detail: full-size preview, ranking semua label dengan exact score, metadata original (URL source, filename, dimensions).

10. Untuk export CSV/ZIP by label, gunakan opsi di History page (lihat related docs) setelah job selesai.

11. Hasil classification tersimpan di History dengan link ke source Harvester job. Anda bisa re-run dengan labels berbeda tanpa re-process image encoding (cached).

## Pengaturan / Konfigurasi

### source_job_id / source_folder
Input gambar dari Harvester job atau folder lokal. Wajib salah satu. Default: kosong. Rekomendasi: pakai job ID untuk integrasi clean, folder lokal untuk ad-hoc analysis.

### labels
List text label untuk classification. Wajib minimum 2 label. Default: kosong. Rekomendasi: 5-15 label yang mutually distinguishable. Label boleh kalimat: `"foto anak bermain di taman"` lebih spesifik dari `"anak"`. Ubah labels sesuai kebutuhan analysis - zero-shot, tidak ada retraining.

### threshold
Minimum confidence untuk display label. Default: 0.25. Rekomendasi: 0.3-0.5 untuk strict filtering, 0.15 untuk exploratory analysis. Ubah naik kalau hasil terlalu noisy (banyak false positive), turun kalau terlalu sparse.

### single_label_mode
Boolean one-label-per-image atau multi-label. Default: false (multi). Rekomendasi: false untuk content dengan overlap (foto bisa pantai DAN sunset), true untuk strictly exclusive categories.

### model_variant
Varian CLIP. Default: `ViT-B/32`. Options tersedia: `ViT-B/16` (lebih akurat, 4x lebih lambat), `ViT-L/14` (state-of-art akurasi, butuh RAM 4GB+). Ubah kalau akurasi kritis dan hardware memadai.

### device
CPU atau GPU. Default: auto-detect. Rekomendasi: biarkan auto. Paksa `cuda` kalau Anda tahu GPU ada tapi tidak terdeteksi. Paksa `cpu` kalau GPU kelebihan beban oleh task lain.

### batch_size
Gambar per inference batch. Default: 16. Rekomendasi: 32 untuk RAM 16GB+, 8 untuk RAM 8GB, 4 untuk RAM minimal. Ubah turun kalau OOM error.

### normalize_labels
Auto-prepend `"a photo of "` ke setiap label (teknik prompting CLIP). Default: true. Rekomendasi: biarkan true - CLIP ditraining dengan konteks foto, prompting improve akurasi 5-10%. Ubah false hanya untuk label yang sudah mengandung context (`"screenshot of ..."`).

### cache_image_embeddings
Cache embedding gambar ke disk. Default: true. Rekomendasi: true, mempercepat re-run dengan labels berbeda. Ubah false kalau concern disk space.

## Output

Struktur hasil:

```
downloads/
└── ai_classifications/
    └── <job_id>/
        ├── results.json              # full data: filename, scores per label
        ├── results.csv               # flat tabular export
        ├── embeddings.npy            # cached image embeddings (reusable)
        ├── report.html               # interactive HTML report with charts
        └── by_label/                 # optional symlinks/copies
            ├── foto_pantai/
            ├── foto_kota/
            └── foto_makanan/
```

- **results.json** struktur: `[{filename, path, scores: {label: confidence, ...}, top_label, ...}]`
- **embeddings.npy** NumPy array, bisa di-load untuk custom analysis (similarity search, clustering).
- **report.html** self-contained dengan chart distribusi, confusion matrix estimation, top-k per label.

## Integrasi dengan fitur lain

- **Image Harvester** - input langsung; klasifikasi otomatis tepat setelah harvest selesai via Scheduler chain.
- **History & Export** - hasil jadi part dari historical record, diff antar run untuk tracking label drift.
- **Pipeline** - feed hasil ke Image Organizer yang auto-move file ke folder per-label.
- **Media Downloader** - klasifikasi thumbnail video untuk kategorisasi library.
- **Site Ripper** - klasifikasi gambar dari mirror untuk content audit.
- **Custom webhook** - trigger action eksternal saat label tertentu terdeteksi (misal Slack notification untuk moderation flag).
- **Search API** - endpoint `/api/ai/search?q=...` untuk visual search di indexed library.

## Tips & Best Practices

1. **Label dalam Bahasa Inggris masih lebih akurat** - CLIP di-training terbesar dengan data English. Label Indonesia bekerja tapi akurasi 10-15% lebih rendah. Kalau critical, pakai English labels.

2. **Label descriptive lebih baik dari single word** - `"a photo of a mountain landscape at sunset"` mengalahkan `"mountain"` dalam akurasi. CLIP merespon kontext well.

3. **Prompting `"a photo of ..."` aktif by default** - biarkan `normalize_labels: true`. Kalau test custom prompting, ingat match dengan domain image (misal `"a screenshot of ..."` untuk UI).

4. **Multi-label > single-label untuk exploration** - single-label force exclusive, yang jarang benar di real content. Multi-label beri richer picture.

5. **Cache embeddings secara religius** - encoding gambar adalah bottleneck (95% compute time). Dengan cache, re-run dengan labels baru hampir instant.

6. **Gunakan ViT-B/32 untuk skala, ViT-L/14 untuk presisi** - B/32 cukup untuk 95% use case. L/14 worth saat akurasi kritis (moderation, medical) dan batch tidak besar.

7. **Jangan percaya confidence absolute** - score CLIP tidak calibrated probability. Score 0.3 di satu label set ≠ 0.3 di set lain. Pakai untuk ranking relative, bukan absolute threshold yang sama di semua run.

8. **Review hasil pada 50 sampel random dulu** - sebelum action mass (auto-move 10.000 file), manual verify 50 random classification result untuk validate labels bekerja seperti diharapkan.

## Troubleshooting

### Problem: Model download gagal di run pertama
**Gejala:** Error `ConnectionError` atau `HTTPError 403` saat start pertama, progress bar stuck di 0%.
**Penyebab:** Koneksi HuggingFace Hub terblock (firewall, ISP), atau rate limit anonymous pull.
**Solusi:** Download manual dari `https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s34B-b79K`, extract ke `~/.cache/huggingface/hub/`. Atau set HTTP proxy env var `HF_HUB_OFFLINE=0 HF_ENDPOINT=<mirror>`.

### Problem: Out of memory saat load model
**Gejala:** Python crash atau "killed" di log saat model load.
**Penyebab:** Model ViT-L/14 butuh RAM 4GB+, system tidak cukup.
**Solusi:** Switch ke ViT-B/32 (1GB RAM cukup). Tutup aplikasi lain. Atau reduce `batch_size` ke 4. Kalau paksa ViT-L, butuh RAM minimal 8GB total.

### Problem: Classification sangat lambat (~10 detik per gambar)
**Gejala:** ETA beberapa jam untuk ratusan gambar.
**Penyebab:** Running di CPU lambat, atau batch_size terlalu kecil (overhead per batch), atau gambar resolution sangat tinggi (preprocessing bottleneck).
**Solusi:** Naikkan `batch_size` ke 32 (kalau RAM muat). Kalau CPU memang lambat, pertimbangkan GPU: install PyTorch dengan CUDA support. Resize gambar ke 512px max sebelum input (pipeline pre-resize).

### Problem: Hasil classification tidak masuk akal
**Gejala:** Foto pantai di-label `"screenshot"` dengan confidence tinggi, pattern random.
**Penyebab:** Label set ambiguous atau overlapping. Atau label sangat di luar distribusi training data (misal medical imagery yang CLIP tidak familiar).
**Solusi:** Review labels - pastikan mutually distinguishable dalam visual features. Tambah konteks (`"an outdoor photo"` vs `"an indoor photo"`). Untuk domain niche, CLIP limited - butuh domain-specific model.

### Problem: CUDA out of memory saat pakai GPU
**Gejala:** Error `torch.cuda.OutOfMemoryError: CUDA out of memory`.
**Penyebab:** batch_size terlalu besar untuk VRAM GPU.
**Solusi:** Turunkan batch_size ke 8 atau 4. Close aplikasi lain yang pakai GPU (game, browser dengan hw accel). `nvidia-smi` untuk cek VRAM.

### Problem: Embedding cache file jadi sangat besar
**Gejala:** `embeddings.npy` lebih besar dari folder gambar original.
**Penyebab:** Per embedding 512 floats × 4 bytes = 2KB per image. Untuk 100k images = 200MB. Plus overhead. Normal kalau banyak.
**Solusi:** Kalau space concern, set `cache_image_embeddings: false`. Trade-off: re-run labels berbeda butuh re-encode semua image (slow).

### Problem: Hasil inconsistent antar run dengan config sama
**Gejala:** Dua run identik, order sort gambar berbeda, beberapa score agak berbeda.
**Penyebab:** Floating point non-determinism di CUDA (minor). CPU deterministic.
**Solusi:** Kalau reproducibility kritis, paksa `device: cpu`. Set `torch.use_deterministic_algorithms(True)` di config advanced.

### Problem: "Tokenizer error" saat labels panjang
**Gejala:** Error saat label seperti `"this is a very long descriptive sentence about a photo ..."`.
**Penyebab:** CLIP text encoder limit 77 token. Label terlalu panjang truncated atau error.
**Solusi:** Keep label <15 kata. Kalau butuh lebih descriptive, pecah jadi multiple label shorter.

### Problem: Model cache corrupt setelah power outage
**Gejala:** Error load model, safetensors invalid signature.
**Penyebab:** Write interrupted, file partial.
**Solusi:** Delete folder `~/.cache/huggingface/hub/models--laion--CLIP-ViT-B-32-laion2B-s34B-b79K/` dan re-download.

### Problem: Threshold filter nol hasil meski confidence terlihat ada
**Gejala:** Slider threshold 0.3, expect banyak match, tapi grid kosong.
**Penyebab:** Softmax across all labels - kalau Anda punya 20 label, max individual confidence average ~0.05. 0.3 terlalu tinggi.
**Solusi:** Turunkan threshold proporsional (0.3 / 20 × 5 ≈ 0.075). Atau pakai raw cosine similarity instead of softmax (toggle di advanced).

### Problem: Karakter non-ASCII di label tidak ter-encode
**Gejala:** Label dengan karakter Indonesia aksara lain rendered sebagai `???`.
**Penyebab:** Tokenizer BPE CLIP berbasis byte-level, seharusnya handle semua UTF-8. Kalau gagal, biasanya issue di UI input sanitization.
**Solusi:** Update PyScrapr. Test label via API langsung bypass UI. Untuk interim, pakai transliterasi Latin.

### Problem: Filter chip tidak berfungsi setelah refresh browser
**Gejala:** Klik chip, grid tidak update, atau error console.
**Penyebab:** State client-side hilang saat refresh, hasil tidak re-fetch dari backend.
**Solusi:** Refresh full dari History → buka job tersebut. Kalau persist, cek browser console untuk error spesifik, report sebagai bug.

## FAQ

**Q: Apakah model bisa train ulang dengan data saya?**
A: CLIP di PyScrapr adalah pretrained, zero-shot only. Fine-tuning butuh infrastruktur ML (GPU, label data) yang di luar scope tool ini. Untuk custom domain, pertimbangkan Roboflow atau fine-tune external lalu pakai via API.

**Q: Berapa akurasi CLIP untuk tugas umum?**
A: Benchmark ImageNet zero-shot: ~63% top-1 accuracy untuk ViT-B/32, ~75% untuk ViT-L/14. Real-world tergantung banget ke label design dan domain - bisa 90%+ untuk task sederhana, 50% untuk challenging.

**Q: Apakah aman memproses gambar privat/sensitif?**
A: Ya - semua processing lokal, tidak ada data dikirim keluar (setelah model downloaded). Model cache tersimpan di komputer Anda saja.

**Q: CLIP bisa detect object spesifik seperti face?**
A: CLIP bukan object detector - dia classify whole image. Untuk face/object detection, butuh model berbeda (YOLO, MediaPipe). Roadmap PyScrapr Phase 4 include object detection module.

**Q: Bagaimana cara ukur label quality?**
A: Jalankan pada 100 manually labeled ground truth, hitung precision/recall. UI belum expose metric ini - WIP. Sementara, export CSV dan compute manual di spreadsheet.

**Q: Bisa klasifikasi video?**
A: Tidak langsung - CLIP image-only. Workaround: extract keyframe via Pipeline Video Frame Extractor, klasifikasi keyframe, aggregate score ke video level.

**Q: Ada model lain selain CLIP di roadmap?**
A: Ya - Phase 4 rencana tambah: BLIP untuk image captioning, Whisper untuk audio transcription, embedding models untuk similarity search lokal.

**Q: Apa beda OpenCLIP dengan OpenAI CLIP original?**
A: OpenCLIP replikasi dan ekstend CLIP dengan data open (LAION). Generally akurasi comparable atau sedikit lebih baik karena dataset lebih besar. Lisensi open-source, sedangkan OpenAI weights original tidak clear commercial license.

**Q: Bisa pakai GPU AMD (ROCm)?**
A: PyTorch punya ROCm build tapi belum diuji extensive di PyScrapr. Theoretically works di Linux dengan ROCm toolkit. Di Windows AMD, fall back ke CPU.

**Q: Cache model bisa di-share antar komputer?**
A: Ya - copy folder `~/.cache/huggingface/hub/` ke komputer lain, tool akan detect dan skip download. Useful untuk deploy ke air-gapped environment.

## Keterbatasan

- Hanya classification, bukan detection/segmentation.
- Tidak bisa detect fine-grained detail (breed anjing spesifik, model mobil exact).
- Bias terhadap English - label Indonesia akurasi lebih rendah.
- Tidak support video native (butuh preprocessing).
- Confidence score tidak calibrated - tidak bisa dibanding absolute.
- CPU inference lambat untuk batch besar (~1s/image).
- Model weights 350MB-1.7GB, butuh space dan first-run download time.
- Tidak ada fine-tuning in-app (zero-shot only).
- Performance pada domain niche (medical, satellite, industrial) bisa poor.
- Limit 77 token per label (batas CLIP text encoder).

## Related docs

- [Image Harvester](image-harvester.md) - input utama untuk AI Tagger
- [Media Downloader](media-downloader.md) - klasifikasi thumbnail video
- [Pipeline](/docs/utilities/pipeline.md) - auto-organize by label hasil
- [History](../system/history.md) - track dan compare classification runs
- [OpenCLIP GitHub](https://github.com/mlfoundations/open_clip) - dokumentasi model upstream
- [HuggingFace model card](https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s34B-b79K) - detail weights dan benchmark
