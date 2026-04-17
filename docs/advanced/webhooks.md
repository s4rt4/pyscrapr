# Webhooks

> Sistem notifikasi multi-channel (Discord, Telegram, HTTP generik) yang otomatis fires ke endpoint eksternal setiap kali job selesai, error, atau Diff mendeteksi perubahan signifikan.

## Deskripsi

Webhooks adalah jembatan antara PyScrapr dan dunia luar. Ketika scheduled scrape berjalan tengah malam dan Anda tidak duduk di depan komputer, bagaimana cara tahu apakah berhasil atau gagal? Jawabannya webhook: PyScrapr akan POST payload JSON ke URL yang Anda konfigurasi — Discord channel, Telegram bot, Slack-compatible endpoint, atau sistem internal custom — sehingga notifikasi masuk ke feed yang Anda monitor secara real-life (mobile app, notif desktop, dll).

Implementasi webhook di PyScrapr terpusat di service `webhooks.py` yang mendefinisikan tiga adapter channel: DiscordWebhook, TelegramBot, dan GenericHttpWebhook. Ketiganya share interface method `send(payload, job_context)` yang men-transform data job menjadi format sesuai channel. Discord pakai rich embeds dengan warna berdasarkan status (hijau done, merah error, biru running), field stats (duration, items downloaded, output path), dan thumbnail dari tool icon. Telegram pakai Markdown formatted text karena tidak support embed. Generic HTTP kirim raw JSON struktur PyScrapr canonical, cocok untuk dikonsumsi oleh webhook consumer custom.

Event system berbasis EventBus global. Saat job terminal state (done/error/stopped), orchestrator tool memanggil `event_bus.emit('job.done', job)` atau equivalent untuk error. Listener yang di-register saat startup akan dispatch ke adapter webhook sesuai trigger flags di Settings: `trigger_on_done`, `trigger_on_error`, `trigger_on_diff`. Logic ini memisahkan concern emit (tanggung jawab tool) dari dispatch (tanggung jawab webhook service), sehingga menambah channel baru tinggal register adapter baru tanpa touch kode tool.

Retry logic ditanam di tiap adapter dengan 3x attempt default dan exponential backoff (1s, 2s, 4s). Khusus Discord dan Telegram, response 429 (rate limit) dihormati dengan `Retry-After` header parsing — kita tidak langsung retry melainkan sleep sesuai saran server. Jika semua retry gagal, event dicatat di log level WARNING tapi tidak mem-block job, sehingga kegagalan webhook tidak memengaruhi scraping core. Untuk testing, ada endpoint `POST /api/webhooks/test` yang kirim dummy payload ke semua channel configured — berguna saat setup awal untuk memastikan credential benar.

## Kapan pakai?

1. **Notifikasi scheduled jobs overnight** — Pulang kerja pagi, langsung tahu dari Discord channel apakah semua schedule semalam sukses.
2. **Alert error untuk job kritikal** — Set trigger_on_error=true agar kegagalan langsung nongol di Telegram tanpa perlu buka Dashboard.
3. **Integration dengan CI/CD** — Generic HTTP webhook bisa trigger downstream pipeline (misal data processing) setelah scraping selesai.
4. **Monitoring diff significant** — Kombinasi Diff Detection + trigger_on_diff mengirim alert ketika situs target berubah drastis.
5. **Logging terpusat ke Slack** — Gunakan Slack-compatible endpoint (format Discord kompatibel) untuk stream log semua job ke channel tim.
6. **Automation trigger downstream** — HTTP webhook bisa trigger Zapier/IFTTT/n8n untuk workflow multi-step.
7. **SMS / WhatsApp via gateway** — Kirim ke HTTP endpoint Twilio atau WhatsApp Business API untuk notif prioritas tinggi.
8. **Email via bridge service** — Konekkan ke Mailgun/SendGrid webhook endpoint yang forward payload jadi email.

## Cara penggunaan

