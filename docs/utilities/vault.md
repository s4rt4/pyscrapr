# Auth Vault

> Tempat penyimpanan profil otentikasi per-domain (cookies, header HTTP, catatan) yang otomatis dipakai oleh semua tool fetch di PyScrapr saat URL target-nya cocok dengan domain yang tersimpan. Mendukung import cookie dari browser Chrome/Firefox/Edge/Brave.

## Deskripsi

Auth Vault memecahkan masalah yang menghantui setiap scraper: "bagaimana cara akses konten yang butuh login tanpa saya harus copy-paste cookie manual setiap job?". Solusinya: sekali setup profil untuk `example.com` - simpan cookies login dan custom headers - lalu setiap kali Image Harvester, Site Ripper, Media Downloader, atau tool lain fetch URL yang domain-nya `example.com`, otentikasi otomatis di-inject tanpa konfigurasi tambahan.

Data disimpan di file flat `data/auth_vault.json` dengan struktur list of profile objects. Setiap profile berisi: `domain` (string, primary key), `cookies` (list of cookie dicts seperti `{"name": "...", "value": "...", "domain": "...", "path": "/"}`), `headers` (dict key-value seperti `{"Authorization": "Bearer xyz", "X-API-Key": "..."}`), dan `notes` (free-text untuk diri Anda sendiri, misalnya "expires 2026-06, pakai akun tester"). CRUD lewat REST API di `app/api/vault.py` - tidak ada enkripsi at rest, jadi **jangan commit file ini ke Git**.

Resolusi domain saat fetch dilakukan di `http_factory.build_client(target_url=...)`. Algoritma: parse `target_url.netloc`, coba exact match (misal `shop.example.com`); jika tidak ada, strip prefix `www.` dan coba lagi; jika masih tidak ada, ambil parent domain 2 bagian terakhir (`example.com`) sebagai fallback. Ini memungkinkan profile `example.com` dipakai untuk semua subdomain-nya tanpa duplikasi, sambil tetap memberi opsi override spesifik per-subdomain jika ditambahkan.

Fitur import browser menggunakan library `browser_cookie3` yang membaca cookie database SQLite lokal Chrome/Firefox/Edge/Brave. Saat user trigger import, PyScrapr membuka file cookie browser (harus close browser dulu di Windows karena lock), decrypt value menggunakan master key OS-specific, lalu dump ke format Auth Vault. Domain filter opsional memungkinkan hanya import cookie untuk domain tertentu (misal ketik "facebook.com" → hanya cookie FB, bukan semua). **Perhatikan**: import bersifat full replacement untuk domain yang match; jika sudah ada profile lama, akan di-overwrite.

## Kapan pakai tool ini?

1. **Situs dengan login required** - forum, member area, paywalled content, internal tools.
2. **API dengan Bearer token** - simpan header `Authorization: Bearer xyz` per-domain untuk akses API scraping.
3. **Akses konten regional** - setelah pakai VPN/proxy di browser, simpan cookie region-specific.
4. **Bypass CSRF minimal** - situs yang cek header `Referer` atau `Origin` tertentu.
5. **Menjaga session scraping panjang** - hindari re-login setiap job baru.
6. **Multi-akun** - simpan 2 profil untuk domain yang sama tidak didukung langsung (domain = unique key), tapi bisa workaround dengan edit manual JSON.
7. **Share config antar mesin** - export `auth_vault.json`, pindah ke PC lain (via secure transfer), import - profil langsung aktif.
8. **Testing otentikasi** - eksperimen cookie/header dengan cepat tanpa edit source code.

## Cara penggunaan

