# Domain Intel (WHOIS + DNS + Subdomain)

> Tool reconnaissance domain yang menggabungkan tiga lookup penting dalam satu tampilan: WHOIS (siapa yang memiliki domain ini, kapan terdaftar, kapan kedaluwarsa), DNS records (A, AAAA, MX, TXT, NS, CAA, SOA), dan enumerasi subdomain via Certificate Transparency log crt.sh. Satu input domain, satu klik, semua data keluar.

## Apa itu Domain Intel

Domain Intel adalah modul PyScrapr yang berfungsi sebagai "tiga tool dalam satu" untuk riset domain. Anda masukkan nama domain (misalnya `contoh.com`), tool akan menjalankan tiga investigasi paralel: pertama, menarik metadata registrasi domain dari RDAP (protokol registry modern pengganti WHOIS klasik), termasuk registrar, tanggal daftar, tanggal expire, nameservers, dan status domain. Kedua, menanyakan DNS resolver untuk semua jenis record populer yaitu A, AAAA, MX, TXT, NS, CAA, dan SOA, lalu menampilkan hasilnya rapi per kategori. Ketiga, menelusuri database Certificate Transparency publik crt.sh untuk mencari semua subdomain yang pernah diterbitkan sertifikat SSL-nya, termasuk yang tidak ter-link publik dan tidak muncul di Google.

Kenapa tiga-tiganya digabung? Karena saat Anda riset sebuah domain, pertanyaannya biasanya berlapis: "Siapa yang punya ini? Kemana DNS-nya mengarah? Apa saja subdomain yang mereka operasikan?" Daripada buka tiga tool terpisah (whois command-line, dig atau nslookup, pencarian subdomain manual), Domain Intel menjalankan ketiganya paralel dalam satu request backend, lalu menampilkan hasil dalam UI ber-tab.

> [!NOTE]
> Domain Intel tidak menyimpan atau mengindeks data domain. Setiap analisis adalah query real-time ke RDAP server, DNS resolver Anda, dan crt.sh. Hasil tidak di-cache oleh PyScrapr, jadi data yang Anda lihat adalah snapshot fresh pada detik request dikirim.

Filosofi modul ini: "reconnaissance ringan sebelum riset lebih dalam". Sebelum Anda scan port, sebelum Anda fuzz endpoint, sebelum Anda bikin proposal maintenance untuk klien, Anda butuh tahu siapa yang punya domain ini dan seperti apa infrastrukturnya. Domain Intel menjawab pertanyaan itu dalam 5 detik.

## Cara pakai (step-by-step)

1. Buka PyScrapr di browser, navigasi ke menu **Domain Intel** di sidebar kiri. Halaman akan menampilkan satu input field untuk domain target dan tombol Analisis.

2. Di field `Domain target`, ketik atau paste nama domain. Anda bisa masukkan format apapun: `contoh.com`, `www.contoh.com`, `https://contoh.com/halaman`, tool akan normalize ke bare domain `contoh.com` otomatis.

3. Klik tombol `Analisis` (biru). Backend akan jalankan tiga query paralel via asyncio.gather, biasanya selesai dalam 2-5 detik kalau semua endpoint responsif.

4. Hasil muncul dalam tiga tab:
   - **WHOIS**: tabel dengan registrar, tanggal registrasi, tanggal kedaluwarsa, update terakhir, daftar nameservers, status domain, dan negara registrant kalau tidak redacted.
   - **DNS**: satu card per record type yang memang ada datanya. Setiap card menampilkan count + daftar value monospace.
   - **Subdomain**: searchable list semua subdomain yang ditemukan di crt.sh, ter-link klikan ke HTTPS.

5. Kalau WHOIS mengembalikan "domain tidak terdaftar", itu signal kuat domain available untuk register. Kalau DNS kosong semua, domain ada tapi tidak aktif. Kalau subdomain list kosong, domain belum pernah issue SSL certificate yang ter-log publik (jarang untuk domain aktif).

## Contoh kasus pakai

- **Due diligence sebelum beli domain** - Anda tertarik beli domain `brandbaru.id` dari reseller. Scan dulu dengan Domain Intel. WHOIS tunjukkan domain expire 3 bulan lagi dengan registrar abal-abal. Info ini membantu Anda negosiasi harga (atau tunggu expire lalu register langsung di registrar proper).

