# Webhooks & Notifications

> Sistem notifikasi multi-channel (Discord, Telegram, HTTP generik) yang otomatis mengirim pesan ke endpoint eksternal setiap kali job selesai, gagal, atau Diff mendeteksi perubahan signifikan pada target. Cocok untuk memonitor scheduled scraping tanpa harus terus membuka aplikasi.

## Deskripsi

Webhooks adalah jembatan antara PyScrapr dan dunia luar. Ketika scheduled scrape berjalan tengah malam dan Anda tidak duduk di depan komputer, bagaimana cara tahu apakah berhasil atau gagal? Jawabannya webhook: PyScrapr akan POST payload JSON ke URL yang Anda konfigurasi, berupa Discord channel, Telegram bot, Slack-compatible endpoint, atau sistem internal custom, sehingga notifikasi masuk ke feed yang Anda monitor secara real-time di mobile app atau desktop notification. Alih-alih polling Dashboard berulang kali, status job akan "datang" sendiri ke tempat Anda biasanya berinteraksi.

Implementasi webhook di PyScrapr terpusat di modul `webhooks.py` yang mendefinisikan tiga adapter channel: `DiscordWebhook`, `TelegramBot`, dan `GenericHttpWebhook`. Ketiganya berbagi interface method `send(payload, job_context)` yang mentransformasi data job menjadi format sesuai channel. Discord menggunakan rich embed dengan warna berdasarkan status (hijau untuk done, merah untuk error, biru untuk running), field stats seperti duration, items downloaded, dan output path, plus footer bertuliskan "PyScrapr" dan timestamp ISO 8601. Telegram menggunakan Markdown formatted text karena tidak mendukung embed, sementara Generic HTTP mengirim raw JSON struktur PyScrapr kanonis yang cocok untuk dikonsumsi oleh webhook consumer custom seperti n8n, Zapier, atau internal service.

Event system berbasis EventBus global di `webhook_listener.py`. Saat job mencapai terminal state (done, error, atau stopped), orchestrator tool memanggil `event_bus.emit('job.done', job)` atau event equivalent untuk error dan stopped. Listener yang teregistrasi saat startup aplikasi akan mendispatch ke adapter webhook sesuai trigger flags di Settings: `webhook_on_done`, `webhook_on_error`, dan `webhook_on_diff_only` (hanya fires saat Diff detection mendeteksi perubahan). Logic ini memisahkan concern emit (tanggung jawab tool) dari dispatch (tanggung jawab webhook service), sehingga menambah channel baru tinggal register adapter tanpa harus menyentuh kode tool satu per satu.

Retry logic ditanam di tiap adapter dengan 3 attempt default dan exponential backoff 1, 2, 4 detik. Khusus Discord dan Telegram, response 429 (rate limit) dihormati dengan parsing header `Retry-After`, jadi PyScrapr tidak langsung retry melainkan sleep sesuai saran server. Jika semua retry gagal, event dicatat di log level WARNING tapi tidak mem-blok job, sehingga kegagalan webhook tidak memengaruhi scraping core. Untuk testing, tersedia endpoint `POST /api/webhooks/test` yang mengirim dummy payload ke semua channel yang configured, berguna saat setup awal untuk memastikan kredensial benar sebelum bergantung pada webhook di production.

## Kapan pakai?

1. **Notifikasi scheduled jobs overnight** - Pulang kerja pagi hari, langsung tahu dari Discord channel apakah semua schedule semalam sukses tanpa harus membuka Dashboard.
2. **Alert error untuk job kritikal** - Set `webhook_on_error=true` agar kegagalan langsung muncul di Telegram tanpa perlu polling History setiap kali.
3. **Integrasi dengan CI/CD atau automation tool** - Generic HTTP webhook bisa trigger downstream pipeline data processing, transformasi, atau loading ke data warehouse setelah scraping selesai.
4. **Monitoring diff signifikan** - Kombinasi Diff Detection dengan `webhook_on_diff_only=true` mengirim alert hanya ketika situs target benar-benar berubah, mengurangi noise di channel.
5. **Logging terpusat ke Slack atau MS Teams** - Gunakan endpoint Slack-compatible (Discord webhook format sebagian kompatibel) untuk stream log semua job ke channel tim kerja.
6. **Automation trigger downstream** - HTTP webhook bisa memicu Zapier, IFTTT, atau n8n untuk workflow multi-step yang melibatkan email, SMS, atau update spreadsheet.
7. **SMS atau WhatsApp via gateway** - Kirim ke HTTP endpoint Twilio atau WhatsApp Business API untuk notifikasi prioritas tinggi pada kegagalan scraping penting.
8. **Email via bridge service** - Konekkan ke Mailgun atau SendGrid webhook endpoint yang meneruskan payload menjadi email dengan formatting HTML.