1. Buka Settings > Webhooks section.
2. Untuk Discord: buat webhook di server Discord (Server Settings > Integrations > Webhooks > New). Copy URL, paste ke field `discord_url`.
3. Untuk Telegram: buat bot via @BotFather, dapatkan token. Cari chat_id dengan mengirim pesan ke bot lalu access `https://api.telegram.org/bot<TOKEN>/getUpdates`. Isi `telegram_token` dan `telegram_chat_id`.
4. Untuk HTTP generik: siapkan endpoint POST Anda sendiri yang accept JSON. Paste URL ke `generic_http_url`.
5. Toggle trigger flags: `trigger_on_done`, `trigger_on_error`, `trigger_on_diff` sesuai kebutuhan.
6. Klik "Save changes" di toolbar.
7. Klik tombol "Send test" di samping field webhook. Request dummy dikirim ke semua channel yang configured.
8. Cek Discord channel/Telegram chat/endpoint Anda. Pesan test harus muncul dalam 2-3 detik.
9. Jika tidak muncul, buka log server untuk lihat error (URL salah, token invalid, network issue).
10. Jalankan job sample (misal harvest URL test) untuk verify trigger on done bekerja dengan data nyata.
11. Monitor beberapa trigger pertama untuk pastikan format embed/markdown sesuai ekspektasi.
12. Fine-tune trigger flags dan threshold (untuk diff) sesuai noise level yang acceptable.

## Pengaturan / Konfigurasi

Field di Settings > Webhooks section:

- **discord_url** (string URL) — Webhook URL Discord lengkap, format `https://discord.com/api/webhooks/<id>/<token>`.
- **discord_username** (string, optional, default `PyScrapr`) — Username yang muncul di Discord post.
- **discord_avatar_url** (string URL, optional) — URL image avatar untuk post.
- **telegram_token** (string) — Bot token format `<bot_id>:<secret>`.
- **telegram_chat_id** (string) — Target chat ID (user atau group). Negative untuk group.
- **telegram_parse_mode** (enum `Markdown`, `MarkdownV2`, `HTML`, default `Markdown`) — Format parse text.
- **generic_http_url** (string URL) — POST endpoint.
- **generic_http_method** (enum `POST`, `PUT`, default `POST`) — HTTP method.
- **generic_http_headers** (object, optional) — Extra headers untuk request (misal Auth).
- **trigger_on_done** (boolean, default true) — Fire saat status berubah ke done.
- **trigger_on_error** (boolean, default true) — Fire saat error.
- **trigger_on_diff** (boolean, default false) — Fire saat Diff detect significant change.
- **diff_threshold_pct** (float 0-100, default 20.0) — Minimum persentase perubahan untuk trigger_on_diff.
- **retry_count** (int, default 3) — Jumlah retry.
- **retry_backoff_base** (float, default 1.0) — Base backoff detik (exponential: base * 2^attempt).
- **include_full_result** (boolean, default false) — Apakah payload include full result JSON (bisa besar).
- **payload_truncate_length** (int char, default 2000) — Truncate text payload.

## Output

Untuk tiap trigger, adapter menghasilkan HTTP request ke URL channel. Payload berbeda per adapter:

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

## Integrasi dengan fitur lain

- **Scheduled Jobs** — Trigger on_fire_webhook atau pada done/error dari schedule fires.
- **Diff Detection** — Trigger on_diff dengan threshold percentage.
- **EventBus** — Global mechanism yang memicu dispatch.
- **Settings** — Semua config terpusat di section webhooks.
- **History** — Detail modal job menampilkan indikator webhook fired dengan status (success/fail).
- **REST API** — Endpoint /api/webhooks/test untuk CI integration.

## Tips & Best Practices

1. **Pisahkan channel Discord untuk severity** — Success ke #scraper-log, error ke #alerts, diff ke #monitoring.
2. **Gunakan Telegram untuk urgent** — Mobile push Telegram lebih reliable daripada Discord untuk notif kritikal.
3. **Jangan aktifkan trigger_on_diff tanpa threshold tuning** — Perubahan minor bisa banjiri channel.
4. **Test webhook setelah setiap config change** — Tombol Send test murah untuk validate.
5. **Gunakan generic HTTP untuk automation chain** — Kirim ke n8n/Zapier untuk workflow kompleks.
6. **Masking credential di Settings UI** — Pastikan Anda logout sebelum screenshot Settings untuk sharing.
7. **Monitor retry failure di log** — Jika sering retry habis, investigate network atau credential.
8. **Set payload_truncate_length rendah untuk Telegram** — Telegram punya limit 4096 char per message.

## Troubleshooting