- **Audit infrastruktur klien freelance** - Klien baru serahkan akses hosting. Anda scan domain mereka untuk crosscheck: nameservers di WHOIS cocok dengan record NS di DNS? MX record mengarah kemana (Google Workspace, Zoho, mail sendiri)? Subdomain apa saja yang mereka punya (staging, api, admin, cms)? Dari situ Anda tahu landscape sebelum sentuh production.

- **Investigasi phishing atau brand protection** - Tim security report ada domain typosquat mirip brand Anda. Scan domain suspect itu. WHOIS tunjukkan registrar tidak wajar, nameservers cloudflare tier gratis, subdomain `login.brandanda-typo.com` dengan SSL cert baru kemarin. Semua signal kuat untuk takedown request.

- **Kompetitor intelligence** - Kompetitor launching produk baru dari subdomain? Scan domain mereka, lihat list subdomain di crt.sh. Ketemu `new.kompetitor.com`, `beta.kompetitor.com`, atau `app-v2.kompetitor.com` meski belum di-publikasi. Clue kuat produk baru mereka.

- **Migrasi domain check** - Setelah pindah DNS provider, scan ulang untuk verify: NS sudah propagate, MX belum ikut kepindah (jangan sampai email down), TXT SPF/DKIM masih ada.

- **Security hygiene check** - Scan domain sendiri, cek CAA record. Tidak ada? Sebaiknya tambahkan supaya hanya CA yang Anda whitelist bisa issue cert untuk domain Anda. Cek TXT, ada SPF dengan `-all` hard fail? Ada DMARC policy? Ada DKIM?

- **Subdomain takeover hunting** - Dari list crt.sh, Anda lihat subdomain yang CNAME-nya mengarah ke service eksternal (Heroku, GitHub Pages, AWS S3 bucket). Kalau service tersebut sudah tidak Anda claim, attacker bisa claim dan host konten di subdomain Anda. Scan subdomain list, check CNAME, audit mana yang "dangling".

## Apa yang dideteksi

### WHOIS (via RDAP)

Tool pakai protokol RDAP (Registration Data Access Protocol), standar modern IETF yang menggantikan WHOIS tradisional. Endpoint `rdap.org/domain/<domain>` otomatis bootstrap ke RDAP server registry yang tepat untuk TLD tersebut.

Field yang di-extract:

| Field | Deskripsi |
|-------|-----------|
| **Registrar** | Perusahaan yang menjual dan mengelola registrasi domain ini (misalnya GoDaddy, Namecheap, Niagahoster) |
| **Tanggal registrasi** | Kapan domain pertama kali di-register di registry |
| **Tanggal kedaluwarsa** | Kapan registrasi berakhir kalau tidak di-renew |
| **Update terakhir** | Kapan record domain di registry terakhir diubah |
| **Nameservers** | Daftar authoritative NS yang akan menjawab query DNS domain ini |
| **Status** | Kode status domain (clientTransferProhibited, serverHold, redemptionPeriod, dll) |
| **Negara registrant** | Kode negara pemilik (kalau tidak redacted via GDPR/privacy protection) |

Karena GDPR dan proxy privacy yang mayoritas registrar aktifkan default, field pemilik personal (nama, email, telepon, alamat) biasanya redacted. Ini normal dan bukan bug.

### DNS Records

Tool pakai library `dnspython` untuk query system resolver Anda (biasanya mengarah ke DNS ISP, atau 1.1.1.1/8.8.8.8 kalau Anda konfigurasi manual). Record types default yang di-query:

| Record | Deskripsi | Kegunaan |
|--------|-----------|----------|
| **A** | IPv4 address | Kemana domain mengarah secara fisik |
| **AAAA** | IPv6 address | Kalau situs sudah support IPv6 |
| **MX** | Mail exchanger | Server email domain |
| **TXT** | Text record | Biasanya SPF, DKIM, DMARC, verifikasi domain (Google, Facebook, dll) |
| **NS** | Nameservers | Authoritative DNS servers (cocokkan dengan WHOIS) |
| **CAA** | Certificate Authority Authorization | CA yang boleh issue cert untuk domain ini |
| **SOA** | Start of Authority | Metadata zona DNS (serial, refresh interval, dll) |

Kalau Anda butuh record selain itu (misal SRV, PTR, DS), pakai endpoint `POST /api/intel/dns` langsung dengan param `record_types: ["SRV"]`. UI defaultnya pakai set yang paling berguna saja.

### Subdomain via Certificate Transparency

