# Settings

> Halaman konfigurasi global dengan 30+ opsi yang tersimpan di `data/settings.json`, mencakup default tiap tool, preferensi UI, webhook config, dan dependency management.

## Deskripsi

Settings adalah control panel tempat Anda memutuskan bagaimana PyScrapr harus berperilaku secara default, sebelum Anda mengoverride per-job via form masing-masing tool. Bayangkan ini sebagai "preferences" aplikasi - pilih default depth untuk Harvester, preferred codec untuk Media Downloader, threshold warning disk, URL webhook Discord, dan berbagai knob lain - lalu semua tool dan halaman akan mengkonsumsi setting ini otomatis. Dengan begitu Anda tidak perlu mengisi field yang sama berulang kali di tiap submission.

Semua setting tersimpan di file JSON flat di `data/settings.json` di root app. Struktur file mirror struktur UI: top-level keys adalah section (scraping, image_filter, url_mapper, media, ripper, ui, webhooks, dependencies), dan tiap section berisi nested keys untuk setting individual. Format ini sengaja dipilih plain JSON agar mudah di-version-control, di-backup, atau di-edit manual dengan text editor tanpa butuh DB migration. Saat startup, PyScrapr memuat file ini ke memory dan menyediakan accessor helpers untuk backend code maupun endpoint GET `/api/settings` yang di-consume frontend.

UI Settings menggunakan layout tabbed atau accordion (tergantung lebar layar) dengan delapan section utama. Tiap field dilengkapi label, helper text yang menjelaskan fungsi, dan validasi realtime (misal angka harus positive, URL harus valid format). Di pojok kanan atas ada tombol "Save changes" yang disabled sampai ada dirty field - konvensi UX yang mencegah save yang tidak perlu dan memberi feedback visual bahwa ada perubahan pending. Ada juga tombol "Reset to defaults" dengan konfirmasi dialog, yang me-restore semua field ke nilai factory default jika Anda kehilangan arah setelah eksperimen.

Section Dependencies adalah yang cukup unik - ia bukan sekadar text field setting, melainkan integration panel yang menampilkan versi installed dari `yt-dlp` dan `browser-cookie3` (dua dependency yang sering butuh update untuk mengimbangi perubahan target situs), serta tombol one-click update yang menjalankan `pip install --upgrade` di backend dan auto-reload modul. Fitur ini mengurangi friction maintenance untuk user non-developer yang tidak familiar dengan terminal.

## Kapan pakai?

1. **Onboarding awal setelah install** - Atur preferensi Anda (folder download, default codec, timezone) sebelum mulai menjalankan job pertama.
2. **Configure webhook sekali untuk notifikasi permanen** - Isi Discord URL atau Telegram token sekali, lalu semua job otomatis notify sesuai trigger.
3. **Switch target environment** - Ubah proxy atau user-agent default ketika berpindah konteks (misal dari home network ke VPN work).
4. **Update dependency yt-dlp** - Ketika YouTube ubah struktur dan yt-dlp perlu di-upgrade untuk tetap kompatibel.
5. **Tweak performance** - Turunkan concurrent workers atau timeout jika mesin low-resource; naikkan jika server kuat.
6. **Adjust UI preferences** - Ubah theme, density, refresh interval sesuai preferensi personal.
7. **Reset setelah eksperimen** - Setelah testing banyak setting untuk troubleshoot, tombol Reset to defaults balikkan semuanya ke known-good state.
8. **Export untuk sharing config** - Copy file `data/settings.json` ke mesin lain untuk replikasi setup cepat.

## Cara penggunaan

1. Buka halaman Settings via icon gear di navbar atau URL `/settings`.
2. Halaman menampilkan tabs: Scraping, Image Filter, URL Mapper, Media, Ripper, UI, Webhooks, Dependencies. Klik tab sesuai area yang ingin diedit.
3. Scroll melalui field di tab tersebut. Tiap field punya label tebal, input widget (text/number/toggle/dropdown), dan helper text abu-abu di bawah.
4. Edit field yang ingin diubah. Tombol "Save changes" di toolbar menjadi enabled dan warna berubah mencolok.
5. Jika ingin membatalkan perubahan, klik "Discard" untuk reset field ke nilai tersimpan.
6. Klik "Save changes" untuk persist. Loading state muncul sebentar, lalu toast hijau "Settings saved" muncul.
7. Untuk reset satu section ke defaults, klik tombol "Reset section" di header tab tersebut.
8. Untuk reset global semua section, klik "Reset to defaults" di toolbar utama dan confirm di dialog.
9. Section Dependencies punya tombol "Check for updates" yang query PyPI dan tampilkan versi terbaru vs installed.
10. Jika ada update, tombol "Update now" muncul. Klik untuk jalankan pip upgrade di backend. Loading bar indicates progress.
11. Setelah update, restart aplikasi mungkin diperlukan (dialog akan notify jika perlu).
12. About section di bawah halaman menampilkan info build (stack, versi PyScrapr, Python version, platform).

## Pengaturan / Konfigurasi

Breakdown per section (nama field adalah key di JSON):

