# SSL Certificate Inspector

> Tool inspeksi sertifikat TLS/SSL dari hostname target (accept URL atau hostname polos) menggunakan stdlib Python ssl dan socket, tanpa dependency eksternal. Menghasilkan laporan lengkap: subject, issuer, masa berlaku, serial number, daftar SAN, algoritma tanda tangan, versi TLS yang di-negosiasi, cipher yang dipakai, hitungan hari sampai expiry, flag expired, self-signed, hostname match, plus daftar issue. Cocok untuk monitoring certificate renewal, audit compliance, atau debug konfigurasi SSL.

## Apa itu SSL Certificate Inspector

SSL Certificate Inspector adalah modul PyScrapr yang melakukan koneksi TLS handshake langsung ke hostname target di port 443 (atau port lain yang Anda tentukan), mengambil sertifikat server yang ditawarkan, lalu parse informasi lengkap dari sertifikat tersebut. Implementasinya minimalis karena Python stdlib sudah menyediakan semua yang diperlukan: modul `ssl` dan `socket` bisa buka koneksi TLS, negosiasi handshake, dan dump certificate dalam format dictionary via `getpeercert()`.

Data yang di-extract dari sertifikat:
- **Subject**: siapa yang memiliki sertifikat. Biasanya berisi CN (Common Name), O (organization), OU, C (country), dsb.
- **Issuer**: siapa yang menerbitkan sertifikat. Untuk cert production biasanya Let's Encrypt, DigiCert, Sectigo, GoDaddy, dll.
- **Valid from** dan **Valid to**: rentang waktu validity sertifikat.
- **Serial number**: identitas unik sertifikat.
- **Version**: versi format X.509 (biasanya 3).
- **SAN (Subject Alternative Names)**: daftar hostname lain yang juga valid untuk cert ini. Cert modern hampir selalu punya SAN karena CN deprecated.

Analisis tambahan yang di-compute:
- **days_until_expiry**: hari tersisa sampai sertifikat expired.
- **is_expired**: boolean, true kalau valid_to sudah lewat.
- **is_self_signed**: true kalau subject sama persis dengan issuer (tidak valid untuk public trust).
- **hostname_match**: true kalau hostname target cocok dengan CN atau salah satu SAN (dengan wildcard support).
- **tls_version**: versi TLS yang dinegosiasi (TLSv1.2, TLSv1.3, dst).
- **cipher**: nama cipher suite dan jumlah bit.

Issue list dibuat berdasarkan evaluasi tersebut:
- Error kalau sertifikat sudah expired atau hostname tidak match.
- Error kalau expiry < 7 hari (urgent renewal).
- Warning kalau expiry < 30 hari.
- Warning kalau self-signed (tidak boleh di production public).

> [!NOTE]
> Tool ini tidak memvalidasi chain of trust secara strict. Mode verifikasi di-set ke CERT_NONE supaya tetap bisa inspect certificate self-signed atau expired (yang justru penting untuk di-flag). Kalau Anda butuh validate chain, pakai tool terpisah seperti openssl s_client atau testssl.sh.

## Cara pakai (step-by-step)

1. Buka menu **SSL Inspector** di sidebar PyScrapr.

2. Isi field `Hostname atau URL`. Tool accept both format:
   - Hostname polos: `contoh.com`, `api.contoh.com`, `www.example.org`
   - URL lengkap: `https://contoh.com/path`, `http://contoh.com` (path dan scheme akan di-strip, hanya hostname yang dipakai)

3. Atur `Port` kalau perlu. Default 443 untuk HTTPS standard. Gunakan port lain kalau service Anda di custom port (misal 8443 untuk API internal, 993 untuk IMAPS, 465 untuk SMTPS).

4. Klik `Inspect`. Tool buat Job SSL_INSPECT, connect ke `hostname:port` dengan TLS, ambil cert, parse.