## Cara penggunaan

1. Buka halaman Settings di aplikasi, scroll ke bagian Webhooks & Notifications.
2. Untuk Discord: buat webhook di server Discord melalui Server Settings > Integrations > Webhooks > New Webhook. Copy URL yang di-generate, paste ke field `webhook_discord_url`. Ekspektasi: URL berformat `https://discord.com/api/webhooks/<id>/<token>`.
3. Untuk Telegram: buat bot via @BotFather di Telegram, simpan token bot yang diberikan. Dapatkan chat_id dengan mengirim pesan apapun ke bot, lalu akses `https://api.telegram.org/bot<TOKEN>/getUpdates` untuk melihat chat.id. Isi `webhook_telegram_token` dan `webhook_telegram_chat_id`.
4. Untuk HTTP generik: siapkan endpoint POST milik Anda sendiri yang menerima JSON payload. Paste URL lengkap ke field `webhook_generic_url`. Endpoint harus menjawab status 2xx dalam waktu 10 detik.
5. Toggle trigger flags sesuai kebutuhan: `webhook_on_done` untuk notifikasi sukses, `webhook_on_error` untuk kegagalan, `webhook_on_diff_only` untuk hanya fires saat Diff mendeteksi perubahan.
6. Klik tombol "Save changes" di toolbar Settings. Konfigurasi tersimpan ke `data/settings.json`.
7. Klik tombol "Send test" di samping field webhook. Request dummy dikirim ke semua channel yang configured dalam 2 hingga 3 detik.
8. Cek Discord channel, Telegram chat, atau endpoint HTTP Anda. Pesan test harus muncul dengan format rich embed (Discord), Markdown (Telegram), atau JSON (generic HTTP).
9. Jika tidak muncul dalam 10 detik, buka log server (terminal tempat FastAPI berjalan) untuk melihat error detail seperti URL salah, token invalid, atau network issue.
10. Jalankan job sample misalnya harvest URL test untuk memverifikasi trigger `on_done` bekerja dengan data nyata.
11. Monitor beberapa trigger pertama untuk memastikan format embed dan Markdown sesuai ekspektasi visual Anda.
12. Fine-tune trigger flags dan threshold (untuk diff) sesuai noise level yang bisa diterima channel Anda.
13. Untuk workload production, pertimbangkan memisahkan channel Discord: satu untuk success logs, satu untuk alerts error, dan satu untuk diff monitoring.
14. Dokumentasikan URL dan token di password manager, jangan commit `data/settings.json` ke Git.
15. Setelah stabil, biarkan webhook bekerja silent; cek channel hanya saat ada pertanyaan audit.

## Pengaturan / Konfigurasi

### webhook_discord_url
URL webhook Discord lengkap berformat `https://discord.com/api/webhooks/<id>/<token>`. Kosongkan jika tidak ingin pakai Discord. Default kosong. Rekomendasi: buat webhook khusus per tipe channel (success vs error) untuk memudahkan filter visual.

### webhook_discord_username
Username yang muncul sebagai pengirim pesan di Discord post. Default `PyScrapr`. Ubah jika ingin branding khusus misalnya "Scraper-Alerts".

### webhook_discord_avatar_url
URL image untuk avatar pengirim pesan Discord. Default kosong (menggunakan avatar default webhook). Rekomendasi: pakai image 512x512 PNG yang hosted di CDN stabil.

### webhook_telegram_token
Bot token dari @BotFather berformat `<bot_id>:<secret>`. Default kosong. Jangan share token ini; treat as password.

### webhook_telegram_chat_id
Target chat ID (user atau group). Angka negatif mengindikasikan group. Default kosong. Bot harus sudah diajak bicara di chat (untuk private) atau sudah ditambahkan ke group sebelum bisa kirim pesan.

### webhook_telegram_parse_mode
Format parsing text: `Markdown`, `MarkdownV2`, atau `HTML`. Default `Markdown`. Rekomendasi: pakai `Markdown` kecuali Anda butuh fitur MarkdownV2 seperti spoiler.

### webhook_generic_url
POST endpoint URL untuk HTTP generik. Default kosong. Endpoint harus return status 2xx dalam 10 detik untuk dianggap sukses.

