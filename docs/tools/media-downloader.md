# Media Downloader

> Tool download video dan audio dari 1000+ situs (YouTube, Instagram, TikTok, Twitter, dll) lewat integrasi yt-dlp, dengan kontrol kualitas, format, subtitle, playlist range, dan cookie browser.

## Deskripsi

Media Downloader adalah jembatan antara PyScrapr dan project open-source legendaris `yt-dlp` - fork aktif dari youtube-dl yang saat ini adalah de-facto standard untuk video extraction. PyScrapr membungkus yt-dlp versi `2026.03.17` dengan UI yang manusiawi, menyediakan preset kualitas yang sensible, dan mengintegrasikan hasil download ke sistem History/Pipeline/Scheduler. Alih-alih memaksa user menghafal flag command-line seperti `-f "bestvideo[height<=1080]+bestaudio/best"`, user cukup pilih preset **1080p** dari dropdown.

Di bawah hood, tool ini memakai yt-dlp sebagai library Python bukan subprocess - artinya komunikasi dua arah tight, callback progress real-time, dan error handling granular. Saat user submit URL, backend pertama kali jalankan **probe phase** (yt-dlp `extract_info` dengan `download=False`) untuk dapat metadata: judul, durasi, available formats, thumbnail, channel, upload date. Metadata ini ditampilkan di UI untuk konfirmasi user sebelum commit download. Baru setelah user klik Download, fase download asli mulai dengan progress hook yang emit SSE setiap ~500ms (speed MB/s, ETA, bytes done/total).

ffmpeg dibundel otomatis via package `imageio_ffmpeg` - user tidak perlu install ffmpeg sistem terpisah. Ini penting untuk operasi seperti merge video+audio separate stream (YouTube DASH), embed thumbnail sebagai album art (audio), embed subtitle ke container MKV, atau convert antar format (MP4 → MP3 audio extraction). Bundled ffmpeg ter-ship dengan build statis untuk semua platform, mencakup libx264, libvpx, aac, opus.

Salah satu fitur yang menonjolkan Media Downloader dari aplikasi desktop kompetitor (4K Video Downloader berbayar, JDownloader bloated) adalah **cookie from browser**. Via library `browser_cookie3`, tool bisa read cookie langsung dari Chrome, Firefox, Edge, atau Brave yang terinstall - memungkinkan download konten behind login (Patreon, members-only YouTube, private TikTok) tanpa harus export cookie manual. Cukup pilih browser dari dropdown, yt-dlp pakai session Anda yang aktif.

Positioning: yt-dlp CLI adalah tool paling powerful tapi intimidating. GUI wrapper yang ada (Tartube, yt-dlg) outdated atau tidak maintained. Media Downloader PyScrapr memberikan UX modern dengan power yt-dlp utuh, plus integrasi lintas-tool yang unik ke ekosistem PyScrapr.

## Kapan pakai tool ini?

- **Backup channel YouTube favorit** - download semua video dari channel sebelum kena demonetization atau takedown.
- **Arsip content creator Indonesia** - simpan podcast YouTube/Spotify pakai audio-only preset untuk dengar offline.
- **Riset content competitor** - download video kompetitor dari TikTok/Instagram Reels untuk analisis hook pattern, editing style, duration.
- **Offline kursus online** - kalau Anda enroll di course YouTube atau platform tanpa offline feature, download untuk belajar tanpa koneksi.
- **Download live stream recorded** - capture past live Twitch/YouTube sebelum di-delete creator.
- **Konversi video jadi audio podcast** - video interview panjang di YouTube → MP3 untuk dengar di commute.
- **Backup Instagram Reels sendiri** - re-upload ke platform lain butuh source file asli.
- **Playlist music compilation** - YouTube playlist 50 lagu → folder MP3 dengan metadata lengkap dan thumbnail embedded sebagai album art.

## Cara penggunaan

1. Buka menu `Media Downloader`. Form di kiri, panel hasil di kanan.

