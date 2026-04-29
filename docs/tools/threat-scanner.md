# Threat Scanner

> Threat Scanner adalah tool static malware analysis di tier P8 PyScrapr yang memeriksa file tanpa pernah mengeksekusinya. Bayangkan: freelancer terima email "Marketing Director PT XYZ", attachment `brief_klien.txt` tampak tidak berbahaya, double-klik, dan ternyata file itu shortcut PowerShell yang drop ransomware di Documents. Threat Scanner dirancang untuk momen seperti itu: geser file ke drop zone, tunggu 10 detik, baca verdict. Tool ini mendeteksi 11 kelas ancaman (extension spoofing, zip bomb, PDF berisi JavaScript, macro Office, steganografi, LNK tersembunyi, CHM weaponized, ISO container, SVG dengan JS, nested archive, packed executable), menjalankan YARA rules, menganalisis struktur internal (PE, PDF, OLE), dan optional cross-check hash ke VirusTotal + MalwareBazaar. Semua analysis static, file tidak pernah dijalankan, dan hash lookup hanya mengirim SHA256, tidak pernah isi file.

## Apa itu Threat Scanner

Threat Scanner adalah jawaban PyScrapr untuk pertanyaan sederhana: "File ini aman dibuka atau tidak?". Jawaban yang biasanya butuh upload ke VirusTotal (yang menyerahkan konten ke cloud pihak ketiga), instalasi antivirus berat, atau pengetahuan reverse engineering, sekarang tersedia offline dengan risk score 0-100 dan breakdown per-indikator.

Positioning tool ini berbeda dari antivirus realtime. Defender, Kaspersky, Bitdefender bekerja behavioral dan signature-based, memantau proses yang running. Threat Scanner bekerja purely static: baca byte di disk, hitung entropy, cek magic bytes, parse struktur internal (PE header, PDF object tree, OLE stream), jalankan YARA, tarik kesimpulan tanpa pernah menjalankan kode target. Dua pendekatan komplementer, bukan substitutif. Antivirus untuk proteksi realtime. Threat Scanner untuk triage cepat sebelum Anda memutuskan membuka file.

Keuntungan offline signifikan. Upload ke VT web interface mengirim file fisik ke Google dan partner vendor. Untuk file publik fine, untuk brief klien rahasia, contract, NDA, atau source code internal, itu data leak nyata. PyScrapr Threat Scanner jalan sepenuhnya di mesin Anda. Hanya saat VT hash lookup aktif, nilai SHA256 (bukan isi file) dikirim ke API publik VT.

Tool ini melayani tiga audience: freelancer dan agency yang terima file dari klien asing, tim QA yang verifikasi output downloader, dan power user yang ingin kontrol atas file masuk. Verdict bisa dibaca dalam 5 detik, dengan rationale per-indikator kalau butuh drill down.

## Setup

Threat Scanner butuh beberapa dependency tambahan yang belum terpasang di installation default PyScrapr. Di PowerShell, aktifkan venv backend PyScrapr, lalu jalankan:

```powershell
pip install python-magic-bin yara-python oletools pymupdf pefile py7zr rarfile
```

Khusus Windows, Anda butuh `python-magic-bin` (yang membundle libmagic.dll), bukan `python-magic`. Library `python-magic` di Windows mengharuskan Anda install libmagic via MSYS2 / Cygwin secara manual, yang merepotkan. Package `python-magic-bin` sudah include DLL pre-built jadi langsung work.

Untuk Linux dan Mac, gunakan `python-magic` biasa dan install libmagic dari package manager sistem:

```bash
# Ubuntu / Debian
sudo apt-get install libmagic1

# macOS
brew install libmagic
```

Library `yara-python` sudah include binary compile di wheel modern (versi 4.5+), jadi biasanya langsung terpasang. Kalau pip compile dari source dan gagal di Windows, install Microsoft Visual C++ Build Tools dulu, atau pakai pre-built wheel dari `.whl` file di GitHub releases `yara-python`.

Restart backend setelah instalasi. Buka Settings, navigasi ke section Threat Scanner, aktifkan flag yang Anda butuhkan (hash lookup, auto-scan, quarantine). Tool sudah siap pakai.

> [!NOTE]
> Semua dependency di atas bersifat optional di level runtime. Kalau salah satu tidak terpasang (misal `pefile` missing karena Anda lupa install), Threat Scanner tidak crash. Analyzer yang butuh module tersebut akan skip dengan log warning, scanner tetap jalan dengan analyzer yang tersedia. Anda bisa mulai dengan install minimal (`python-magic-bin` + `yara-python`) lalu tambah yang lain saat butuh.

## Mode input

Threat Scanner menerima input via tiga mode berbeda yang menutup hampir semua skenario realistis.

### 1. File upload (drag & drop / file picker)

Mode paling umum. Buka tab Pindai, drag file dari explorer ke drop zone (atau klik untuk buka file picker), tool upload file ke endpoint `POST /api/threat/scan/upload` (multipart), simpan sementara di `data/temp/threat_uploads/`, jalankan scan, lalu auto-delete file temp setelah selesai. Maksimum ukuran file default 500 MB, bisa dinaikkan di Settings.

