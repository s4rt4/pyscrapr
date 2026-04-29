# Exposure Scanner

> Exposure Scanner adalah tool audit di tier PyScrapr yang memeriksa apakah situs target meng-expose path sensitif yang tidak seharusnya bisa diakses publik. Bukan brute force, bukan fuzzing acak: tool ini cek 30 path "known leak" yang dunia keamanan sudah konsensusi sebagai kebocoran umum, mulai dari `.git/HEAD` (source code repo bocor), `.env` (credential), `wp-config.php.bak` (backup config WordPress), `.DS_Store` (mac directory listing), sampai `*.sql` dump database. Setiap path di-probe HEAD-then-GET, divalidasi plausibility (bukan cuma "200 OK" tapi "isinya betul-betul `.env` syntax atau git pack format"), lalu di-grade dengan severity. Output rapi dengan severity color-coded (critical/high/medium/low/info), risk score, dan rekomendasi remediasi per finding. Designed untuk audit situs sendiri atau klien yang Anda dapat izin tertulisnya.

## Apa itu Exposure Scanner

Mayoritas data breach mid-tier bukan dari serangan canggih. Mereka berasal dari developer yang lupa bahwa folder `.git/` deploy ke production, atau intern marketing yang upload `database_backup.sql` ke `/uploads/` lalu lupa hapus, atau sysadmin yang copy `wp-config.php` ke `wp-config.php.bak` sebelum edit dan lupa cleanup. Path-path ini tidak di-link dari mana-mana, tidak ada di sitemap, dan crawler regular tidak akan menemukan. Tapi mereka tetap accessible kalau Anda tahu URL-nya, dan attacker punya wordlist persis berisi URL-URL itu.

Exposure Scanner adalah jawaban PyScrapr untuk pertanyaan: "Apa saja path standar yang sering bocor, dan apakah situs saya bocor di salah satunya?". Tool jalankan probing minimal-aggressive (30 request total dengan throttle), validasi setiap finding via plausibility check, lalu return verdict.

Positioning tool ini berbeda dari OWASP ZAP active scan atau Burp Intruder. Tool ini tidak fuzz parameter, tidak inject payload, tidak brute force credential, tidak load wordlist 100K. Cuma cek 30 path yang sudah well-known sebagai leak. Footprint kecil, false positive rendah, signal-to-noise tinggi.

Tool ini melayani tiga audience utama. Pertama, founder dan tech lead startup yang audit production stack mereka pasca-deploy. Kedua, freelancer / agency yang inherit project klien dari developer sebelumnya dan butuh quick check kebersihan. Ketiga, bug bounty hunter yang lakukan responsible disclosure setelah menerima invite dari program publik.

> [!WARNING]
> Pakai tool ini hanya di domain Anda sendiri, klien dengan izin tertulis, atau target bug bounty yang scope-nya jelas allow recon ini. Walaupun probing-nya minimal-aggressive (30 request, dengan throttle), unauthorized scanning bisa melanggar Computer Misuse Act / UU ITE / equivalent di yurisdiksi Anda. Lihat section Etika di bawah.

## Daftar path yang dicek

Tool punya 30 path baseline yang dikelompokkan dalam 7 kategori. Daftar ini di-curate berdasarkan analisis incident report publik OWASP, SANS, dan pengalaman komunitas pentest.

### VCS / source code (paling kritis)

| # | Path | Apa yang bocor |
|---|------|----------------|
| 1 | `/.git/HEAD` | Indicator git repo aktif di docroot. Kombinasi dengan `git-dumper` bisa rekonstruksi seluruh source code |
| 2 | `/.git/config` | Remote URL repo (sering punya credential embedded) |
| 3 | `/.git/logs/HEAD` | History commit |
| 4 | `/.svn/entries` | SVN repo aktif |
| 5 | `/.hg/hgrc` | Mercurial repo aktif |
| 6 | `/.bzr/branch-format` | Bazaar repo aktif |

### Environment / credential