2. Paste URL video/playlist/channel di field `Media URL`. Mendukung banyak platform: YouTube, YouTube Music, Instagram (post/reel/story), TikTok, Twitter/X, Facebook, Vimeo, Twitch, Reddit, SoundCloud, Bandcamp, Bilibili, dll. Ekspektasi: auto-detect platform muncul di bawah field.

3. Klik tombol `Probe` (ikon mata). Backend jalankan `extract_info` tanpa download. Dalam 2-10 detik muncul card preview: thumbnail, title, channel, duration, upload date, available quality list, subtitle availability.

4. Pilih `Quality` dari dropdown: `Best`, `4K`, `1080p`, `720p`, `480p`, atau `Audio only`. Ekspektasi: estimasi file size muncul berdasarkan pilihan.

5. Pilih `Format` output: `MP4` (kompatibel universal), `WebM` (open codec, ukuran efisien), `MKV` (container flexible, support multi-track), `MP3` (audio lossy standard), `M4A` (audio AAC), `FLAC` (audio lossless besar), `Opus` (audio modern efisien).

6. Pilih `Subtitles` mode: `Skip` (tidak download), `Download (.srt)` (save sebagai .srt terpisah), `Embed` (embed ke container MKV). Kalau pilih download/embed, masukkan `Subtitle langs` comma-separated: `en,id,ms`.

7. Untuk playlist: set range via `Start #` (item ke-N mulai), `End #` (sampai item ke-M), `Max items` (batasi total). Default: download semua. Ubah untuk hemat bandwidth atau testing.

8. Opsional: pilih `Cookies from browser` dan pilih source (Chrome/Firefox/Edge/Brave). Aktifkan hanya untuk konten behind login.

9. Opsional: centang `Embed thumbnail` (jadikan album art untuk audio atau chapter preview untuk video), `Embed metadata` (ID3 tags, chapter marks).

10. Klik `Start download`. Backend create job, mulai download. Panel kanan populate dengan per-item progress: filename, speed (MB/s), ETA, percent complete, current action (downloading video / downloading audio / merging / embedding).

11. Saat selesai, tiap item menunjukkan status (OK / error), link ke file lokal, preview thumbnail. Klik thumbnail untuk preview dalam modal player (HTML5 video/audio).

12. Buka folder tujuan via tombol `Open download folder` di header, atau tambahkan ke playlist player eksternal via path yang di-copy. History otomatis menyimpan job untuk re-download atau resume kalau interrupted.

## Pengaturan / Konfigurasi

### Media URL
Alamat video/playlist/channel. Wajib. Default: kosong. Rekomendasi: satu URL per job untuk clarity. Ubah ke playlist URL kalau bulk.

### quality_preset
Preset kualitas download. Default: `1080p`. Options: `best`, `4k`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `audio`. Rekomendasi: `720p` untuk mobile archive (hemat space), `1080p` untuk desktop viewing, `best` kalau disk melimpah. Ubah ke `audio` untuk podcast/music use case.

### format
Container/codec output. Default: `mp4`. Rekomendasi: `mp4` untuk max compatibility, `webm` untuk hemat size, `mkv` kalau butuh multi-audio track. Audio: `mp3` default, `opus` untuk compactness modern, `flac` untuk arsip lossless.

### subtitles_mode
Cara handle subtitle. Default: `skip`. Rekomendasi: `download` kalau subtitle penting untuk reference (misal bahasa asing), `embed` kalau mau single file portable.

### subtitle_languages
Bahasa subtitle comma-separated. Default: `en`. Rekomendasi: `en,id` untuk content Indonesia. Tambah `auto` untuk auto-generated.

### playlist_start
Item pertama yang di-download (1-indexed). Default: 1. Rekomendasi: ubah untuk resume playlist yang sebagian sudah di-download.

### playlist_end
Item terakhir. Default: null (sampai habis). Rekomendasi: set limit untuk testing.

### max_items
Hard cap total items. Default: null. Rekomendasi: 50 untuk exploration, unlimited untuk archival.

### cookies_from_browser
Browser source cookie. Default: `none`. Options: `none`, `chrome`, `firefox`, `edge`, `brave`. Rekomendasi: `none` untuk public content, pilih browser untuk behind-login.