### Section: scraping
- **default_timeout** (int detik, default 30) - Timeout HTTP request default untuk semua tool.
- **default_retry_count** (int, default 3) - Jumlah retry otomatis saat request gagal.
- **default_concurrency** (int, default 5) - Jumlah concurrent request parallel.
- **default_user_agent** (string) - UA string fallback sebelum UA Rotation ambil alih.
- **respect_robots** (boolean, default true) - Apakah default menghormati `robots.txt`.

### Section: image_filter
- **min_width** (int px, default 100) - Minimum width image yang didownload.
- **min_height** (int px, default 100) - Minimum height.
- **min_size_kb** (int KB, default 10) - Minimum ukuran file.
- **allowed_formats** (array, default `["jpg","png","webp","gif"]`) - Whitelist ekstensi.
- **dedupe_by_hash** (boolean, default true) - Skip duplikat berdasarkan hash.

### Section: url_mapper
- **default_max_depth** (int, default 3) - Kedalaman crawl default.
- **default_max_pages** (int, default 500) - Maksimum halaman di-crawl.
- **follow_external** (boolean, default false) - Apakah ikuti link ke domain lain.
- **include_fragments** (boolean, default false) - Apakah URL dengan `#hash` dihitung unik.

### Section: media
- **preferred_codec** (string, default `best`) - Codec preference yt-dlp.
- **max_resolution** (string, default `1080p`) - Resolusi maksimum default.
- **subtitle_langs** (array, default `["en","id"]`) - Bahasa subtitle untuk download.
- **embed_metadata** (boolean, default true) - Embed thumbnail + metadata ke file.
- **cookies_from_browser** (string enum: `chrome`, `firefox`, `edge`, `none`, default `none`) - Source cookies untuk autentikasi.

### Section: ripper
- **default_max_pages** (int, default 200) - Batas halaman ripper.
- **default_max_depth** (int, default 5) - Batas kedalaman.
- **asset_types** (array, default `["css","js","img","font"]`) - Jenis asset yang di-download.
- **rewrite_links** (boolean, default true) - Rewrite absolute ke relative untuk offline browsing.

### Section: ui
- **theme** (enum `light`, `dark`, `auto`, default `auto`) - Tema warna.
- **density** (enum `compact`, `comfortable`, default `comfortable`) - Kerapatan spacing UI.
- **refresh_interval** (int ms, default 3000) - Polling interval shared.
- **timezone** (string, default auto-detect) - IANA timezone untuk display timestamp.
- **language** (enum `id`, `en`, default `id`) - Bahasa UI.

### Section: webhooks
- **discord_url** (string URL, optional) - Discord webhook URL lengkap.
- **telegram_token** (string) - Bot token dari @BotFather.
- **telegram_chat_id** (string) - Target chat ID.
- **generic_http_url** (string URL, optional) - Custom HTTP POST endpoint.
- **trigger_on_done** (boolean, default true) - Fire saat job done.
- **trigger_on_error** (boolean, default true) - Fire saat error.
- **trigger_on_diff** (boolean, default false) - Fire saat diff significant.

### Section: dependencies
- **yt_dlp_version** (read-only, string) - Versi terdeteksi.
- **browser_cookie3_version** (read-only, string) - Versi terdeteksi.
- **auto_check_updates** (boolean, default true) - Auto-check saat startup.

## Output

Settings menghasilkan satu file utama: `data/settings.json`. Format plain JSON flat dengan keys nested per section. File ini di-read saat:
- Startup aplikasi (full load ke memory).
- Endpoint `/api/settings` dipanggil dari frontend.
- Individual accessor `get_setting(key)` dipanggil dari kode tool.

File ini safe di-edit manual dengan text editor bila aplikasi stopped; namun saat running, perubahan manual tidak langsung reflect (butuh restart atau call endpoint reload). Format JSON yang plain juga memudahkan backup - cukup copy file, atau version control via Git.

## Integrasi dengan fitur lain

- **Semua tool** - Default config field di tiap tool form di-populate dari Settings relevant section.
- **Webhooks** - Konfigurasi channel + trigger diambil dari section webhooks.
- **Dashboard** - Refresh interval dan thresholds dari section ui.
- **History** - Page size, default sort, export options.
- **Scheduled** - Default timezone dan misfire grace.
- **Proxy/UA Rotation** - List proxy dan ua_mode diambil dari advanced sections.
- **Dependencies** - Runtime check saat Media Downloader dipanggil.

## Tips & Best Practices

1. **Backup settings.json rutin** - Simpan salinan di cloud sync atau USB agar config painstaking tidak hilang saat pindah device.
2. **Jangan naikkan concurrency secara membabi-buta** - Target situs bisa rate-limit atau block jika terlalu agresif. Mulai dari 5, naikkan bertahap.
3. **Aktifkan dedupe_by_hash untuk image-heavy sites** - Hemat disk signifikan.
4. **Set preferred_codec ke `bestvideo+bestaudio`** - Untuk kualitas maksimum saat download via yt-dlp.
5. **Pakai theme=auto** - Otomatis adjust light/dark berdasarkan OS preference untuk comfort mata.
6. **Set trigger_on_error=true minimal** - Untuk awareness jika ada job gagal yang perlu perhatian.
7. **Review Dependencies bulanan** - yt-dlp update frequent; stale version sering penyebab Media Downloader gagal.
8. **Export shareable preset** - Untuk tim, share template settings.json yang sudah dituning untuk target use case mereka.

