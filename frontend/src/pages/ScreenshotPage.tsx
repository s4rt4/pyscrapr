import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Accordion,
  ActionIcon,
  Anchor,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Divider,
  Grid,
  Group,
  Image,
  Loader,
  Modal,
  MultiSelect,
  NumberInput,
  Pagination,
  Progress,
  SegmentedControl,
  Select,
  Slider,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconCalendarRepeat,
  IconCamera,
  IconDownload,
  IconGitCompare,
  IconHourglass,
  IconList,
  IconPhotoScan,
  IconSparkles,
  IconTarget,
  IconTrash,
  IconVideo,
  IconZip,
} from "@tabler/icons-react";
import type {
  BatchResult,
  BatchScreenshotResponse,
  CompareResponse,
  GalleryItem,
  GalleryResponse,
  ScreenshotCapture,
  ScreenshotColorScheme,
  ScreenshotOutputFormat,
  ScreenshotRequest,
  ScreenshotResponse,
  ScreenshotViewport,
  ScreenshotWaitUntil,
  VideoResponse,
  WatermarkPosition,
} from "../types";

// ───────────────────────── constants ─────────────────────────

const WAIT_OPTIONS: { value: ScreenshotWaitUntil; label: string }[] = [
  { value: "networkidle", label: "networkidle (tunggu network tenang)" },
  { value: "load", label: "load (tunggu event load)" },
  { value: "domcontentloaded", label: "domcontentloaded (paling cepat)" },
];

const WATERMARK_POS: { value: WatermarkPosition; label: string }[] = [
  { value: "top-left", label: "Kiri atas" },
  { value: "top-right", label: "Kanan atas" },
  { value: "bottom-left", label: "Kiri bawah" },
  { value: "bottom-right", label: "Kanan bawah" },
  { value: "center", label: "Tengah" },
];

function formatBytes(n: number): string {
  if (!n && n !== 0) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

function parseHttpError(r: Response, txt: string): string {
  let msg = txt || `HTTP ${r.status}`;
  try {
    const parsed = JSON.parse(txt);
    msg = parsed.detail || msg;
  } catch {}
  return msg;
}

async function playwrightAwareFetch<T>(
  path: string,
  init: RequestInit,
): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    const txt = await r.text();
    const msg = parseHttpError(r, txt);
    if (r.status === 503 || msg.toLowerCase().includes("playwright")) {
      notifications.show({
        title: "Playwright belum terpasang",
        message:
          "Jalankan: pip install playwright (lalu python -m playwright install chromium). Restart backend setelahnya.",
        color: "orange",
        autoClose: 8000,
      });
    }
    throw new Error(msg);
  }
  return (await r.json()) as T;
}

// ───────────────────────── shared settings hook ─────────────────────────

interface CaptureSettings {
  viewports: string[];
  customWidth: number;
  customHeight: number;
  fullPage: boolean;
  colorScheme: ScreenshotColorScheme;
  deviceScale: number;
  outputFormat: ScreenshotOutputFormat;
  jpegQuality: number;
  elementSelector: string;
  multipleElements: boolean;
  hideSelectors: string;
  waitForSelector: string;
  waitUntil: ScreenshotWaitUntil;
  scrollThrough: boolean;
  timeoutMs: number;
  customCss: string;
  watermarkText: string;
  watermarkPosition: WatermarkPosition;
  watermarkOpacity: number;
  useAuthVault: boolean;
}

function defaultSettings(): CaptureSettings {
  return {
    viewports: ["desktop"],
    customWidth: 1440,
    customHeight: 900,
    fullPage: true,
    colorScheme: "light",
    deviceScale: 1,
    outputFormat: "png",
    jpegQuality: 85,
    elementSelector: "",
    multipleElements: false,
    hideSelectors: "",
    waitForSelector: "",
    waitUntil: "networkidle",
    scrollThrough: false,
    timeoutMs: 30000,
    customCss: "",
    watermarkText: "",
    watermarkPosition: "bottom-right",
    watermarkOpacity: 0.5,
    useAuthVault: false,
  };
}

function buildRequestBase(
  s: CaptureSettings,
): Omit<ScreenshotRequest, "url"> {
  const hasCustom = s.viewports.includes("custom");
  const hides = s.hideSelectors
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  return {
    viewports: s.viewports,
    custom_width: hasCustom ? s.customWidth : null,
    custom_height: hasCustom ? s.customHeight : null,
    full_page: s.fullPage,
    color_scheme: s.colorScheme,
    device_scale: s.deviceScale,
    output_format: s.outputFormat,
    jpeg_quality: s.jpegQuality,
    element_selector: s.elementSelector.trim() || null,
    multiple_elements: s.multipleElements,
    hide_selectors: hides.length ? hides : undefined,
    wait_for_selector: s.waitForSelector.trim() || null,
    wait_until: s.waitUntil,
    scroll_through: s.scrollThrough,
    timeout_ms: s.timeoutMs,
    custom_css: s.customCss.trim() || null,
    watermark_text: s.watermarkText.trim() || null,
    watermark_position: s.watermarkPosition,
    watermark_opacity: s.watermarkOpacity,
    use_auth_vault: s.useAuthVault,
  };
}

