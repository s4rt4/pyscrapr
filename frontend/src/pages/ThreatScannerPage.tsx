import { useEffect, useMemo, useState } from "react";
import {
  Accordion,
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Chip,
  CopyButton,
  FileInput,
  Grid,
  Group,
  Modal,
  Paper,
  Progress,
  RingProgress,
  ScrollArea,
  SegmentedControl,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertTriangle,
  IconBox,
  IconChartPie,
  IconCheck,
  IconCopy,
  IconDownload,
  IconFileCode,
  IconFileUpload,
  IconRefresh,
  IconShieldLock,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import type {
  FolderScanResponse,
  QuarantineEntry,
  ThreatDepth,
  ThreatScanResponse,
  ThreatSeverity,
  ThreatStats,
  ThreatVerdict,
  YaraRule,
} from "../types";

const BASE = "/api/threat";

// ───────── helpers ─────────

function formatBytes(n: number): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(2)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function truncSha(sha: string, len = 12): string {
  if (!sha) return "-";
  return sha.length <= len * 2 ? sha : `${sha.slice(0, len)}...${sha.slice(-4)}`;
}

const VERDICT_COLOR: Record<ThreatVerdict, string> = {
  clean: "teal",
  suspicious: "yellow",
  dangerous: "red",
};

const SEVERITY_COLOR: Record<ThreatSeverity, string> = {
  critical: "red",
  high: "orange",
  medium: "yellow",
  low: "cyan",
  info: "gray",
};

const SEVERITY_ORDER: ThreatSeverity[] = ["critical", "high", "medium", "low", "info"];

function notifyError(msg: string) {
  notifications.show({ color: "red", title: "Error", message: msg });
}

function notifySuccess(msg: string) {
  notifications.show({ color: "teal", title: "Sukses", message: msg });
}

async function parseErr(res: Response): Promise<string> {
  try {
    const txt = await res.text();
    try {
      const j = JSON.parse(txt);
      return j.detail || txt;
    } catch {
      return txt || `HTTP ${res.status}`;
    }
  } catch {
    return `HTTP ${res.status}`;
  }
}

// ───────── component ─────────

export default function ThreatScannerPage() {
  const [activeTab, setActiveTab] = useState<string | null>("scan");
  return (
    <Stack gap="md">
      <Group gap="sm">
        <IconShieldLock size={28} />
        <Title order={2}>Threat Scanner</Title>
        <Badge variant="light" color="cyan">
          P8
        </Badge>
      </Group>
      <Text c="dimmed" size="sm">
        Analisis statis berkas untuk mendeteksi ancaman, malware, dan konten mencurigakan.
        Gunakan secara offline sebagai alat pribadi.
      </Text>

      <Tabs value={activeTab} onChange={setActiveTab} keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="scan" leftSection={<IconShieldLock size={16} />}>
            Pindai
          </Tabs.Tab>
          <Tabs.Tab value="quarantine" leftSection={<IconBox size={16} />}>
            Karantina
          </Tabs.Tab>
          <Tabs.Tab value="rules" leftSection={<IconFileCode size={16} />}>
            Aturan YARA
          </Tabs.Tab>
          <Tabs.Tab value="stats" leftSection={<IconChartPie size={16} />}>
            Statistik
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="scan" pt="md">
          <ScanTab />
        </Tabs.Panel>
        <Tabs.Panel value="quarantine" pt="md">
          <QuarantineTab />
        </Tabs.Panel>
        <Tabs.Panel value="rules" pt="md">
          <RulesTab />
        </Tabs.Panel>
        <Tabs.Panel value="stats" pt="md">
          <StatsTab />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}

// ───────── Scan tab ─────────

function ScanTab() {
  const [mode, setMode] = useState<"upload" | "path">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [path, setPath] = useState("");
  const [depth, setDepth] = useState<ThreatDepth>("standard");
  const [scanning, setScanning] = useState(false);
  const [fileResult, setFileResult] = useState<ThreatScanResponse | null>(null);
  const [folderResult, setFolderResult] = useState<FolderScanResponse | null>(null);
  const [quarantineOpen, setQuarantineOpen] = useState(false);
  const [quarantineReason, setQuarantineReason] = useState("");
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailFile, setDetailFile] = useState<ThreatScanResponse | null>(null);
  const [folderFilter, setFolderFilter] = useState<"all" | ThreatVerdict>("all");

  async function runScan() {
    setScanning(true);
    setFileResult(null);
    setFolderResult(null);
    try {
      if (mode === "upload") {
        if (!file) {
          notifyError("Pilih berkas terlebih dahulu.");
          setScanning(false);
          return;
        }
        const fd = new FormData();
        fd.append("file", file);
        fd.append("depth", depth);
        const res = await fetch(`${BASE}/scan/upload`, { method: "POST", body: fd });
        if (!res.ok) {
          notifyError(await parseErr(res));
          return;
        }
        const data = (await res.json()) as ThreatScanResponse;
        setFileResult(data);
        notifySuccess("Pindai selesai.");
      } else {
        if (!path.trim()) {
          notifyError("Masukkan path absolut.");
          setScanning(false);
          return;
        }
        const res = await fetch(`${BASE}/scan/path`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: path.trim(), depth }),
        });
        if (!res.ok) {
          notifyError(await parseErr(res));
          return;
        }
        const data = await res.json();
        if (data && "files_total" in data) {
          setFolderResult(data as FolderScanResponse);
        } else {
          setFileResult(data as ThreatScanResponse);
        }
        notifySuccess("Pindai selesai.");
      }
    } catch (e: any) {
      notifyError(e?.message || "Gagal menjalankan pindai.");
    } finally {
      setScanning(false);
    }
  }

  async function quarantineFile(filePath: string, reason: string) {
    try {
      const res = await fetch(`${BASE}/quarantine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: filePath, reason }),
      });
      if (!res.ok) {
        notifyError(await parseErr(res));
        return;
      }
      notifySuccess("Berkas dikarantina.");
      setQuarantineOpen(false);
      setQuarantineReason("");
    } catch (e: any) {
      notifyError(e?.message || "Gagal karantina.");
    }
  }

  function exportJson(data: any, name: string) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }

  const folderFiltered = useMemo(() => {
    if (!folderResult) return [];
    if (folderFilter === "all") return folderResult.files;
    return folderResult.files.filter((f) => f.verdict === folderFilter);
  }, [folderResult, folderFilter]);

  return (
    <Stack gap="md">
      <Card withBorder padding="md">
        <Stack gap="sm">
          <Group>
            <Text fw={600}>Mode input</Text>
            <SegmentedControl
              value={mode}
              onChange={(v) => setMode(v as "upload" | "path")}
              data={[
                { value: "upload", label: "Unggah" },
                { value: "path", label: "Path Lokal" },
              ]}
            />
          </Group>

          {mode === "upload" ? (
            <FileInput
              label="Pilih berkas"
              placeholder="Klik untuk memilih berkas apa saja"
              value={file}
              onChange={setFile}
              leftSection={<IconFileUpload size={16} />}
              clearable
              description={
                file ? `${file.name} (${formatBytes(file.size)})` : "Ukuran maksimum tergantung konfigurasi backend."
              }
            />
          ) : (
            <TextInput
              label="Path absolut"
              placeholder="C:\\path\\ke\\berkas atau folder"
              value={path}
              onChange={(e) => setPath(e.currentTarget.value)}
              description="Path harus dapat dibaca oleh proses backend. Bisa berupa berkas atau folder."
            />
          )}

          <Group align="end">
            <Select
              label="Kedalaman pindai"
              value={depth}
              onChange={(v) => setDepth((v as ThreatDepth) || "standard")}
              data={[
                { value: "quick", label: "Cepat" },
                { value: "standard", label: "Standar" },
                { value: "deep", label: "Dalam" },
              ]}
              style={{ maxWidth: 220 }}
            />
            <Button
              leftSection={<IconUpload size={16} />}
              onClick={runScan}
              loading={scanning}
            >
              Pindai
            </Button>
          </Group>
        </Stack>
      </Card>

      {fileResult && (
        <FileResultView
          result={fileResult}
          onQuarantine={() => setQuarantineOpen(true)}
          onExport={() => exportJson(fileResult, `threat-report-${fileResult.job_id}.json`)}
        />
      )}

      {folderResult && (
        <Card withBorder padding="md">
          <Stack gap="sm">
            <Group justify="space-between">
              <Title order={4}>Ringkasan folder</Title>
              <Button
                size="xs"
                leftSection={<IconDownload size={14} />}
                variant="light"
                onClick={() => exportJson(folderResult, `folder-report-${folderResult.job_id}.json`)}
              >
                Ekspor JSON
              </Button>
            </Group>
            <Text size="sm" c="dimmed" style={{ wordBreak: "break-all" }}>
              {folderResult.folder_path}
            </Text>
            <Group>
              <Chip checked={folderFilter === "all"} onChange={() => setFolderFilter("all")}>
                Total: {folderResult.files_total}
              </Chip>
              <Chip
                color="teal"
                checked={folderFilter === "clean"}
                onChange={() => setFolderFilter("clean")}
              >
                Bersih: {folderResult.files_clean}
              </Chip>
              <Chip
                color="yellow"
                checked={folderFilter === "suspicious"}
                onChange={() => setFolderFilter("suspicious")}
              >
                Mencurigakan: {folderResult.files_suspicious}
              </Chip>
              <Chip
                color="red"
                checked={folderFilter === "dangerous"}
                onChange={() => setFolderFilter("dangerous")}
              >
                Berbahaya: {folderResult.files_dangerous}
              </Chip>
            </Group>

            {folderResult.top_threats.length > 0 && (
              <Stack gap={4}>
                <Text fw={600} size="sm">
                  Ancaman teratas
                </Text>
                {folderResult.top_threats.map((t) => {
                  const max = Math.max(...folderResult.top_threats.map((x) => x.count), 1);
                  return (
                    <Group key={t.category} gap="xs" wrap="nowrap">
                      <Text size="xs" style={{ minWidth: 140 }}>
                        {t.category}
                      </Text>
                      <Progress value={(t.count / max) * 100} style={{ flex: 1 }} />
                      <Text size="xs" c="dimmed" style={{ minWidth: 32 }}>
                        {t.count}
                      </Text>
                    </Group>
                  );
                })}
              </Stack>
            )}

            <ScrollArea>
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Berkas</Table.Th>
                    <Table.Th>Vonis</Table.Th>
                    <Table.Th>Skor</Table.Th>
                    <Table.Th>Temuan Utama</Table.Th>
                    <Table.Th>Aksi</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {folderFiltered.map((f) => {
                    const top = f.findings[0];
                    return (
                      <Table.Tr key={f.job_id + f.file_path}>
                        <Table.Td style={{ maxWidth: 280, wordBreak: "break-all" }}>
                          <Text size="xs">{f.file_path}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge color={VERDICT_COLOR[f.verdict]}>{f.verdict}</Badge>
                        </Table.Td>
                        <Table.Td>{f.risk_score}</Table.Td>
                        <Table.Td>
                          {top ? (
                            <Group gap={4}>
                              <Badge size="xs" color={SEVERITY_COLOR[top.severity]}>
                                {top.severity}
                              </Badge>
                              <Text size="xs">{top.title}</Text>
                            </Group>
                          ) : (
                            <Text size="xs" c="dimmed">
                              -
                            </Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Button
                            size="xs"
                            variant="light"
                            onClick={() => {
                              setDetailFile(f);
                              setDetailOpen(true);
                            }}
                          >
                            Detail
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                  {folderFiltered.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={5}>
                        <Text size="sm" c="dimmed" ta="center">
                          Tidak ada berkas untuk filter ini.
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          </Stack>
        </Card>
      )}

      <Modal
        opened={quarantineOpen}
        onClose={() => setQuarantineOpen(false)}
        title="Karantina berkas"
      >
        <Stack>
          <Text size="sm" c="dimmed">
            Berkas akan dipindahkan ke folder karantina yang terisolasi.
          </Text>
          <Textarea
            label="Alasan"
            placeholder="Contoh: terdeteksi sebagai ransomware"
            value={quarantineReason}
            onChange={(e) => setQuarantineReason(e.currentTarget.value)}
            autosize
            minRows={2}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setQuarantineOpen(false)}>
              Batal
            </Button>
            <Button
              color="red"
              disabled={!quarantineReason.trim() || !fileResult}
              onClick={() =>
                fileResult && quarantineFile(fileResult.file_path, quarantineReason.trim())
              }
            >
              Karantina
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={detailOpen}
        onClose={() => setDetailOpen(false)}
        title="Detail berkas"
        size="xl"
      >
        {detailFile && (
          <FileResultView
            result={detailFile}
            onQuarantine={() => {
              setQuarantineOpen(true);
            }}
            onExport={() => exportJson(detailFile, `threat-report-${detailFile.job_id}.json`)}
          />
        )}
      </Modal>
    </Stack>
  );
}

function FileResultView({
  result,
  onQuarantine,
  onExport,
}: {
  result: ThreatScanResponse;
  onQuarantine: () => void;
  onExport: () => void;
}) {
  const color = VERDICT_COLOR[result.verdict];
  const grouped = useMemo(() => {
    const m: Record<ThreatSeverity, typeof result.findings> = {
      critical: [],
      high: [],
      medium: [],
      low: [],
      info: [],
    };
    for (const f of result.findings) m[f.severity]?.push(f);
    return m;
  }, [result.findings]);

  return (
    <Stack gap="md">
      <Paper withBorder p="md" bg={`var(--mantine-color-${color}-light)`}>
        <Grid align="center">
          <Grid.Col span={{ base: 12, sm: 8 }}>
            <Group>
              <Badge size="xl" color={color} variant="filled">
                {result.verdict.toUpperCase()}
              </Badge>
              <Stack gap={2}>
                <Text fw={700} size="lg">
                  {result.verdict === "clean"
                    ? "Berkas bersih"
                    : result.verdict === "suspicious"
                    ? "Berkas mencurigakan"
                    : "Berkas berbahaya"}
                </Text>
                <Text size="xs" c="dimmed">
                  Durasi pindai {result.scan_duration_ms} ms
                </Text>
              </Stack>
            </Group>
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <Group justify="flex-end">
              <RingProgress
                size={110}
                thickness={10}
                sections={[{ value: result.risk_score, color }]}
                label={
                  <Text ta="center" fw={700} size="lg">
                    {result.risk_score}
                  </Text>
                }
              />
            </Group>
          </Grid.Col>
        </Grid>
      </Paper>

      {result.type_spoof && (
        <Alert color="red" icon={<IconAlertTriangle size={16} />} title="Type spoofing terdeteksi">
          Ekstensi berkas tidak cocok dengan isi sebenarnya. Terdeteksi sebagai{" "}
          <b>{result.detected_type || "tidak diketahui"}</b>, diklaim sebagai{" "}
          <b>{result.claimed_type}</b>.
        </Alert>
      )}

      <Card withBorder>
        <Stack gap="xs">
          <Group justify="space-between">
            <Text fw={600}>Metadata</Text>
            <Group gap="xs">
              <Button
                size="xs"
                variant="light"
                color="red"
                leftSection={<IconAlertTriangle size={14} />}
                onClick={onQuarantine}
              >
                Karantina
              </Button>
              <Button
                size="xs"
                variant="light"
                leftSection={<IconDownload size={14} />}
                onClick={onExport}
              >
                Ekspor JSON
              </Button>
            </Group>
          </Group>
          <Grid gutter="xs">
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Text size="xs" c="dimmed">
                Path
              </Text>
              <Text size="sm" style={{ wordBreak: "break-all" }}>
                {result.file_path}
              </Text>
            </Grid.Col>
            <Grid.Col span={{ base: 6, sm: 3 }}>
              <Text size="xs" c="dimmed">
                Ukuran
              </Text>
              <Text size="sm">{formatBytes(result.file_size)}</Text>
            </Grid.Col>
            <Grid.Col span={{ base: 6, sm: 3 }}>
              <Text size="xs" c="dimmed">
                Entropi
              </Text>
              <Text size="sm">{result.entropy.toFixed(3)}</Text>
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Text size="xs" c="dimmed">
                SHA256
              </Text>
              <Group gap={4}>
                <Tooltip label={result.sha256}>
                  <Text size="sm" ff="monospace">
                    {truncSha(result.sha256)}
                  </Text>
                </Tooltip>
                <CopyButton value={result.sha256}>
                  {({ copied, copy }) => (
                    <ActionIcon size="sm" variant="subtle" onClick={copy}>
                      {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
                    </ActionIcon>
                  )}
                </CopyButton>
              </Group>
            </Grid.Col>
            <Grid.Col span={{ base: 6, sm: 3 }}>
              <Text size="xs" c="dimmed">
                Tipe terdeteksi
              </Text>
              <Text size="sm">{result.detected_type || "-"}</Text>
            </Grid.Col>
            <Grid.Col span={{ base: 6, sm: 3 }}>
              <Text size="xs" c="dimmed">
                Tipe diklaim
              </Text>
              <Text size="sm">{result.claimed_type}</Text>
            </Grid.Col>
          </Grid>
        </Stack>
      </Card>

      <Card withBorder>
        <Stack gap="xs">
          <Text fw={600}>Temuan ({result.findings.length})</Text>
          {result.findings.length === 0 ? (
            <Text size="sm" c="dimmed">
              Tidak ada temuan.
            </Text>
          ) : (
            <Accordion multiple variant="separated">
              {SEVERITY_ORDER.filter((s) => grouped[s].length > 0).map((sev) => (
                <Accordion.Item key={sev} value={sev}>
                  <Accordion.Control>
                    <Group>
                      <Badge color={SEVERITY_COLOR[sev]}>{sev}</Badge>
                      <Text size="sm">{grouped[sev].length} temuan</Text>
                    </Group>
                  </Accordion.Control>
                  <Accordion.Panel>
                    <Stack gap="xs">
                      {grouped[sev].map((f, i) => (
                        <Card key={i} withBorder padding="xs">
                          <Group justify="space-between" align="flex-start">
                            <Stack gap={2} style={{ flex: 1 }}>
                              <Group gap="xs">
                                <Badge size="xs" variant="light">
                                  {f.category}
                                </Badge>
                                <Text fw={600} size="sm">
                                  {f.title}
                                </Text>
                              </Group>
                              <Text size="xs" c="dimmed">
                                {f.description}
                              </Text>
                            </Stack>
                            <Badge color={SEVERITY_COLOR[sev]} variant="outline">
                              +{f.score_delta}
                            </Badge>
                          </Group>
                        </Card>
                      ))}
                    </Stack>
                  </Accordion.Panel>
                </Accordion.Item>
              ))}
            </Accordion>
          )}
        </Stack>
      </Card>
    </Stack>
  );
}

// ───────── Quarantine tab ─────────

function QuarantineTab() {
  const [items, setItems] = useState<QuarantineEntry[]>([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const res = await fetch(`${BASE}/quarantine`);
      if (!res.ok) {
        notifyError(await parseErr(res));
        return;
      }
      const data = await res.json();
      setItems(Array.isArray(data) ? data : data.items || []);
    } catch (e: any) {
      notifyError(e?.message || "Gagal memuat daftar karantina.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function restore(id: string) {
    try {
      const res = await fetch(`${BASE}/quarantine/restore/${id}`, { method: "POST" });
      if (!res.ok) {
        notifyError(await parseErr(res));
        return;
      }
      notifySuccess("Berkas dipulihkan.");
      await load();
    } catch (e: any) {
      notifyError(e?.message || "Gagal memulihkan.");
    }
  }

  async function remove(id: string) {
    if (!confirm("Hapus berkas ini secara permanen?")) return;
    try {
      const res = await fetch(`${BASE}/quarantine/${id}`, { method: "DELETE" });
      if (!res.ok) {
        notifyError(await parseErr(res));
        return;
      }
      notifySuccess("Berkas dihapus permanen.");
      await load();
    } catch (e: any) {
      notifyError(e?.message || "Gagal menghapus.");
    }
  }

  return (
    <Card withBorder>
      <Stack>
        <Group justify="space-between">
          <Title order={4}>Berkas terkarantina</Title>
          <Button
            size="xs"
            variant="light"
            leftSection={<IconRefresh size={14} />}
            onClick={load}
            loading={loading}
          >
            Muat ulang
          </Button>
        </Group>
        {items.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            Tidak ada berkas di karantina.
          </Text>
        ) : (
          <ScrollArea>
            <Table striped withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Path asal</Table.Th>
                  <Table.Th>SHA256</Table.Th>
                  <Table.Th>Tanggal</Table.Th>
                  <Table.Th>Alasan</Table.Th>
                  <Table.Th>Aksi</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {items.map((q) => (
                  <Table.Tr key={q.id}>
                    <Table.Td style={{ maxWidth: 300, wordBreak: "break-all" }}>
                      <Text size="xs">{q.original_path}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Tooltip label={q.sha256}>
                        <Text size="xs" ff="monospace">
                          {truncSha(q.sha256, 8)}
                        </Text>
                      </Tooltip>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs">{new Date(q.moved_at).toLocaleString()}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs">{q.reason}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button size="xs" variant="light" onClick={() => restore(q.id)}>
                          Pulihkan
                        </Button>
                        <ActionIcon
                          color="red"
                          variant="subtle"
                          onClick={() => remove(q.id)}
                          title="Hapus permanen"
                        >
                          <IconTrash size={14} />
                        </ActionIcon>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>
        )}
      </Stack>
    </Card>
  );
}

// ───────── Rules tab ─────────

function RulesTab() {
  const [rules, setRules] = useState<YaraRule[]>([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const res = await fetch(`${BASE}/rules`);
      if (!res.ok) {
        notifyError(await parseErr(res));
        return;
      }
      const data = await res.json();
      setRules(Array.isArray(data) ? data : data.rules || []);
    } catch (e: any) {
      notifyError(e?.message || "Gagal memuat aturan.");
    } finally {
      setLoading(false);
    }
  }

  async function reload() {
    try {
      const res = await fetch(`${BASE}/rules/reload`, { method: "POST" });
      if (!res.ok) {
        notifyError(await parseErr(res));
        return;
      }
      notifySuccess("Aturan YARA dimuat ulang.");
      await load();
    } catch (e: any) {
      notifyError(e?.message || "Gagal memuat ulang.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <Stack>
      <Alert color="blue" icon={<IconFileCode size={16} />}>
        Tambahkan aturan YARA kustom Anda di folder <code>data/yara-rules/</code>, lalu klik Muat
        Ulang.
      </Alert>
      <Card withBorder>
        <Stack>
          <Group justify="space-between">
            <Title order={4}>Aturan dimuat ({rules.length})</Title>
            <Group>
              <Button
                size="xs"
                variant="light"
                leftSection={<IconRefresh size={14} />}
                onClick={load}
                loading={loading}
              >
                Segarkan
              </Button>
              <Button size="xs" onClick={reload}>
                Muat ulang aturan
              </Button>
            </Group>
          </Group>
          {rules.length === 0 ? (
            <Text c="dimmed" ta="center" py="xl">
              Tidak ada aturan termuat.
            </Text>
          ) : (
            <ScrollArea>
              <Table striped withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Nama</Table.Th>
                    <Table.Th>Namespace</Table.Th>
                    <Table.Th>Tag</Table.Th>
                    <Table.Th>Sumber</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rules.map((r, i) => (
                    <Table.Tr key={`${r.namespace}.${r.name}.${i}`}>
                      <Table.Td>
                        <Text size="sm" ff="monospace">
                          {r.name}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed">
                          {r.namespace}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap={4}>
                          {(r.tags || []).map((t) => (
                            <Badge key={t} size="xs" variant="light">
                              {t}
                            </Badge>
                          ))}
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        <Badge
                          size="xs"
                          color={r.source === "bundled" ? "cyan" : "grape"}
                          variant="light"
                        >
                          {r.source}
                        </Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          )}
        </Stack>
      </Card>
    </Stack>
  );
}

// ───────── Stats tab ─────────

function StatsTab() {
  const [stats, setStats] = useState<ThreatStats | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const res = await fetch(`${BASE}/stats`);
      if (!res.ok) {
        notifyError(await parseErr(res));
        return;
      }
      const raw = (await res.json()) as any;
      // Backend may return either the nested shape or a flat one. Normalize.
      const normalized: ThreatStats = {
        total_scans: raw.total_scans ?? 0,
        total_findings: raw.total_findings ?? 0,
        verdict_breakdown: raw.verdict_breakdown ?? {
          clean: raw.clean ?? 0,
          suspicious: raw.suspicious ?? 0,
          dangerous: raw.dangerous ?? 0,
        },
        top_categories: Array.isArray(raw.top_categories) ? raw.top_categories : [],
      };
      setStats(normalized);
    } catch (e: any) {
      notifyError(e?.message || "Gagal memuat statistik.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (!stats) {
    return (
      <Card withBorder>
        <Group justify="space-between">
          <Text c="dimmed">{loading ? "Memuat..." : "Tidak ada data."}</Text>
          <Button size="xs" variant="light" onClick={load} loading={loading}>
            Segarkan
          </Button>
        </Group>
      </Card>
    );
  }

  const vb = stats.verdict_breakdown;
  const maxCat = Math.max(...stats.top_categories.map((t) => t.count), 1);

  return (
    <Stack>
      <Group justify="flex-end">
        <Button
          size="xs"
          variant="light"
          leftSection={<IconRefresh size={14} />}
          onClick={load}
          loading={loading}
        >
          Segarkan
        </Button>
      </Group>
      <Grid>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <Card withBorder>
            <Text size="xs" c="dimmed">
              Total pindai
            </Text>
            <Title order={2}>{stats.total_scans}</Title>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <Card withBorder>
            <Text size="xs" c="dimmed">
              Total temuan
            </Text>
            <Title order={2}>{stats.total_findings}</Title>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <Card withBorder>
            <Text size="xs" c="dimmed">
              Bersih
            </Text>
            <Title order={2} c="teal">
              {vb.clean}
            </Title>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <Card withBorder>
            <Text size="xs" c="dimmed">
              Mencurigakan / Berbahaya
            </Text>
            <Group gap="xs">
              <Title order={2} c="yellow">
                {vb.suspicious}
              </Title>
              <Text c="dimmed">/</Text>
              <Title order={2} c="red">
                {vb.dangerous}
              </Title>
            </Group>
          </Card>
        </Grid.Col>
      </Grid>

      <Card withBorder>
        <Stack gap="xs">
          <Title order={5}>Kategori deteksi teratas</Title>
          {stats.top_categories.length === 0 ? (
            <Text size="sm" c="dimmed">
              Belum ada data.
            </Text>
          ) : (
            stats.top_categories.map((t) => (
              <Group key={t.category} gap="xs" wrap="nowrap">
                <Text size="sm" style={{ minWidth: 180 }}>
                  {t.category}
                </Text>
                <Progress value={(t.count / maxCat) * 100} style={{ flex: 1 }} />
                <Text size="xs" c="dimmed" style={{ minWidth: 40 }}>
                  {t.count}
                </Text>
              </Group>
            ))
          )}
        </Stack>
      </Card>
    </Stack>
  );
}