Mode ini cocok saat file sudah ada di mesin Anda sebagai attachment email, download dari chat Telegram/WhatsApp, atau hasil export dari tool lain. Anda tidak perlu tahu path absolutnya.

### 2. Local path (file atau folder di backend)

Isi field `path` dengan path absolut ke file atau folder di mesin yang menjalankan backend PyScrapr. Kalau Anda isi path folder, tool akan iterate semua file di dalamnya (recursive kalau checkbox recursive aktif). Endpoint: `POST /api/threat/scan/path` dengan body `{"path": "C:/Users/you/Downloads/suspicious_folder", "depth": "standard"}`.

Mode ini ideal untuk audit folder yang sudah ada di disk Anda (misal folder Downloads, folder sharing tim, folder hasil Site Ripper). Tidak ada upload, scan langsung dari disk, jadi jauh lebih cepat untuk file besar.

### 3. Auto-scan (triggered by downloader completion)

Kalau Anda aktifkan setting `threat_auto_scan_downloads`, EventBus PyScrapr akan listen job completion dari Media Downloader, Site Ripper, dan Image Harvester. Saat job selesai, Threat Scanner otomatis scan folder output job tersebut, tanpa Anda harus klik apa-apa. Hasil scan tercatat di History dengan `type=THREAT_SCAN` dan linked ke job asalnya.

Mode ini adalah killer feature untuk workflow yang mengandalkan downloader ke sumber tidak terpercaya. Download 200 gambar dari forum random via Image Harvester? Auto-scan akan flag kalau ada yang ternyata `.jpg.exe` atau SVG dengan embedded JS.

## Alur kerja

Dari input sampai verdict, alur interaksi tool cukup ringkas.

1. Buka PyScrapr, navigasi ke menu **Threat Scanner** di sidebar (atau shortcut `Ctrl+8`). Halaman terbuka dengan tab Pindai aktif.

2. Pilih input: drag file ke drop zone, paste path absolut di field path, atau pilih folder via folder picker.

3. Pilih scan depth: `Quick`, `Standard`, atau `Deep`. Default `Standard`. Tradeoff detail di section berikut.

4. (Opsional) Aktifkan toggle `Recursive` kalau Anda scan folder dan ingin tool masuk ke subfolder.

5. (Opsional) Aktifkan toggle `Hash reputation` kalau Anda ingin cross-check SHA256 ke VirusTotal + MalwareBazaar. Default off untuk mode offline pure.

6. Klik tombol **Pindai**. Backend akan spawn worker thread, dispatch file ke analyzer chain yang relevan (berdasarkan magic bytes), kumpulkan indikator, hitung risk score, return verdict.

7. Hasil muncul di panel kanan sebagai card per-file. Setiap card menampilkan: nama file, SHA256 hash, verdict badge (clean / suspicious / dangerous dengan warna), risk score 0-100, dan list indikator yang di-trigger.

8. Klik card untuk expand detail: magic bytes aktual, entropy value, YARA rule yang match (kalau ada), output PDF/Office/PE analyzer, dan aksi (download report JSON, move to quarantine, delete, ignore).

9. (Opsional) Stream real-time progress via SSE endpoint `GET /api/threat/scan/events/{job_id}` kalau Anda scan folder besar. UI otomatis subscribe ke SSE saat scan folder dimulai.

## Kategori ancaman yang dideteksi

Threat Scanner mencakup 11 kelas ancaman. Tabel di bawah meringkas setiap kategori dengan metode deteksi, severity default, dan contoh nyata.

| # | Ancaman | Metode deteksi | Severity | Contoh dunia nyata |
|---|---------|----------------|----------|--------------------|
| 1 | Extension spoofing | Magic bytes (python-magic) vs extension | Tinggi | `invoice.pdf.exe` dengan icon PDF Adobe, yang sebetulnya PE executable |
| 2 | Zip bomb | Compression ratio check (extracted size / compressed size) | Tinggi | File 42 KB yang expand jadi 4.5 PB, crash disk saat di-extract |
| 3 | Malicious PDF | Keyword scan (JavaScript, OpenAction, Launch, EmbeddedFile) + pymupdf | Tinggi | PDF dengan `/OpenAction /JS` yang fetch payload dari remote C2 |
| 4 | Office macro auto-exec | olevba parser untuk VBA macro | Tinggi | Excel `.xlsm` dengan AutoOpen subroutine yang decode shellcode |
| 5 | Steganografi / payload high-entropy | Shannon entropy threshold (>7.2 / >7.6) | Sedang | JPG normal dengan appended ZIP di EOF marker, entropy tinggi |
| 6 | LNK shortcut dalam archive | Archive inspection (zipfile / py7zr / rarfile) + extension match | Tinggi | `photos.zip` berisi `readme.txt.lnk` yang jalankan PowerShell encoded |
| 7 | CHM / HLP weaponized | Magic bytes CHM signature + dangerous file dalam container | Tinggi | `helpdoc.chm` dengan embedded HTML yang execute command via CHM vuln |
| 8 | ISO / IMG container | Magic bytes ISO9660 + scan isi container | Tinggi | `order_details.iso` yang mount otomatis di Windows, berisi `.exe` disamarkan |
| 9 | SVG dengan JavaScript | XML parse, cek tag `<script>` dan handler `onload/onerror` | Sedang | SVG profile picture dengan `<script>fetch(...)` untuk CSRF |
| 10 | Nested archive (recursive) | Recursive scan sampai depth 5 | Sedang | ZIP dalam ZIP dalam RAR dalam 7Z untuk evasi scanner sederhana |
| 11 | Packed / obfuscated executable | PE entropy section + pefile analysis | Sedang | `.exe` dengan section `.text` entropy > 7.6 (UPX, Themida, VMProtect) |