### embed_thumbnail
Boolean embed thumbnail ke file. Default: true untuk audio, false untuk video.

### embed_metadata
Boolean embed metadata ID3/container tags. Default: true. Rekomendasi: biarkan true selalu.

### concurrent_downloads
Jumlah file paralel. Default: 3. Rekomendasi: 1-2 untuk koneksi lambat, 3-5 untuk fast. Ubah turun kalau dapat rate limit.

### download_archive
Track file yang sudah di-download via archive file. Default: true. Rekomendasi: aktifkan untuk playlist - re-run akan skip yang sudah ada.

### rate_limit_bps
Cap bandwidth per download. Default: unlimited. Rekomendasi: set kalau share internet agar tidak drain.

## Output

Struktur folder hasil:

```
downloads/
└── media/
    └── <platform>/
        └── <channel_or_uploader>/
            ├── <YYYY-MM-DD>_<title>.mp4
            ├── <YYYY-MM-DD>_<title>.info.json      # metadata yt-dlp
            ├── <YYYY-MM-DD>_<title>.en.srt         # subtitle
            ├── <YYYY-MM-DD>_<title>.jpg            # thumbnail
            └── download_archive.txt                # tracked IDs
```

- Filename pattern bisa di-customize di settings global `output_template`.
- `.info.json` berisi metadata lengkap (durasi, upload date, tags, description) - berguna untuk indexing offline library.
- `download_archive.txt` mencegah re-download di run berikutnya.

## Integrasi dengan fitur lain

- **AI Tagger** - extract thumbnail untuk klasifikasi CLIP (misal kategorisasi video library by visual content).
- **Pipeline audio processing** - convert MP4 ke MP3, normalize loudness, strip silence, generate transcript via Whisper integration.
- **Scheduler** - jadwalkan daily check channel YouTube untuk auto-download video baru.
- **History/Archive integration** - track semua download dengan metadata, filter by channel, date, duration.
- **URL Mapper handoff** - crawl halaman artikel yang embed video, export URL list video, batch download via Media Downloader.
- **Export module** - generate M3U playlist dari folder download untuk media player.

## Tips & Best Practices

1. **Selalu Probe dulu sebelum Download** - Probe murah (metadata only) dan memberitahu Anda size/format available. Menghindari kaget download 8K accidentally.

2. **Pakai audio preset untuk podcast** - video YouTube podcast 2-jam bisa 2GB di 1080p, sedangkan MP3 cuma 100MB. Kualitas audio identik.

3. **Aktifkan download_archive untuk channel subscription** - re-run weekly, auto-skip yang sudah ada, hanya fetch video baru. Save bandwidth banyak.

4. **Cookie browser untuk age-gated content** - YouTube age-restricted atau Instagram private account butuh cookie. Firefox cookie paling reliable karena tidak encrypt.

5. **Rate limit saat share WiFi** - full-speed download bisa 20MB/s, drain koneksi rumah. Set `rate_limit_bps: 2M` untuk 2MB/s cap.

6. **Test dengan video singkat dulu** - sebelum batch channel dengan 500 video, test 1 video untuk validate preset + format benar.

7. **Simpan .info.json** - metadata ini invaluable kalau later butuh cari video by tag/description. Bangun local search index pakai file ini.

8. **Perbarui yt-dlp via backend rebuild reguler** - situs seperti YouTube sering breaking change, yt-dlp patched cepat tapi Anda harus pull versi baru. Check release weekly.

## Troubleshooting

### Problem: "Video unavailable" error meski URL aktif di browser
**Gejala:** Error `ERROR: Video unavailable` atau `Sign in to confirm your age`.
**Penyebab:** Geo-block, age-restriction, atau video memang private/deleted.
**Solusi:** Test URL di incognito browser - kalau butuh sign-in, aktifkan cookie browser option. Kalau geo-block, butuh VPN (configure HTTP_PROXY env var sebelum start PyScrapr).