5. Hasil tampil dalam bentuk:
   - **Big expiry countdown** di lingkaran besar, menampilkan "X hari lagi" atau "EXPIRED", warna merah kalau expired atau <7 hari, kuning kalau <30 hari, hijau kalau lebih aman
   - **Header info** hostname:port, badge hostname match, badge self-signed kalau applicable, badge TLS version
   - **Tabel Subject** dan **Tabel Issuer** side-by-side
   - **Tabel Detail Sertifikat**: valid_from, valid_to, serial_number, version, tls_version, cipher
   - **Badge SAN list**: semua hostname alternatif yang di-cover cert
   - **Alert list issues**: daftar isu dengan warna severity

6. Tersimpan di History sebagai Job SSL_INSPECT.

## Contoh kasus pakai

- **Monitoring certificate expiry proaktif** - Anda punya 20 domain dengan cert manual. Scheduled job tiap hari scan semua, webhook notify ke Slack kalau ada yang <30 hari. Tidak pernah lagi ada outage karena lupa renew.

- **Debug situs mendadak browser "Not Secure"** - User komplain situs kasih warning. Inspect cepat. Ketahuan cert expired 2 hari lalu karena auto-renew gagal. Renew manual, selesai.

- **Verify migrasi cert** - Anda baru rotate cert lama ke cert baru dengan provider berbeda. Inspect untuk confirm: issuer baru benar, valid_to benar, SAN cover semua subdomain yang perlu.

- **Audit chain di environment staging** - Staging server pakai self-signed cert (normal). Inspect untuk confirm. Production harus Let's Encrypt. Catch kalau ada mix-up deployment.

- **Due diligence SaaS vendor** - Anda evaluate SaaS vendor. Inspect cert subdomain mereka. Cert expired 2 bulan lalu tapi masih live? Red flag operational hygiene.

- **Troubleshoot TLS handshake fail** - Aplikasi Anda tidak bisa connect ke API target, error "certificate verify failed". Inspect API tersebut. Ketahuan issuer-nya root CA private yang tidak ada di trust store Anda. Fix dengan install root CA atau pin cert.

- **Compliance audit trail** - Beberapa standar (PCI DSS, HIPAA) require TLS 1.2+. Scan semua endpoint produksi, pastikan tls_version selalu TLSv1.2 atau TLSv1.3.

## Hostname matching

Tool mengecek apakah hostname yang Anda inspect benar-benar cocok dengan cert. Logika:
1. Cek CN (Common Name) di subject. Kalau sama persis (case-insensitive), match.
2. Cek tiap entry di SAN. Match kalau sama persis, atau kalau SAN pakai wildcard (`*.domain.com`) dan hostname target punya suffix yang sesuai.
3. Kalau tidak satu pun match, flag error.

Wildcard support: `*.contoh.com` match dengan `www.contoh.com`, `api.contoh.com`, tapi TIDAK match dengan `contoh.com` itu sendiri (sesuai spek RFC) atau dengan `foo.bar.contoh.com` (wildcard hanya cover satu level).

## Pengaturan

### port
Port TCP untuk koneksi. Default 443. Gunakan port custom untuk service non-HTTPS (IMAPS 993, SMTPS 465, LDAPS 636, dll).

### timeout
Timeout (detik) untuk koneksi TCP dan TLS handshake. Default 15. Jarang perlu diubah karena handshake biasanya selesai <3 detik.

Tool ini tidak pakai http_factory karena koneksi murni TLS/socket, bukan HTTP. Proxy settings dari http_factory tidak berlaku di sini. Kalau Anda butuh proxy tunnel untuk koneksi ke internal hostname, itu di luar scope tool ini saat ini.

## Tips monitoring