Setiap kategori punya set rule internal yang contribute ke risk score. Satu file bisa trigger beberapa kategori sekaligus, dan risk score di-akumulasi (dengan cap per-kategori supaya satu class tidak memonopoli skor).

## Scan depth

Tool menyediakan tiga preset depth yang mengatur tradeoff antara kecepatan dan thoroughness.

| Depth | Waktu / file | Cakupan | Kapan dipakai |
|-------|--------------|---------|---------------|
| Quick | 3-5 detik | Magic bytes, entropy, hash SHA256, basic dispatch per-type | Triage cepat untuk batch besar (scan folder 500 file) atau first-pass check |
| Standard | 10-30 detik | Quick + YARA rules + archive tree + PDF analyzer + Office analyzer | Default untuk file tunggal suspicious atau folder kecil-menengah |
| Deep | 1-5 menit | Standard + recursive archive sampai depth 5 + string extraction + full PE analysis (imports, sections, anomalies) + hash reputation (VT + MalwareBazaar) | File yang sudah flagged suspicious di Quick/Standard dan butuh evidence lebih kuat sebelum eskalasi |

Rekomendasi umum: mulai dengan Quick untuk folder besar, identifikasi file suspect, lalu rerun Deep hanya untuk file yang di-flag. Ini menghemat puluhan menit di folder 1000+ file dibanding langsung Deep semuanya.

> [!TIP]
> Kalau Anda selalu Deep by default, coba benchmark perbedaan verdict antara Quick dan Deep di sample folder Anda. Biasanya 95% file clean di Quick tetap clean di Deep. 5% yang beda adalah file yang butuh depth lebih, dan biasanya yang beneran suspicious. Workflow `Quick filter dulu, Deep untuk hasil positive` memberi speed tanpa sacrifice accuracy.

## Risk scoring

Risk score adalah angka 0-100 yang di-compute dari akumulasi indikator yang trigger pada satu file. Rubrik default:

| Indikator | Kontribusi skor |
|-----------|-----------------|
| Extension spoofing (magic mismatch major, misal `.pdf` tapi PE) | +40 |
| Magic mismatch minor (misal `.jpg` tapi PNG) | +15 |
| Entropy > 7.6 | +20 |
| Entropy > 7.2 (tapi < 7.6) | +10 |
| YARA rule high-severity match | +30 per match, cap total +50 |
| Zip bomb detected | +60 |
| Dangerous file dalam archive (.exe, .ps1, .vbs, .lnk, .chm, .bat, .scr) | +15 per file, cap +30 |
| PDF JavaScript embedded | +20 |
| PDF OpenAction trigger | +15 |
| PDF EmbeddedFile + executable payload | +30 |
| Office VBA macro present | +15 |
| Office VBA auto-exec (AutoOpen / Workbook_Open) | +25 |
| PE suspicious imports (VirtualAllocEx, CreateRemoteThread, WriteProcessMemory) | +15 per import, cap +25 |
| PE packed (section entropy > 7.6) | +15 |
| VirusTotal 5+ engines flag | +50 |
| VirusTotal 1-5 engines flag | +25 |
| MalwareBazaar hash known | +40 |

Total dibatasi maksimum 100. Verdict di-turunkan dari bucket skor:

- **0-29 Clean** (teal badge): tidak ada atau hanya satu-dua indikator ringan. Aman dibuka normal.
- **30-59 Suspicious** (yellow badge): ada pattern mencurigakan tapi tidak konklusif. Butuh inspection manual atau Deep scan follow-up.
- **60-100 Dangerous** (red badge): banyak indikator kuat atau satu indikator very-high (zip bomb, VT hit berat, PE packed dengan suspicious imports). Jangan dibuka, move to quarantine langsung.

> [!IMPORTANT]
> Skor adalah heuristic, bukan judgment mutlak. File installer legitimate sering score 30-50 karena kombinasi PE + high entropy (installer memang packed) + banyak imports. Developer executable yang Anda compile sendiri juga bisa score 20-40. Gunakan verdict sebagai sinyal, bukan keputusan final. Kalau Anda tahu origin file dan tahu apa yang dia lakukan, verdict Suspicious bisa di-accept.

## YARA rules

YARA adalah framework pattern-matching yang sangat populer di komunitas threat intel. Rule adalah file text dengan syntax mirip C yang describe byte pattern, string, dan kondisi boolean untuk klasifikasi malware.

### Bundled rules