**Problem: Webhook test sukses tapi actual job tidak trigger.**
Cause: Trigger flags off, atau EventBus tidak emit event (bug tool orchestrator).
Solution: Verifikasi flags true di Settings. Cek log untuk "event emitted: job.done".

**Problem: Discord menerima pesan tapi format embed rusak.**
Cause: Character encoding issue atau struktur embed invalid (color bukan integer, field > 25).
Solution: Test dengan payload sederhana. Validate payload via Discord webhook tester online.

**Problem: Telegram 401 Unauthorized.**
Cause: Bot token salah atau bot telah di-revoke.
Solution: Regenerate token via @BotFather. Update di Settings.

**Problem: Telegram 400 chat not found.**
Cause: Chat ID salah, atau bot belum diajak bicara di chat tersebut (bot harus initiate atau di-add ke group dulu).
Solution: Send `/start` ke bot dari chat target. Verifikasi chat_id via getUpdates endpoint.

**Problem: HTTP generic 401/403 di receiver.**
Cause: Auth header missing atau salah.
Solution: Isi `generic_http_headers` dengan Authorization header yang sesuai.

**Problem: Retry terus gagal padahal URL benar.**
Cause: SSL cert issue (self-signed cert di endpoint custom).
Solution: Allow insecure SSL di settings (advanced flag), atau fix cert.

**Problem: Rate limit 429 dari Discord.**
Cause: Terlalu banyak webhook fires dalam interval singkat (Discord limit ~30/min).
Solution: Batch notifikasi atau gunakan Telegram/generic. Implement debouncing di event bus.

**Problem: Payload terpotong di channel.**
Cause: `payload_truncate_length` terlalu rendah.
Solution: Naikkan limit, atau pindah `include_full_result` ke false untuk kurangi size.

**Problem: Webhook tidak fires untuk job dari Scheduled source.**
Cause: EventBus listener tidak aktif untuk scheduled source (misconfiguration).
Solution: Pastikan event emission konsisten across sources. Bug fix jika perlu.

## FAQ

**Q: Apakah bisa pakai multiple Discord webhook URL sekaligus?**
A: Default satu URL per field. Untuk multi, extend adapter atau pakai Discord webhook yang forward ke multi channel.

**Q: Apakah payload aman (encrypted)?**
A: Default pakai HTTPS jika URL https. Payload plain JSON; tidak ada end-to-end encryption.

**Q: Bisa custom template message?**
A: Sekarang hardcoded format per adapter. Template customization feature request.

**Q: Apakah rate limit PyScrapr sendiri ada?**
A: Tidak di sisi PyScrapr; bergantung pada rate limit channel.

**Q: Bagaimana handle secrets di settings.json (versi control)?**
A: Jangan commit settings.json ke Git. Pakai env var override untuk secrets di environment production.

**Q: Bisa skip webhook untuk job tertentu?**
A: Ya, field `skip_webhook: true` di config submission akan bypass.

**Q: Apakah webhook async atau blocking?**
A: Async (task queued), tidak block job completion.

**Q: Berapa ukuran payload maksimum?**
A: Discord 6000 char total embeds, Telegram 4096 char text, Generic bergantung receiver.

**Q: Bisa retry webhook manual dari UI?**
A: Ada tombol "Resend webhook" di detail modal job untuk retry.

**Q: Apakah webhook firing tercatat di History?**
A: Ya, di tab Timeline detail job dengan status success/fail per attempt.

## Keterbatasan

- Hanya 3 channel built-in (Discord, Telegram, HTTP generic); adapter lain butuh code.
- Format embed/markdown hardcoded, tidak template-able.
- Tidak ada batching/digest mode (satu notif per event).
- Rate limiting di channel bisa drop notifikasi saat burst.
- Tidak ada end-to-end encryption untuk payload.
- Retry terbatas 3x dengan backoff tetap; tidak configurable advanced (circuit breaker).
- Tidak ada UI log khusus webhook activity; harus lewat History detail.

## Related docs

- [Settings](../system/settings.md) — Section Webhooks untuk config.
- [Scheduled Jobs](../system/scheduled.md) — Pair dengan webhook on_fire.
- [Diff Detection](../system/diff.md) — Trigger on_diff.
- [History](../system/history.md) — Audit trail webhook fires.
- [REST API](./rest-api.md) — Endpoint test webhook.
