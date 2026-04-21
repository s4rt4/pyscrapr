import { useEffect, useMemo, useState } from "react";
import {
  Anchor,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Image,
  Loader,
  NumberInput,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCamera, IconDownload, IconRepeat } from "@tabler/icons-react";
import type {
  ScreenshotRequest,
  ScreenshotResponse,
  ScreenshotViewport,
} from "../types";

type WaitUntil = "load" | "domcontentloaded" | "networkidle";

const WAIT_OPTIONS: { value: WaitUntil; label: string }[] = [
  { value: "networkidle", label: "networkidle (tunggu network tenang)" },
  { value: "load", label: "load (tunggu event load)" },
  { value: "domcontentloaded", label: "domcontentloaded (paling cepat)" },
];

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

export default function ScreenshotPage() {
  const [url, setUrl] = useState("");
  const [viewport, setViewport] = useState<string>("desktop");
  const [customWidth, setCustomWidth] = useState<number>(1440);
  const [customHeight, setCustomHeight] = useState<number>(900);
  const [fullPage, setFullPage] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [waitUntil, setWaitUntil] = useState<WaitUntil>("networkidle");
  const [timeoutMs, setTimeoutMs] = useState<number>(30000);
  const [viewports, setViewports] = useState<ScreenshotViewport[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScreenshotResponse | null>(null);

  useEffect(() => {
    fetch("/api/screenshot/viewports")
      .then((r) => r.json())
      .then((d) => setViewports(d.viewports || []))
      .catch(() => {});
  }, []);

  const viewportOptions = useMemo(
    () =>
      viewports.map((v) => ({
        value: v.key,
        label: v.label,
      })),
    [viewports],
  );

  const isCustom = viewport === "custom";

  const buildBody = (): ScreenshotRequest => ({
    url: url.trim(),
    viewport,
    custom_width: isCustom ? customWidth : null,
    custom_height: isCustom ? customHeight : null,
    full_page: fullPage,
    dark_mode: darkMode,
    wait_until: waitUntil,
    timeout_ms: timeoutMs,
  });

  const onCapture = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      const r = await fetch("/api/screenshot/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildBody()),
      });
      if (!r.ok) {
        const txt = await r.text();
        let msg = txt || `HTTP ${r.status}`;
        try {
          const parsed = JSON.parse(txt);
          msg = parsed.detail || msg;
        } catch {}
        if (r.status === 503 || msg.toLowerCase().includes("playwright")) {
          notifications.show({
            title: "Playwright belum terpasang",
            message:
              "Jalankan: pip install playwright && playwright install chromium",
            color: "orange",
            autoClose: 8000,
          });
          return;
        }
        throw new Error(msg);
      }
      const data: ScreenshotResponse = await r.json();
      setResult(data);
    } catch (e: any) {
      notifications.show({
        title: "Capture gagal",
        message: e?.message || "Tidak dapat mengambil screenshot",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const onDownload = () => {
    if (!result) return;
    window.open(`/api/screenshot/file/${result.job_id}`, "_blank");
  };

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconCamera size={26} />
          <Title order={2}>Screenshot Generator</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Ambil screenshot situs dalam berbagai viewport via headless Chromium
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="sm">
          <Group align="flex-end" wrap="wrap">
            <TextInput
              label="URL target"
              placeholder="https://contoh.com"
              value={url}
              onChange={(e) => setUrl(e.currentTarget.value)}
              onKeyDown={(e) => e.key === "Enter" && onCapture()}
              style={{ flex: 1, minWidth: 260 }}
            />
            <Select
              label="Viewport"
              data={viewportOptions}
              value={viewport}
              onChange={(v) => setViewport(v || "desktop")}
              w={280}
              allowDeselect={false}
            />
            <Button
              color="cyan"
              leftSection={<IconCamera size={16} />}
              onClick={onCapture}
              loading={loading}
            >
              Capture
            </Button>
          </Group>

          {isCustom && (
            <Group>
              <NumberInput
                label="Lebar (px)"
                value={customWidth}
                onChange={(v) =>
                  setCustomWidth(typeof v === "number" ? v : 1440)
                }
                min={200}
                max={5000}
                w={160}
              />
              <NumberInput
                label="Tinggi (px)"
                value={customHeight}
                onChange={(v) =>
                  setCustomHeight(typeof v === "number" ? v : 900)
                }
                min={200}
                max={5000}
                w={160}
              />
            </Group>
          )}

          <Group>
            <Switch
              label="Full-page screenshot"
              description="Gulir otomatis dan tangkap seluruh halaman"
              checked={fullPage}
              onChange={(e) => setFullPage(e.currentTarget.checked)}
            />
            <Switch
              label="Dark mode"
              description="Emulasi prefers-color-scheme: dark"
              checked={darkMode}
              onChange={(e) => setDarkMode(e.currentTarget.checked)}
            />
          </Group>

          <Group>
            <Select
              label="Wait until"
              data={WAIT_OPTIONS}
              value={waitUntil}
              onChange={(v) => setWaitUntil((v as WaitUntil) || "networkidle")}
              w={320}
              allowDeselect={false}
            />
            <NumberInput
              label="Timeout (ms)"
              value={timeoutMs}
              onChange={(v) => setTimeoutMs(typeof v === "number" ? v : 30000)}
              min={5000}
              max={120000}
              step={1000}
              w={160}
            />
          </Group>
        </Stack>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="cyan" />
          <Text c="dimmed" size="sm">
            Mengambil screenshot {url}...
          </Text>
        </Group>
      )}

      {result && !loading && (
        <Stack gap="md">
          <Card withBorder radius="lg" p="md">
            <Group justify="space-between" wrap="wrap">
              <Group gap="sm">
                <Badge
                  size="lg"
                  color={result.status < 400 ? "teal" : "red"}
                  variant="light"
                >
                  HTTP {result.status}
                </Badge>
                <Badge color="cyan" variant="light" size="lg">
                  {result.viewport_used}
                </Badge>
                {result.dark_mode && (
                  <Badge color="dark" variant="filled" size="lg">
                    dark mode
                  </Badge>
                )}
                <Badge color="gray" variant="light" size="lg">
                  {formatBytes(result.file_size_bytes)}
                </Badge>
                <Badge color="gray" variant="light" size="lg">
                  {result.dimensions.width}x{result.dimensions.height}
                </Badge>
              </Group>
              <Group gap="xs">
                <Button
                  leftSection={<IconDownload size={16} />}
                  onClick={onDownload}
                  variant="light"
                >
                  Download
                </Button>
                <Button
                  leftSection={<IconRepeat size={16} />}
                  onClick={onCapture}
                  variant="subtle"
                >
                  Capture lagi
                </Button>
              </Group>
            </Group>
          </Card>

          <Card withBorder radius="lg" p="md">
            <Grid gutter="xs">
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Text size="xs" c="dimmed">
                  Judul halaman
                </Text>
                <Text size="sm" fw={500}>
                  {result.title || "(tanpa judul)"}
                </Text>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Text size="xs" c="dimmed">
                  Final URL
                </Text>
                <Anchor
                  href={result.final_url}
                  target="_blank"
                  rel="noreferrer"
                  size="sm"
                  ff="monospace"
                >
                  {result.final_url}
                </Anchor>
              </Grid.Col>
            </Grid>
          </Card>

          <Card withBorder radius="lg" p="sm">
            <Image
              src={`/api/screenshot/file/${result.job_id}`}
              alt={`Screenshot ${result.final_url}`}
              fit="contain"
              radius="md"
              style={{ border: "1px solid var(--mantine-color-default-border)" }}
            />
          </Card>
        </Stack>
      )}
    </Stack>
  );
}