PyScrapr ships dengan 5 rule default di `data/yara-rules/bundled/`:

- **suspicious_powershell.yar** - matches base64-encoded PowerShell, IEX DownloadString, bypass execution policy, reflective DLL injection pattern.
- **suspicious_office.yar** - matches VBA auto-exec combined dengan Shell, WScript, atau HTTP request.
- **pdf_suspicious.yar** - matches PDF dengan combine JavaScript + OpenAction + EmbeddedFile.
- **packer_detection.yar** - matches signature UPX, Themida, VMProtect, ASPack, Morphine.
- **generic_malware_strings.yar** - matches string umum di malware: `cmd.exe /c`, `powershell -enc`, `certutil -urlcache`, pastebin.com URL, bitly URL di binary.

Setiap rule punya metadata severity (`low`, `medium`, `high`) yang menentukan bobot skor saat match.

### Tambah custom rule

Rule user kustom diletakkan di `data/yara-rules/user/`. Semua file `.yar` atau `.yara` di folder ini akan di-load saat startup dan setiap kali Anda klik tombol **Reload** di tab Aturan YARA. Contoh rule kustom untuk detect specific threat:

```yara
rule my_custom_ransomware_strings
{
    meta:
        author = "me"
        description = "Detect strings specific to XYZ ransomware campaign"
        severity = "high"

    strings:
        $ransom_note = "YOUR FILES HAVE BEEN ENCRYPTED"
        $contact = "pay_via_bitcoin_to"
        $extension_marker = ".locked_xyz"

    condition:
        2 of them
}
```

Save ke `data/yara-rules/user/xyz_ransomware.yar`, buka tab Aturan YARA di UI, klik **Reload rules**. Log backend akan print jumlah rule yang ter-load. Kalau ada compile error di rule Anda, error message akan muncul dengan line number yang jelas.

### Reload endpoint

Endpoint `POST /api/threat/rules/reload` trigger reload semua rule tanpa restart backend. Cocok untuk iterative development rule baru: edit `.yar` file, klik Reload, langsung scan test file, lihat hasil match.

## Hash reputation

Untuk file yang ter-identifikasi malware global, hash reputation memberi evidence kuat dengan cross-check ke 2 service publik.

### VirusTotal

VirusTotal adalah aggregator 70+ engine antivirus. Saat Anda enable VT lookup, PyScrapr kirim hanya SHA256 file (32 byte hex string, bukan isi file) ke API `vtapi v3 /files/{sha256}`. Response berisi statistik berapa engine yang flag, kapan pertama kali submitted, dan breakdown per-engine.

Setup API key di Settings: buat akun gratis di virustotal.com, copy API key dari profile, paste ke field `VT API key` di Settings Threat Scanner. API public punya rate limit 4 request per menit, 500 per hari. Tool cache hash lookup result lokal selama 24 jam supaya hash yang sama tidak hit API berulang dalam satu hari.

Interpretasi hasil VT:
- **0 engines flag**: hash tidak dikenal sebagai malware di database global. Tidak ada kontribusi skor.
- **1-5 engines flag**: kemungkinan false positive dari engine yang kurang akurat, atau malware baru yang belum terdistribusi luas. +25 skor.
- **5+ engines flag**: confidence tinggi bahwa file ini malware terkenal. +50 skor.

### MalwareBazaar

MalwareBazaar (dari abuse.ch) adalah database malware sample yang free, no API key required. Endpoint `POST https://mb-api.abuse.ch/api/v1/` dengan query `get_info` + SHA256. Hit di MalwareBazaar = +40 skor.

Default: anonymous mode dengan rate limit 1000 request per hari (lebih dari cukup untuk personal use). Untuk rate limit lebih tinggi (10K+/hari), daftar Auth-Key gratis di `https://bazaar.abuse.ch/login/` lalu masukkan ke Settings: Threat Scanner reputation: MalwareBazaar Auth-Key.

> [!TIP]
> Kalau Auth-Key Anda kadaluarsa, di-revoke, atau salah ketik, request otomatis fallback ke anonymous mode tanpa menampilkan error. Jadi aman saja kalau lupa update key, scan tetap jalan dengan rate limit lebih rendah.

Setting `threat_malwarebazaar_enabled` default true, `threat_virustotal_enabled` default true (butuh key di `threat_virustotal_api_key`).

> [!NOTE]
> Hash lookup sifatnya privacy-preserving. Server VirusTotal dan MalwareBazaar hanya terima nilai SHA256. Mereka tidak bisa reconstruct konten file dari hash itu, dan mereka tidak tahu nama file Anda. Jadi bahkan kalau file Anda confidential (contract, source code), hash lookup aman dilakukan.

## AI Threat Explainer

Threat Scanner menghasilkan list indikator teknis (magic mismatch, entropy 7.78, YARA `packer_detection.UPX`, PE imports `VirtualAllocEx`, dst). Untuk pengguna yang bukan reverse engineer, deretan istilah itu sulit diterjemahkan jadi keputusan praktis. AI Threat Explainer menjembatani gap itu: ia mengambil ringkasan finding dan minta language model menulis penjelasan plain-language, beserta rekomendasi tindakan, dalam bahasa yang Anda pilih.

