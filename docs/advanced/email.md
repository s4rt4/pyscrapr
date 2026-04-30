# Email Notifications (SMTP)

> Sistem notifikasi berbasis email yang mengirim ringkasan job PyScrapr ke inbox Anda via SMTP. Alternatif dari webhook untuk pengguna yang lebih nyaman monitor via email ketimbang Discord, Telegram, atau HTTP endpoint custom. Implementasi murni pakai stdlib Python `smtplib`, tidak perlu dependency tambahan, mendukung STARTTLS dan SMTP_SSL, serta bisa kirim ke multiple penerima sekaligus. Cocok untuk personal use, tim kecil, atau audit trail formal yang perlu arsip di mailbox.

## Apa itu Email Notifications

PyScrapr punya dua jalur notifikasi utama: webhook (Discord, Telegram, HTTP generik) dan email. Webhook cocok untuk notifikasi instan ke channel chat. Email cocok untuk laporan yang perlu disimpan, dibagikan, atau dicari kembali. Banyak user lebih akrab dengan inbox sebagai central hub notifikasi daripada channel chat yang ramai. Email juga lebih universal: hampir semua HP dan laptop sudah terkonfigurasi mail client, tanpa perlu install app tambahan.

Implementasi email notifier di PyScrapr sengaja minimalis. Modul `email_service.py` hanya tergantung pada `smtplib` dan `email.mime` dari stdlib Python. Tidak ada library eksternal seperti `yagmail` atau `aiosmtplib`. Alasannya konsistensi dengan filosofi PyScrapr sebagai offline toolkit yang tidak menambah dependency kecuali benar-benar perlu. Trade-off performance minor tidak terasa karena email notification bukan hot path.

Email fires pada event terminal yang sama dengan webhook: `job.done`, `job.error`, `job.stopped`. Listener teregistrasi di EventBus global yang sama dengan webhook, jadi email dan webhook bisa fires barengan tanpa konflik. Trigger flags dikontrol terpisah via `smtp_on_done` dan `smtp_on_error` supaya Anda bisa kombinasi misalnya webhook untuk semua event dan email hanya untuk error kritikal.

Format email menggunakan multipart: ada plain text fallback untuk mail client jadul, ada HTML body dengan table stats yang rapi untuk mail client modern. Subject line mengikuti pattern `[OK] Harvester selesai: example.com` atau `[ERROR] URL Mapper gagal: example.com`, jadi Anda bisa set filter Gmail atau rule Outlook untuk route ke folder tertentu berdasarkan prefix.

## Setup / Konfigurasi

### Langkah umum

1. Siapkan akun SMTP. Bisa Gmail, Outlook, Yandex, ProtonMail, SendGrid, Mailgun, atau self-hosted Postfix.
2. Jika provider butuh app password (Gmail wajib), generate lewat setting akun.
3. Buka Settings di PyScrapr, scroll ke section Email Notifications.
4. Aktifkan toggle `smtp_enabled`.
5. Isi host, port, user, password, from, dan to sesuai provider.
6. Klik "Send test email" untuk verifikasi.
7. Cek inbox; email test harus muncul dalam beberapa detik.
8. Atur trigger flags sesuai kebutuhan.

### Setup Gmail

