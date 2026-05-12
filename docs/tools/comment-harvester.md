# Comment Harvester

> Comment Harvester adalah tool tier P11 di PyScrapr untuk ekstrak komentar plus reply tree dari YouTube, Reddit, dan forum umum. Anda paste URL video YouTube, thread Reddit, atau forum thread (vBulletin, XenForo, Discourse, phpBB), tool akan fetch semua komentar termasuk reply nested sampai depth 10, render dalam tree view yang bisa di-collapse, dan opsional kasih sentiment score per komentar (positif/netral/negatif) via Ollama lokal. Hasil bisa di-filter by author atau text, sort by upvote/newest/depth, dan export ke CSV flat. Cocok untuk riset opini publik atas brand, monitor Reddit thread tentang produk Anda, kompetitor feedback analysis, marketing insight dari komen viral, atau penelitian akademik thread analysis.

## Apa itu Comment Harvester

Comment Harvester menjawab kebutuhan: gimana caranya saya baca seribu komentar secara terstruktur tanpa scroll manual selama berjam-jam? UI native YouTube atau Reddit di-design untuk konsumsi linear, bukan analisis. Anda scroll, baca satu komen, lupa konteks komen 50 sebelumnya, lupa apakah reply yang ini bagian dari thread mana. Comment Harvester ubah komentar jadi data terstruktur: tree dengan parent-child relationship eksplisit, metadata per node (author, timestamp, upvote count), dan filter/sort/search yang biasanya tidak ada di UI native.

Positioning di sidebar Tools (warna grape, route `/comments`, ikon balon chat). Tool ini tidak membaca komentar private, group tertutup, atau konten yang butuh login khusus. Hanya komentar publik yang bisa di-access tanpa auth (yang juga bisa Anda baca dengan browser biasa). Beda dengan scraper YouTube atau Reddit yang fokus konten utama (video metadata, post body), Comment Harvester fokus eksklusif ke komentar.

Engine berbeda per platform:

- **YouTube**: pakai `yt-dlp` dengan flag `getcomments=True`. yt-dlp handle YouTube internal API yang complex, return top-level + replies dalam struktur yang konsisten.
- **Reddit**: pakai public `.json` endpoint (append `.json` ke URL thread). Reddit kasih kita JSON tree built-in dengan field `replies` recursive. Tool parse dengan `depth=10` max.
- **Forum generic**: pakai BeautifulSoup dengan 6 selector triples untuk vBulletin, XenForo, Discourse, phpBB, NodeBB, dan generic forum. Best-effort flat (tree relationship tidak selalu eksplisit di forum).

> [!NOTE]
> Comment Harvester tidak scrape DM, komentar private, atau konten di balik paywall. Hanya komen publik. Lihat section Etika untuk detail GDPR / privacy.

## Platform yang didukung

| Platform | Coverage | Tree | Metadata |
|----------|----------|------|----------|
| YouTube (video) | Full komen + replies (max 10000 default) | Yes (parent-child eksplisit) | author, timestamp, upvote, is_pinned, is_creator_reply |
| Reddit (thread) | Full komen + replies (depth 10) | Yes (recursive) | author, timestamp, upvote, score, awards, is_OP |
| Discourse forum | Full thread post-by-post | No (flat per topic) | author, timestamp, like_count |
| vBulletin | Full thread | No (flat) | author, timestamp, post_count |
| XenForo | Full thread | No (flat) | author, timestamp, reaction_score |
| phpBB | Full thread | No (flat) | author, timestamp |
| NodeBB | Full thread | Yes (limited 2 levels) | author, timestamp, votes |
| Generic forum | Best effort | No | author (kalau ada), timestamp (kalau ada) |

Generic selector triples adalah list (container selector, author selector, text selector) yang dicoba berurutan. Tool stop di yang pertama yang return jumlah match masuk akal (lebih dari 3 post).

## Cara pakai

Buka menu **Comment Harvester** di sidebar Tools (warna grape, ikon balon chat). Halaman terbagi: form input di atas, tree view komentar di tengah, panel filter + sort + export di kanan.

### Langkah 1: Paste URL