### Provider yang didukung

Ada tiga provider pluggable, dipilih lewat setting `ai_explain_provider`.

- **DeepSeek** (`deepseek`) - cloud API murah, latensi rendah, kualitas mirip GPT-4 untuk security domain. Butuh `deepseek_api_key`. Estimasi biaya sekitar **$0.0009 per scan** (rata-rata 800 token input + 400 token output di model `deepseek-chat`). 1000 scan kira-kira $0.90.
- **Ollama** (`ollama`) - runtime LLM lokal di mesin Anda, tanpa biaya per call dan tanpa data keluar. Pilih model di setting Ollama (rekomendasi `llama3.2` atau `qwen2.5:7b`). Cocok untuk laptop modern, butuh RAM minimal 8 GB.
- **OpenAI** (`openai`) - GPT-4o-mini default. Butuh `openai_api_key`. Lebih mahal dari DeepSeek tapi kualitas paling konsisten untuk bahasa non-Inggris.

Switch provider tanpa restart, perubahan setting langsung dipakai pada call berikutnya.

### Threshold guard

Setting `ai_explain_threshold` (default `50`) menentukan risk score minimum yang memicu explainer. File dengan score di bawah threshold dianggap clean atau low-risk dan tidak butuh narasi. Tujuannya menghemat biaya API dan menghindari LLM mengarang risk signal palsu untuk file yang aman. Untuk audit ekstra-konservatif, turunkan ke `30`. Untuk paranoid mode kontrol biaya, naikkan ke `70`.

### SHA256 cache

Setiap explanation disimpan di tabel `ai_threat_cache` dengan key SHA256 file + provider + model + bahasa. Saat file dengan hash sama di-scan ulang, cached explanation langsung di-return tanpa hit API. Cache tidak pernah expire otomatis, tapi bisa di-flush manual lewat tombol "Reset cache" di Settings. Manfaat: scan folder yang sama berulang kali (auto-scan output downloader) hanya bayar sekali per file unik.

### Settings walkthrough

1. Buka **Settings** dari ikon gear di navbar.
2. Scroll ke section **AI Threat Explainer**.
3. Toggle `ai_explain_enabled = true`.
4. Pilih `ai_explain_provider`: `deepseek` / `ollama` / `openai`.
5. Tergantung provider, isi credential:
   - DeepSeek: `deepseek_api_key` (dapat dari platform.deepseek.com).
   - OpenAI: `openai_api_key`.
   - Ollama: pastikan service jalan di `http://localhost:11434`, lalu set model name di setting Ollama existing.
6. Set `ai_explain_threshold` sesuai selera (default 50).
7. Set `ai_explain_max_tokens` (default 600) untuk batasi panjang response.
8. Set `ai_explain_language`: `id` (Bahasa Indonesia), `en`, atau kode locale lain.
9. Save. Scan file suspect, expand card-nya, lihat tab "AI Explanation" di samping detail teknis.

### Privacy

Yang dikirim ke provider hanya **string indikator + SHA256 hash + nama file**. Tidak ada konten file yang dikirim. Contoh payload outgoing:

```
File: invoice.pdf.exe
SHA256: a4b1c...
Indicators: extension_spoofing (PE in .pdf), entropy=7.84, yara=UPX, imports=VirtualAllocEx,CreateRemoteThread
VT: 32/70 engines flagged
```

LLM tidak punya akses ke byte file. Ini desain disengaja: explainer beroperasi di layer hasil scan, bukan di file mentah. Untuk file confidential (NDA, source code, dokumen kontrak), tidak ada bocoran selain hash dan list indikator generic. Kalau tetap khawatir, pakai provider Ollama lokal sehingga zero data keluar mesin Anda.

### Disable toggle

Selain master switch `ai_explain_enabled`, ada toggle UI per-scan di card hasil. Anda bisa run scan tanpa explainer dengan uncheck "Enable AI explanation" di form Pindai. Cocok untuk batch besar yang Anda tahu mostly clean - hemat biaya dan waktu. Setting global tetap on, override hanya untuk scan ini.

### Usage tracker

Tab **AI Usage** di halaman Settings menampilkan rolling window 30 hari: jumlah call, token total, cost estimate per provider, dan top 10 file (by hash) yang paling sering minta explanation. Berguna untuk audit budget dan mendeteksi pattern abuse (misal scheduled scan menabrak cache miss berulang karena hash file berubah tiap run).

## Quarantine

Saat Anda identify file dangerous, kadang Anda ingin lebih dari sekadar tidak membukanya: Anda ingin mencegah orang lain atau proses otomatis di sistem Anda membukanya. Quarantine solusinya.

### Enable quarantine

Aktifkan di Settings: `threat_quarantine_enabled = true`. Default false supaya scanner tidak secara agresif memindahkan file user tanpa permission eksplisit.

### Aksi quarantine

Di UI tab Pindai, setiap card file hasil scan punya tombol **Pindah ke Karantina**. Tombol ini call endpoint `POST /api/threat/quarantine` dengan body `{"file_path": "...", "reason": "Verdict Dangerous, 3 YARA matches"}`. Backend akan:

1. Move file dari lokasi asli ke `data/quarantine/<random_id>/`.
2. Di Windows, append `.txt` ke nama file. `malware.exe` jadi `malware.exe.txt`. Tujuannya: mencegah double-click accidental mengeksekusi file (Windows tidak akan jalankan `.exe.txt`).
3. Tulis manifest JSON `manifest.json` di folder quarantine berisi: original_path, original_name, quarantine_timestamp, verdict, risk_score, indicators triggered, reason dari user.
4. Update database dengan entry `QuarantinedFile` yang linkable dari History.

### Restore

Tab **Karantina** di UI list semua file yang pernah di-quarantine dengan metadata lengkap. Kalau Anda ter-quarantine file yang ternyata false positive (installer legitimate misalnya), klik **Restore**. Tool akan move file kembali ke `original_path` (atau ke Downloads kalau path asli sudah tidak ada), remove `.txt` suffix, dan update database.

Endpoint: `POST /api/threat/quarantine/restore/{id}`.

> [!WARNING]
> Jangan sembarangan restore kalau Anda tidak yakin. Quarantine adalah safety net. Kalau Anda restore lalu double-click, payload yang dideteksi tool tetap akan jalan. Baca manifest dulu, cek indikator yang trigger, verifikasi dengan scan ulang mode Deep + hash reputation, baru restore kalau Anda benar-benar yakin file itu benign.

## Auto-scan integration

Fitur yang membedakan Threat Scanner dari standalone scanner biasa: integrasi otomatis dengan downloader PyScrapr.

### Cara kerja

Saat Anda aktifkan `threat_auto_scan_downloads = true` di Settings, EventBus PyScrapr (publish-subscribe internal) akan subscribe ke event berikut:
- `JOB_COMPLETED` dengan `tool_name = "image_harvester"`
- `JOB_COMPLETED` dengan `tool_name = "site_ripper"`
- `JOB_COMPLETED` dengan `tool_name = "media_downloader"`

Setiap kali salah satu event fire, listener di `threat_scanner_service.py` akan spawn background task:

1. Ambil output folder dari job yang baru selesai (misal `data/images/harvested_<job_id>/` untuk Image Harvester).
2. Call `scan_folder(path, depth="standard", recursive=true)`.
3. Tulis hasil scan ke tabel `ThreatScanResult` dengan field `linked_job_id` yang point ke job downloader asalnya.
4. Push notification ke UI via SSE channel global kalau ada file dangerous ditemukan.

### Integrasi History

Hasil auto-scan muncul di History dengan `type = THREAT_SCAN` dan badge link ke job parent. Dari History Anda bisa lihat: "Image Harvester job #1234 selesai → auto-scan menemukan 2 file suspicious di 200 file downloaded". Klik untuk drill-down ke detail scan.

### Notifikasi

Kalau Anda punya Webhook configured (Discord, Telegram, atau HTTP endpoint), finding dangerous dari auto-scan akan trigger webhook payload `threat_scanner.dangerous_file_found` dengan preview indikator. Cocok untuk setup tim: developer download ZIP dari klien via Site Ripper, finding dangerous langsung muncul di channel Discord security tim.

## Contoh skenario

### 1. Freelancer terima brief dari klien baru

Web designer freelance terima email dari "Marketing Director PT XYZ" (domain legit tapi belum dikenal), attachment `Brief_Proyek_Redesign_2026.zip`. Download ZIP, drag ke Threat Scanner, depth Standard. Hasil: 1 file suspicious dalam archive, `Brief_Detail.pdf.lnk` (LNK shortcut disamarkan sebagai PDF), indikator "LNK in archive" + "Dangerous file" trigger, risk score 65, verdict Dangerous. Reply sopan minta brief sebagai PDF asli, laporkan ke IT untuk block sender.

### 2. QA scan output Media Downloader dari YouTube

Content creator download 50 video reference dari YouTube via Media Downloader. Auto-scan aktif, jalan otomatis setelah job selesai. 50 file Clean (MP4 murni dari pipeline yt-dlp). History tampilkan entry `THREAT_SCAN` dengan `summary: 50 clean, 0 suspicious, 0 dangerous`, tanpa intervensi manual.

### 3. Review ZIP attachment dari email

Tim sales kirim `Proposal_Final_v7.zip` 2 MB. Drag ke Threat Scanner, depth Standard. Hasil: 3 file clean (PPTX, XLSX, PDF text-only, no macro), compression ratio normal, risk score 12, verdict Clean. Aman dibuka.

### 4. Investigasi file muncul di Downloads

Anda menemukan `update_installer.exe` yang tidak diingat di-download. Paste path, depth Deep, enable hash reputation. Hasil: PE verified, entropy `.text` = 7.8 (packed), UPX signature via YARA, 3 suspicious imports (VirtualAllocEx, CreateRemoteThread), VT 32/70 flag sebagai `Trojan.Generic.KDZ`, MalwareBazaar known. Risk score 100, Dangerous. Quarantine, cek Event Viewer untuk trace source, scan full system dengan Defender.