1. **Buka Auth Vault** - sidebar `Auth Vault`. Ekspektasi: tabel daftar profile yang sudah ada.
2. **Klik `Add profile`** - modal `Add auth profile` muncul. Ekspektasi: field `Domain`, `Cookies (JSON)`, `Headers (JSON)`, `Notes`.
3. **Isi `Domain`** - format bare tanpa scheme, misal `example.com`. Untuk subdomain spesifik: `shop.example.com`. Ekspektasi: input text, lowercase normalization di backend.
4. **Tambahkan `Cookies (JSON)`** - paste JSON object key-value seperti `{"session_id": "abc123"}`. Ekspektasi: editor JSON dengan format-on-blur, validasi saat save.
5. **Tambahkan `Headers (JSON)`** - paste JSON object key-value. Contoh: `{"Authorization": "Bearer eyJ...", "User-Agent": "MyCustomUA/1.0"}`. Ekspektasi: format object standard.
6. **Tulis `Notes`** - kapan cookie ini expire, dari akun mana, dll. Ekspektasi: bebas text.
7. **Klik `Save profile`** - upsert ke `auth_vault.json`. Ekspektasi: toast sukses, modal close, tabel refresh dengan entry baru.
8. **Alternatif: Import dari Browser** - klik `Import from browser`, pilih `Browser` (Chrome/Firefox/Edge/Brave), optionally isi `Domain filter (optional)`. Ekspektasi: modal `Import cookies from browser` terbuka, klik `Import cookies` untuk proses.
9. **Review setelah import** - cek jumlah cookie yang di-import, edit profile kalau perlu hapus cookie sensitif.
10. **Test profile** - jalankan Image Harvester atau tool lain pada URL yang match domain profile; cek log/hasil untuk konfirmasi cookie di-kirim.
11. **Edit existing profile** - saat ini edit inline belum tersedia; add profile dengan domain yang sama untuk overwrite entry existing.
12. **Hapus profile** - klik ikon trash (tooltip `Delete`) di kolom paling kanan tabel, konfirmasi `window.confirm` browser. Ekspektasi: entry hilang dari JSON dan tabel.

## Pengaturan / Konfigurasi

### Domain

Primary key profile. Format: bare domain tanpa scheme dan tanpa path. Normalisasi ke lowercase otomatis. Contoh valid: `example.com`, `api.example.com`, `co.uk`. Tidak boleh: `https://example.com/`, `example.com/path`.

### Cookies (JSON)

Object JSON dengan key-value, di mana key = nama cookie dan value = value cookie. Contoh:
```json
{
  "session_id": "abc123xyz",
  "csrf_token": "def456"
}
```
Import dari browser akan populate struktur ini otomatis. Untuk detail cookie seperti path/domain/expires, lakukan import dari browser agar metadata ikut terbawa.

### Headers

Dict JSON key-value. Semua string. Contoh:
```json
{
  "Authorization": "Bearer eyJhbGc...",
  "X-CSRF-Token": "csrf_value",
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "Accept-Language": "id-ID,id;q=0.9,en;q=0.8"
}
```
Kalau header yang sama dikirim oleh tool lain (misal default UA), header dari Vault akan override.

### Notes

Free-text, tidak ter-parse. Murni untuk reminder Anda sendiri.

### Import from Browser

Dialog/modal dengan field:
- **Browser**: enum `chrome` | `firefox` | `edge` | `brave`.
- **Domain filter (optional)**: jika diisi, hanya cookie yang domain-nya match akan di-import. Kosong = semua domain.
- **Profile path (optional)**: untuk browser dengan multiple profile (misal `Profile 1`); default ke profile primary.

Backend (`browser_cookie3`) butuh browser tertutup di Windows karena cookie DB di-lock. Di macOS/Linux kadang bisa concurrent.

### Upsert Behavior

Save dengan domain yang sudah ada akan **overwrite** seluruh record (cookies, headers, notes), bukan merge. Jika ingin merge, edit manual lalu save.

### File Path

`data/auth_vault.json` relatif ke root PyScrapr. Backup dengan copy file.

## Output

Satu-satunya output persistence adalah `data/auth_vault.json`. Format:
```json
[
  {
    "domain": "example.com",
    "cookies": [...],
    "headers": {...},
    "notes": "..."
  },
  {
    "domain": "other.com",
    "cookies": [...],
    "headers": {...},
    "notes": "..."
  }
]
```
Tidak ada log audit siapa modifikasi kapan. Tidak ada history versi.