| # | Path | Apa yang bocor |
|---|------|----------------|
| 7 | `/.env` | Environment variable file - sering berisi DB credential, API key, secret |
| 8 | `/.env.local` | Environment variable local override |
| 9 | `/.env.production` | Environment variable production |
| 10 | `/.env.backup` | Backup file `.env` |

### Backup files

| # | Path | Apa yang bocor |
|---|------|----------------|
| 11 | `/wp-config.php.bak` | Backup config WordPress dengan DB credential |
| 12 | `/wp-config.php~` | Vim backup file config WordPress |
| 13 | `/config.php.bak` | Backup config aplikasi PHP generic |
| 14 | `/database.sql` | Dump database |
| 15 | `/db_backup.sql` | Dump database |
| 16 | `/dump.sql` | Dump database |
| 17 | `/backup.zip` | Backup arsip whole site |
| 18 | `/site_backup.tar.gz` | Backup arsip whole site |

### IDE / editor metadata

| # | Path | Apa yang bocor |
|---|------|----------------|
| 19 | `/.vscode/settings.json` | VS Code workspace setting (kadang ada path absolut + secret) |
| 20 | `/.idea/workspace.xml` | JetBrains IDE workspace metadata |
| 21 | `/.DS_Store` | macOS directory listing - bocor file structure folder |

### Common framework leak

| # | Path | Apa yang bocor |
|---|------|----------------|
| 22 | `/composer.json` | PHP dependency list (mengungkap library + version untuk targeted CVE) |
| 23 | `/composer.lock` | Same + version exact |
| 24 | `/package.json` | Node.js dependency list |
| 25 | `/package-lock.json` | Same + version exact |
| 26 | `/.npmrc` | NPM config (kadang berisi token registry private) |

### Server / infra config

| # | Path | Apa yang bocor |
|---|------|----------------|
| 27 | `/.htaccess` | Apache config (kadang ungkap rewrite rule, basic auth setup) |
| 28 | `/web.config` | IIS config (sama poin) |
| 29 | `/Dockerfile` | Build instruction container - mengungkap base image, build secret kadang |

### Misc

| # | Path | Apa yang bocor |
|---|------|----------------|
| 30 | `/server-status` | Apache mod_status endpoint (kalau open, ungkap request rate, IP requestor real-time) |

> [!NOTE]
> Tool ini sengaja tidak brute force ribuan path. Wordlist besar (Dirbuster, gobuster) menghasilkan ribuan request, banyak false positive (custom 200 page yang bukan bocoran), dan footprint scan masif. Eksposur tier-1 di atas sudah cover 90% case nyata. Untuk recon mendalam, kombinasikan dengan tool eksternal yang Anda miliki izinnya.

## Plausibility validation

Cek HTTP status 200 saja tidak cukup. Banyak situs return 200 untuk path apapun (custom 404 page, SPA fallback, atau security-by-obscurity yang return generic text). Tool ini tambah layer plausibility validator per kategori untuk pastikan finding adalah real eksposur.

### Validator per kategori

| Kategori | Validation |
|----------|------------|
| `.git/HEAD` | Body harus match pattern `^ref: refs/heads/` atau berisi commit hash 40 hex char |
| `.git/config` | Body harus match `[core]` atau `[remote "..."]` (INI-style) |
| `.env*` | Body harus mengandung min 2 line yang match `^[A-Z_]+=` (env var pattern) |
| `wp-config.php.bak` | Body harus mengandung `DB_NAME`, `DB_USER`, atau `DB_PASSWORD` literal |
| `.sql` files | Magic byte / leading content harus include keyword SQL: `INSERT INTO`, `CREATE TABLE`, `DROP TABLE`, `-- MySQL dump`, `-- PostgreSQL` |
| `package.json` | Body valid JSON dengan field `name` dan `version` di top level |
| `composer.json` | Same poin |
| `.DS_Store` | Magic byte `\x00\x00\x00\x01Bud1` di awal file |
| `Dockerfile` | Body match regex `^FROM\s+\S+` |
| `.htaccess` | Body mengandung min 1 directive Apache (`RewriteEngine`, `Options`, `AuthType`, dst) |
| Generic backup arsip | Magic bytes ZIP (`PK\x03\x04`) atau gzip (`\x1f\x8b`) |