### webhook_generic_method
HTTP method: `POST` atau `PUT`. Default `POST`. PUT jarang dipakai kecuali API receiver mensyaratkan.

### webhook_generic_headers
Objek berisi extra headers untuk request, misalnya `{"Authorization": "Bearer xyz"}`. Default kosong. Gunakan untuk auth custom atau content type override.

### webhook_on_done
Boolean, fires saat status job berubah ke `done`. Default true. Disable jika Anda hanya peduli error.

### webhook_on_error
Boolean, fires saat job gagal. Default true. Sangat direkomendasikan tetap true untuk visibility.

### webhook_on_diff_only
Boolean, fires hanya saat Diff Detection mendeteksi perubahan signifikan. Default false. Aktifkan untuk mode monitoring situs yang jarang berubah.

### webhook_diff_threshold_pct
Float 0 sampai 100, minimum persentase perubahan yang memicu `webhook_on_diff_only`. Default 20.0. Turunkan untuk sensitivitas tinggi.

### webhook_retry_count
Integer jumlah retry per dispatch yang gagal. Default 3. Naikkan sampai 5 untuk jaringan tidak stabil.

### webhook_retry_backoff_base
Float base backoff dalam detik (exponential: base * 2^attempt). Default 1.0. Hindari nilai terlalu kecil untuk menghormati rate limit channel.

### webhook_include_full_result
Boolean, apakah payload menyertakan full result JSON (bisa besar untuk job harvester ribuan asset). Default false.

### webhook_payload_truncate_length
Integer jumlah karakter maksimum payload text. Default 2000. Telegram punya limit 4096 character per message; set di bawah itu.

## Output / Efek

Untuk tiap trigger, adapter menghasilkan HTTP request ke URL channel dengan payload sesuai format masing-masing.

**Discord payload (rich embed):**
```json
{
  "username": "PyScrapr",
  "embeds": [{
    "title": "Job Done: Harvester",
    "description": "https://example.com/gallery",
    "color": 3066993,
    "fields": [
      {"name": "Duration", "value": "1m 23s", "inline": true},
      {"name": "Downloaded", "value": "147 images", "inline": true},
      {"name": "Status", "value": "done", "inline": true}
    ],
    "footer": {"text": "PyScrapr"},
    "timestamp": "2026-04-17T03:00:00Z"
  }]
}
```

**Telegram payload:**
```json
{
  "chat_id": "<id>",
  "parse_mode": "Markdown",
  "text": "*Job Done: Harvester*\n`https://example.com/gallery`\n*Duration:* 1m 23s\n*Downloaded:* 147 images"
}
```

**Generic HTTP payload:**
```json
{
  "event": "job.done",
  "job": {"id": "uuid", "tool": "harvester", "url": "...", "status": "done", "stats": {...}},
  "timestamp": "2026-04-17T03:00:00Z"
}
```

Catatan: field `event` pada generic payload bisa berupa `job.done`, `job.error`, `job.stopped`, atau `diff.changed` tergantung trigger. Ukuran payload tidak di-compress; untuk receiver yang sensitif bandwidth, aktifkan truncate length.

## Integrasi dengan fitur lain

![Discord](../images/icons/discord.svg) ![Telegram](../images/icons/telegram.svg)

- **Scheduled Jobs** - Webhook fires saat job hasil schedule mencapai terminal state, memberi visibility pada automation yang berjalan tanpa pengawasan.
- **Diff Detection** - Opsi `webhook_on_diff_only` mengunci notifikasi hanya pada job yang Diff mendeteksi perubahan di atas threshold, mengurangi false positive.
- **EventBus** - Mekanisme global yang memicu dispatch; semua tool emit event terminal via bus yang sama.
- **Settings page** - Semua konfigurasi terpusat di section Webhooks untuk kemudahan audit.
- **History** - Detail modal tiap job menampilkan indikator `webhook_fired` dengan status success atau fail per attempt, berguna untuk debugging.
- **REST API** - Endpoint `/api/webhooks/test` dapat di-curl untuk integrasi CI atau pengecekan rutin.

## Tips & Best Practices

1. **Pisahkan channel Discord berdasarkan severity.** Buat webhook terpisah untuk success (`#scraper-log`), error (`#alerts`), dan diff (`#monitoring`). Ini memudahkan filter visual dan menghindari channel yang terlalu ramai jadi di-ignore.