## Integrasi dengan fitur lain

1. **Image Harvester** - auto-inject cookie/header saat fetch halaman target dan image asset.
2. **Site Ripper** - setiap crawl request lewat `http_factory` akan pakai Vault. Essential untuk mirror situs auth-gated.
3. **Media Downloader** - download file dari URL yang butuh cookie auth (misal konten premium).
4. **URL Mapper** - crawl situs yang butuh login; tanpa Vault hanya bisa akses public area.
5. **Custom Pipeline** - script bisa baca `data/auth_vault.json` langsung untuk lookup credentials per-domain jika butuh request custom.

## Tips & Best Practices

1. **Import segera setelah login** - cookie freshest, expire jauh. Jangan import kalau Anda belum login di browser.
2. **Update berkala** - cookie session biasanya expire 1-30 hari. Set reminder kalender untuk re-import.
3. **Sanitize sebelum import all** - filter domain saat import agar tidak menyimpan cookie perbankan/email Anda di vault.
4. **Jangan share `auth_vault.json`** - isinya setara password. Tambah ke `.gitignore`, enkripsi kalau backup ke cloud.
5. **Pakai akun tester** - untuk scraping repeat, gunakan akun disposable, bukan akun utama Anda (risiko ban).
6. **Dokumentasikan di Notes** - "cookie expire 2026-05-01, dari akun user@test.com, re-login via OTP" - Anda akan berterima kasih kemudian.
7. **Gunakan exact subdomain bila perlu** - kalau `shop.example.com` butuh cookie berbeda dari `blog.example.com`, buat dua profile terpisah.
8. **Test segera setelah save** - jalankan fetch percobaan; kalau dapat 401, cookie mungkin salah format atau sudah expire.

## Troubleshooting

### Problem: Import from Browser error "database is locked"
- **Symptom**: Chrome import gagal di Windows.
- **Cause**: Chrome masih running, cookie DB di-lock.
- **Solution**: close semua window Chrome (termasuk background task dari system tray), tunggu 5 detik, retry import.

### Problem: Import berhasil tapi fetch masih 401
- **Symptom**: cookie jelas tersimpan, tapi Harvester masih dapat "Unauthorized".
- **Cause**: (1) cookie path/domain salah sehingga tidak match URL target; (2) situs tambahan butuh header (CSRF, Origin); (3) cookie sudah expire antara import dan fetch.
- **Solution**: (1) cek di DevTools browser, lihat Request Headers untuk halaman yang sama - bandingkan dengan yang di vault. (2) tambah header manual ke profile. (3) re-login di browser, import ulang.

### Problem: Cookie ter-import banyak tapi yang penting (session) tidak ada
- **Symptom**: 50 cookie tracking tapi tidak ada `JSESSIONID` / `session`.
- **Cause**: cookie `httpOnly` kadang perlu permission lebih; atau cookie ada di profile browser yang berbeda.
- **Solution**: pastikan login di browser profile yang benar; coba profile path override saat import.

### Problem: Firefox import error "no such file"
- **Symptom**: error path ke cookies.sqlite.
- **Cause**: Firefox profile directory bukan default, atau Firefox Flatpak/Snap di Linux.
- **Solution**: cari path manual (`about:support` → Profile Directory), edit backend untuk point ke path itu, atau copy file cookies.sqlite ke lokasi default.

### Problem: Upsert malah duplicate (dua entry domain sama)
- **Symptom**: tabel menampilkan `example.com` dua kali.
- **Cause**: save race condition, atau edit manual JSON yang buat duplikasi.
- **Solution**: hapus duplikasi manual di `data/auth_vault.json`, save ulang. Restart backend untuk reload.

