# Metadata Inspector

> Metadata Inspector adalah utility PyScrapr yang baca metadata tersembunyi di file: EXIF GPS dari foto smartphone, author + last modified PDF brief klien, software pembuat dari export Photoshop, codec + bitrate dari video, hash + filesize generic dari file apapun. Drag file ke drop zone atau paste path absolut, tool extract semua tag yang relevan dalam 1-2 detik, GPS coordinate ter-link otomatis ke OpenStreetMap, dan output bisa di-download sebagai JSON. Cocok untuk cek privasi (apakah foto saya bocorkan lokasi rumah?), audit dokumen confidential (siapa author asli?), atau forensik ringan saat menerima file dari sumber tidak dikenal.

## Apa itu Metadata Inspector

File modern jarang yang benar-benar "kosong" metadata. Foto smartphone bawa GPS coordinate persis, model kamera, tanggal pengambilan, dan kadang serial number lensa. PDF dari Word punya field author, last modified, software pembuat, dan template asal. File Office (`.docx`, `.xlsx`, `.pptx`) sebetulnya ZIP yang isi XML, dengan node `<dc:creator>` dan `<cp:lastModifiedBy>`. Video MP4 punya track audio, codec, bitrate, dan kadang GPS dari smartphone. Bahkan file generic punya MIME type, hash, dan size yang relevan untuk verifikasi.

Metadata Inspector adalah jawaban PyScrapr untuk pertanyaan: "File ini mengandung apa, di luar konten utamanya?". Daripada install ExifTool command-line + pdfinfo + ffprobe + custom script per file type, Anda dapat satu UI ber-drop-zone dengan output rapi per kategori.

Tool ini punya dua audience utama. Pertama, content creator yang sadar privacy: sebelum upload foto travel ke Instagram, mereka cek dulu apakah GPS-nya bocor. Kedua, freelancer dan analyst yang sering terima file dari klien: mereka audit `proposal.pdf` untuk lihat siapa author asli (bukan klien yang nama di email-nya, tapi mungkin software pembuat di kantor pusat), atau cek `report_v2.docx` apakah ada track changes yang lupa di-clean.

Positioning tool ini berbeda dari Threat Scanner. Threat Scanner fokus deteksi malware. Metadata Inspector fokus extract informasi tag-style dari file aman. Dua tool, dua tujuan, sering jalan bersama: scan file dengan Threat Scanner dulu (aman?), baca metadata dengan Inspector kedua (bocoran apa?).

## Format yang didukung

Tool punya 5 defensive branch (extractor) yang dipilih berdasarkan magic bytes dan extension:

| Branch | Format | Library | Field utama |
|--------|--------|---------|-------------|
| EXIF | JPEG, JPG, TIFF, HEIC, PNG (text chunks), WebP, RAW (CR2, NEF, ARW) | Pillow + piexif | GPS lat/lng/altitude, kamera model, lensa, ISO, aperture, shutter, software, tanggal |
| PDF | PDF | pymupdf (fitz) | Title, author, subject, keywords, creator, producer, creation date, modification date, page count, bookmarks |
| Office | DOCX, XLSX, PPTX, ODT, ODS, ODP | zipfile + xml.etree | dc:creator, dc:title, lastModifiedBy, lastPrinted, revision, version, application, template, total editing time |
| Office legacy | DOC, XLS, PPT (binary OLE) | olefile | Same field set + summary stream + document summary stream |
| Media | MP4, MOV, AVI, MKV, MP3, FLAC, OGG, WebM | ffprobe (ffmpeg) | Duration, bitrate, codec video/audio, resolution, fps, GPS (kalau ada), encoder, creation time |
| Generic | Apapun yang tidak match di atas | Built-in | MIME type, file size, SHA256, MD5, magic bytes preview, mtime/ctime/atime |

Branch dipilih runtime berdasarkan `python-magic` magic bytes, jadi ekstensi file tidak menentukan. File `.jpg` yang sebetulnya PDF akan tetap di-route ke PDF branch.

> [!NOTE]
> Branch akan skip dengan warning kalau library yang dibutuhkan tidak terpasang. Pillow biasanya sudah ada dari install PyScrapr default. pymupdf, olefile, ffprobe optional. Tool tetap jalan, hanya branch yang missing dependency-nya yang skip. Lihat Troubleshooting di bawah untuk install instruction per library.