2. **Gunakan Telegram untuk notifikasi urgent.** Mobile push Telegram lebih reliable dan cepat dibanding Discord untuk alert kritikal. Discord desktop notification sering ter-mute pengguna kalau banyak server.

3. **Jangan aktifkan trigger_on_diff tanpa tuning threshold.** Perubahan minor seperti timestamp atau iklan dinamis bisa membanjiri channel. Mulai dengan threshold 30 persen, turunkan bertahap.

4. **Test webhook setelah setiap perubahan konfigurasi.** Tombol Send test sangat murah untuk memvalidasi bahwa kredensial masih benar, terutama setelah regenerate token.

5. **Gunakan generic HTTP untuk automation chain kompleks.** Kirim ke n8n atau Zapier sebagai entry point untuk workflow multi-step: misalnya scraping selesai, transform data, kirim email laporan dengan attachment.

6. **Masking kredensial saat sharing screenshot Settings.** Logout atau blur area token sebelum screenshot UI untuk dokumentasi atau bug report.

7. **Monitor retry failure di log server.** Jika webhook sering habis retry, investigate network upstream atau rotasi kredensial. Jangan biarkan alert silent karena token expired.

8. **Set payload_truncate_length rendah untuk Telegram.** Telegram punya limit 4096 karakter per message; set 2000 untuk safety margin.

9. **Timestamp timezone konsisten.** Payload PyScrapr menggunakan UTC ISO 8601. Jika viewer Anda di WIB, konversi di consumer side atau aktifkan flag timezone override.

10. **Dokumentasikan webhook URL di team.** Jika tim multiple orang, catat mana channel untuk apa di internal wiki supaya tidak ada yang confused saat alert datang.

## Troubleshooting

### Problem: Webhook test sukses tapi actual job tidak trigger
**Gejala:** Tombol Send test berhasil kirim dummy ke Discord, tapi setelah job production selesai, tidak ada pesan masuk.
**Penyebab:** Trigger flags mati, atau EventBus tidak emit event terminal karena bug di orchestrator tool.
**Solusi:** Verifikasi `webhook_on_done=true` di Settings. Cek log server untuk baris `event emitted: job.done`. Jika tidak ada, investigate orchestrator tool yang bersangkutan.

### Problem: Discord menerima pesan tapi format embed rusak
**Gejala:** Pesan masuk Discord tapi tampil sebagai JSON mentah atau embed kosong.
**Penyebab:** Character encoding issue, atau struktur embed invalid (color bukan integer, field lebih dari 25).
**Solusi:** Test dengan payload sederhana (embed hanya title dan description). Validasi payload via Discord webhook tester online seperti `discohook.org`.

### Problem: Telegram 401 Unauthorized
**Gejala:** Log server menampilkan error 401 saat dispatch ke Telegram.
**Penyebab:** Bot token salah, bot di-revoke via BotFather, atau typo saat paste.
**Solusi:** Regenerate token via @BotFather dengan perintah `/revoke` lalu `/newbot`. Update di Settings dan test ulang.

### Problem: Telegram 400 chat not found
**Gejala:** Error 400 dengan pesan "chat not found" di log.
**Penyebab:** Chat ID salah, atau bot belum diajak bicara di chat tersebut (bot harus di-initiate atau di-add ke group dulu).
**Solusi:** Kirim `/start` ke bot dari chat target. Verifikasi chat_id via `api.telegram.org/bot<TOKEN>/getUpdates` dan pastikan angka persis sama termasuk minus untuk group.

### Problem: HTTP generic 401 atau 403 di receiver
**Gejala:** Endpoint custom reject dengan auth error.
**Penyebab:** Header authorization tidak ter-kirim atau format salah.
**Solusi:** Isi `webhook_generic_headers` dengan `{"Authorization": "Bearer <your_key>"}` atau format auth yang di-expect receiver.

### Problem: Retry terus gagal padahal URL benar
**Gejala:** Log menunjukkan 3 attempt gagal connection.
**Penyebab:** SSL cert issue (self-signed cert di endpoint custom), atau firewall memblokir outbound.
**Solusi:** Allow insecure SSL via flag advanced (hanya untuk dev), atau fix cert di receiver side. Cek outbound firewall rules.

### Problem: Rate limit 429 dari Discord
**Gejala:** Error 429 dengan header Retry-After di log.
**Penyebab:** Terlalu banyak webhook fires dalam interval singkat. Discord limit kira-kira 30 message per menit per webhook.
**Solusi:** Batch notifikasi dengan interval dispatch, atau split ke multiple webhook URL. Implement debouncing di event bus jika volume memang tinggi.