1. Field `URL` di header. Format apa saja diterima.
   - YouTube: `https://youtube.com/watch?v=...`, `youtu.be/...`, atau channel page tidak (perlu URL video spesifik).
   - Reddit: `https://reddit.com/r/<sub>/comments/<id>/<slug>` atau short `redd.it/<id>`.
   - Forum: URL thread spesifik (bukan board index).
2. Tool auto-detect platform dari hostname dan path. Kalau tidak ter-detect (custom forum), pilih manual dari dropdown **Platform**.
3. Atur opsi:
   - **Max comments**: cap total komentar yang di-fetch. Default 1000, max 10000.
   - **Max depth**: untuk Reddit, batas kedalaman reply tree. Default 10.
   - **Include sentiment**: toggle on untuk run sentiment scoring (perlu Ollama running, lihat section bawah).
4. Klik **Harvest**.

### Langkah 2: Tunggu progress

Job spawn di background, progress streaming via SSE. Bar progress menunjukkan jumlah komentar yang sudah di-parse, ETA berdasarkan rate. Untuk YouTube 1000 komentar biasanya 1-3 menit. Reddit lebih cepat (5-30 detik) karena single API call. Forum bervariasi.

### Langkah 3: Eksplorasi tree

Hasil muncul sebagai recursive `CommentCard` di panel tengah. Setiap card menampilkan:

- Avatar author + nama + (badge OP / Creator kalau applicable)
- Timestamp relatif (`3 hari lalu`, `2 jam lalu`)
- Body komentar (text + link auto-detect)
- Upvote count (kalau ada)
- Tombol Reply expand/collapse (kalau ada children)
- Badge sentiment (kalau sentiment scoring on): hijau positif, kuning netral, merah negatif

Klik tombol di pojok kanan card untuk collapse seluruh subtree. Click ulang untuk expand. Useful untuk navigate thread besar di Reddit.

### Langkah 4: Filter, sort, search

Panel kanan punya control:

- **Search**: textbox, search substring case-insensitive di text dan author. Real-time filter.
- **Filter by author**: dropdown multi-select dengan top 20 author by jumlah komen.
- **Sort**: by upvote desc (default), newest first, oldest first, depth (shallow first).
- **Min sentiment**: slider -1 sampai +1 (kalau sentiment scoring aktif). Hanya tampilkan komen dengan sentiment di atas threshold.

Filter berlaku visual saja (tree tetap utuh di state). Reset filter via tombol clear.

### Langkah 5: Export

Klik tombol **Export CSV** untuk download flat list. Kolom: `id`, `parent_id`, `depth`, `author`, `timestamp`, `text`, `upvotes`, `sentiment_score`, `sentiment_label`. Cocok untuk Excel atau Pandas analysis.

## Sentiment scoring

Sentiment scoring optional, opt-in via toggle di form. Backend pakai Ollama lokal (model default `llama3.2:3b`, configurable).

### Setup Ollama