## Cara pakai

Buka PyScrapr, navigasi ke menu **Metadata Inspector** di sidebar Utilities (warna cyan, ikon file-info). Halaman terbuka dengan dua mode tab.

### Mode 1: Upload (drag & drop)

Mode paling umum. Anda punya file di disk, drag ke drop zone, tool baca, return.

1. Pilih tab **Upload**.
2. Drag file dari Windows Explorer / Finder ke drop zone, atau klik untuk buka file picker.
3. Backend menerima file via multipart upload, simpan sementara di `data/temp/metadata_uploads/`, dispatch ke branch yang sesuai, extract, return JSON, hapus file temp.
4. Hasil muncul di panel kanan dalam bentuk card per-section (EXIF Camera, EXIF GPS, EXIF Software, dst). Setiap field tampil sebagai key-value dengan formatting human-readable (tanggal di-parse, koordinat GPS jadi link OSM, durasi video dalam HH:MM:SS).

Mode upload cocok kalau file sudah ada di mesin Anda dan Anda tidak hafal path absolutnya. Maksimum file size default 200 MB, bisa di-set lewat `metadata_max_upload_mb`.

### Mode 2: Local Path

Mode yang menghindari upload, langsung baca dari disk backend.

1. Pilih tab **Local Path**.
2. Paste path absolut file di field `Path file` (misal `C:/Users/you/Pictures/IMG_0042.jpg` atau `/home/you/docs/report.pdf`).
3. Klik **Inspect**.
4. Backend baca file langsung dari disk, dispatch, extract, return.

Mode ini lebih cepat untuk file besar (video 2 GB tidak perlu di-upload ulang) dan tidak makan slot temp folder. Cocok untuk audit batch (loop call API endpoint dengan list path).

### Deep-link via query string

Tool support `?path=...` di URL. Misalnya `http://localhost:5173/metadata?path=C:/Users/you/Pictures/IMG_0042.jpg`. Halaman terbuka dengan mode Local Path pre-filled, Anda tinggal klik Inspect. Berguna untuk integrasi dari tool lain (misal Image Harvester yang sudah download file, langsung link ke Metadata Inspector untuk verifikasi).

## Hasil EXIF

Foto dari smartphone modern membawa metadata yang seringkali lebih kaya dari yang user sadari.

### GPS coordinate

Field GPS yang di-extract:
- **Latitude / Longitude** dalam decimal degree (dikonversi dari format DMS asli)
- **Altitude** dalam meter (kalau ada)
- **GPS timestamp** waktu UTC saat snapshot
- **GPS direction** arah hadap kamera (kalau magnetometer aktif)

Setiap koordinat di-render dengan tombol "Buka di OpenStreetMap" yang link ke `https://www.openstreetmap.org/?mlat=<lat>&mlon=<lng>#map=18/<lat>/<lng>`. Klik untuk lihat lokasi persis di peta.

> [!WARNING]
> GPS dari foto smartphone biasanya akurat 5-10 meter. Foto rumah Anda akan tunjukkan rumah Anda persis di peta. Sebelum upload foto ke social media public, cek GPS-nya dengan tool ini. Untuk privacy: kebanyakan upload service (Instagram, Twitter, Facebook) auto-strip EXIF, tapi WhatsApp, Telegram (default), email attachment, dan direct file share TIDAK strip. Kalau Anda kirim foto ke kontak yang tidak Anda kenal benar, GPS bisa terkirim utuh.

### Camera & lens info

| Field | Contoh |
|-------|--------|
| Make | `Apple`, `Sony`, `Canon`, `samsung` |
| Model | `iPhone 15 Pro`, `ILCE-7M4`, `EOS R6` |
| Lens | `iPhone 15 Pro back triple camera 6.86mm f/1.78` |
| Software | `iOS 17.4`, `Adobe Lightroom 13.0`, `Capture One 23` |
| ISO | `400`, `1600` |
| Aperture | `f/1.8`, `f/2.8` |
| Shutter | `1/120s`, `30s` |
| Focal length | `35mm`, `85mm` (35mm equivalent) |
| Date taken | `2026-04-15 14:32:08` |
| Date modified | `2026-04-16 09:11:22` |