// ───────────────────────── settings form (reused) ─────────────────────────

interface SettingsFormProps {
  settings: CaptureSettings;
  setSettings: (s: CaptureSettings) => void;
  viewports: ScreenshotViewport[];
  collapsedByDefault?: boolean;
}

function SettingsForm({
  settings: s,
  setSettings,
  viewports,
  collapsedByDefault = false,
}: SettingsFormProps) {
  const update = <K extends keyof CaptureSettings>(
    key: K,
    v: CaptureSettings[K],
  ) => setSettings({ ...s, [key]: v });

  const viewportData = useMemo(
    () => viewports.map((v) => ({ value: v.key, label: v.label })),
    [viewports],
  );

  const hasCustom = s.viewports.includes("custom");

  return (
    <Stack gap="md">
      <Card withBorder radius="md" p="md">
        <Stack gap="sm">
          <Grid gutter="sm">
            <Grid.Col span={{ base: 12, md: 6 }}>
              <MultiSelect
                label="Viewport (boleh pilih lebih dari satu)"
                placeholder="Pilih viewport"
                data={viewportData}
                value={s.viewports}
                onChange={(v) =>
                  update("viewports", v.length ? v : ["desktop"])
                }
                searchable
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Stack gap={4}>
                <Text size="sm" fw={500}>
                  Skema warna
                </Text>
                <SegmentedControl
                  value={s.colorScheme}
                  onChange={(v) =>
                    update("colorScheme", v as ScreenshotColorScheme)
                  }
                  data={[
                    { value: "light", label: "Light" },
                    { value: "dark", label: "Dark" },
                    { value: "both", label: "Keduanya" },
                  ]}
                  fullWidth
                />
              </Stack>
            </Grid.Col>
          </Grid>

          {hasCustom && (
            <Grid gutter="sm">
              <Grid.Col span={{ base: 6, md: 3 }}>
                <NumberInput
                  label="Lebar kustom (px)"
                  value={s.customWidth}
                  onChange={(v) =>
                    update("customWidth", typeof v === "number" ? v : 1440)
                  }
                  min={200}
                  max={5000}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 6, md: 3 }}>
                <NumberInput
                  label="Tinggi kustom (px)"
                  value={s.customHeight}
                  onChange={(v) =>
                    update("customHeight", typeof v === "number" ? v : 900)
                  }
                  min={200}
                  max={5000}
                />
              </Grid.Col>
            </Grid>
          )}

          <Grid gutter="sm">
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Switch
                label="Full-page screenshot"
                description="Tangkap seluruh halaman, bukan cuma viewport"
                checked={s.fullPage}
                onChange={(e) => update("fullPage", e.currentTarget.checked)}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Select
                label="Device pixel ratio"
                data={[
                  { value: "1", label: "1x (standar)" },
                  { value: "2", label: "2x (Retina)" },
                  { value: "3", label: "3x (High-DPI)" },
                ]}
                value={String(s.deviceScale)}
                onChange={(v) => update("deviceScale", Number(v || 1))}
                allowDeselect={false}
              />
            </Grid.Col>
          </Grid>
        </Stack>
      </Card>

      <Accordion
        multiple
        variant="separated"
        defaultValue={collapsedByDefault ? [] : ["format"]}
      >
        <Accordion.Item value="format">
          <Accordion.Control icon={<IconPhotoScan size={18} />}>
            Format & Output
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="sm">
              <SegmentedControl
                value={s.outputFormat}
                onChange={(v) =>
                  update("outputFormat", v as ScreenshotOutputFormat)
                }
                data={[
                  { value: "png", label: "PNG" },
                  { value: "jpeg", label: "JPEG" },
                  { value: "webp", label: "WebP" },
                  { value: "pdf", label: "PDF" },
                ]}
                fullWidth
              />
              {s.outputFormat === "jpeg" && (
                <Box>
                  <Text size="sm" fw={500}>
                    Kualitas JPEG: {s.jpegQuality}
                  </Text>
                  <Slider
                    value={s.jpegQuality}
                    onChange={(v) => update("jpegQuality", v)}
                    min={10}
                    max={100}
                    step={1}
                    marks={[
                      { value: 40, label: "40" },
                      { value: 70, label: "70" },
                      { value: 90, label: "90" },
                    ]}
                  />
                </Box>
              )}
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="element">
          <Accordion.Control icon={<IconTarget size={18} />}>
            Element & Hide
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="sm">
              <TextInput
                label="CSS selector element"
                placeholder=".card atau #hero"
                value={s.elementSelector}
                onChange={(e) =>
                  update("elementSelector", e.currentTarget.value)
                }
              />
              {s.elementSelector.trim() && (
                <Switch
                  label="Tangkap semua element yang cocok"
                  description="Jika matikan, hanya element pertama yang diambil"
                  checked={s.multipleElements}
                  onChange={(e) =>
                    update("multipleElements", e.currentTarget.checked)
                  }
                />
              )}
              <Textarea
                label="Sembunyikan selector (satu per baris)"
                placeholder={".cookie-banner\n#chat-widget"}
                value={s.hideSelectors}
                onChange={(e) =>
                  update("hideSelectors", e.currentTarget.value)
                }
                minRows={3}
                autosize
              />
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="wait">
          <Accordion.Control icon={<IconHourglass size={18} />}>
            Wait & Interaction
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="sm">
              <TextInput
                label="Tunggu selector muncul (opsional)"
                placeholder="contoh: .hero-loaded"
                value={s.waitForSelector}
                onChange={(e) =>
                  update("waitForSelector", e.currentTarget.value)
                }
              />
              <Switch
                label="Auto-scroll untuk lazy-load"
                description="Gulir halaman sampai bawah agar gambar lazy-load tampil"
                checked={s.scrollThrough}
                onChange={(e) =>
                  update("scrollThrough", e.currentTarget.checked)
                }
              />
              <Grid gutter="sm">
                <Grid.Col span={{ base: 12, md: 7 }}>
                  <Select
                    label="Wait until"
                    data={WAIT_OPTIONS}
                    value={s.waitUntil}
                    onChange={(v) =>
                      update(
                        "waitUntil",
                        (v as ScreenshotWaitUntil) || "networkidle",
                      )
                    }
                    allowDeselect={false}
                  />
                </Grid.Col>
                <Grid.Col span={{ base: 12, md: 5 }}>
                  <NumberInput
                    label="Timeout (ms)"
                    value={s.timeoutMs}
                    onChange={(v) =>
                      update("timeoutMs", typeof v === "number" ? v : 30000)
                    }
                    min={5000}
                    max={120000}
                    step={1000}
                  />
                </Grid.Col>
              </Grid>
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="advanced">
          <Accordion.Control icon={<IconSparkles size={18} />}>
            Advanced
          </Accordion.Control>
          <Accordion.Panel>
            <Stack gap="sm">
              <Textarea
                label="Custom CSS (disuntikkan sebelum capture)"
                placeholder="body { background: #fff !important; }"
                value={s.customCss}
                onChange={(e) => update("customCss", e.currentTarget.value)}
                minRows={4}
                autosize
                styles={{ input: { fontFamily: "monospace", fontSize: 13 } }}
              />
              <Grid gutter="sm">
                <Grid.Col span={{ base: 12, md: 6 }}>
                  <TextInput
                    label="Watermark teks"
                    placeholder="contoh: CONFIDENTIAL"
                    value={s.watermarkText}
                    onChange={(e) =>
                      update("watermarkText", e.currentTarget.value)
                    }
                  />
                </Grid.Col>
                <Grid.Col span={{ base: 12, md: 6 }}>
                  <Select
                    label="Posisi watermark"
                    data={WATERMARK_POS}
                    value={s.watermarkPosition}
                    onChange={(v) =>
                      update(
                        "watermarkPosition",
                        (v as WatermarkPosition) || "bottom-right",
                      )
                    }
                    allowDeselect={false}
                  />
                </Grid.Col>
              </Grid>
              {s.watermarkText.trim() && (
                <Box>
                  <Text size="sm" fw={500}>
                    Opacity watermark: {s.watermarkOpacity.toFixed(2)}
                  </Text>
                  <Slider
                    value={s.watermarkOpacity}
                    onChange={(v) => update("watermarkOpacity", v)}
                    min={0}
                    max={1}
                    step={0.05}
                    marks={[
                      { value: 0.25, label: "0.25" },
                      { value: 0.5, label: "0.5" },
                      { value: 0.75, label: "0.75" },
                    ]}
                  />
                </Box>
              )}
              <Switch
                label="Pakai cookies tersimpan untuk domain ini"
                description="Ambil dari Auth Vault agar bisa screenshot halaman login"
                checked={s.useAuthVault}
                onChange={(e) =>
                  update("useAuthVault", e.currentTarget.checked)
                }
              />
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  );
}