### Problem: Payload terpotong di channel
**Gejala:** Pesan muncul tapi terpotong di tengah kalimat.
**Penyebab:** `webhook_payload_truncate_length` terlalu rendah atau `include_full_result=true` dengan data besar.
**Solusi:** Naikkan truncate length sesuai limit channel, atau set `include_full_result=false` untuk ringkas.

### Problem: Webhook tidak fires untuk job dari Scheduled source
**Gejala:** Job manual fires webhook normal, tapi job dari Scheduled tidak.
**Penyebab:** EventBus listener tidak aktif untuk source scheduled (misconfiguration routing).
**Solusi:** Pastikan event emission konsisten di semua sources. Cek `webhook_listener.py` apakah listener subscribe ke event global atau per-source.

### Problem: Multiple fires untuk satu job (duplicate notification)
**Gejala:** Satu job sukses, tapi webhook masuk 2-3 kali ke Discord.
**Penyebab:** EventBus listener ter-register multiple kali (biasanya karena hot reload dev mode).
**Solusi:** Restart server clean. Verifikasi `webhook_listener.register_once()` dipanggil sekali di lifecycle startup.

### Problem: Embed color selalu abu-abu
**Gejala:** Discord embed muncul tapi tanpa warna.
**Penyebab:** Field color dalam payload bukan integer (misalnya string hex).
**Solusi:** Konversi hex ke integer: `#3BA55C` jadi `3908956`. PyScrapr default sudah handle ini; cek jika ada override custom.

## FAQ

**Q: Apakah bisa pakai multiple Discord webhook URL sekaligus?**
A: Default satu URL per field. Untuk multi-channel, extend adapter atau gunakan Discord webhook yang sudah dikonfigurasi forward ke multiple channel via integration Discord sendiri.

**Q: Apakah payload aman dan terenkripsi?**
A: Default menggunakan HTTPS jika URL target adalah HTTPS. Payload berupa plain JSON di dalam TLS. Tidak ada end-to-end encryption tambahan dari PyScrapr.

**Q: Bisa kustomisasi template pesan?**
A: Saat ini format hardcoded per adapter untuk menjamin konsistensi. Template customization ada di roadmap fitur.

**Q: Apakah rate limit dari sisi PyScrapr sendiri ada?**
A: Tidak ada rate limit internal; PyScrapr bergantung pada rate limit channel (Discord 30/min, Telegram 30/s per chat).

**Q: Bagaimana handle secrets di settings.json saat version control?**
A: Jangan commit `data/settings.json` ke Git. Tambahkan ke `.gitignore`. Untuk production, gunakan environment variable override.

**Q: Bisa skip webhook untuk job tertentu?**
A: Ya, tambahkan field `skip_webhook: true` di config submission, listener akan bypass dispatch.

**Q: Apakah webhook async atau blocking terhadap job?**
A: Async. Task di-queue ke background, tidak mem-blok completion job.

**Q: Berapa ukuran payload maksimum per channel?**
A: Discord 6000 karakter total embeds, Telegram 4096 karakter text, Generic bergantung pada receiver (biasanya 1-10 MB default).

**Q: Bisa retry webhook manual dari UI?**
A: Ya, ada tombol "Resend webhook" di detail modal job pada History.

**Q: Apakah webhook firing tercatat di History?**
A: Ya, di tab Timeline detail job dengan status success atau fail per attempt plus timestamp.

**Q: Bisa webhook fires untuk event selain terminal state?**
A: Saat ini hanya done, error, stopped, dan diff.changed. Event progress tidak fires untuk menghindari spam.

**Q: Bagaimana tested webhook tanpa running full job?**
A: Endpoint `POST /api/webhooks/test` mengirim dummy payload tanpa butuh job real; pakai ini untuk smoke test saja.

## Keterbatasan

- Hanya 3 channel built-in (Discord, Telegram, HTTP generic); adapter lain butuh custom code.
- Format embed dan Markdown hardcoded, belum template-able melalui UI.
- Tidak ada batching atau digest mode; satu notifikasi per event.
- Rate limit di sisi channel bisa menyebabkan notification drop saat burst traffic.
- Tidak ada end-to-end encryption tambahan untuk payload.
- Retry terbatas 3 kali dengan backoff tetap; tidak ada circuit breaker advanced.
- Tidak ada UI log khusus webhook activity, harus melalui History detail per job.
- Tidak ada filtering payload selektif (misalnya exclude field tertentu) dari UI.
- Event hanya terminal state; intermediate progress tidak fires.
- Telegram tidak support rich embed, hanya Markdown text.