Software field sering bocorkan workflow Anda. Klien terima foto, lihat software `Lightroom 13.0`, mereka tahu Anda edit (bukan deliver dari kamera mentah). Tergantung kontrak, ini bisa relevan.

### Software / editor history

Beberapa editor (Photoshop, Lightroom, Capture One) bahkan tag history edit di EXIF custom tag. Tidak semua, tapi worth checking untuk asset yang Anda terima dari third party.

## Hasil PDF / Office / Media

### PDF

Field standard PDF metadata:

| Field | Sumber | Note |
|-------|--------|------|
| Title | `/Title` di info dictionary | Sering kosong atau filename |
| Author | `/Author` | Bisa beda dari pengirim email - clue siapa author asli |
| Subject | `/Subject` | Jarang diisi |
| Keywords | `/Keywords` | Jarang diisi |
| Creator | `/Creator` | Software yang generate konten (Word, InDesign, LaTeX) |
| Producer | `/Producer` | Software yang generate file PDF (Adobe PDF Library, GhostScript, wkhtmltopdf) |
| Creation Date | `/CreationDate` | Saat file pertama dibuat |
| Modification Date | `/ModDate` | Saat file terakhir di-save |
| Page count | dari struktur PDF | |
| Bookmarks / outline | tree struktur | |
| Linearized | boolean | Apakah PDF di-optimize untuk web streaming |
| Encrypted | boolean | Apakah ada permission restriction |

> [!TIP]
> Combo `Author` + `Creator` + `Producer` + `Modification Date` adalah forensik ringan PDF. PDF brief klien dengan Author "John Doe" tapi Producer "Microsoft Word for Mac" sementara klien Anda kerja Windows, signal layak ditanyakan. Modification Date di-cek terhadap email send time. Discrepancy bisa indikasi PDF diteruskan dari pihak lain.

### Office (DOCX/XLSX/PPTX dan legacy)

Office Open XML format (`.docx`, `.xlsx`, `.pptx`) sebetulnya ZIP. Inspector extract `docProps/core.xml` dan `docProps/app.xml` yang berisi:

| Field | Path |
|-------|------|
| Title | `dc:title` |
| Subject | `dc:subject` |
| Author | `dc:creator` |
| Last Modified By | `cp:lastModifiedBy` |
| Created | `dcterms:created` |
| Modified | `dcterms:modified` |
| Last Printed | `cp:lastPrinted` |
| Revision | `cp:revision` |
| Version | `cp:version` |
| Application | `Application` (di app.xml) |
| Template | `Template` |
| Total Editing Time | `TotalTime` (dalam menit) |
| Slides / Pages | tergantung tipe dokumen |
| Company | `Company` (kalau tidak di-clean) |

Untuk format legacy (`.doc`, `.xls`, `.ppt`), olefile parse OLE compound file dan baca SummaryInformation + DocumentSummaryInformation stream. Field set mirip, plus beberapa property windows-specific.

> [!IMPORTANT]
> Field `cp:lastModifiedBy` sering bocorkan struktur tim. Dokumen yang dikirim "dari" Pak Direktur bisa punya Last Modified By "intern_marketing" atau "agency_pic" - clue siapa yang sebenarnya draft. Untuk konfidensialitas tim, biasakan clean metadata sebelum kirim dokumen ke external pakai File - Info - Inspect Document - Document Inspector di Word/Excel.

### Media (Video / Audio)

ffprobe extract:

| Field | Contoh |
|-------|--------|
| Format | `mov, mp4, m4a, 3gp, 3g2, mj2`, `matroska, webm` |
| Duration | `00:42:31.420` |
| Bitrate | `5234 kb/s` |
| Streams | List per stream (video, audio, subtitle) |
| Video codec | `h264`, `hevc`, `av1`, `vp9` |
| Resolution | `1920x1080`, `3840x2160` |
| FPS | `29.97`, `60` |
| Audio codec | `aac`, `opus`, `flac` |
| Audio channels | `stereo`, `5.1` |
| Sample rate | `44100`, `48000` |
| Encoder | `Lavf60.16.100`, `HandBrake 1.7.0` |
| Creation time | dari container metadata |
| GPS | dari `com.apple.quicktime.location.ISO6709` (iOS) |