Tool query `crt.sh/?q=%.<domain>&output=json`. crt.sh adalah mirror publik dari semua CT log browser, yang artinya semua sertifikat SSL yang pernah di-issue publik ter-catat di sana. Setiap issuance certificate wajib deklarasikan subject domain, jadi subdomain yang pernah punya HTTPS cert pasti muncul.

Yang bisa ditemukan:

- Subdomain publik yang Anda sudah tahu (www, api, blog, shop)
- Subdomain internal yang pernah issue cert via Let's Encrypt DNS challenge (misal `internal-admin.contoh.com`)
- Subdomain lama yang sudah tidak aktif tapi cert-nya pernah issued
- Subdomain wildcard (`*.contoh.com`) - tool strip wildcard prefix

Yang tidak bisa ditemukan di sini:

- Subdomain yang tidak pernah punya HTTPS cert (plain HTTP only atau tidak di-expose)
- Subdomain yang cert-nya self-signed atau private CA (tidak ter-log CT)
- Subdomain yang baru di-create <24 jam (CT log propagation delay)

Untuk cakupan lebih luas, kombinasikan dengan tool subdomain brute-force eksternal (amass, subfinder). Domain Intel deliberately minimal, cuma pakai satu sumber pasif.

## Cara kerja internal (teknis)

1. **Normalize domain input.** Tool extract bare domain dari input apapun via urlparse + strip www + lowercase + strip port.

2. **Tiga query paralel via asyncio.gather.** WHOIS, DNS, crt.sh jalan bersamaan, bukan sequential. Total waktu = max(t_whois, t_dns, t_crtsh), bukan sum-nya.

3. **WHOIS flow.** GET `https://rdap.org/domain/<dom>` dengan header Accept `application/rdap+json`. rdap.org akan bounce ke RDAP server registry yang tepat (Verisign untuk .com, PIR untuk .org, PANDI untuk .id, dll). Tool parse response JSON, extract events untuk tanggal, entities[role=registrar] untuk nama registrar, nameservers array, status array.

4. **DNS flow.** dnspython `Resolver().resolve(domain, rtype)` untuk setiap record type. Timeout 5 detik per query, lifetime 10 detik total per record type. NXDOMAIN di-handle (domain tidak ada di DNS), NoAnswer di-handle (record type tidak di-set tapi domain ada). Karena dnspython sync, jalan di `asyncio.to_thread` supaya tidak block event loop.

5. **crt.sh flow.** GET `https://crt.sh/?q=%.<dom>&output=json` dengan User-Agent custom (crt.sh kadang reject tanpa UA). Response array of {name_value, not_before, not_after, issuer_name, ...}. Tool iterate, split name_value by newline (satu cert bisa punya multiple SAN), strip wildcard `*.` prefix, filter hanya yang match suffix domain, dedupe via set, sort alfabetis.

6. **Graceful degradation.** Kalau salah satu dari tiga lookup fail (RDAP timeout, crt.sh 503, DNS server unreachable), dua lainnya tetap kembali dengan data valid. Gagal total hanya kalau domain input invalid.

## Pengaturan

Modul ini intentional minimal:

### timeout per lookup
WHOIS: 20 detik. DNS: 5 detik per record + 10 detik overall. crt.sh: 30 detik (bisa lama karena database besar). Tidak exposed di UI karena nilai default sudah calibrated.

### record_types
Default untuk endpoint `/analyze` adalah A, AAAA, MX, TXT, NS, CAA, SOA. Kalau Anda butuh SRV, PTR, NAPTR, dll, pakai endpoint `/api/intel/dns` dengan body `{"domain": "x", "record_types": ["SRV", "PTR"]}`.

### User-Agent untuk crt.sh
Hardcoded `Mozilla/5.0 (PyScrapr Intel) DomainIntel/1.0`. crt.sh tidak accept request tanpa UA yang reasonable.

## Tips akurasi

- **WHOIS cache stale.** Registry RDAP server kadang cache response 5-60 menit. Kalau Anda baru saja update nameservers dan hasil WHOIS belum berubah, tunggu 1 jam lalu scan ulang.

- **DNS lokal vs authoritative.** Default pakai system resolver yang propagate dari ISP Anda. Kalau Anda butuh authoritative answer langsung (skip cache), pakai tool eksternal `dig @<ns> <domain> <rtype>` manual.

- **crt.sh boleh lambat.** Database besar + load variable. Kalau timeout, retry setelah 1-2 menit. Tidak jarang crt.sh down beberapa jam; dalam kasus itu subdomain list akan kosong.