Saat path return 200 OK tapi body gagal plausibility check (misal HTML SPA fallback yang return halaman main app), tool tag finding sebagai `false_positive_filtered` dan tidak masukkan ke output. Log audit trail tetap ada di History entry untuk debugging.

### Filter yang menghindari false positive

- **Custom 404 trap.** Server yang return 200 untuk semua path (SPA index.html catch-all) di-detect dengan prob halaman fictitious `/this-path-definitely-does-not-exist-<random>` di awal scan. Kalau itu return 200, tool sadar dan apply stricter validation.

- **CDN cache page.** CDN seperti Cloudflare kadang return cached page generic untuk path yang non-cached. Plausibility check filter ini.

- **WAF challenge page.** Cloudflare / AWS WAF return 200 dengan halaman "Just a moment, checking your browser". Body validation filter ini juga.

## Severity & scoring

Setiap finding di-grade dengan severity berdasarkan dampak potensial. Tabel:

| Severity | Warna | Contoh kategori | Score |
|----------|-------|-----------------|-------|
| Critical | merah | `.env` dengan AWS_SECRET / STRIPE_SECRET / DATABASE_URL terdeteksi di body. SQL dump berisi `INSERT INTO users (password, ...)` | 90-100 |
| High | oranye | `.git/HEAD` aktif (memungkinkan rekonstruksi source). `.env` dengan environment variable apapun. `wp-config.php.bak` |  60-89 |
| Medium | kuning | `.DS_Store` dengan listing file. `.idea/workspace.xml`. `package.json` di production (info disclosure mild) | 30-59 |
| Low | biru | `composer.json` di production (mostly info disclosure). `Dockerfile` di docroot | 10-29 |
| Info | abu | `server-status` 403 (terkonfirmasi tapi protected). `.git/HEAD` 403 (terkonfirmasi tapi blocked) | 1-9 |

### Severity escalation

Tool punya escalation logic. Default `.env` finding adalah High, tapi kalau body parsing menemukan keyword sensitif, di-eskalasi ke Critical:

- `AWS_SECRET_ACCESS_KEY=` → Critical
- `STRIPE_SECRET_KEY=sk_live_` → Critical
- `DATABASE_URL=postgres://...:...@` (dengan password segment) → Critical
- `OPENAI_API_KEY=sk-` → Critical
- `JWT_SECRET=` → Critical (kalau value > 16 char)
- `MAILGUN_API_KEY=key-` → Critical
- `SECRET_KEY_BASE=` (Rails) > 32 char → Critical

Tujuan eskalasi: pastikan finding "we found .env with real secret keys" tidak bercampur dengan "we found .env file dengan placeholder dev value".

### Total scan score

Dari semua finding, tool compute aggregate score 0-100:

- 0-9: Clean (semua findingl info-only atau tidak ada finding)
- 10-29: Low risk (1-2 finding low severity)
- 30-59: Medium risk
- 60-89: High risk (ada finding high atau multiple medium)
- 90-100: Critical (ada finding critical, action required)

## Cara pakai

Buka PyScrapr, navigasi ke menu **Exposure Scanner** di sidebar Audit & Intel (warna lime, ikon door-enter). Halaman terbuka dengan field input.

1. Paste URL target di field `URL situs`. Format apapun diterima (`example.com`, `https://example.com`). Tool normalize ke origin (scheme + host + port).

2. (Opsional) Toggle kategori yang ingin di-cek. Default semua aktif. Kalau Anda hanya butuh cek VCS leak, matikan kategori lain untuk speed.

3. (Opsional) Atur `Throttle delay` (default 500ms). Delay antar request. Untuk situs Anda sendiri yang kuat, bisa turunkan. Untuk audit klien yang server-nya kecil, naikkan ke 1000-2000ms.