// ───────────────────────── capture card (single result) ─────────────────────────

function CaptureGrid({ captures }: { captures: ScreenshotCapture[] }) {
  if (!captures.length) {
    return (
      <Text c="dimmed" size="sm">
        Belum ada hasil capture.
      </Text>
    );
  }
  return (
    <Grid gutter="sm">
      {captures.map((c, idx) => (
        <Grid.Col
          key={`${c.file_path}-${idx}`}
          span={{ base: 12, sm: 6, md: captures.length > 2 ? 4 : 6 }}
        >
          <Card withBorder radius="md" p="sm">
            <Stack gap="xs">
              {c.format === "pdf" ? (
                <Box
                  style={{
                    height: 180,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "var(--mantine-color-dark-8)",
                    borderRadius: 8,
                  }}
                >
                  <Text c="dimmed">PDF</Text>
                </Box>
              ) : (
                <Image
                  src={c.file_url || undefined}
                  alt={c.viewport_used}
                  fit="contain"
                  h={220}
                  radius="sm"
                />
              )}
              <Group gap={4} wrap="wrap">
                <Badge size="xs" color="cyan" variant="light">
                  {c.viewport_used}
                </Badge>
                <Badge size="xs" color="grape" variant="light">
                  {c.color_scheme_used}
                </Badge>
                <Badge size="xs" color="gray" variant="light">
                  {c.format.toUpperCase()}
                </Badge>
                <Badge size="xs" color="gray" variant="light">
                  {c.dimensions.width}x{c.dimensions.height}
                </Badge>
                <Badge size="xs" color="gray" variant="light">
                  {formatBytes(c.file_size_bytes)}
                </Badge>
              </Group>
              {c.file_url && (
                <Button
                  size="xs"
                  variant="light"
                  leftSection={<IconDownload size={14} />}
                  component="a"
                  href={c.file_url}
                  target="_blank"
                >
                  Download
                </Button>
              )}
            </Stack>
          </Card>
        </Grid.Col>
      ))}
    </Grid>
  );
}