Video iOS bawa GPS sama seperti foto. Cek dulu sebelum publish video travel.

### Generic fallback

Untuk file yang tidak match branch lain (binary, source code, archive belum support deep parse, dll):

| Field | Detail |
|-------|--------|
| MIME type | dari python-magic |
| File size | bytes (formatted human-readable) |
| SHA256 | hash full file |
| MD5 | hash full file (untuk compatibility tool legacy) |
| First 64 bytes | hex preview |
| First 256 bytes ASCII printable | text preview |
| Modified time | dari filesystem stat |
| Created time | kalau OS support |
| Accessed time | dari filesystem stat |

## Contoh skenario

### 1. Privacy check sebelum upload foto

Travel blogger akan upload foto dari hotel ke Instagram. Sebelum publish, drag foto ke Metadata Inspector. Hasil: GPS koordinat menunjuk hotel persis (kamar 3 lantai 2 timur). Action: pakai foto editor untuk strip EXIF, atau pakai Pillow CLI `exiftool -all= IMG_0042.jpg` di terminal sebelum upload. Atau pakai fitur "Save without metadata" di smartphone gallery modern.

### 2. Audit dokumen confidential

Tim sales terima `proposal_signed.pdf` dari calon klien. Drag ke Inspector. Hasil: Author "Marketing Intern XYZ", Creator "Microsoft Word for Mac", Modification Date 3 hari lalu padahal email klaim "this is the final signed PDF as agreed last month". Discrepancy → tanyakan klien sebelum sign back, mungkin ada revisi yang tidak Anda awari.

### 3. Identifikasi software pembuat asset

Designer freelance terima brand asset (`logo_v2.psd`) dari klien. Klien claim "ini final, tidak perlu rework". Inspect file. Hasil: Software "Photoshop CS6 (2012)" - software 14 tahun lalu. Layer mungkin tidak compatible dengan workflow modern designer. Push back ke klien minta deliverable di format ai/svg vector untuk longevity.

### 4. Forensik foto kemenangan kompetisi

Juri kompetisi fotografi audit foto submission. Inspect EXIF: kamera Canon EOS R5, lensa 70-200mm f/2.8, ISO 100, shutter 1/250s, GPS di lokasi yang claim Pulau Komodo, software "Lightroom Classic 13.4", date taken 2026-03-15. Konsisten dengan klaim peserta. Submission diterima. Foto submission lain GPS-nya di studio Jakarta padahal claim diambil di Bali, disqualify.

### 5. Audit video presentation klien

Project manager terima `quarterly_review.mp4` dari klien remote. Inspect: encoder "OBS Studio 30.1", duration 47 menit, encoded last week (sebelum email send), resolution 1920x1080. Konsisten dengan klaim "saya rekam sendiri minggu lalu". Kalau encoder muncul "HandBrake" atau "Adobe Media Encoder" mungkin file-nya re-export dari sumber lain.

### 6. Identifikasi malware embed di document

Inspector tunjukkan `Application: Microsoft Office` di file `.docx` yang Anda terima, normal. Tapi di field Title field tampil string panjang base64 - itu unusual untuk Office field, bisa jadi indicator obfuscation. Kombinasi dengan Threat Scanner depth Deep akan extract VBA macro untuk inspeksi.

## Tips & best practices

- **Combo dengan Threat Scanner.** Untuk file dari sumber tidak kenal, scan dengan Threat Scanner dulu (apakah aman?), inspect metadata setelahnya (apa yang bocor?). Urutan ini menghindari kemungkinan parser metadata hit malformed file yang crash.

- **Strip metadata sebelum publish via tool produktif.** Exiftool (`exiftool -all=`), ImageMagick (`convert -strip`), atau "Remove Properties and Personal Information" di Windows Explorer (klik kanan file > Properties > Details > Remove Properties).

- **Untuk batch privacy strip, pakai Custom Pipeline.** Tulis snippet Python yang loop folder, baca via Pillow, save tanpa EXIF. PyScrapr Pipeline cocok untuk workflow ini.

- **Cache hasil per SHA256.** Setiap inspeksi tercatat di tabel `MetadataResult` dengan key SHA256. Re-inspect file yang sama langsung return dari cache, hemat waktu untuk audit folder besar.