4. (Opsional) Atur `Request timeout` (default 10 detik) per path.

5. Klik **Mulai Scan**. Tool jalankan probing sekuensial dengan throttle, masing-masing path: HEAD request dulu (cek status saja, body tidak di-fetch). Kalau status menjanjikan (200 atau 403), promote ke GET request untuk plausibility check.

6. Progress bar tampilkan path yang sedang di-cek. Total scan biasanya 30-60 detik tergantung throttle dan response time situs target.

7. Hasil muncul di panel kanan dalam bentuk:
   - **Aggregate score** dengan badge severity tertinggi
   - **List finding** sorted by severity desc, expandable per item dengan status code, response size, plausibility check verdict, body snippet (untuk validasi manual), severity dengan color, dan tombol "Buka URL" untuk verifikasi di browser
   - **Rekomendasi remediasi** per finding

8. Export hasil sebagai JSON via tombol **Export JSON**.

## Contoh skenario

### 1. Developer lupa exclude .git/ dari deploy

Startup small team deploy dengan `rsync -av source/ server:/var/www/` tanpa exclude. Setelah Exposure Scan, finding Critical: `/.git/HEAD` returns 200 dengan body `ref: refs/heads/main`, `/.git/config` returns 200 dengan remote URL `git@github.com:startup/repo.git` (mengungkap private repo path). Severity High. Action: tambah `.git/` ke deploy exclude di rsync atau Dockerfile, lalu hapus `.git/` di production via SSH. Atau pakai `nginx deny` directive untuk block path `.git/`.

### 2. Leaked .env in production

Tim ops convert dev environment ke staging via copy-paste. Lupa rename `.env.production` ke `.env` (atau set permission denying public read). Exposure Scan: `/.env.production` 200 OK, plausibility pass, body mengandung `STRIPE_SECRET_KEY=sk_live_abc...`, `DATABASE_URL=postgres://prod-db...`. Severity Critical. Action: rotate semua secret yang bocor SEGERA (Stripe rotate dashboard, DB password reset). Setelah rotate, hapus `.env.production` dari docroot. Audit access log untuk lihat apakah ada IP suspicious yang sudah pull file - kalau ya, escalate ke incident response.

### 3. Exposed wp-config backup

Plugin update WordPress generate `wp-config.php.bak` automatic, tidak otomatis di-cleanup. Exposure Scan: `/wp-config.php.bak` 200 OK, body mengandung `define('DB_PASSWORD', 'real_password_here')`. Severity High. Action: hapus file backup, ganti DB password (assume sudah bocor), tambah rule di `.htaccess` atau nginx untuk deny pattern `*.bak` dan `*.backup`.

### 4. Leaked database dump in /uploads/

Intern dev export DB untuk test, simpan di `/uploads/dump.sql` "sementara", lupa hapus 6 bulan. Exposure Scan: `/dump.sql` 200 OK, body mengandung `INSERT INTO users (email, password_hash) VALUES (...)`. Severity Critical. Action: hapus file segera, audit access log untuk evidence pengambilan, force password reset semua user kalau dump berisi credential, notifikasi user sesuai compliance regulation (GDPR breach notification 72 jam, PDP-Indonesia notification setara).

### 5. .DS_Store leak directory listing

Designer Mac upload folder ke shared hosting via FTP, default macOS create `.DS_Store` di setiap folder. Exposure Scan: `/.DS_Store` 200 OK, magic bytes valid. Severity Medium. File berisi listing folder (nama file, ukuran). Bukan critical leak tapi attacker bisa pakai untuk discover path tidak terindeks (e.g. `/_drafts/admin_panel.html`). Action: hapus semua `.DS_Store` rekursif, set `find / -name ".DS_Store" -delete` di server, tambah block rule di nginx/Apache.

### 6. Bug bounty initial recon