### 5. Audit folder proyek sebelum share

Lead developer akan share `project_assets/` 400 file ke tim. Scan Standard recursive. Hasil: 397 clean, 3 suspicious (SVG dengan `<script>` inline untuk animasi legitimate dari library vendor). Verifikasi manual, ignore, lanjut share.

### 6. Cek executable dari forum modding

Gamer download `awesome_mod_v3.7.zip` dari thread forum. Depth Deep. 15 file: 1 installer, 12 asset, 2 config. Installer: PE valid, entropy `.text` = 7.3, no suspicious imports, no YARA match, VT 0 engines flag. Risk score 18, Clean. Tetap recommend install di VM kalau source kurang reputable.

## Pengaturan detail

Semua setting key yang relevan di `settings.json` section Threat Scanner:

| Key | Tipe | Default | Keterangan |
|-----|------|---------|------------|
| `threat_scanner_enabled` | boolean | true | Master switch. Disable untuk matikan semua endpoint threat scanner |
| `threat_scan_default_depth` | string | `"standard"` | `quick`, `standard`, `deep` |
| `threat_scan_max_file_size_mb` | integer | 500 | Upload size limit per file |
| `threat_scan_archive_max_depth` | integer | 5 | Recursive archive depth limit |
| `threat_scan_archive_max_total_size_mb` | integer | 2048 | Guard zip bomb saat recursive extract |
| `threat_scan_entropy_threshold_suspicious` | float | 7.2 | Entropy di atas ini trigger +10 skor |
| `threat_scan_entropy_threshold_packed` | float | 7.6 | Entropy di atas ini trigger +20 skor |
| `threat_yara_rules_dir` | string | `"data/yara-rules"` | Root folder rule YARA |
| `threat_yara_auto_reload` | boolean | false | Watch file system dan reload otomatis saat rule berubah |
| `threat_hash_reputation_enabled` | boolean | false | Master switch hash lookup |
| `threat_hash_reputation_virustotal` | boolean | false | Enable VT lookup (butuh API key) |
| `threat_hash_reputation_virustotal_api_key` | string | `""` | API key dari virustotal.com |
| `threat_hash_reputation_malwarebazaar` | boolean | true | Enable MalwareBazaar lookup (no key needed) |
| `threat_hash_cache_ttl_hours` | integer | 24 | Cache hasil hash lookup lokal selama N jam |
| `threat_quarantine_enabled` | boolean | false | Enable move to quarantine action |
| `threat_quarantine_dir` | string | `"data/quarantine"` | Root folder quarantine |
| `threat_quarantine_windows_append_txt` | boolean | true | Append `.txt` di Windows supaya tidak executable |
| `threat_auto_scan_downloads` | boolean | false | EventBus listener untuk Image Harvester / Site Ripper / Media Downloader |
| `threat_auto_scan_depth` | string | `"standard"` | Depth yang dipakai saat auto-scan jalan |
| `threat_notify_webhook_on_dangerous` | boolean | true | Push ke webhook saat finding Dangerous |

## Tips & best practices

- **Kombinasi Quick + Deep optimal.** Quick dulu untuk folder besar, identify Suspicious / Dangerous, rerun Deep hanya untuk subset. Hemat 5-10x waktu dibanding Deep semua.

- **Tambah YARA rule kustom untuk threat industri spesifik.** Sektor finance, healthcare, gov punya pattern attack berbeda. Threat intel blog seperti Mandiant, CrowdStrike, Kaspersky Securelist publish rule YARA gratis bersama campaign report, copy ke `data/yara-rules/user/`.

- **Aktifkan auto-scan untuk workflow file eksternal.** Download rutin dari YouTube / forum / Google Drive share, auto-scan memberi peace of mind tanpa overhead. Setting `threat_auto_scan_downloads: true` + depth `standard` sweet spot.

- **Jangan disable quarantine saat scan folder sistem.** Banyak DLL / EXE legitimate di `System32` atau `Program Files` score tinggi karena packed + suspicious imports. Dengan quarantine enabled, aksi destructive reversible.

- **Cache hash reputation agresif.** TTL 24 jam default menghindari rate limit VT untuk folder yang di-audit berulang.

- **Skip hash lookup untuk batch besar.** Hash lookup +500ms-2s per file. Folder 500+ file dengan VT enable tambah 10+ menit. Enable selektif di Deep per-file.

- **Baca manifest quarantine sebelum restore.** Kalau ragu, rescan depth Deep dulu. Lebih baik keep false positive di quarantine daripada restore true positive.

## Troubleshooting

### Problem: "libmagic unavailable" atau "magic module not found" di Windows

**Gejala:** Saat start backend, log warning `python_magic not available, magic bytes detection disabled`.
**Penyebab:** Anda install `python-magic` tanpa `-bin` suffix, dan libmagic.dll tidak ter-bundle.
**Solusi:**

```powershell
pip uninstall python-magic -y
pip install python-magic-bin
```

Restart backend.

### Problem: yara-python compile error saat install