### Problem: Download sangat lambat (~50KB/s) padahal internet cepat
**Gejala:** Progress crawl sangat lambat, ETA berjam-jam.
**Penyebab:** YouTube throttling kadang di pengguna anonymous. Format yang dipilih pakai DASH yang per-chunk lambat.
**Solusi:** Aktifkan cookie browser (signed-in user dapat bandwidth lebih baik). Coba format berbeda - `best` kadang pick DASH sedangkan preset `1080p` pakai progressive stream.

### Problem: "ffmpeg not found" error
**Gejala:** Error saat merge video+audio atau convert format.
**Penyebab:** `imageio_ffmpeg` gagal extract binary, atau permission issue.
**Solusi:** Reinstall `pip install --force-reinstall imageio_ffmpeg`. Cek path via Python: `from imageio_ffmpeg import get_ffmpeg_exe; print(get_ffmpeg_exe())` - pastikan file ada dan executable.

### Problem: Cookie browser tidak terbaca
**Gejala:** Error `Unable to load cookies from Chrome` atau download tetap gagal seperti non-logged-in.
**Penyebab:** Chrome encrypt cookie dengan OS keychain (di Windows dengan DPAPI). `browser_cookie3` kadang gagal jika Chrome sedang running dan holding lock.
**Solusi:** Tutup total browser (semua window + background process). Re-run. Untuk Chrome encrypted, pastikan PyScrapr run sebagai user yang sama dengan Chrome profile.

### Problem: Playlist hanya download sebagian, stuck di tengah
**Gejala:** Item 1-20 OK, item 21+ semua fail, tidak ada progress.
**Penyebab:** Rate limit per session kena. YouTube throttle kalau IP sama download terlalu cepat.
**Solusi:** Turunkan `concurrent_downloads` ke 1. Set delay antar item via `sleep_interval` di advanced. Resume lewat `download_archive` setelah cooldown 30 menit.

### Problem: File output corrupt / tidak bisa play
**Gejala:** Download selesai tapi player error "invalid format" atau video pixelated.
**Penyebab:** Merge video+audio gagal silent, atau download terpotong tanpa error proper.
**Solusi:** Cek file via ffprobe: `ffprobe <file>.mp4`. Kalau corrupt, delete dan re-download dengan format berbeda (misal mkv alih-alih mp4). Enable `--keep-fragments` untuk debug.

### Problem: Disk space penuh di tengah download playlist
**Gejala:** Error space, setengah file sudah ada.
**Penyebab:** Estimasi salah karena video bervariasi resolution.
**Solusi:** Aktifkan `estimate_size_before_download` - tool hitung total dulu sebelum commit. Pindah output ke external drive untuk bulk.

### Problem: Subtitle embed tapi tidak muncul di player
**Gejala:** MKV file ada, subtitle claim embedded, tapi VLC/player tidak menampilkan.
**Penyebab:** Subtitle embed format mismatch (srt dalam mp4 container tidak support di semua player).
**Solusi:** Pakai MKV container untuk embed (lebih fleksibel). Atau download sebagai `.srt` terpisah, load manual di player.

### Problem: Twitter/X video tidak bisa di-download
**Gejala:** Error khusus Twitter, padahal URL valid.
**Penyebab:** Twitter API berubah (sering), yt-dlp versi Anda mungkin outdated untuk perubahan terbaru.
**Solusi:** Update yt-dlp ke nightly: `pip install -U --pre yt-dlp`. Cek GitHub issues yt-dlp untuk breaking change terbaru.

### Problem: TikTok download no-watermark tapi tetap ada watermark
**Gejala:** Download berhasil, tapi video punya TikTok logo.
**Penyebab:** Default config pakai watermarked stream. Need specific format selector.
**Solusi:** Di advanced, set `format: "download_addr"` (no-watermark stream) alih-alih default. Ini implementation-specific, ubah-ubah dengan update yt-dlp.

### Problem: Metadata tidak ter-embed di MP3
**Gejala:** File MP3 tanpa artist/title/album tags, player show filename saja.
**Penyebab:** `embed_metadata` off, atau library mutagen missing.
**Solusi:** Aktifkan `embed_metadata`. Install: `pip install mutagen`. Re-download atau run post-processor manual.

