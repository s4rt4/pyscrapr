import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Divider,
  Grid,
  Group,
  NumberInput,
  PasswordInput,
  Progress,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDeviceFloppy, IconRefresh } from "@tabler/icons-react";

function fmtBytes(n: number): string {
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1073741824) return `${(n / 1048576).toFixed(1)} MB`;
  return `${(n / 1073741824).toFixed(2)} GB`;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, any> | null>(null);
  const [defaults, setDefaults] = useState<Record<string, any>>({});
  const [disk, setDisk] = useState<any>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = () => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then((d) => {
        setSettings(d.settings);
        setDefaults(d.defaults);
        setDirty(false);
      })
      .catch((e) =>
        notifications.show({
          title: "Gagal memuat data",
          message: e?.message || "Terjadi kesalahan tidak dikenal",
          color: "red",
        })
      );
    fetch("/api/system/dashboard")
      .then((r) => r.json())
      .then((d) => setDisk(d.disk))
      .catch((e) =>
        notifications.show({
          title: "Gagal memuat data",
          message: e?.message || "Terjadi kesalahan tidak dikenal",
          color: "red",
        })
      );
  };

  useEffect(load, []);

  const set = (key: string, value: any) => {
    setSettings((s) => (s ? { ...s, [key]: value } : s));
    setDirty(true);
  };

  const onSave = async () => {
    if (!settings) return;
    try {
      setSaving(true);
      const r = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      setSettings(d.settings);
      setDirty(false);
      notifications.show({ title: "Saved", message: "Settings updated", color: "teal" });
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setSaving(false);
    }
  };

  const onReset = async () => {
    try {
      const r = await fetch("/api/settings/reset", { method: "POST" });
      const d = await r.json();
      setSettings(d.settings);
      setDirty(false);
      notifications.show({ title: "Reset", message: "All settings restored to defaults", color: "cyan" });
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    }
  };

  if (!settings) {
    return (
      <Stack gap="md">
        <Title order={2}>Settings</Title>
        <SimpleGrid cols={2}>
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} h={200} radius="lg" />
          ))}
        </SimpleGrid>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Settings</Title>
          <Text c="dimmed" size="sm">
            Configure defaults for all tools. Changes apply to new jobs.
          </Text>
        </div>
        <Group>
          <Button
            variant="subtle"
            color="gray"
            leftSection={<IconRefresh size={16} />}
            onClick={onReset}
          >
            Reset defaults
          </Button>
          <Button
            leftSection={<IconDeviceFloppy size={16} />}
            onClick={onSave}
            loading={saving}
            disabled={!dirty}
          >
            Save
          </Button>
        </Group>
      </Group>

      <Grid>
        {/* ─── Scraping defaults ─── */}
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="lg" p="lg">
            <Text fw={700} mb="md">Scraping defaults</Text>
            <Stack gap="sm">
              <NumberInput
                label="Default concurrency"
                description="Parallel downloads/requests per job"
                value={settings.default_concurrency}
                onChange={(v) => set("default_concurrency", v)}
                min={1}
                max={32}
              />
              <NumberInput
                label="Default rate limit (req/sec)"
                description="Max requests per second per host"
                value={settings.default_rate_limit}
                onChange={(v) => set("default_rate_limit", v)}
                min={0.1}
                max={20}
                step={0.5}
                decimalScale={1}
              />
              <NumberInput
                label="HTTP timeout (seconds)"
                value={settings.default_timeout}
                onChange={(v) => set("default_timeout", v)}
                min={5}
                max={120}
              />
              <NumberInput
                label="Max retries on failure"
                value={settings.max_retries}
                onChange={(v) => set("max_retries", v)}
                min={0}
                max={10}
              />
              <TextInput
                label="User-Agent string"
                value={settings.user_agent}
                onChange={(e) => set("user_agent", e.currentTarget.value)}
              />
            </Stack>
          </Card>
        </Grid.Col>

        {/* ─── Image filter defaults ─── */}
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="lg" p="lg">
            <Text fw={700} mb="md">Image Harvester defaults</Text>
            <Stack gap="sm">
              <NumberInput
                label="Min image width (px)"
                value={settings.min_image_width}
                onChange={(v) => set("min_image_width", v)}
                min={0}
              />
              <NumberInput
                label="Min image height (px)"
                value={settings.min_image_height}
                onChange={(v) => set("min_image_height", v)}
                min={0}
              />
              <NumberInput
                label="Min image size (bytes)"
                value={settings.min_image_bytes}
                onChange={(v) => set("min_image_bytes", v)}
                min={0}
                step={1024}
              />
            </Stack>

            <Divider my="md" label="URL Mapper defaults" labelPosition="left" />
            <Stack gap="sm">
              <NumberInput
                label="Max depth"
                value={settings.mapper_max_depth}
                onChange={(v) => set("mapper_max_depth", v)}
                min={1}
                max={10}
              />
              <NumberInput
                label="Max pages"
                value={settings.mapper_max_pages}
                onChange={(v) => set("mapper_max_pages", v)}
                min={1}
                max={50000}
              />
              <Switch
                label="Stay on domain by default"
                checked={settings.mapper_stay_on_domain}
                onChange={(e) => set("mapper_stay_on_domain", e.currentTarget.checked)}
              />
              <Switch
                label="Respect robots.txt by default"
                checked={settings.mapper_respect_robots}
                onChange={(e) => set("mapper_respect_robots", e.currentTarget.checked)}
              />
            </Stack>
          </Card>
        </Grid.Col>

        {/* ─── Media Downloader defaults ─── */}
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="lg" p="lg">
            <Text fw={700} mb="md">Media Downloader defaults</Text>
            <Stack gap="sm">
              <Select
                label="Default quality"
                value={settings.default_quality}
                onChange={(v) => set("default_quality", v)}
                data={[
                  { value: "best", label: "Best" },
                  { value: "4k", label: "4K" },
                  { value: "1080p", label: "1080p" },
                  { value: "720p", label: "720p" },
                  { value: "480p", label: "480p" },
                  { value: "audio", label: "Audio only" },
                ]}
              />
              <Select
                label="Default format"
                value={settings.default_format}
                onChange={(v) => set("default_format", v)}
                data={[
                  { value: "mp4", label: "MP4" },
                  { value: "webm", label: "WebM" },
                  { value: "mkv", label: "MKV" },
                  { value: "mp3", label: "MP3" },
                  { value: "m4a", label: "M4A" },
                  { value: "flac", label: "FLAC" },
                ]}
              />
              <Select
                label="Default subtitles"
                value={settings.default_subtitles}
                onChange={(v) => set("default_subtitles", v)}
                data={[
                  { value: "skip", label: "Skip" },
                  { value: "download", label: "Download (.srt)" },
                  { value: "embed", label: "Embed in video" },
                ]}
              />
              <Switch
                label="Embed thumbnail by default"
                checked={settings.embed_thumbnail}
                onChange={(e) => set("embed_thumbnail", e.currentTarget.checked)}
              />
              <Switch
                label="Embed metadata by default"
                checked={settings.embed_metadata}
                onChange={(e) => set("embed_metadata", e.currentTarget.checked)}
              />
              <Select
                label="Default cookies browser"
                description="Auto-import cookies from this browser"
                value={settings.cookies_browser}
                onChange={(v) => set("cookies_browser", v || "")}
                data={[
                  { value: "", label: "None" },
                  { value: "chrome", label: "Chrome" },
                  { value: "firefox", label: "Firefox" },
                  { value: "edge", label: "Edge" },
                  { value: "brave", label: "Brave" },
                ]}
                clearable
              />
            </Stack>
          </Card>
        </Grid.Col>

        {/* ─── Site Ripper + UI ─── */}
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="lg" p="lg">
            <Text fw={700} mb="md">Site Ripper defaults</Text>
            <Stack gap="sm">
              <NumberInput
                label="Max depth"
                value={settings.ripper_max_depth}
                onChange={(v) => set("ripper_max_depth", v)}
                min={0}
                max={10}
              />
              <NumberInput
                label="Max pages"
                value={settings.ripper_max_pages}
                onChange={(v) => set("ripper_max_pages", v)}
                min={1}
                max={10000}
              />
              <NumberInput
                label="Max assets"
                value={settings.ripper_max_assets}
                onChange={(v) => set("ripper_max_assets", v)}
                min={1}
                max={100000}
              />
              <Switch
                label="Rewrite links by default"
                checked={settings.ripper_rewrite_links}
                onChange={(e) => set("ripper_rewrite_links", e.currentTarget.checked)}
              />
              <Switch
                label="Generate PDF report by default"
                checked={settings.ripper_generate_report}
                onChange={(e) => set("ripper_generate_report", e.currentTarget.checked)}
              />
            </Stack>

            <Divider my="md" label="UI Preferences" labelPosition="left" />
            <Stack gap="sm">
              <Switch
                label="Notification sound on job complete"
                checked={settings.notification_sound}
                onChange={(e) => set("notification_sound", e.currentTarget.checked)}
              />
              <Switch
                label="Auto-open download folder when done"
                checked={settings.auto_open_folder}
                onChange={(e) => set("auto_open_folder", e.currentTarget.checked)}
              />
              <TextInput
                label="Download directory"
                description="Base folder for all downloads"
                value={settings.download_dir}
                onChange={(e) => set("download_dir", e.currentTarget.value)}
              />
            </Stack>
          </Card>
        </Grid.Col>

        {/* ─── Playwright ─── */}
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="lg" p="lg">
            <Text fw={700} mb="md">Playwright (browser renderer)</Text>
            <Text size="xs" c="dimmed" mb="md">
              Jalankan `playwright install chromium` setelah enable pertama kali.
            </Text>
            <Stack gap="sm">
              <Switch
                label="Enable Playwright sebagai default global"
                checked={!!settings.playwright_enabled}
                onChange={(e) => set("playwright_enabled", e.currentTarget.checked)}
              />
              <Select
                label="Wait until"
                description="Kapan Chromium dianggap selesai load"
                value={settings.playwright_wait_until}
                onChange={(v) => set("playwright_wait_until", v)}
                data={[
                  { value: "load", label: "load" },
                  { value: "domcontentloaded", label: "domcontentloaded" },
                  { value: "networkidle", label: "networkidle" },
                ]}
              />
              <NumberInput
                label="Timeout (ms)"
                value={settings.playwright_timeout_ms}
                onChange={(v) => set("playwright_timeout_ms", v)}
                min={1000}
                max={300000}
                step={1000}
              />
            </Stack>
          </Card>
        </Grid.Col>

        {/* ─── Disk + About (stacked in one half-width card) ─── */}
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="lg" p="lg">
            <Text fw={700} mb="md">Disk usage</Text>
            {disk ? (
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text size="sm">Downloads</Text>
                  <Text size="sm" fw={600}>{fmtBytes(disk.downloads_bytes)}</Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm">Database + AI</Text>
                  <Text size="sm" fw={600}>{fmtBytes(disk.data_bytes)}</Text>
                </Group>
                <Progress
                  value={disk.disk_total_gb > 0 ? ((disk.disk_total_gb - disk.disk_free_gb) / disk.disk_total_gb) * 100 : 0}
                  size="sm"
                  radius="xl"
                  mt="xs"
                />
                <Text size="xs" c="dimmed">
                  {disk.disk_free_gb} GB free / {disk.disk_total_gb} GB total
                </Text>
              </Stack>
            ) : (
              <Skeleton h={80} />
            )}
            <Divider my="lg" />
            <Text fw={700} mb="md">About PyScrapr</Text>
            <Stack gap={4}>
              <InfoRow label="Version" value="0.1.0" />
              <InfoRow label="Backend" value="FastAPI + SQLAlchemy + httpx + yt-dlp + CLIP" />
              <InfoRow label="Frontend" value="React 18 + Mantine v7 + Vite" />
              <InfoRow label="Database" value="SQLite (async)" />
            </Stack>
          </Card>
        </Grid.Col>

        {/* ─── Cluster / Worker Nodes ─── */}
        <Grid.Col span={12}>
          <ClusterSection settings={settings} set={set} />
        </Grid.Col>

        {/* ─── Webhooks ─── */}
        <Grid.Col span={12}>
          <WebhookSection settings={settings} set={set} />
        </Grid.Col>

        {/* ─── Email (SMTP) ─── */}
        <Grid.Col span={12}>
          <EmailSection settings={settings} set={set} />
        </Grid.Col>

        {/* ─── Dependencies ─── */}
        <Grid.Col span={12}>
          <DependencyManager />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