### Problem: Profile tidak ter-apply saat fetch
- **Symptom**: Log fetch tidak menunjukkan cookie di Request, padahal profile ada.
- **Cause**: domain resolution gagal - misal URL target `https://cdn.example.com/img.jpg`, profile `example.com`, tapi resolusi fallback ke 2-part gagal karena CDN-nya punya domain pihak ketiga.
- **Solution**: tambah profile spesifik untuk `cdn.example.com`, atau hardcode domain cookie ke `.example.com`.

### Problem: Cookie Secure tidak ter-kirim di HTTP
- **Symptom**: situs HTTP (non-TLS) tidak pakai cookie meski Secure=false.
- **Cause**: cookie punya flag `Secure: true` - memang hanya dikirim di HTTPS.
- **Solution**: edit cookie, set `secure: false` jika memang target HTTP. Tapi idealnya situs target pakai HTTPS.

### Problem: Import Brave tapi salah profile
- **Symptom**: cookie di-import dari profile default, padahal Anda pakai profile kerja.
- **Cause**: Brave multi-profile, default selected pertama.
- **Solution**: kalau UI tidak expose profile picker, edit backend untuk iterate profile atau pilih manual.

### Problem: JSON editor reject input valid
- **Symptom**: paste array cookie yang Anda yakin valid, save error "Invalid JSON".
- **Cause**: smart quotes (kutip keriting) dari paste, atau trailing comma.
- **Solution**: paste via plain text editor dulu untuk sanitize, atau tulis manual di JSON editor.

## FAQ

**Q: Apakah Auth Vault enkripsi data?**
A: Tidak. File plain JSON. Protect dengan filesystem permission.

**Q: Bisa pakai per-user authentication (login ke PyScrapr)?**
A: PyScrapr tool personal tanpa multi-user. Tidak ada auth PyScrapr.

**Q: Bisa import dari Safari?**
A: Tidak di `browser_cookie3` saat ini (Safari pakai keychain, lebih kompleks).

**Q: Cookie kadaluarsa - ada notifikasi?**
A: Tidak. Anda monitor manual lewat Notes atau trial.

**Q: Bisa 2 profile untuk domain sama (multi-akun)?**
A: Tidak via UI. Workaround: subdomain berbeda (kalau applicable), atau edit JSON manual dengan "domain": "example.com#akun2" lalu rewrite resolver.

**Q: Cookie di-refresh otomatis saat re-login di browser?**
A: Tidak. Re-import manual.

**Q: Apakah domain resolution case-sensitive?**
A: Tidak - di-normalize lowercase.

**Q: Tool bypass Cloudflare (cf_clearance) didukung?**
A: Ya, selama Anda import cookie setelah lulus CF challenge di browser. Cookie `cf_clearance` akan tersimpan dan dikirim.

**Q: Bisa share vault via QR / cloud sync?**
A: Tidak built-in. Copy file manual.

**Q: Berapa banyak profile yang disupport?**
A: Tidak ada hard limit. File JSON bisa handle ribuan profile tanpa masalah performance signifikan.

## Keterbatasan

- **Tidak terenkripsi** - file plaintext di disk.
- **Tidak ada expiry tracking** - cookie expire tidak di-warn.
- **Tidak multi-akun per-domain** - satu profile per domain.
- **Browser harus closed untuk import (Windows)** - agak mengganggu workflow.
- **Tidak support Safari, Opera (di luar Chromium-based)** - browser_cookie3 limitation.
- **Tidak ada audit log** - siapa ubah apa kapan tidak ter-track.
- **Tidak ada validasi format cookie deep** - invalid cookie dengan field aneh bisa tersimpan, error muncul saat fetch.
- **Import full replacement** - tidak bisa partial merge otomatis.

## Related docs

- [Image Harvester](../tools/image-harvester.md) - konsumen utama Vault untuk fetch halaman auth-gated.
- [Site Ripper](../tools/site-ripper.md) - pakai Vault untuk mirror situs login-required.
- [Media Downloader](../tools/media-downloader.md) - download file yang butuh auth.
- [Custom Pipeline](./pipeline.md) - akses `auth_vault.json` langsung dari script.
- [Index dokumentasi](../index.md) - navigasi utama.