// ───────────────────────── tab: single ─────────────────────────

function SingleTab({ viewports }: { viewports: ScreenshotViewport[] }) {
  const [url, setUrl] = useState("");
  const [settings, setSettings] = useState<CaptureSettings>(defaultSettings());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScreenshotResponse | null>(null);

  const onCapture = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      const body: ScreenshotRequest = {
        url: url.trim(),
        ...buildRequestBase(settings),
      };
      const data = await playwrightAwareFetch<ScreenshotResponse>(
        "/api/screenshot/capture",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      setResult(data);
      notifications.show({
        title: "Capture berhasil",
        message: `${data.captures.length} file dihasilkan dalam ${data.duration_ms} ms`,
        color: "teal",
      });
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

  return (
    <Stack gap="md">
      <Card withBorder radius="md" p="md">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="URL target"
            placeholder="https://contoh.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onCapture()}
            style={{ flex: 1, minWidth: 260 }}
          />
          <Button
            color="cyan"
            leftSection={<IconCamera size={16} />}
            onClick={onCapture}
            loading={loading}
            disabled={!url.trim()}
          >
            Capture
          </Button>
        </Group>
      </Card>

      <SettingsForm
        settings={settings}
        setSettings={setSettings}
        viewports={viewports}
      />

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
          <Card withBorder radius="md" p="md">
            <Group justify="space-between" wrap="wrap">
              <Group gap="xs">
                <Badge
                  size="lg"
                  color={result.status < 400 ? "teal" : "red"}
                  variant="light"
                >
                  HTTP {result.status}
                </Badge>
                <Badge size="lg" color="indigo" variant="light">
                  {result.captures.length} file
                </Badge>
                <Badge size="lg" color="gray" variant="light">
                  {result.duration_ms} ms
                </Badge>
              </Group>
              <Anchor
                href={result.final_url}
                target="_blank"
                rel="noreferrer"
                size="sm"
                ff="monospace"
              >
                {result.final_url}
              </Anchor>
            </Group>
            {result.title && (
              <Text size="sm" mt="xs">
                <Text span c="dimmed">
                  Judul:{" "}
                </Text>
                {result.title}
              </Text>
            )}
          </Card>
          <CaptureGrid captures={result.captures} />
        </Stack>
      )}
    </Stack>
  );
}

// ───────────────────────── tab: batch ─────────────────────────