- **Field GPS bisa di-export ke KML.** JSON output bisa di-transform ke KML untuk import ke Google Earth atau QGIS, untuk visualisasi multi-foto travel route.

- **Time skew ke timezone lokal.** Field date di EXIF biasanya tanpa timezone. Asumsi UTC kecuali ada `OffsetTime` tag. Untuk forensik strict, cek field `OffsetTime` dan `OffsetTimeOriginal`.

- **PDF "encrypted" bukan berarti aman.** Encryption PDF mayoritas pakai password lemah dan permission flag yang trivial di-bypass. Jangan andalkan untuk dokumen sensitif - pakai 7zip dengan AES-256 password atau Vault PyScrapr.

## Troubleshooting

### Problem: "Pillow not installed"

**Gejala:** Branch EXIF return error, semua foto tidak ke-extract.
**Penyebab:** Pillow library missing di venv backend.
**Solusi:** `pip install Pillow piexif` di venv, restart backend. Pillow biasanya sudah ada karena dipakai banyak tool PyScrapr lain, jadi error ini jarang muncul.

### Problem: "pymupdf import failed"

**Gejala:** PDF inspect error.
**Penyebab:** pymupdf (fitz) belum terpasang.
**Solusi:** `pip install pymupdf` di venv. Di Windows, kadang butuh Visual C++ Redistributable.

### Problem: "olefile not installed" untuk file .doc lawas

**Gejala:** File `.doc` legacy return generic-only, tidak ada field Office.
**Penyebab:** olefile library missing.
**Solusi:** `pip install olefile` di venv.

### Problem: "ffprobe not found"

**Gejala:** Video / audio file return generic-only.
**Penyebab:** ffmpeg (yang menyertakan ffprobe) tidak ada di PATH sistem.
**Solusi:** Install ffmpeg dari [ffmpeg.org/download.html](https://ffmpeg.org/download.html), pastikan `ffprobe --version` jalan di terminal. Di Windows pakai `winget install ffmpeg` atau Chocolatey `choco install ffmpeg`. Di macOS `brew install ffmpeg`. Di Linux `apt install ffmpeg` atau equivalent.

### Problem: HEIC photo tidak ke-extract

**Gejala:** File `.heic` dari iPhone tidak ada EXIF padahal ada metadata-nya.
**Penyebab:** Pillow default tidak baca HEIC, butuh plugin `pillow-heif`.
**Solusi:** `pip install pillow-heif` di venv, restart backend. Plugin auto-register saat import.

### Problem: Path Local Path mode "file not found" padahal file ada

**Gejala:** Anda paste path yang valid di File Explorer, tapi tool return error.
**Penyebab:** Backslash di Windows path harus di-escape atau pakai forward slash. Path dengan spasi atau karakter non-ASCII kadang issue.
**Solusi:** Pakai forward slash: `C:/Users/you/Pictures/file.jpg`. Atau backslash double: `C:\\Users\\you\\Pictures\\file.jpg`. Hindari path dengan emoji atau karakter spesial.

### Problem: Output GPS link OSM tidak muncul

**Gejala:** Foto jelas ada GPS di properties Windows, tapi tool tunjukkan section GPS kosong.
**Penyebab:** Format GPS tag di EXIF bervariasi. Beberapa kamera write `GPSLatitudeRef` + `GPSLatitude` sebagai DMS (degree-minute-second tuple), beberapa direct decimal. Parser kami handle keduanya tapi edge case bisa luput.
**Solusi:** Compare dengan exiftool CLI: `exiftool -GPS* file.jpg`. Kalau exiftool tunjukkan dan kami tidak, report sebagai bug dengan sample file (yang tidak privacy-sensitive).

## Related docs

- [Threat Scanner](/docs/tools/threat-scanner.md) - scan file aman atau tidak sebelum inspeksi metadata
- [Image Harvester](/docs/tools/image-harvester.md) - hasil download bisa langsung di-link ke `?path=` Metadata Inspector
- [Custom Pipeline](/docs/utilities/pipeline.md) - batch strip metadata dari folder dengan Pipeline custom
- [OSINT Harvester](/docs/tools/osint-harvester.md) - extract metadata dari URL publik (situs target) bukan file lokal
- [Settings](/docs/system/settings.md) - flag `metadata_max_upload_mb`, `metadata_cache_enabled`