### Problem: Live stream recording stuck / tidak berhenti
**Gejala:** Job jalan terus, live stream sudah berakhir di source.
**Penyebab:** Live stream format (HLS) tidak signal EOF proper.
**Solusi:** Set `duration_limit` di advanced (misal 7200 untuk 2 jam max). Manual stop via button Cancel kalau perlu.

## FAQ

**Q: Berapa banyak site yang support?**
A: yt-dlp saat ini support 1700+ site. List lengkap: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md. Termasuk site populer Indonesia seperti Vidio, RCTI+, dll.

**Q: Apakah legal download YouTube video?**
A: Tergantung juridiksi dan use case. Personal archival di banyak negara diperbolehkan fair use. Re-upload atau komersialisasi tanpa izin pemilik = pelanggaran. PyScrapr adalah tool, tanggung jawab legal di user.

**Q: Bisa download livestream real-time?**
A: Ya - yt-dlp support HLS live recording. Aktifkan saat stream berjalan, tool akan record sampai stream berakhir atau Anda stop manual.

**Q: Format terbaik untuk arsip jangka panjang?**
A: Video: MKV dengan AV1/VP9 codec (open, future-proof). Audio: FLAC (lossless) atau Opus (compactness). Hindari MP3 kalau bisa - lossy legacy.

**Q: Bagaimana cara download hanya chapter tertentu?**
A: Probe video dulu untuk lihat chapter list. Pakai `--download-sections "*<start_time>-<end_time>"` via advanced custom yt-dlp args. PyScrapr UI belum expose chapter picker - WIP.

**Q: Apakah bisa resume download yang gagal?**
A: Ya - yt-dlp otomatis resume dari partial file (.part). Job yang marked failed di History bisa di-retry tanpa download ulang chunk yang sudah ada.

**Q: Kenapa video 8K available di YouTube tapi preset 4k saja?**
A: Default preset cap di 4K karena file size besar (10+ GB per jam). Aktifkan `best` preset atau custom format selector untuk true source quality.

**Q: Playlist YouTube private bisa di-download tidak?**
A: Ya, dengan cookie browser dari akun yang punya akses. Pastikan playlist tidak "unlisted-but-restricted".

**Q: Bagaimana dengan DRM content (Netflix, HBO, dll)?**
A: Tidak support. DRM content pakai Widevine CDM yang yt-dlp (dan hampir semua open-source tool) tidak decrypt. Don't even try.

**Q: Output naming bisa custom?**
A: Ya - lewat `output_template` pakai yt-dlp template syntax: `%(uploader)s/%(upload_date)s_%(title)s.%(ext)s`. Banyak variable tersedia di yt-dlp docs.

## Keterbatasan

- Tidak bisa bypass DRM (Netflix, Disney+, HBO Max, dll).
- Live stream recording terbatas ke format HLS/DASH standar.
- Tidak support site dengan CAPTCHA wajib (kadang Instagram).
- Rate limit server target bisa memblock - tidak ada magic bypass.
- Playlist besar (>1000 item) butuh waktu probe lama.
- Cookie encryption Chrome kadang tidak ter-decrypt di edge case.
- Quality preset `best` tidak selalu benar-benar tertinggi (tergantung API response).
- Thumbnail embed terbatas JPG/PNG - AVIF belum didukung penuh.
- Subtitle auto-translate tidak tersedia di sisi PyScrapr.
- Update yt-dlp butuh rebuild backend, bukan hot-patch.

## Related docs

- [Pipeline: Audio Processing](/docs/utilities/pipeline.md) - convert, normalize, transcribe
- [Image Harvester](image-harvester.md) - untuk thumbnail/gambar artikel
- [AI Tagger](ai-tools.md) - klasifikasi thumbnail video
- [Scheduler](/docs/system/scheduled.md) - auto-download channel update
- [yt-dlp upstream docs](https://github.com/yt-dlp/yt-dlp/blob/master/README.md) - detail format selector dan advanced flags
- [History](../system/history.md) - track dan replay download