Bug hunter dapat invite ke program bug bounty. Scope explicit allow recon path-based, target `app.example.com`. Exposure Scan return 1 Medium (`/.idea/workspace.xml`). Tidak critical sendiri tapi mengungkap path SSH key kontainer dev di workspace, yang bisa di-cross-reference dengan finding lain untuk eskalasi. Submit report dengan PoC dan severity discussion ke triage team.

## Etika

> [!IMPORTANT]
> Exposure Scanner adalah tool active probing yang generate request ke server target. Walaupun probing-nya minimal (30 request, throttled), tetap ada konsiderasi etika dan legal:

- **Audit own site only** sebagai default workflow. Domain yang Anda miliki secara teknis dan legal.

- **Klien dengan izin tertulis.** Ada email atau kontrak yang explicitly authorize Anda audit. Simpan bukti.

- **Bug bounty program in-scope.** Baca scope dengan seksama. Beberapa program allow recon path-based, beberapa explicit forbid (mereka anggap noise). Pakai hanya kalau di-allow.

- **Throttle by default 500ms.** Jangan turunkan ke 0 untuk target yang bukan milik Anda. Kalau Anda jalankan di latopo bareng VPN sambil lihat Netflix, server klien yang kapasitasnya kecil bisa terganggu. Adjust naik kalau klien punya server kecil.

- **Jangan brute force di luar 30 path baseline.** Tool ini sengaja tidak provide custom wordlist support untuk avoid scope creep. Kalau Anda butuh wordlist-based fuzzing, pakai gobuster/dirbuster sendiri dengan permission yang sesuai.

- **Kalau temukan finding di domain non-izin tidak sengaja:** stop, jangan exploit, kontak owner via responsible disclosure (security@domain, atau via security.txt yang valid menurut RFC 9116).

- **Audit log tersimpan di History.** Setiap scan tercatat dengan timestamp, target URL, parameter. Kalau Anda audit profesional, dokumentasikan di laporan dengan reference ke history entry.

- **Data finding sensitif tetap rahasia.** Kalau scan return body `.env` dengan secret real, tool simpan di History untuk reproducibility. Pastikan akses backend Anda di-protect, dan setelah Anda submit laporan + remediation done, hapus history entry yang berisi secret raw.

## Tips remediation

Setelah Anda temukan finding, beberapa pola remediation umum:

### Untuk VCS leak (`.git/`, `.svn/`, dll)

- Hapus folder `.git/` dari production. Production tidak butuh git history.
- Tambah rule deny di server: nginx `location ~ /\.git { deny all; }`, Apache `RedirectMatch 404 /\.git`.
- Audit `git log` lokal untuk lihat apakah commit ada secret yang harus di-purge dengan `git filter-repo`.

### Untuk environment file (`.env`, `.env.production`, dll)

- Hapus file dari docroot. Application loader baca dari `/etc/myapp/env` atau `process.env` injected via systemd / Docker, bukan dari file di docroot.
- Rotate SEMUA secret di file (assume sudah bocor walau Anda baru audit hari ini).
- Tambah ke `.gitignore`, set permission 600 (owner-only) di file source-of-truth.

### Untuk backup files (`*.bak`, `*.sql`, `*.zip`)

- Cleanup script di CI/CD: `find . -name "*.bak" -delete && find . -name "*.sql" -delete` di build step.
- Block pattern di server: nginx `location ~* \.(bak|backup|old|orig|sql)$ { deny all; }`.
- Backup harus di-store di S3 / B2 / cloud storage dengan IAM control, jangan di docroot.

### Untuk IDE metadata (`.DS_Store`, `.idea/`, `.vscode/`)