- **Jadwalkan scan harian**. Pakai Scheduled Jobs. Webhook kalau days_until_expiry < 14.
- **Monitor semua subdomain penting**. SAN list memang cover banyak, tapi some domain punya cert terpisah per subdomain.
- **Simpan history untuk diff**. Perubahan issuer tiba-tiba (dari Let's Encrypt ke provider komersial, atau sebaliknya) bisa jadi signal dan perlu di-review.
- **Kombinasikan dengan Security Headers Scanner**. Cert valid + HSTS proper = safer baseline.

## Interpretasi TLS version

| TLS Version | Status 2026 | Aksi |
|-------------|-------------|------|
| TLSv1.3 | Modern, recommended | Pertahankan |
| TLSv1.2 | Acceptable, widely supported | OK untuk legacy client |
| TLSv1.1 | Deprecated sejak 2020 | Upgrade server, disable TLS 1.1 |
| TLSv1.0 | Deprecated sejak 2020 | Urgent upgrade |
| SSLv3 | Broken sejak POODLE | Harus dimatikan total |
| SSLv2 | Broken lama | Sudah tidak support di stdlib modern |

## Troubleshooting

### Problem: Connection refused atau timeout
**Gejala:** Error saat coba inspect hostname. 
**Penyebab:** Port 443 tidak terbuka, firewall block, atau service belum start. 
**Solusi:** Verify dengan `curl -I https://hostname` atau `openssl s_client -connect hostname:443`. Kalau juga fail, confirm service status.

### Problem: Hostname mismatch tapi Anda yakin cert benar
**Gejala:** hostname_match = false. 
**Penyebab:** Anda inspect via IP address, bukan hostname. Atau cert untuk domain lain yang reverse proxy share. 
**Solusi:** Inspect pakai hostname domain, bukan IP. Kalau memang shared hosting, cek SAN list apakah domain Anda termasuk.

### Problem: Days until expiry negatif
**Gejala:** days_until_expiry = -5. 
**Penyebab:** Cert sudah expired. 
**Solusi:** Renew cert segera. Browser akan terus warning user.

### Problem: Self-signed detected di production
**Gejala:** is_self_signed = true di domain public. 
**Penyebab:** Setup testing masuk ke production tanpa replace cert. Atau reverse proxy default cert tidak diganti. 
**Solusi:** Deploy cert real dari Let's Encrypt atau CA komersial. Kalau self-signed legitimate (internal tool), abaikan warning.

### Problem: Cipher lemah
**Gejala:** Cipher name mengandung RC4, DES, atau EXPORT. 
**Penyebab:** Konfigurasi TLS server terlalu permissive. 
**Solusi:** Update cipher suites di config server, disable cipher lama.

### Problem: Subject CN kosong, hanya ada SAN
**Gejala:** Subject dict kosong atau minim. 
**Penyebab:** Modern cert (Let's Encrypt, banyak issuer lain) tidak set CN lagi karena deprecated. 
**Solusi:** Normal. Focus ke SAN untuk hostname match.

### Problem: Cert valid tapi browser masih warn
**Gejala:** Tool bilang valid, tapi Chrome kasih "Not Secure". 
**Penyebab:** Browser validate chain of trust, tool tidak strict. Mungkin issuer tidak ada di trust store browser. 
**Solusi:** Pakai issuer yang well-known (Let's Encrypt, DigiCert). Atau install root CA di client kalau legitimate private CA.

## Keamanan dan etika

> [!WARNING]
> TLS handshake adalah koneksi network ke server target. Log di server pasti mencatat koneksi Anda. Walaupun minimal footprint, respect server.

- Satu koneksi TCP + TLS handshake per scan. Cepat dan ringan.
- Tool tidak mencoba extract private key, tidak exploit cipher weakness, tidak downgrade attack. Pure read.
- Hasil scan adalah snapshot. Cert bisa rotate setiap detik (walaupun biasanya 60-90 hari). Untuk monitoring renewal, scheduled scan lebih reliable daripada satu-off.
- Jangan jadikan tool ini satu-satunya defence. Validate chain, pin cert di critical app, enable HSTS, dan rotate cert proaktif.

## Related docs

- [Security Headers Scanner](security-headers.md) - audit response header, complementary
- [Tech Stack Detector](/docs/tools/tech-detector.md) - deteksi web server untuk context
- [SEO Auditor](seo.md) - audit on-page SEO
- [Scheduled Jobs](/docs/system/scheduled.md) - jadwalkan SSL inspection harian atau mingguan
- [Webhooks](/docs/advanced/webhooks.md) - notify kalau days_until_expiry di bawah threshold
- [History](/docs/system/history.md) - track perubahan cert dari waktu ke waktu