function BatchTab({ viewports }: { viewports: ScreenshotViewport[] }) {
  const [urlsText, setUrlsText] = useState("");
  const [settings, setSettings] = useState<CaptureSettings>(defaultSettings());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BatchScreenshotResponse | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const urls = urlsText
    .split("\n")
    .map((u) => u.trim())
    .filter(Boolean);

  const onBatch = async () => {
    if (!urls.length) return;
    try {
      setLoading(true);
      const body = {
        urls,
        ...buildRequestBase(settings),
      };
      const data = await playwrightAwareFetch<BatchScreenshotResponse>(
        "/api/screenshot/batch",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      setResult(data);
      notifications.show({
        title: "Batch selesai",
        message: `${data.results.length} URL diproses dalam ${data.duration_ms} ms`,
        color: "teal",
      });
    } catch (e: any) {
      notifications.show({
        title: "Batch gagal",
        message: e?.message || "Tidak dapat menjalankan batch",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const okCount = result?.results.filter((r) => !r.error).length ?? 0;
  const total = result?.results.length ?? 0;

  return (
    <Stack gap="md">
      <Card withBorder radius="md" p="md">
        <Stack gap="sm">
          <Textarea
            label={`Daftar URL (${urls.length} URL terdeteksi)`}
            placeholder={"https://contoh1.com\nhttps://contoh2.com"}
            value={urlsText}
            onChange={(e) => setUrlsText(e.currentTarget.value)}
            minRows={5}
            autosize
          />
          <Group>
            <Button
              color="cyan"
              leftSection={<IconList size={16} />}
              onClick={onBatch}
              loading={loading}
              disabled={!urls.length}
            >
              Capture Batch ({urls.length})
            </Button>
          </Group>
        </Stack>
      </Card>

      <Accordion variant="separated">
        <Accordion.Item value="opts">
          <Accordion.Control icon={<IconSparkles size={18} />}>
            Pengaturan capture (sama untuk semua URL)
          </Accordion.Control>
          <Accordion.Panel>
            <SettingsForm
              settings={settings}
              setSettings={setSettings}
              viewports={viewports}
              collapsedByDefault
            />
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>

      {loading && (
        <Stack gap="xs">
          <Progress value={100} animated striped />
          <Text size="sm" c="dimmed" ta="center">
            Memproses {urls.length} URL, harap tunggu...
          </Text>
        </Stack>
      )}

      {result && !loading && (
        <Card withBorder radius="md" p="md">
          <Group justify="space-between" mb="sm">
            <Group gap="xs">
              <Badge color="teal" variant="light">
                {okCount}/{total} berhasil
              </Badge>
              <Badge color="gray" variant="light">
                {result.duration_ms} ms
              </Badge>
            </Group>
          </Group>
          <Table striped withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>URL</Table.Th>
                <Table.Th>Files</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Error</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {result.results.map((r: BatchResult, i) => {
                const key = `${i}-${r.url}`;
                const isOpen = expanded === key;
                return (
                  <>
                    <Table.Tr key={key}>
                      <Table.Td
                        style={{ maxWidth: 320, wordBreak: "break-all" }}
                      >
                        <Text size="xs" ff="monospace">
                          {r.url}
                        </Text>
                      </Table.Td>
                      <Table.Td>{r.captures.length}</Table.Td>
                      <Table.Td>
                        <Badge
                          color={r.error ? "red" : "teal"}
                          variant="light"
                          size="sm"
                        >
                          {r.error ? "gagal" : `HTTP ${r.status}`}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="red">
                          {r.error || ""}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        {!!r.captures.length && (
                          <Button
                            size="xs"
                            variant="subtle"
                            onClick={() => setExpanded(isOpen ? null : key)}
                          >
                            {isOpen ? "Tutup" : "Lihat"}
                          </Button>
                        )}
                      </Table.Td>
                    </Table.Tr>
                    {isOpen && (
                      <Table.Tr key={`${key}-exp`}>
                        <Table.Td colSpan={5}>
                          <CaptureGrid captures={r.captures} />
                        </Table.Td>
                      </Table.Tr>
                    )}
                  </>
                );
              })}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
}

// ───────────────────────── tab: gallery ─────────────────────────

interface SelectedFile {
  jobId: string;
  filename: string;
  url: string;
}

function GalleryTab() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const limit = 12;
  const [data, setData] = useState<GalleryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [detailJob, setDetailJob] = useState<GalleryItem | null>(null);
  const [selectedForCompare, setSelectedForCompare] = useState<SelectedFile[]>(
    [],
  );
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareMode, setCompareMode] =
    useState<"side_by_side" | "overlay">("side_by_side");
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(
    null,
  );
  const [comparing, setComparing] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const q = new URLSearchParams({
        limit: String(limit),
        offset: String((page - 1) * limit),
      });
      if (search.trim()) q.set("search", search.trim());
      const r = await fetch(`/api/screenshot/gallery?${q.toString()}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const json: GalleryResponse = await r.json();
      setData(json);
    } catch (e: any) {
      notifications.show({
        title: "Gagal memuat gallery",
        message: e?.message || "Tidak dapat memuat daftar",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const onSearch = () => {
    setPage(1);
    load();
  };

  const toggleJob = (id: string) => {
    setSelectedJobs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const onDeleteJob = async (jobId: string) => {
    try {
      const r = await fetch(`/api/screenshot/gallery/${jobId}`, {
        method: "DELETE",
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      notifications.show({
        title: "Dihapus",
        message: `Job ${jobId} dihapus`,
        color: "teal",
      });
      setDetailJob(null);
      load();
    } catch (e: any) {
      notifications.show({
        title: "Hapus gagal",
        message: e?.message || "Tidak dapat menghapus",
        color: "red",
      });
    }
  };

  const onBulkDelete = async () => {
    if (!selectedJobs.size) return;
    for (const id of selectedJobs) {
      await fetch(`/api/screenshot/gallery/${id}`, { method: "DELETE" }).catch(
        () => {},
      );
    }
    setSelectedJobs(new Set());
    load();
  };

  const onExportZip = async () => {
    if (!selectedJobs.size) return;
    try {
      const r = await fetch("/api/screenshot/export/zip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_ids: Array.from(selectedJobs) }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `screenshots-${Date.now()}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      notifications.show({
        title: "Export ZIP gagal",
        message: e?.message || "Tidak dapat mengunduh ZIP",
        color: "red",
      });
    }
  };

  const toggleCompareFile = (f: SelectedFile) => {
    setSelectedForCompare((prev) => {
      const exists = prev.find(
        (p) => p.jobId === f.jobId && p.filename === f.filename,
      );
      if (exists) {
        return prev.filter(
          (p) => !(p.jobId === f.jobId && p.filename === f.filename),
        );
      }
      if (prev.length >= 2) return [prev[1], f];
      return [...prev, f];
    });
  };

  const runCompare = async () => {
    if (selectedForCompare.length !== 2) return;
    try {
      setComparing(true);
      const [a, b] = selectedForCompare;
      const body = {
        job_id_a: a.jobId,
        filename_a: a.filename,
        job_id_b: b.jobId,
        filename_b: b.filename,
        mode: compareMode,
      };
      const data = await playwrightAwareFetch<CompareResponse>(
        "/api/screenshot/compare",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      setCompareResult(data);
    } catch (e: any) {
      notifications.show({
        title: "Bandingkan gagal",
        message: e?.message || "Tidak dapat membandingkan",
        color: "red",
      });
    } finally {
      setComparing(false);
    }
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / limit)) : 1;

  return (
    <Stack gap="md">
      <Group wrap="wrap">
        <TextInput
          placeholder="Cari berdasarkan URL..."
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearch()}
          style={{ flex: 1, minWidth: 240 }}
        />
        <Button variant="light" onClick={onSearch}>
          Cari
        </Button>
        {selectedForCompare.length === 2 && (
          <Button
            color="grape"
            leftSection={<IconGitCompare size={16} />}
            onClick={() => setCompareOpen(true)}
          >
            Bandingkan ({selectedForCompare.length})
          </Button>
        )}
        {selectedJobs.size > 0 && (
          <>
            <Button
              variant="light"
              color="cyan"
              leftSection={<IconZip size={16} />}
              onClick={onExportZip}
            >
              Export ZIP ({selectedJobs.size})
            </Button>
            <Button
              variant="light"
              color="red"
              leftSection={<IconTrash size={16} />}
              onClick={onBulkDelete}
            >
              Hapus ({selectedJobs.size})
            </Button>
          </>
        )}
      </Group>

      {loading && (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      )}

      {data && (
        <>
          {!data.items.length ? (
            <Text c="dimmed" ta="center" py="xl">
              Belum ada hasil screenshot tersimpan.
            </Text>
          ) : (
            <Grid gutter="sm">
              {data.items.map((item) => (
                <Grid.Col
                  key={item.job_id}
                  span={{ base: 12, sm: 6, md: 4, lg: 3 }}
                >
                  <Card withBorder radius="md" p="sm">
                    <Stack gap="xs">
                      <Box style={{ position: "relative" }}>
                        <Image
                          src={
                            item.thumbnail_url ||
                            item.files[0]?.file_url ||
                            undefined
                          }
                          h={140}
                          fit="cover"
                          radius="sm"
                          alt={item.url}
                          fallbackSrc="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciLz4="
                        />
                        <Checkbox
                          checked={selectedJobs.has(item.job_id)}
                          onChange={() => toggleJob(item.job_id)}
                          style={{ position: "absolute", top: 6, left: 6 }}
                        />
                      </Box>
                      <Text size="xs" ff="monospace" lineClamp={1}>
                        {item.url}
                      </Text>
                      <Group justify="space-between">
                        <Badge size="xs" variant="light">
                          {item.file_count} file
                        </Badge>
                        <Text size="xs" c="dimmed">
                          {new Date(item.created_at).toLocaleDateString()}
                        </Text>
                      </Group>
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() => setDetailJob(item)}
                      >
                        Lihat detail
                      </Button>
                    </Stack>
                  </Card>
                </Grid.Col>
              ))}
            </Grid>
          )}

          <Group justify="center">
            <Pagination value={page} onChange={setPage} total={totalPages} />
          </Group>
        </>
      )}

      {/* Detail modal */}
      <Modal
        opened={!!detailJob}
        onClose={() => setDetailJob(null)}
        title={detailJob?.url || "Detail"}
        size="xl"
      >
        {detailJob && (
          <Stack gap="sm">
            <Group>
              <Badge variant="light">{detailJob.file_count} file</Badge>
              <Text size="xs" c="dimmed">
                {new Date(detailJob.created_at).toLocaleString()}
              </Text>
              <Button
                size="xs"
                variant="light"
                color="red"
                leftSection={<IconTrash size={14} />}
                onClick={() => onDeleteJob(detailJob.job_id)}
                ml="auto"
              >
                Hapus job
              </Button>
            </Group>
            <Divider />
            <Grid gutter="sm">
              {detailJob.files.map((f) => {
                const sel = selectedForCompare.find(
                  (p) =>
                    p.jobId === detailJob.job_id && p.filename === f.filename,
                );
                return (
                  <Grid.Col key={f.filename} span={{ base: 12, sm: 6 }}>
                    <Card withBorder radius="md" p="xs">
                      <Stack gap={4}>
                        <Image
                          src={f.file_url}
                          h={180}
                          fit="contain"
                          radius="sm"
                          alt={f.filename}
                        />
                        <Text size="xs" ff="monospace" lineClamp={1}>
                          {f.filename}
                        </Text>
                        <Group gap={4}>
                          {f.viewport_used && (
                            <Badge size="xs" variant="light">
                              {f.viewport_used}
                            </Badge>
                          )}
                          {f.format && (
                            <Badge size="xs" variant="light" color="gray">
                              {f.format}
                            </Badge>
                          )}
                          <Badge size="xs" variant="light" color="gray">
                            {formatBytes(f.file_size_bytes)}
                          </Badge>
                        </Group>
                        <Group gap="xs">
                          <Button
                            size="xs"
                            variant="light"
                            component="a"
                            href={f.file_url}
                            target="_blank"
                            leftSection={<IconDownload size={12} />}
                          >
                            Download
                          </Button>
                          <Tooltip label="Pilih untuk dibandingkan (maks 2)">
                            <Button
                              size="xs"
                              variant={sel ? "filled" : "subtle"}
                              color="grape"
                              leftSection={<IconGitCompare size={12} />}
                              onClick={() =>
                                toggleCompareFile({
                                  jobId: detailJob.job_id,
                                  filename: f.filename,
                                  url: f.file_url,
                                })
                              }
                            >
                              {sel ? "Dipilih" : "Pilih"}
                            </Button>
                          </Tooltip>
                        </Group>
                      </Stack>
                    </Card>
                  </Grid.Col>
                );
              })}
            </Grid>
          </Stack>
        )}
      </Modal>

      {/* Compare modal */}
      <Modal
        opened={compareOpen}
        onClose={() => {
          setCompareOpen(false);
          setCompareResult(null);
        }}
        title="Bandingkan 2 screenshot"
        size="xl"
      >
        {selectedForCompare.length === 2 && (
          <Stack gap="sm">
            <Grid gutter="sm">
              {selectedForCompare.map((f, i) => (
                <Grid.Col key={i} span={6}>
                  <Card withBorder radius="md" p="xs">
                    <Text size="xs" fw={500} mb={4}>
                      {i === 0 ? "A" : "B"}: {f.filename}
                    </Text>
                    <Image src={f.url} h={200} fit="contain" />
                  </Card>
                </Grid.Col>
              ))}
            </Grid>
            <SegmentedControl
              value={compareMode}
              onChange={(v) => setCompareMode(v as typeof compareMode)}
              data={[
                { value: "side_by_side", label: "Side-by-side" },
                { value: "overlay", label: "Overlay" },
              ]}
              fullWidth
            />
            <Button
              color="grape"
              onClick={runCompare}
              loading={comparing}
              leftSection={<IconGitCompare size={16} />}
            >
              Bandingkan
            </Button>
            {compareResult && (
              <Card withBorder radius="md" p="sm">
                <Stack gap="xs">
                  <Group>
                    <Badge color="grape" variant="light" size="lg">
                      Diff ratio: {(compareResult.stats.diff_ratio * 100).toFixed(2)}%
                    </Badge>
                    <Badge variant="light" size="lg">
                      {compareResult.stats.different_pixels.toLocaleString()} /{" "}
                      {compareResult.stats.total_pixels.toLocaleString()} px
                    </Badge>
                  </Group>
                  <Image
                    src={compareResult.diff_image_url}
                    fit="contain"
                    radius="sm"
                  />
                </Stack>
              </Card>
            )}
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}

// ───────────────────────── tab: video ─────────────────────────

function VideoTab({ viewports }: { viewports: ScreenshotViewport[] }) {
  const [url, setUrl] = useState("");
  const [viewport, setViewport] = useState("desktop");
  const [duration, setDuration] = useState(4000);
  const [fps, setFps] = useState(24);
  const [format, setFormat] = useState<"mp4" | "gif" | "webm">("mp4");
  const [useAuthVault, setUseAuthVault] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VideoResponse | null>(null);

  const onRecord = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      const body = {
        url: url.trim(),
        viewport,
        scroll_duration_ms: duration,
        fps,
        output_format: format,
        use_auth_vault: useAuthVault,
      };
      const data = await playwrightAwareFetch<VideoResponse>(
        "/api/screenshot/video",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      setResult(data);
      notifications.show({
        title: "Video siap",
        message: `Durasi: ${data.duration_ms} ms`,
        color: "teal",
      });
    } catch (e: any) {
      notifications.show({
        title: "Rekam gagal",
        message: e?.message || "Tidak dapat merekam",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack gap="md">
      <Card withBorder radius="md" p="md">
        <Stack gap="sm">
          <TextInput
            label="URL target"
            placeholder="https://contoh.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
          />
          <Grid gutter="sm">
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Select
                label="Viewport"
                data={viewports.map((v) => ({ value: v.key, label: v.label }))}
                value={viewport}
                onChange={(v) => setViewport(v || "desktop")}
                allowDeselect={false}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 3 }}>
              <NumberInput
                label="Durasi scroll (ms)"
                value={duration}
                onChange={(v) => setDuration(typeof v === "number" ? v : 4000)}
                min={1000}
                max={60000}
                step={500}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 3 }}>
              <NumberInput
                label="FPS"
                value={fps}
                onChange={(v) => setFps(typeof v === "number" ? v : 24)}
                min={5}
                max={60}
              />
            </Grid.Col>
          </Grid>
          <Stack gap={4}>
            <Text size="sm" fw={500}>
              Format output
            </Text>
            <SegmentedControl
              value={format}
              onChange={(v) => setFormat(v as typeof format)}
              data={[
                { value: "mp4", label: "MP4" },
                { value: "webm", label: "WebM" },
                { value: "gif", label: "GIF" },
              ]}
            />
          </Stack>
          <Switch
            label="Pakai cookies tersimpan untuk domain ini"
            checked={useAuthVault}
            onChange={(e) => setUseAuthVault(e.currentTarget.checked)}
          />
          <Group>
            <Button
              color="cyan"
              leftSection={<IconVideo size={16} />}
              onClick={onRecord}
              loading={loading}
              disabled={!url.trim()}
            >
              Rekam Scroll
            </Button>
          </Group>
        </Stack>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader />
          <Text c="dimmed" size="sm">
            Merekam, ini bisa memakan waktu lebih lama...
          </Text>
        </Group>
      )}

      {result && !loading && (
        <Card withBorder radius="md" p="md">
          <Stack gap="sm">
            <Group>
              <Badge color="teal" variant="light">
                {result.format.toUpperCase()}
              </Badge>
              <Badge variant="light">{result.duration_ms} ms</Badge>
              <Button
                ml="auto"
                size="xs"
                variant="light"
                component="a"
                href={result.file_url}
                target="_blank"
                leftSection={<IconDownload size={14} />}
              >
                Download
              </Button>
            </Group>
            {result.format === "gif" ? (
              <Image src={result.file_url} fit="contain" radius="sm" />
            ) : (
              <video
                controls
                src={result.file_url}
                style={{
                  width: "100%",
                  borderRadius: 8,
                  background: "var(--mantine-color-dark-9)",
                }}
              />
            )}
          </Stack>
        </Card>
      )}
    </Stack>
  );
}

// ───────────────────────── tab: schedule ─────────────────────────

function ScheduleTab() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  return (
    <Stack gap="md">
      <Card withBorder radius="md" p="md">
        <Stack gap="sm">
          <Title order={4}>Jadwalkan screenshot berulang</Title>
          <Text size="sm" c="dimmed">
            Gunakan Scheduled Jobs untuk mengambil screenshot secara berkala -
            berguna untuk memonitor perubahan visual halaman (visual diff,
            uptime banner, dsb). Isi URL lalu buka halaman Scheduled Jobs untuk
            membuat jadwal baru.
          </Text>
          <TextInput
            label="URL awal (opsional)"
            placeholder="https://contoh.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
          />
          <Group>
            <Button
              color="cyan"
              leftSection={<IconCalendarRepeat size={16} />}
              onClick={() => {
                const qs = new URLSearchParams({ template: "screenshot" });
                if (url.trim()) qs.set("url", url.trim());
                navigate(`/scheduled?${qs.toString()}`);
              }}
            >
              Buka Scheduled Jobs
            </Button>
          </Group>
        </Stack>
      </Card>
      <Card withBorder radius="md" p="md">
        <Stack gap="xs">
          <Text size="sm" fw={500}>
            Kenapa perlu dijadwalkan?
          </Text>
          <Text size="xs" c="dimmed">
            - Deteksi perubahan visual di halaman kompetitor atau landing page
            sendiri.
          </Text>
          <Text size="xs" c="dimmed">
            - Arsipkan tampilan homepage setiap hari untuk keperluan audit.
          </Text>
          <Text size="xs" c="dimmed">
            - Kombinasikan dengan Compare di tab Gallery untuk diff otomatis.
          </Text>
        </Stack>
      </Card>
    </Stack>
  );
}

// ───────────────────────── root page ─────────────────────────

export default function ScreenshotPage() {
  const [viewports, setViewports] = useState<ScreenshotViewport[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>("single");

  useEffect(() => {
    fetch("/api/screenshot/viewports")
      .then((r) => r.json())
      .then((d) => setViewports(d.viewports || []))
      .catch(() => {});
  }, []);

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconCamera size={26} />
          <Title order={2}>Screenshot Studio</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Capture, batch, gallery, video, dan penjadwalan - semua dalam satu
          tempat.
        </Text>
      </div>

      <Tabs value={activeTab} onChange={setActiveTab} keepMounted>
        <Tabs.List>
          <Tabs.Tab value="single" leftSection={<IconCamera size={16} />}>
            Single
          </Tabs.Tab>
          <Tabs.Tab value="batch" leftSection={<IconList size={16} />}>
            Batch
          </Tabs.Tab>
          <Tabs.Tab value="gallery" leftSection={<IconPhotoScan size={16} />}>
            Gallery
          </Tabs.Tab>
          <Tabs.Tab value="video" leftSection={<IconVideo size={16} />}>
            Video
          </Tabs.Tab>
          <Tabs.Tab
            value="schedule"
            leftSection={<IconCalendarRepeat size={16} />}
          >
            Schedule
          </Tabs.Tab>
        </Tabs.List>

        <Box pt="md">
          <Tabs.Panel value="single">
            <SingleTab viewports={viewports} />
          </Tabs.Panel>
          <Tabs.Panel value="batch">
            <BatchTab viewports={viewports} />
          </Tabs.Panel>
          <Tabs.Panel value="gallery">
            <GalleryTab />
          </Tabs.Panel>
          <Tabs.Panel value="video">
            <VideoTab viewports={viewports} />
          </Tabs.Panel>
          <Tabs.Panel value="schedule">
            <ScheduleTab />
          </Tabs.Panel>
        </Box>
      </Tabs>
    </Stack>
  );
}