- **Subdomain list tidak lengkap.** Ingat, crt.sh cuma tunjukkan subdomain yang pernah issue public CT-logged cert. Ini snapshot penting tapi bukan eksaustif. Kombinasikan dengan URL Mapper untuk crawl situs dan ekstrak subdomain dari HTML.

- **Wildcard cert bikin noise.** Domain yang pakai `*.contoh.com` wildcard akan muncul sebagai `contoh.com` setelah stripping. Tidak ada cara pasif untuk enumerate subdomain spesifik di balik wildcard.

## Troubleshooting

### Problem: "rdap fetch failed"
**Gejala:** WHOIS tab tunjukkan error. 
**Penyebab:** RDAP server registry TLD tersebut mungkin down, atau domain pakai TLD yang belum support RDAP. 
**Solusi:** Coba beberapa menit lagi. Kalau persisten, cek manual di `https://rdap.org/domain/<dom>` di browser. Beberapa ccTLD lama memang belum RDAP-compliant.

### Problem: DNS tab menunjukkan "dnspython not installed"
**Gejala:** Semua record kosong dengan error "_error". 
**Penyebab:** Dependency DNS library belum terinstall di venv. 
**Solusi:** `pip install dnspython>=2.6.0` di venv backend, restart server.

### Problem: Semua DNS record kosong padahal domain jelas aktif
**Gejala:** Website buka normal tapi DNS tab kosong. 
**Penyebab:** DNS resolver sistem down atau rate-limit Anda. 
**Solusi:** Cek `nslookup <domain>` di terminal. Kalau itu juga gagal, ganti DNS resolver sistem (1.1.1.1 atau 8.8.8.8).

### Problem: Subdomain tab kosong padahal domain besar
**Gejala:** Domain major company, tapi list subdomain cuma 1-2. 
**Penyebab:** crt.sh sedang down atau rate-limit IP Anda. 
**Solusi:** Tunggu 5-10 menit, retry. Cek manual di `https://crt.sh/?q=%.<dom>` browser.

### Problem: Subdomain list mengandung entries aneh
**Gejala:** Ada entries seperti `contoh.com.contoh.com` atau domain pihak ketiga. 
**Penyebab:** crt.sh response kadang mengandung cert yang SAN-nya kena multiple domain. Tool filter by suffix, tapi edge case bisa tembus. 
**Solusi:** Abaikan entries yang aneh, atau report sebagai bug dengan contoh data.

## Keamanan / etika

> [!WARNING]
> Domain Intel melakukan query pasif. Tidak ada scan port, tidak ada probing, tidak ada brute force. Tapi request tetap tercatat di log RDAP server dan crt.sh.

- **WHOIS lookup legal di mana-mana.** Data registrasi adalah publik by design (meski mayoritas field sekarang redacted GDPR). Anda tidak melanggar hukum dengan lookup WHOIS.

- **DNS query legal.** DNS adalah protokol publik. Menanyakan DNS server "apa A record untuk contoh.com" tidak berbeda dengan browser yang buka situs.

- **crt.sh adalah data publik.** Certificate Transparency dibuat justru supaya publik bisa audit issuance cert. Semua data di crt.sh adalah public knowledge.

- **Jangan kombinasikan pasif dengan aktif tanpa izin.** Pakai Domain Intel untuk enumerate subdomain OK. Setelah itu scan port atau brute force endpoint di subdomain tersebut tanpa izin pemilik, itu sudah aktivitas berbeda dan legality-nya tergantung yurisdiksi.

- **Subdomain enumeration bisa dianggap reconnaissance.** Dalam konteks penetration test, ini dianggap "passive recon" dan biasanya di-allow tanpa written consent. Tapi dalam konteks korporat dengan audit kompetitor, praktek ini gray area; jangan pakai untuk bikin laporan komersial ke klien yang tidak punya relasi bisnis dengan target.

## Related docs

- [Tech Stack Detector](/docs/tools/tech-detector.md) - untuk scan teknologi di subdomain yang Anda temukan
- [Wayback Machine Explorer](/docs/intel/wayback.md) - untuk lihat arsip historis domain
- [Sitemap Analyzer](/docs/intel/sitemap.md) - untuk enumerate URL dari sitemap public
- [URL Mapper](/docs/tools/url-mapper.md) - untuk crawl dan discover URL aktif
- [SSL Inspector](/docs/tools/ssl-inspect.md) - deep-dive sertifikat SSL subdomain yang ditemukan