**Gejala:** `pip install yara-python` gagal dengan error compile `cl.exe not found` atau `Microsoft Visual C++ 14.0 is required`.
**Penyebab:** Tidak ada Visual C++ Build Tools di Windows.
**Solusi:** Install "Build Tools for Visual Studio" dari microsoft.com/visualstudio, pilih workload "Desktop development with C++". Atau pakai pre-built wheel dari `yara-python` GitHub releases:

```powershell
pip install https://github.com/VirusTotal/yara-python/releases/download/v4.5.1/yara_python-4.5.1-cp311-cp311-win_amd64.whl
```

Ganti versi dan tag Python sesuai environment Anda.

### Problem: pymupdf import error

**Gejala:** Saat scan PDF, log error `ImportError: DLL load failed while importing fitz`.
**Penyebab:** Konflik versi pymupdf dengan Python atau Visual C++ runtime missing.
**Solusi:** Reinstall pymupdf versi paling baru:

```powershell
pip uninstall pymupdf -y
pip install --upgrade pymupdf
```

Kalau masih error, install "Visual C++ Redistributable for Visual Studio 2015-2022" dari microsoft.com.

### Problem: VirusTotal rate limit exceeded

**Gejala:** Sebagian hash lookup gagal dengan message "API rate limit exceeded, retry after X seconds".
**Penyebab:** API public VirusTotal limit 4 req/menit dan 500 req/hari. Anda scan folder besar dengan hash reputation enabled, hit limit.
**Solusi:** Naikkan `threat_hash_cache_ttl_hours` supaya hash yang sama tidak re-hit API. Disable VT lookup untuk batch scan, enable hanya per-file. Atau upgrade ke VT Premium kalau use case Anda heavy.

### Problem: False positive pada installer legitimate

**Gejala:** Installer besar seperti NodeJS, Visual Studio, Python di-flag Dangerous dengan score 50-70.
**Penyebab:** Installer umumnya PE packed (entropy tinggi), banyak imports (termasuk yang dianggap suspicious oleh heuristic sederhana), dan kadang embed file dalam self-extracting archive. Ini pattern yang mirip packed malware.
**Solusi:** Kombinasi signal akhir yang membedakan installer legitimate vs malware adalah hash reputation. Enable VT lookup, installer resmi akan return 0/70 engines. Kalau VT clean, Anda bisa accept skor Suspicious di static analysis sebagai "high-entropy tapi legitimate". Tambahan: cek digital signature dengan `signtool verify /pa file.exe` di Command Prompt, installer resmi akan verified signed.

### Problem: Scan folder hang di archive besar

**Gejala:** Scan folder yang berisi ZIP 5 GB dengan nested archive, backend stuck selama 10+ menit.
**Penyebab:** Depth `standard` default recursive archive, ZIP besar dengan nested level 5 bisa spawn ratusan temporary extract yang fill disk.
**Solusi:** Turunkan `threat_scan_archive_max_total_size_mb` ke 512 atau 256. Turunkan `threat_scan_archive_max_depth` ke 3. Atau pakai depth Quick untuk folder yang dominan archive besar, karena Quick skip archive inspection.

## Keamanan & batasan

Jujur tentang kapabilitas tool adalah bagian penting dari security tool yang baik.

- **Static analysis bukan pengganti antivirus realtime.** Tool analyze file on-demand, bukan behavioral monitoring proses running. Defender / Kaspersky / Bitdefender tetap perlu untuk proteksi layer lain. Ini pelengkap, bukan pengganti.

- **Tidak detect zero-day yang butuh behavioral analysis.** Malware baru yang belum match YARA, belum di-submit ke VT, dan PE structure normal akan return Clean. Behavior sandboxing (jalankan di VM, amati syscall) di luar scope tool.

- **Tidak defeat targeted attack dengan custom packing.** APT scenario dengan packer kustom, entropy dikendalikan, dan VT first-seen yang di-time dengan attack tidak akan ter-catch oleh tool general-purpose.

- **Scope terbatas pada file di disk.** Tidak analyze memory process, network traffic, atau browser cache.

- **VT hash lookup aman dari sisi privacy.** SHA256 one-way, VT tidak bisa reconstruct isi file dari hash, cuma cek apakah hash pernah muncul di submission orang lain. File unique return "unknown", tidak ada info bocor.

- **YARA rule kustom dari internet perlu di-review.** Rule dari blog tidak dikenal bisa false-positive besar-besaran. Validasi di sample known-clean dan known-malicious sebelum dipakai production.

## Related docs

- [Media Downloader](/docs/tools/media-downloader.md) - integrasi auto-scan untuk file hasil download
- [Site Ripper](/docs/tools/site-ripper.md) - integrasi auto-scan untuk asset hasil ripping
- [Image Harvester](/docs/tools/image-harvester.md) - integrasi auto-scan untuk image batch download
- [History](/docs/system/history.md) - entry `THREAT_SCAN` dan linked job parent
- [Settings](/docs/system/settings.md) - semua threat scanner flag
- [Webhooks](/docs/advanced/webhooks.md) - notifikasi Discord / Telegram saat finding Dangerous
- [Scheduled Jobs](/docs/system/scheduled.md) - schedule scan rutin folder Downloads atau share network