- `.gitignore` dengan baseline lengkap dari [github.com/github/gitignore](https://github.com/github/gitignore).
- Pre-deploy hook: `find . -name ".DS_Store" -delete; rm -rf .idea/ .vscode/`.

### Untuk dependency manifest (`package.json`, `composer.json`)

- Sebetulnya sering by design (NPM/Yarn pakai untuk install client-side dep). Tidak selalu harus di-block.
- Tapi kalau Anda backend-only API server, tidak ada alasan `package.json` accessible publik. Block via server config.

### Untuk server status (`server-status`, `server-info`, `phpinfo()`)

- Disable di production. Apache: `<Location /server-status> Require local </Location>`. PHP: hapus file `phpinfo.php` yang sering di-create developer untuk debug.

## Troubleshooting

### Problem: Scan return semua 200 OK termasuk path yang jelas tidak ada

**Gejala:** 25 finding "200 OK" tapi plausibility validator tag mereka semua sebagai `false_positive_filtered`.
**Penyebab:** Server pakai SPA fallback yang return `index.html` untuk semua path. Tool detect ini via prob halaman fictitious dan apply stricter validation.
**Solusi:** Behavior expected. Lihat output finding dengan severity tinggi - itu yang lolos validasi. False positive filtered tidak muncul di output user.

### Problem: WAF block scan setelah 5-10 request

**Gejala:** Setelah scan 5-10 path, semua sisanya return 403 atau timeout.
**Penyebab:** WAF (Cloudflare, AWS WAF) detect rapid request dari IP Anda dan block.
**Solusi:** Naikkan throttle ke 2000ms atau lebih, retry. Atau pakai User-Agent custom yang lebih masuk akal (default UA tool agak generic). Untuk audit own site, whitelist IP Anda di WAF rule.

### Problem: Plausibility check pass tapi Anda yakin file palsu / honeypot

**Gejala:** Tool report `.env` finding dengan body yang plausibility-valid, tapi Anda tahu klien set honeypot file untuk catch attacker.
**Penyebab:** Tool tidak bisa bedakan honeypot dari real eksposur. Plausibility check based on syntax, bukan provenance.
**Solusi:** Verifikasi manual di server. Honeypot biasanya value-nya placeholder atau mengandung canary token. Diskusikan dengan klien di pre-engagement.

### Problem: HTTPS cert error pada situs target

**Gejala:** Scan gagal total dengan SSL error.
**Penyebab:** Cert expired, self-signed, atau hostname mismatch.
**Solusi:** Toggle `verify_ssl` di setting (default true). Set false hanya untuk testing internal, jangan untuk audit klien production. Sebenarnya cert error itu sendiri sudah finding yang relevan untuk laporan audit.

### Problem: Severity escalation tidak trigger walau ada AWS_SECRET di body

**Gejala:** `.env` finding masih High padahal body mengandung `AWS_SECRET_ACCESS_KEY=...`.
**Penyebab:** Value setelah `=` adalah placeholder seperti `your-key-here` atau `xxx`. Escalation logic check kalau value-nya panjang dan match pattern AWS key actual.
**Solusi:** Behavior expected. Placeholder bukan secret. Kalau Anda lihat real value di body manually dan tool tidak escalate, buat issue dengan sample (sanitized).

### Problem: Beberapa path return Connection Reset

**Gejala:** Sebagian dari 30 path return error "ConnectionResetError" atau RST.
**Penyebab:** Server target rate limit atau IDS detect probing dan reset connection.
**Solusi:** Naikkan throttle ke 2000-5000ms. Behavior expected untuk security-aware target. Document di laporan sebagai "ada signal aktif blocking, partial scan only".

## Related docs

- [OSINT Harvester](/docs/tools/osint-harvester.md) - audit body halaman publik (complement Exposure path-based)
- [Domain Intel](/docs/intel/domain.md) - WHOIS + DNS + subdomain (recon sebelum Exposure Scan)
- [Security Headers Scanner](/docs/audit/security-headers.md) - audit header HTTP (HSTS, CSP, dst)
- [SSL Inspector](/docs/audit/ssl.md) - inspeksi cert TLS situs target
- [SEO Auditor](/docs/audit/seo.md) - audit on-page SEO complement
- [Settings](/docs/system/settings.md) - flag `exposure_throttle_ms`, `exposure_timeout_seconds`, `exposure_verify_ssl`
- [History](/docs/system/history.md) - entry `EXPOSURE_SCAN` untuk audit trail