type WorkerHealthRow = { url: string; healthy: boolean; latency_ms: number };

function ClusterSection({ settings, set }: { settings: Record<string, any>; set: (key: string, value: any) => void }) {
  const [checking, setChecking] = useState(false);
  const [health, setHealth] = useState<WorkerHealthRow[] | null>(null);

  const onCheck = async () => {
    try {
      setChecking(true);
      const r = await fetch("/api/cluster/workers");
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      setHealth(Array.isArray(d) ? d : []);
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setChecking(false);
    }
  };

  return (
    <Card withBorder radius="lg" p="lg">
      <Text fw={700} mb="md">Cluster / Worker Nodes</Text>
      <Text size="xs" c="dimmed" mb="md">
        Distribusikan job scraping ke beberapa mesin. Mode Master mengirim job ke pool worker via HTTP.
        Mode Worker menerima job dari master. Standalone berarti mesin ini hanya jalan sendiri.
      </Text>
      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Stack gap="sm">
            <Select
              label="Mode node"
              description="Peran instance backend ini"
              value={settings.worker_mode}
              onChange={(v) => set("worker_mode", v || "master")}
              data={[
                { value: "master", label: "Master (punya UI, kirim job)" },
                { value: "worker", label: "Worker (headless, terima job)" },
                { value: "standalone", label: "Standalone (lokal saja)" },
              ]}
            />
            <Switch
              label="Aktifkan dispatch ke worker remote"
              description="Jika nonaktif, semua job dijalankan lokal"
              checked={!!settings.worker_enabled}
              onChange={(e) => set("worker_enabled", e.currentTarget.checked)}
            />
            <Select
              label="Strategi dispatch"
              value={settings.worker_dispatch_strategy}
              onChange={(v) => set("worker_dispatch_strategy", v || "round_robin")}
              data={[
                { value: "round_robin", label: "Round-robin" },
                { value: "random", label: "Acak" },
                { value: "least_loaded", label: "Paling sedikit beban" },
              ]}
            />
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Stack gap="sm">
            <Textarea
              label="Daftar worker URL"
              description="Satu URL per baris, atau dipisah koma (mis. http://192.168.1.10:8000)"
              value={settings.worker_pool}
              onChange={(e) => set("worker_pool", e.currentTarget.value)}
              minRows={3}
              autosize
            />
            <PasswordInput
              label="Token autentikasi worker"
              description="Shared secret; kosongkan jika jaringan lokal tepercaya"
              value={settings.worker_auth_token}
              onChange={(e) => set("worker_auth_token", e.currentTarget.value)}
            />
            <Button variant="light" onClick={onCheck} loading={checking}>
              Cek worker health
            </Button>
          </Stack>
        </Grid.Col>
      </Grid>

      {health !== null && (
        <>
          <Divider my="md" label="Hasil health check" labelPosition="left" />
          {health.length === 0 ? (
            <Text size="sm" c="dimmed">Tidak ada worker terkonfigurasi.</Text>
          ) : (
            <Table striped withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>URL</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Latency (ms)</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {health.map((row) => (
                  <Table.Tr key={row.url}>
                    <Table.Td style={{ fontFamily: "monospace" }}>{row.url}</Table.Td>
                    <Table.Td>
                      {row.healthy ? (
                        <Badge color="teal" variant="light">Sehat</Badge>
                      ) : (
                        <Badge color="red" variant="light">Tidak merespon</Badge>
                      )}
                    </Table.Td>
                    <Table.Td>{row.latency_ms}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </>
      )}
    </Card>
  );
}

function WebhookSection({ settings, set }: { settings: Record<string, any>; set: (key: string, value: any) => void }) {
  const [testing, setTesting] = useState(false);

  const onTest = async () => {
    try {
      setTesting(true);
      const r = await fetch("/api/webhooks/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: "all" }),
      });
      const d = await r.json();
      const lines = Object.entries(d.sent).map(([ch, ok]) => `${ok ? "✅" : "❌"} ${ch}`).join("  ");
      notifications.show({
        title: d.any_success ? "Test sent" : "Test failed",
        message: lines || "No channels configured",
        color: d.any_success ? "teal" : "yellow",
      });
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card withBorder radius="lg" p="lg">
      <Group justify="space-between" mb="md">
        <div>
          <Text fw={700}>Webhooks & Notifications</Text>
          <Text size="xs" c="dimmed">Get notified when jobs complete via Discord, Telegram, or generic HTTP.</Text>
        </div>
        <Button size="xs" variant="light" onClick={onTest} loading={testing}>Send test</Button>
      </Group>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Stack gap="sm">
            <TextInput
              label="Discord webhook URL"
              description="Server Settings → Integrations → Webhooks → Copy URL"
              placeholder="https://discord.com/api/webhooks/..."
              value={settings.webhook_discord_url}
              onChange={(e) => set("webhook_discord_url", e.currentTarget.value)}
            />
            <TextInput
              label="Generic webhook URL"
              description="Any URL that accepts POST JSON (Slack, custom backend, etc.)"
              placeholder="https://example.com/hook"
              value={settings.webhook_generic_url}
              onChange={(e) => set("webhook_generic_url", e.currentTarget.value)}
            />
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Stack gap="sm">
            <TextInput
              label="Telegram Bot Token"
              description="Create a bot via @BotFather on Telegram"
              placeholder="123456:ABC-DEF..."
              value={settings.webhook_telegram_token}
              onChange={(e) => set("webhook_telegram_token", e.currentTarget.value)}
            />
            <TextInput
              label="Telegram Chat ID"
              description="Your user ID or group chat ID (use @userinfobot to find)"
              placeholder="123456789"
              value={settings.webhook_telegram_chat_id}
              onChange={(e) => set("webhook_telegram_chat_id", e.currentTarget.value)}
            />
          </Stack>
        </Grid.Col>
      </Grid>

      <Divider my="md" label="Triggers" labelPosition="left" />
      <Group>
        <Switch
          label="Notify on job completion"
          checked={settings.webhook_on_done}
          onChange={(e) => set("webhook_on_done", e.currentTarget.checked)}
        />
        <Switch
          label="Notify on errors"
          checked={settings.webhook_on_error}
          onChange={(e) => set("webhook_on_error", e.currentTarget.checked)}
        />
        <Switch
          label="Only when Diff detects changes"
          checked={settings.webhook_on_diff_only}
          onChange={(e) => set("webhook_on_diff_only", e.currentTarget.checked)}
        />
      </Group>
    </Card>
  );
}

function EmailSection({ settings, set }: { settings: Record<string, any>; set: (key: string, value: any) => void }) {
  const [testing, setTesting] = useState(false);

  const onTest = async () => {
    try {
      setTesting(true);
      const r = await fetch("/api/email/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const d = await r.json();
      if (d.success) {
        notifications.show({
          title: "Email terkirim",
          message: `Berhasil dikirim ke ${(d.recipients || []).join(", ")}`,
          color: "teal",
        });
      } else {
        notifications.show({
          title: "Gagal mengirim email",
          message: d.error || "Unknown error",
          color: "red",
        });
      }
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card withBorder radius="lg" p="lg">
      <Group justify="space-between" mb="md">
        <div>
          <Text fw={700}>Notifikasi Email (SMTP)</Text>
          <Text size="xs" c="dimmed">Kirim notifikasi via email saat job selesai. Alternatif untuk webhook.</Text>
        </div>
        <Group gap="sm">
          <Switch
            label="Aktif"
            checked={settings.smtp_enabled}
            onChange={(e) => set("smtp_enabled", e.currentTarget.checked)}
          />
          <Button size="xs" variant="light" onClick={onTest} loading={testing}>Kirim test</Button>
        </Group>
      </Group>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Stack gap="sm">
            <TextInput
              label="SMTP Host"
              description="Contoh: smtp.gmail.com, smtp.mailgun.org"
              placeholder="smtp.gmail.com"
              value={settings.smtp_host}
              onChange={(e) => set("smtp_host", e.currentTarget.value)}
            />
            <NumberInput
              label="SMTP Port"
              description="587 (STARTTLS), 465 (SSL), 25 (plain)"
              value={settings.smtp_port}
              onChange={(v) => set("smtp_port", v)}
              min={1}
              max={65535}
            />
            <TextInput
              label="Username"
              description="Biasanya alamat email pengirim"
              placeholder="you@example.com"
              value={settings.smtp_user}
              onChange={(e) => set("smtp_user", e.currentTarget.value)}
            />
            <PasswordInput
              label="Password"
              description="Gunakan app password untuk Gmail/Outlook"
              value={settings.smtp_password}
              onChange={(e) => set("smtp_password", e.currentTarget.value)}
            />
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Stack gap="sm">
            <TextInput
              label="Dari (From)"
              description="Alamat pengirim. Kosongkan untuk pakai username."
              placeholder="noreply@example.com"
              value={settings.smtp_from}
              onChange={(e) => set("smtp_from", e.currentTarget.value)}
            />
            <TextInput
              label="Kepada (To)"
              description="Daftar penerima, pisahkan dengan koma"
              placeholder="admin@example.com, alert@example.com"
              value={settings.smtp_to}
              onChange={(e) => set("smtp_to", e.currentTarget.value)}
            />
            <Switch
              label="Gunakan STARTTLS"
              description="Nonaktifkan hanya jika port 465 (SSL) atau 25 (plain)"
              checked={settings.smtp_use_tls}
              onChange={(e) => set("smtp_use_tls", e.currentTarget.checked)}
            />
          </Stack>
        </Grid.Col>
      </Grid>

      <Divider my="md" label="Pemicu" labelPosition="left" />
      <Group>
        <Switch
          label="Kirim saat job selesai"
          checked={settings.smtp_on_done}
          onChange={(e) => set("smtp_on_done", e.currentTarget.checked)}
        />
        <Switch
          label="Kirim saat error"
          checked={settings.smtp_on_error}
          onChange={(e) => set("smtp_on_error", e.currentTarget.checked)}
        />
      </Group>
    </Card>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <Group gap="sm">
      <Text size="sm" c="dimmed" w={80}>{label}</Text>
      <Text size="sm">{value}</Text>
    </Group>
  );
}

interface DepInfo {
  key: string;
  pip_name: string;
  description: string;
  why_update: string;
  current: string;
  latest: string | null;
  update_available: boolean;
}

function DependencyManager() {
  const [deps, setDeps] = useState<DepInfo[]>([]);
  const [checking, setChecking] = useState(false);
  const [updatingKey, setUpdatingKey] = useState<string | null>(null);
  const [updatingAll, setUpdatingAll] = useState(false);

  const refresh = () => {
    setChecking(true);
    fetch("/api/settings/deps")
      .then((r) => r.json())
      .then(setDeps)
      .catch((e) =>
        notifications.show({
          title: "Gagal memuat data",
          message: e?.message || "Terjadi kesalahan tidak dikenal",
          color: "red",
        })
      )
      .finally(() => setChecking(false));
  };

  useEffect(refresh, []);

  const onUpdate = async (key: string) => {
    try {
      setUpdatingKey(key);
      const r = await fetch(`/api/settings/deps/${key}/update`, { method: "POST" });
      const d = await r.json();
      if (d.success) {
        notifications.show({ title: `${d.package} updated`, message: `Version: ${d.version}`, color: "teal" });
      } else {
        notifications.show({ title: "Update failed", message: d.output?.slice(0, 200), color: "red" });
      }
      refresh();
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setUpdatingKey(null);
    }
  };

  const onUpdateAll = async () => {
    try {
      setUpdatingAll(true);
      const r = await fetch("/api/settings/deps/update-all", { method: "POST" });
      const results = await r.json();
      const ok = results.filter((r: any) => r.success).length;
      const fail = results.filter((r: any) => !r.success).length;
      notifications.show({
        title: "Bulk update done",
        message: `${ok} updated, ${fail} failed`,
        color: fail > 0 ? "yellow" : "teal",
      });
      refresh();
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setUpdatingAll(false);
    }
  };

  const anyUpdates = deps.some((d) => d.update_available);

  return (
    <Card withBorder radius="lg" p="lg">
      <Group justify="space-between" mb="md">
        <div>
          <Text fw={700}>Dependencies</Text>
          <Text size="xs" c="dimmed">Packages that need regular updates when target sites change.</Text>
        </div>
        <Group gap="sm">
          <Button size="xs" variant="subtle" onClick={refresh} loading={checking}>
            Check updates
          </Button>
          {anyUpdates && (
            <Button size="xs" color="yellow" onClick={onUpdateAll} loading={updatingAll}>
              Update all
            </Button>
          )}
        </Group>
      </Group>

      <Stack gap="md">
        {deps.length === 0 && checking && (
          <Text size="sm" c="dimmed">Checking versions…</Text>
        )}
        {deps.map((dep) => (
          <Card key={dep.key} withBorder radius="md" p="sm" style={dep.update_available ? { borderColor: "var(--mantine-color-yellow-6)" } : undefined}>
            <Group justify="space-between" wrap="nowrap">
              <div style={{ flex: 1 }}>
                <Group gap="sm" mb={2}>
                  <Text size="sm" fw={700}>{dep.pip_name}</Text>
                  {dep.update_available ? (
                    <Badge color="yellow" variant="light" size="xs">update available</Badge>
                  ) : dep.latest ? (
                    <Badge color="teal" variant="light" size="xs">up to date</Badge>
                  ) : null}
                </Group>
                <Text size="xs" c="dimmed">{dep.description}</Text>
                <Group gap="lg" mt={4}>
                  <Text size="xs">
                    Installed: <Text span fw={600} ff="monospace">{dep.current}</Text>
                  </Text>
                  {dep.latest && (
                    <Text size="xs">
                      Latest: <Text span fw={600} ff="monospace" c={dep.update_available ? "yellow" : "teal"}>{dep.latest}</Text>
                    </Text>
                  )}
                </Group>
                <Text size="xs" c="dimmed" mt={2} fs="italic">{dep.why_update}</Text>
              </div>
              <Button
                size="xs"
                variant="light"
                color={dep.update_available ? "yellow" : "gray"}
                loading={updatingKey === dep.key}
                onClick={() => onUpdate(dep.key)}
                style={{ minWidth: 100 }}
              >
                {dep.update_available ? "Update" : "Reinstall"}
              </Button>
            </Group>
          </Card>
        ))}
      </Stack>
    </Card>
  );
}