## Troubleshooting

**Problem: Save changes button tetap disabled walaupun sudah edit field.**
Cause: Form state tidak detect dirty (bug UI) atau field validation gagal diam-diam.
Solution: Refresh halaman dan edit ulang. Cek console untuk validation error. Pastikan value valid (angka positive, URL benar).

**Problem: Setting tersimpan tapi tool tidak menggunakan nilai baru.**
Cause: Tool cache setting di memory dan tidak reload setelah save.
Solution: Restart server untuk force reload penuh, atau implement "reload settings" endpoint (feature).

**Problem: File settings.json corrupt setelah edit manual.**
Cause: JSON syntax error (missing comma, trailing comma, unquoted key).
Solution: Restore dari backup. Gunakan JSON validator online sebelum save manual edit. App akan fallback ke defaults jika corrupt.

**Problem: Dependencies check gagal dengan "ConnectionError".**
Cause: PyPI unreachable dari jaringan (firewall, offline).
Solution: Set `auto_check_updates: false`. Update manual via terminal saat online.

**Problem: Update dependency gagal dengan permission error di Windows.**
Cause: Process tidak punya write access ke site-packages.
Solution: Run PyScrapr as administrator, atau gunakan virtual environment terisolasi.

**Problem: Theme tidak berubah setelah save.**
Cause: localStorage browser override setting, atau CSS cache.
Solution: Clear browser cache + localStorage. Hard reload (Ctrl+Shift+R).

**Problem: Webhook test fires berhasil tapi actual job tidak trigger.**
Cause: Trigger flags (trigger_on_done, trigger_on_error) false atau job tidak reach terminal state.
Solution: Verifikasi flags true. Cek log EventBus untuk event emission.

**Problem: Default values after reset tidak match yang ekspected.**
Cause: Factory defaults di-override oleh environment variables atau config file external.
Solution: Cek env vars (PYSCRAPR_*) yang mungkin override. Delete `data/settings.json` untuk regenerate murni.

**Problem: Dropdown field kosong untuk timezone.**
Cause: Browser tidak support Intl API (sangat jarang) atau JS error.
Solution: Update browser ke versi modern. Fallback ke UTC manual.

## FAQ

**Q: Apakah setting berlaku untuk user lain (multi-user)?**
A: PyScrapr single-user. Setting global untuk instance tersebut.

**Q: Bisa override setting per-job tanpa ubah global?**
A: Ya, form tiap tool menyediakan field yang override global untuk job itu saja.

**Q: Dimana setting tersimpan di filesystem?**
A: `<app_root>/data/settings.json`. Lokasi ini bisa diubah via env var `PYSCRAPR_DATA_DIR`.

**Q: Apakah ada setting yang butuh restart untuk apply?**
A: Beberapa (misal logging level, DB path). Dialog akan notify saat save.

**Q: Bisa pakai env var untuk override file?**
A: Ya, env var prefix `PYSCRAPR_` dengan nested path underscore (misal `PYSCRAPR_SCRAPING_DEFAULT_TIMEOUT=60`).

**Q: Apakah password webhook tersembunyi di UI?**
A: Telegram token di-mask dengan bullet setelah save. Click "Show" untuk reveal sementara.

**Q: Apakah setting migration antar versi otomatis?**
A: Ada migration script yang jalan saat startup, menambah field baru dengan default. Existing values preserved.

**Q: Bisa export settings ke format lain (YAML, TOML)?**
A: Tidak built-in. Convert manual dengan tool online.

**Q: Apakah setting validate saat load atau hanya saat save?**
A: Validation dilakukan di save UI dan di load startup (dengan fallback ke defaults jika invalid).

**Q: Bisa hide section tertentu dari UI?**
A: Tidak ada toggle visibility. Untuk hide, modifikasi komponen React.

## Keterbatasan

- Format hanya JSON; tidak support YAML/TOML native.
- Tidak ada per-user settings (single-user system).
- Beberapa setting butuh restart untuk full effect.
- Dependency manager hanya support yt-dlp dan browser-cookie3 (tidak generic).
- Tidak ada history/audit perubahan settings.
- Validasi sederhana (tidak cross-field validation, misal thresholds relative).
- Reset tidak selective per-field; hanya section atau global.

## Related docs

- [Dashboard](./dashboard.md) - Konsumer setting refresh_interval dan thresholds.
- [Webhooks](../advanced/webhooks.md) - Section dedicated di Settings.
- [Proxy](../advanced/proxy.md) - Settings proxy_list, proxy_mode.
- [UA Rotation](../advanced/ua-rotation.md) - Setting ua_mode.
- [CAPTCHA](../advanced/captcha.md) - Setting captcha_provider, captcha_api_key.