1. Login ke akun Gmail, masuk ke [myaccount.google.com/security](https://myaccount.google.com/security).
2. Aktifkan 2-Step Verification jika belum.
3. Buat app password di section "App passwords" dengan nama "PyScrapr".
4. Copy password 16 karakter yang di-generate.
5. Isi di Settings PyScrapr:

```
smtp_host: smtp.gmail.com
smtp_port: 587
smtp_user: your.email@gmail.com
smtp_password: <app password 16 karakter>
smtp_use_tls: true
smtp_from: your.email@gmail.com
smtp_to: your.email@gmail.com
```

### Setup Outlook / Hotmail

```
smtp_host: smtp-mail.outlook.com
smtp_port: 587
smtp_user: your.email@outlook.com
smtp_password: <password akun atau app password>
smtp_use_tls: true
```

Outlook juga mendukung STARTTLS di port 587. Akun dengan 2FA butuh app password.

### Setup Yandex

```
smtp_host: smtp.yandex.com
smtp_port: 465
smtp_user: your.email@yandex.com
smtp_password: <app password>
smtp_use_tls: false
```

Yandex pakai SMTP_SSL di port 465. Set `smtp_use_tls=false` karena tunnel sudah TLS dari awal, bukan STARTTLS.

### Setup self-hosted SMTP

```
smtp_host: mail.mydomain.com
smtp_port: 25
smtp_user: scraper@mydomain.com
smtp_password: <password>
smtp_use_tls: false
```

Port 25 untuk SMTP plain (biasanya cuma relay internal). Naikkan ke 587 atau 465 jika ada TLS.

## Cara pakai

1. Setelah setup selesai, biarkan PyScrapr jalan seperti biasa.
2. Submit job apapun (Harvester, Mapper, Ripper, dll).
3. Saat job selesai, listener email akan fires otomatis.
4. Cek inbox target; email subject akan muncul dengan prefix `[OK]` atau `[ERROR]`.
5. Buka email, lihat body HTML berisi stats: duration, items processed, output path, status.
6. Jika ada error, body juga berisi traceback singkat plus link ke History detail.
7. Untuk testing configuration baru, gunakan endpoint `POST /api/email/test`.
8. Dari curl:

```bash
curl -X POST http://localhost:8585/api/email/test \
  -H "Content-Type: application/json" \
  -d '{"to": "override@example.com"}'
```

Field `to` opsional; kosongkan supaya kirim ke `smtp_to` default.

9. Response endpoint test berisi `{"status": "sent", "recipients": [...], "duration_ms": 342}`.
10. Jika sukses, konfigurasi siap production.

## Contoh skenario

### Skenario 1: Laporan scraping harian ke email pribadi

Seorang freelance researcher jalankan 10 Harvester job overnight via Scheduler. Daripada bangun pagi buka Dashboard, dia set `smtp_on_done=true`. Setiap job selesai, email masuk inbox dengan subject `[OK] Harvester selesai: target.com`. Saat sarapan, tinggal scroll Gmail untuk konfirmasi semua sukses. Filter Gmail route semua email subject `[OK]` ke label "PyScrapr/Success" dan `[ERROR]` ke label "PyScrapr/Alert" dengan star merah.

### Skenario 2: Distribusi laporan ke tim via mailing list

Tim data analyst jalankan scraping mingguan untuk kompetitor monitoring. Hasil dikirim via email ke `data-team@company.com` yang dikelola sebagai mailing list 5 anggota. Konfigurasi: `smtp_to=data-team@company.com`. Ketika job selesai, semua anggota tim dapat notifikasi identik. Tidak perlu setup Discord server atau Slack workspace khusus.

### Skenario 3: Alert kritikal ke mobile via provider push

Admin IT konfigurasi Outlook akun yang push notification ke smartphone via Outlook mobile app. Set `smtp_on_error=true` dan `smtp_on_done=false`. Hanya kegagalan yang fires email, jadi notifikasi iPhone cuma muncul saat ada masalah. Kombinasi webhook Discord untuk success log dan email Outlook untuk error alert memberi coverage penuh tanpa noise.

## Pengaturan detail

### smtp_enabled

Boolean, default `false`. Master switch. Ketika `false`, semua trigger email diabaikan meski flag spesifik aktif. Berguna sebagai kill switch cepat.

### smtp_host

String hostname SMTP server. Tidak ada default. Contoh: `smtp.gmail.com`, `smtp.office365.com`, `mail.mydomain.com`.

### smtp_port

Integer, default 587. Port SMTP. Nilai umum: 25 (plain), 587 (STARTTLS), 465 (SMTP_SSL). Pilih 587 untuk mayoritas provider modern.

### smtp_user

String, username login SMTP. Biasanya alamat email lengkap. Default kosong.

### smtp_password

String, password login SMTP. Untuk Gmail dan Outlook dengan 2FA, ini adalah app password, bukan password akun utama. Tersimpan plaintext di `data/settings.json`; lindungi file tersebut.

### smtp_use_tls

Boolean, default `true`. Jika `true`, gunakan STARTTLS (upgrade plain connection ke TLS via command STARTTLS). Jika `false`, gunakan SMTP_SSL (TLS dari awal handshake) atau plain SMTP tergantung port. Rule of thumb: port 587 pakai `true`, port 465 pakai `false`.

### smtp_from

String alamat "From" yang muncul di email header. Biasanya sama dengan `smtp_user`. Beberapa provider menolak kalau beda.

### smtp_to

String, comma-separated list alamat penerima. Contoh: `alice@company.com, bob@company.com, team@company.com`. Semua akan dapat email identik. Maksimum efektif sekitar 50 alamat; lebih dari itu pakai mailing list.

### smtp_on_done

Boolean, default `true`. Fires email saat status job `done`.

### smtp_on_error

Boolean, default `true`. Fires email saat job `error`. Sangat direkomendasikan tetap `true`.

### smtp_on_stopped

Boolean, default `false`. Fires email saat job di-stop manual oleh user. Biasanya tidak perlu karena sudah tahu alasan stop.

### smtp_subject_prefix

String, default `[PyScrapr]`. Prepended ke subject line. Ganti ke `[SCRAPER-PROD]` untuk membedakan dari instance lain.

### smtp_include_html

Boolean, default `true`. Jika `true`, kirim multipart dengan HTML dan plain text. Jika `false`, plain text saja (hemat bandwidth).

### smtp_timeout_seconds

Integer, default 30. Timeout koneksi ke SMTP server. Naikkan jika server lambat atau latency tinggi.

## Tips & best practices

1. **Selalu pakai app password untuk Gmail dan Outlook.** Password akun utama berisiko dan biasanya ditolak oleh provider yang sudah enforce 2FA. App password lebih aman karena bisa di-revoke terpisah.

2. **Set filter di mail client.** Buat filter berdasarkan prefix subject: `[OK]` ke folder Success, `[ERROR]` ke folder Alert dengan notification. Inbox utama tidak berantakan.

3. **Hindari `smtp_on_done=true` untuk job frekuensi tinggi.** Kalau Anda run Harvester tiap 5 menit, inbox akan kebanjiran. Pakai `on_error` saja, atau beralih ke webhook untuk success log.

4. **Masking password saat share konfigurasi.** Jika share setup dengan tim, blur atau ganti password di screenshot. Password SMTP bisa dipakai kirim email spam dari akun Anda.

5. **Test dengan endpoint `/api/email/test` setelah ubah konfigurasi.** Murah dan cepat untuk verifikasi credential masih valid, terutama setelah rotate app password.

6. **Gunakan akun email khusus untuk PyScrapr.** Buat alias atau akun baru `pyscrapr@mydomain.com` supaya tidak campur dengan inbox personal. Memudahkan revoke dan audit.

7. **Monitor bounce dan spam folder.** Jika email tidak datang, cek spam folder dulu; banyak filter aggressive terhadap email automation.

8. **Set rate limit di sisi provider.** Gmail limit kira-kira 500 email per hari untuk akun gratis. Kalau Anda run banyak job, pertimbangkan SMTP relay seperti SendGrid atau Mailgun yang punya kuota lebih besar.

9. **Pakai relay service untuk production.** Mailgun, Postmark, atau SendGrid menyediakan SMTP endpoint dengan delivery rate lebih bagus dibanding SMTP consumer seperti Gmail. Berguna jika email business.

10. **Jangan commit settings.json ke Git.** Password plaintext berbahaya kalau bocor. Tambahkan `data/settings.json` ke `.gitignore`.

## Troubleshooting

### Problem: Error "SMTPAuthenticationError: 535 authentication failed"

**Gejala:** Test email gagal dengan status 535.

**Penyebab:** Password salah, app password belum dibuat, atau akun butuh 2FA.

**Solusi:** Untuk Gmail, buat app password baru via [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). Untuk Outlook, sama. Untuk self-hosted, verifikasi credential via `swaks` atau `telnet`.

### Problem: Timeout saat connect ke port 587 atau 465

**Gejala:** Error connection timeout setelah 30 detik.

**Penyebab:** Firewall ISP atau router memblokir outbound SMTP. Beberapa ISP residential block port 25, 465, 587 secara default untuk cegah spam.

**Solusi:** Coba dari koneksi lain (mobile hotspot) untuk konfirmasi masalah firewall. Pakai SMTP relay HTTPS seperti SendGrid API sebagai alternatif (butuh adapter custom).

### Problem: Email masuk spam folder

**Gejala:** Email sukses terkirim tapi tidak di inbox.

**Penyebab:** SPF, DKIM, atau DMARC record domain pengirim belum konfigurasi. Mail client mark sebagai suspicious.

**Solusi:** Jika self-hosted, setup SPF record di DNS: `v=spf1 mx ~all`. Tambah DKIM key. Untuk Gmail sebagai sender, biasanya sudah auto-handled. Tambah alamat pengirim ke whitelist inbox Anda.

### Problem: Gmail error "less secure app access"

**Gejala:** Gmail tolak login dengan pesan tentang "less secure apps".

**Penyebab:** Google sudah deprecate fitur ini. Akun hanya bisa dipakai dengan app password atau OAuth2.

**Solusi:** Generate app password seperti di section Setup Gmail. PyScrapr tidak support OAuth2 untuk SMTP saat ini.

### Problem: Multi-recipient tidak semua dapat email

**Gejala:** Hanya beberapa alamat di `smtp_to` menerima email.

**Penyebab:** Typo di daftar alamat, spasi ekstra, atau alamat bounce.

**Solusi:** Cek format `smtp_to`: comma-separated tanpa semicolon atau newline. Verifikasi tiap alamat valid via mail ping tool. Cek log server untuk pesan SMTP `550 user not found`.

### Problem: Error "SMTPServerDisconnected" setelah beberapa email

**Gejala:** Email pertama sukses, berikutnya gagal dengan disconnect error.

**Penyebab:** Server SMTP tidak keep-alive; PyScrapr coba re-use connection yang sudah di-close.

**Solusi:** PyScrapr seharusnya buat koneksi baru per email; jika masalah persist, periksa apakah code PyScrapr pakai connection pooling incorrect. Restart server untuk reset state.

### Problem: Subject line berantakan dengan karakter aneh

**Gejala:** Subject di inbox tampil `=?utf-8?B?...?=` atau karakter hex.

**Penyebab:** Mail client tidak decode MIME encoded-word subject.

**Solusi:** PyScrapr default sudah encode UTF-8 dengan benar; mail client modern (Gmail, Outlook, Apple Mail) seharusnya decode otomatis. Jika lihat raw encoded-word, update mail client Anda.

## Keamanan / batasan

- Password SMTP tersimpan plaintext di `data/settings.json`; lindungi file ini dengan permission filesystem (chmod 600 di Unix).
- Email dikirim unencrypted antara PyScrapr dan SMTP server kalau STARTTLS/SSL tidak aktif; jangan pakai di jaringan public tanpa TLS.
- Email itu sendiri tidak end-to-end encrypted; body bisa dibaca oleh provider email.
- Tidak ada rate limiting internal; kalau Anda run ratusan job paralel, SMTP server bisa reject dengan 421 quota exceeded.
- App password Gmail limit 16 karakter tanpa spasi; treat as sensitive credential.
- Tidak ada support OAuth2 untuk SMTP; kalau provider wajib OAuth2 (misalnya Microsoft 365 modern auth), pakai app password fallback atau relay service.
- Multi-recipient di satu `smtp_to` kirim 1 email ke banyak orang (BCC model); tidak ada personalization per recipient.
- Tidak ada template customization via UI saat ini; format subject dan body hardcoded.
- Attachment tidak didukung; email hanya berisi text dan HTML body dengan link ke History detail.
- Local mail server tanpa auth (port 25 open relay) berisiko di-abuse; pastikan hanya listen localhost.

## FAQ

**Q: Bisa kirim attachment file hasil scraping via email?**
A: Saat ini belum. Body email hanya berisi stats dan link ke History detail. Attachment file besar (misalnya ZIP ratusan gambar) berisiko kena limit size SMTP provider (biasanya 25 MB); implementasi ini sengaja dihindari. Workaround: link ke endpoint download di PyScrapr yang reachable dari client penerima.

**Q: Apakah support OAuth2 untuk Gmail atau Outlook?**
A: Tidak. PyScrapr hanya support plain SMTP auth dengan username dan password (atau app password). Untuk akun yang enforce modern auth, gunakan app password sebagai workaround.

**Q: Apakah bisa schedule email digest harian, bukan per-job?**
A: Saat ini email fires per event terminal. Mode digest (aggregate X job dalam 24 jam) ada di roadmap. Sementara, filter inbox untuk arsip lalu baca batch di waktu tertentu.

**Q: Multi-account SMTP untuk load balancing?**
A: Tidak didukung native. Satu konfigurasi SMTP per instance PyScrapr. Untuk kirim via beberapa akun, pakai relay service atau jalankan multiple instance.

**Q: Apakah email body include hyperlink ke output folder?**
A: Ya, body berisi link `http://localhost:8585/history/<job_id>` yang buka detail di PyScrapr. Hyperlink hanya reachable dari mesin yang bisa akses instance PyScrapr.

**Q: Karakter non-ASCII di subject atau body?**
A: Full UTF-8 support via MIME encoding. Subject Indonesia dengan karakter aksen atau emoji tampil benar di mail client modern. Plain text fallback tetap UTF-8.

**Q: Apakah webhook dan email fires bersamaan atau bergantian?**
A: Paralel. Keduanya subscribe ke EventBus yang sama dan fires concurrent. Tidak ada priority atau urutan garanti.

**Q: Email gagal apakah job status berubah?**
A: Tidak. Kegagalan email hanya di-log level WARNING. Job status tetap sesuai hasil scraping. Notifikasi adalah side channel, bukan bagian dari pipeline utama.

**Q: Bisa pakai SMTP tanpa TLS untuk internal network?**
A: Ya, set `smtp_use_tls=false` dan port 25. Hanya aman di trusted network. Tidak direkomendasikan untuk traffic lintas internet.

**Q: Retry policy kalau SMTP server sementara down?**
A: 3 attempt dengan exponential backoff 2, 4, 8 detik. Setelah itu email drop dan di-log. Tidak ada queue persisten untuk retry hari berikutnya.

## Related docs

- [Webhooks](/docs/advanced/webhooks.md) - Alternatif notifikasi via Discord, Telegram, atau HTTP generik. Bisa dipakai bareng dengan email.
- [Scheduled Jobs](/docs/system/scheduled.md) - Pair dengan email untuk laporan scraping overnight.
- [Settings](/docs/system/settings.md) - Section Email untuk konfigurasi terpusat.
- [REST API](/docs/advanced/rest-api.md) - Endpoint `/api/email/test` untuk integrasi CI.
- [History](/docs/system/history.md) - Email body berisi link ke detail job di History.