## Studi kasus penggunaan nyata

Untuk memberi gambaran konkret bagaimana webhook dipakai, berikut beberapa skenario nyata yang biasa ditemui:

**Skenario 1: Monitoring scraping e-commerce harian.** Pengguna menjalankan Harvester setiap pagi pukul 6 untuk menangkap daftar produk flash sale dari 3 marketplace. Webhook Discord di-set dengan trigger on_done dan on_error. Channel `#flash-sale-monitor` menerima summary scraping plus link untuk lihat detail di History. Jika ada error karena situs down, channel `#alerts` juga fires ke Telegram untuk notifikasi mobile. Total tiga notifikasi per hari, tidak overwhelming, dan visibility lengkap.

**Skenario 2: Research akademik longitudinal.** Tim peneliti tracking konten situs berita selama 6 bulan dengan Diff Detection aktif. Webhook `on_diff_only` fires hanya saat perubahan signifikan (threshold 25 persen). Dari 180 hari scraping, webhook hanya fires 12 kali, semua coincide dengan event politik besar. Generic HTTP endpoint meneruskan payload ke Google Sheet log via n8n workflow untuk dokumentasi.

**Skenario 3: CI integration untuk data pipeline.** Tim data engineering memakai PyScrapr sebagai extractor di pipeline ETL. Generic HTTP webhook dikirim ke orchestrator Airflow yang listen di endpoint internal. Saat job PyScrapr done, Airflow trigger DAG downstream untuk transform dan load ke Snowflake. Tidak ada polling; pipeline event-driven dengan latency rendah.

**Skenario 4: Alert budget CAPTCHA.** Target tertentu memicu banyak CAPTCHA dan solve cost naik cepat. Webhook warning fires ke Telegram saat `captcha_budget_usd` tercapai. Admin bisa intervensi manual (pause job, ganti provider, atau tambah budget) tanpa menunggu email laporan bulanan dari provider.

**Skenario 5: Integration dengan smart home notification.** Pengguna pribadi pakai Home Assistant untuk notifikasi rumah. Generic HTTP webhook dikirim ke endpoint HA local (`http://homeassistant.local:8123/api/webhook/pyscrapr_done`) yang trigger flash lampu kantor warna hijau saat scraping selesai, merah saat error. Integrasi fun untuk workflow visual.

## Debugging webhook lebih dalam

Saat webhook tidak berfungsi sesuai ekspektasi, beberapa langkah debugging tingkat lanjut:

1. **Aktifkan debug log.** Set log level ke DEBUG di `data/settings.json` field `log_level`. Server akan menampilkan detail payload per dispatch termasuk request headers dan response body dari channel.

2. **Pakai ngrok atau webhook.site untuk inspect.** Untuk Generic HTTP, sementara point URL ke `https://webhook.site/unique-id` untuk lihat raw payload yang PyScrapr kirim. Ini membantu konfirmasi format data sebelum integrate dengan endpoint custom Anda.

3. **Curl manual ke Discord URL.** Test kredensial Discord dengan payload minimal:
```bash
curl -X POST <discord_url> -H "Content-Type: application/json" \
  -d '{"content":"test from terminal"}'
```
Jika sukses, credential OK dan masalah ada di payload PyScrapr.

4. **Cek EventBus registration.** Di startup log, cari baris `webhook_listener registered for events: [job.done, job.error, job.stopped, diff.changed]`. Jika missing, listener tidak terdaftar dan webhook tidak akan pernah fires.

5. **Isolate per channel.** Disable dua channel, test satu. Bergantian. Ini lokalisasi masalah apakah di adapter spesifik atau di shared logic.

6. **Monitor retry pattern.** Log backoff attempt ke-1 di 1 detik, ke-2 di 2 detik, ke-3 di 4 detik. Jika pattern tidak sesuai, retry logic mungkin buggy dan butuh inspect code.

## Related docs

- [Settings](/docs/system/settings.md) - Section Webhooks untuk konfigurasi terpusat.
- [Scheduled Jobs](/docs/system/scheduled.md) - Pair dengan webhook untuk automation overnight.
- [Diff Detection](/docs/system/diff.md) - Source trigger untuk `webhook_on_diff_only`.
- [History](/docs/system/history.md) - Audit trail webhook fires per job.
- [REST API](/docs/advanced/rest-api.md) - Endpoint test webhook untuk integrasi CI.