1. Install Ollama dari [ollama.com](https://ollama.com) (cek [AI Extract docs](/docs/utilities/ai-extract.md) untuk panduan setup lengkap).
2. Pull model: `ollama pull llama3.2:3b` (atau model lain yang Anda preferred).
3. Pastikan Ollama service running di `localhost:11434`.
4. Di PyScrapr Settings, set `ollama_endpoint` dan `comment_sentiment_model`.

### Cara kerja batch processing

Komentar dikirim ke Ollama dalam batch 10 per call untuk efisiensi. Tiap call return array score (-1 sampai +1) plus label (`positive` / `neutral` / `negative`). Hasil di-cache pakai hash text komentar, jadi kalau Anda re-harvest URL yang sama, komen yang sama tidak perlu di-score ulang.

Prompt template:

```
Analyze sentiment of these comments. Return JSON array.
Each item: {id, score, label}.
score range: -1 (very negative) to +1 (very positive).
label: positive/neutral/negative.

Comments:
1. <text 1>
2. <text 2>
...
```

### Trade-off performance

| Mode | Speed | Use case |
|------|-------|----------|
| Sentiment off | 30 dtk untuk 1000 komen YouTube | Quick browse, tree exploration |
| Sentiment on (3B model) | +2-5 menit untuk 1000 komen | Pattern detection, audience mood |
| Sentiment on (7B model) | +5-15 menit untuk 1000 komen | Higher accuracy, akademik |

> [!TIP]
> Untuk first exploration, jalankan tanpa sentiment dulu. Kalau Anda decide butuh analisis mood, re-run dengan sentiment on. Cache make re-run cepat untuk komen yang sama.

## Tree view UI

Tree view di-render dengan komponen React `CommentCard` recursive. Tiap level reply geser kanan dengan indentation 24px. Garis vertikal connector menunjukkan parent-child relationship visual.

Behavior interaktif:

- **Collapse subtree**: klik chevron kiri header card. Subtree fold, badge menunjukkan "N hidden replies". Click ulang untuk expand.
- **Collapse semua reply**: tombol di toolbar atas, toggle semua subtree.
- **Highlight author**: klik nama author, semua komen oleh author yang sama di-highlight kuning.
- **Permalink**: klik timestamp, copy permalink ke clipboard (untuk Reddit/YouTube, link ke komen spesifik).
- **Expand all by default**: di Settings, atur preference default expand atau collapse.

Tree besar (5000+ komen) di-render dengan virtualization (react-virtuoso) supaya scroll smooth. Indikator "Loading more..." muncul kalau Anda scroll cepat ke posisi yang belum di-render.

## Filter, sort, search

### Search

Search box pakai substring case-insensitive. Search dilakukan di text dan author. Tidak ada regex search di UI (gunakan export CSV lalu grep manual kalau perlu).

### Filter author

Dropdown multi-select. Tool calculate top 20 author by jumlah komen di hasil harvest. Pilih satu atau lebih untuk show only komen dari author tersebut. Useful untuk track thread dengan beberapa kontributor dominan, atau focus pada OP + creator reply.

### Sort

| Opsi | Kriteria |
|------|----------|
| Upvotes (desc) | Komen dengan upvote tertinggi di atas |
| Newest first | Timestamp terbaru di atas |
| Oldest first | Timestamp terlama di atas |
| Depth (shallow) | Top-level dulu, baru reply |
| Sentiment (pos to neg) | Positif di atas, negatif bawah |

### Search + filter + sort kombinasi

Bisa kombinasi semua. Contoh: sort by upvote desc + filter author = "JohnDoe" + search "great" = lihat komen most-liked dari JohnDoe yang mengandung kata "great".

## Contoh skenario

### 1. Riset opini publik atas brand di YouTube comment

Tim marketing brand minuman mau tahu sentiment audience terhadap kampanye iklan baru yang viral di YouTube (1 juta views, 5000 komen).

Setup: paste URL video, max comments 5000, sentiment on. Hasil setelah 15 menit: tree dengan 5000 komen + sentiment score per komen. Filter sentiment slider ke "below -0.3" (negatif): muncul 800 komen. Read top 50 (sort by upvote): tema dominan adalah komplain musik iklan terlalu loud. Action: brief tim audio untuk versi v2 dengan musik soften.

### 2. Monitor Reddit thread untuk produk Anda

Startup B2B SaaS launch produk di r/startups, dapat 200 komen dalam 6 jam. Founder mau respond cepat ke komen substansial, tapi capek scroll Reddit UI yang noisy.

Setup: paste URL Reddit thread, max comments 500, sentiment on. Tree view tampilkan struktur thread jelas. Filter sentiment "above 0.3" untuk komen positif (validation untuk testimonial dengan izin). Filter "below -0.3" untuk negatif (objection yang perlu di-address proaktif). Plus search "pricing" untuk komen tentang harga (concern paling sering di r/startups). Founder reply prioritized di komen high-engagement (upvote desc) + critical (sentiment negatif) dalam 2 jam, raise community sentiment overall.

### 3. Kompetitor feedback analysis dari Trustpilot atau forum review

Kompetitor punya thread review di forum gadget besar. 50 page thread, mungkin 500 komen tentang produk mereka. Anda mau tahu pain point yang paling sering disebut.

Setup: pilih platform "Generic forum", paste URL thread page 1. Tool auto-paginate sampai max comments tercapai. Sentiment on. Hasil flat list (forum generic tidak punya tree). Sort by sentiment ascending: 100 komen paling negatif. Manual cluster dengan eye: 30 komplain battery life, 20 keluhan customer support, 15 keluhan harga, 10 keluhan packaging. Anda design pitch produk Anda highlight kelebihan di area itu.

### 4. Marketing insight dari komen viral

Influencer post review produk lifestyle. 500 komen dalam 24 jam. Anda brand strategist, mau identifikasi tema komentar yang nyambung dengan messaging brand Anda.

Setup: paste URL Instagram via Reddit cross-post atau YouTube version (Instagram comments tidak supported langsung), sentiment on. Filter positive sentiment + sort by upvote. Read top 100, tag manual tema yang muncul: "konsep minimalis" 40 mentions, "value for money" 25 mentions, "color palette" 18 mentions. Brief copywriter pakai phrasing yang resonansi dengan audience asli.

### 5. Akademik: thread analysis Reddit

Mahasiswa S2 sosiologi research wacana publik tentang topik tertentu di r/indonesia. 10 thread populer, total ~2000 komen.

Setup: harvest 10 URL satu per satu, export CSV per thread. Concat di Pandas, total dataset 2000 baris dengan kolom text, author, timestamp, sentiment_score. Analisis frekuensi term (Python with NLTK), co-occurrence, sentiment distribution. Hasil masuk thesis chapter sebagai data primer dengan citation: "Data dikumpulkan via PyScrapr Comment Harvester pada tanggal X dengan parameter Y". Reproducible.

> [!NOTE]
> Untuk research akademik, simpan parameter run (URL list, max_comments, max_depth, tanggal, versi PyScrapr). Bagian dari methodology section.

## Tips

- **Mulai dari Reddit kalau bisa.** Reddit JSON API stabil dan tree-nya clean. Hasil bagus untuk first experiment.

- **YouTube butuh patient.** yt-dlp navigate banyak pagination internal. 5000 komen bisa 5-10 menit. Jangan refresh halaman, biarkan jalan.

- **Forum generic dicek manual hasilnya.** Selector tidak match-mate untuk semua forum custom. Spot check 5-10 entries pertama, kalau author atau text terlihat aneh, mungkin selector salah dan Anda butuh fallback ke manual scraping pakai [Selector Playground](/docs/utilities/playground.md).

- **Sentiment scoring lebih akurat di bahasa Inggris.** Model 3B umum dilatih dominan English. Kalau komen Anda bahasa Indonesia, accuracy turun. Coba model multilingual (`qwen2.5:7b`) untuk Indonesian content.

- **Export CSV untuk arsip.** Tool tidak simpan harvest permanen by default (state lost saat refresh). Export CSV setelah harvest besar.

- **Re-harvest periodik.** Komen baru terus muncul. Re-run harvest URL yang sama tiap minggu untuk longitudinal analysis. Cache sentiment memastikan komen lama tidak di-score ulang.

## Troubleshooting

### Problem: YouTube harvest stuck di 10% selama lama

**Gejala:** Progress bar bergerak lambat di awal, lalu stuck.
**Penyebab:** YouTube rate limit yt-dlp, atau IP Anda flagged.
**Solusi:** Tunggu 5 menit, retry. Aktifkan proxy rotation di Settings kalau sering kena. Kurangi max_comments untuk first try.

### Problem: Reddit return JSON kosong

**Gejala:** Tool report 0 komentar padahal thread punya 200 komen.
**Penyebab:** Thread di-archive (lebih dari 6 bulan, Reddit kunci komentar), atau thread sensitif yang butuh login.
**Solusi:** Cek URL di browser tanpa login. Kalau Anda lihat komen tanpa login, harusnya tool juga bisa. Kalau butuh login, tool tidak handle auth (by design).

### Problem: Forum selector tidak match, hasil 0

**Gejala:** Generic forum return 0 atau hanya 1-2 post.
**Penyebab:** Selector triples built-in tidak cover forum custom Anda.
**Solusi:** Buka [Selector Playground](/docs/utilities/playground.md), uji selector manual di halaman thread. Setelah dapat selector yang work, file issue GitHub dengan domain forum + selector, akan di-tambahkan ke built-in list rilis berikutnya.

### Problem: Sentiment scoring sangat lambat

**Gejala:** Setelah harvest selesai, sentiment processing jalan 30+ menit.
**Penyebab:** Model 7B atau lebih besar dengan CPU only, 1000+ komen.
**Solusi:** Switch ke model lebih kecil (`llama3.2:3b`), atau aktifkan GPU acceleration di Ollama, atau turunkan max_comments untuk first pass.

### Problem: Tree view lag saat scroll thread besar

**Gejala:** UI lag scroll thread dengan 5000+ komen.
**Penyebab:** Virtualization tidak optimal, atau browser kehabisan memory.
**Solusi:** Collapse subtree top-level non-relevant. Atau export CSV dan analisis di tool lain (Excel, Pandas).

## Etika

> [!IMPORTANT]
> Komentar publik bukan berarti "data Anda boleh apa-apa". Patuhi aturan dasar berikut.

- **Hanya komen publik.** Tool ini hanya akses URL publik yang bisa di-view tanpa login. Tidak ada bypass auth, tidak ada DM scrape, tidak ada private group.

- **Jangan harvest profile pribadi.** Komen di thread = data publik. Tapi profile author (alamat email yang tampil, IG handle, dll) tetap PII (Personal Identifiable Information). Aggregating profile data per author dari berbagai thread untuk profiling individual = mendekati pelanggaran privacy. Hindari.

- **GDPR / PDP awareness.** Kalau Anda Eropa atau audience Eropa, GDPR berlaku ke processing komentar yang mengidentifikasi individu. Untuk research dengan data dari user EU, Anda butuh basis legal (consent, legitimate interest yang well-documented, atau anonymization). Untuk Indonesia PDP sejak 2024, prinsip serupa. Konsultasi DPO kalau commercial use.

- **Akademik = anonymize untuk publikasi.** Untuk thesis atau paper, anonymize username di kutipan. Author asli jangan di-publish kecuali figure publik dalam kapasitas publik.

- **Jangan stalk individu.** Repeat harvest komen dari satu user spesifik di berbagai thread = harassment territory. Tool ini untuk corpus analysis, bukan personal targeting.

- **Hormati DMCA / Terms of Service platform.** YouTube ToS membatasi scraping otomatis di skala besar. Tool ini personal scale untuk personal research. Jangan resell data, jangan publish dataset full komen sebagai data product tanpa license dari platform.

- **Marketing use case: transparant.** Kalau Anda brand marketer pakai insight dari Comment Harvester untuk respond ke komen, jujur saat reply ke user. Jangan pretend "kebetulan lewat" kalau Anda systematic monitoring.

## Pengaturan teknis

| Key | Tipe | Default | Keterangan |
|-----|------|---------|------------|
| `comment_harvester_enabled` | boolean | true | Master switch tool |
| `comment_max_comments_default` | integer | 1000 | Default cap per harvest |
| `comment_max_depth_default` | integer | 10 | Default depth Reddit |
| `comment_sentiment_enabled_default` | boolean | false | Default state toggle sentiment |
| `comment_sentiment_model` | string | `"llama3.2:3b"` | Model Ollama untuk sentiment |
| `comment_sentiment_batch_size` | integer | 10 | Komen per batch ke Ollama |
| `comment_youtube_user_agent` | string | yt-dlp default | UA untuk YouTube |
| `comment_request_timeout_seconds` | integer | 60 | Timeout per harvest call |
| `comment_cache_retention_days` | integer | 30 | Retain sentiment cache |

## Related docs

- [AI Extract (Ollama)](/docs/utilities/ai-extract.md) - setup Ollama yang dipakai sentiment scoring
- [Selector Playground](/docs/utilities/playground.md) - debug selector untuk forum generic
- [Media Downloader](/docs/tools/media-downloader.md) - download video YouTube source dari URL yang sama
- [Settings](/docs/system/settings.md) - semua flag Comment Harvester
- [Custom Pipeline](/docs/utilities/pipeline.md) - transformasi hasil CSV ke format custom
