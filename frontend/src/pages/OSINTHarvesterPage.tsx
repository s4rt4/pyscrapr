import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Collapse,
  Group,
  NumberInput,
  Progress,
  SegmentedControl,
  Slider,
  Stack,
  Switch,
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
  IconCopy,
  IconDownload,
  IconExternalLink,
  IconLeaf,
  IconSearch,
} from "@tabler/icons-react";
import type { OSINTFinding, OSINTReport } from "../types";

type Mode = "single" | "crawl";

const CATEGORY_LABELS: Record<string, string> = {
  emails: "Email",
  socials: "Akun Sosial",
  cloud: "Cloud",
  phones: "Telepon",
  secrets: "Secrets",
  custom: "Custom",
};

function copyToClipboard(text: string) {
  navigator.clipboard
    .writeText(text)
    .then(() =>
      notifications.show({ message: "Disalin", color: "green", autoClose: 1200 }),
    )
    .catch(() => {});
}

export default function OSINTHarvesterPage() {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<Mode>("single");
  const [depth, setDepth] = useState(1);
  const [maxPages, setMaxPages] = useState(50);
  const [stayOnDomain, setStayOnDomain] = useState(true);
  const [filters, setFilters] = useState({
    emails: true,
    socials: true,
    phones: true,
    cloud: true,
    custom: true,
    secrets: false,
  });
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [customPatterns, setCustomPatterns] = useState("");

  const [scanning, setScanning] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [pagesCrawled, setPagesCrawled] = useState(0);
  const [findingsCount, setFindingsCount] = useState(0);
  const [report, setReport] = useState<OSINTReport | null>(null);
  const [activeTab, setActiveTab] = useState<string>("all");
  const [filterText, setFilterText] = useState("");

  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      if (sseRef.current) sseRef.current.close();
    };
  }, []);

  const startScan = async () => {
    if (!url.trim()) return;
    setScanning(true);
    setReport(null);
    setPagesCrawled(0);
    setFindingsCount(0);
    setActiveTab("all");

    const customList = customPatterns
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      const r = await fetch("/api/osint/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          max_depth: mode === "single" ? 0 : depth,
          max_pages: mode === "single" ? 1 : maxPages,
          stay_on_domain: stayOnDomain,
          filters,
          custom_patterns: customList,
        }),
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }
      const data = await r.json();
      setJobId(data.job_id);
      subscribeSSE(data.job_id);
    } catch (e: any) {
      setScanning(false);
      notifications.show({
        title: "Scan gagal",
        message: e?.message || "Tidak dapat memulai scan",
        color: "red",
      });
    }
  };

  const subscribeSSE = (id: string) => {
    if (sseRef.current) sseRef.current.close();
    const es = new EventSource(`/api/osint/scan/events/${id}`);
    sseRef.current = es;
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "progress") {
          if (typeof data.pages_crawled === "number") setPagesCrawled(data.pages_crawled);
          if (typeof data.findings_count === "number") setFindingsCount(data.findings_count);
        } else if (data.type === "done") {
          es.close();
          sseRef.current = null;
          fetchReport(id);
        } else if (data.type === "error") {
          es.close();
          sseRef.current = null;
          setScanning(false);
          notifications.show({
            title: "Scan error",
            message: data.message || "Unknown error",
            color: "red",
          });
        }
      } catch {
        // ignore
      }
    };
    es.onerror = () => {
      // SSE may close when scan finishes; fall back to fetching report
      es.close();
      sseRef.current = null;
      fetchReport(id);
    };
  };

  const fetchReport = async (id: string) => {
    try {
      const r = await fetch(`/api/osint/scan/${id}`);
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      if (data.report) {
        setReport(data.report as OSINTReport);
      }
    } catch (e: any) {
      notifications.show({
        title: "Gagal mengambil laporan",
        message: e?.message || "",
        color: "red",
      });
    } finally {
      setScanning(false);
    }
  };

  const filteredFindings = useMemo(() => {
    if (!report) return [];
    let list = report.findings;
    if (activeTab !== "all") {
      list = list.filter((f) => f.category === activeTab);
    }
    if (filterText.trim()) {
      const q = filterText.trim().toLowerCase();
      list = list.filter(
        (f) =>
          f.value.toLowerCase().includes(q) ||
          (f.subcategory || "").toLowerCase().includes(q) ||
          f.source_url.toLowerCase().includes(q),
      );
    }
    return list;
  }, [report, activeTab, filterText]);

  const visibleCategories = useMemo(() => {
    if (!report) return [];
    const cats = new Set<string>();
    report.findings.forEach((f) => cats.add(f.category));
    return Array.from(cats);
  }, [report]);

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconLeaf size={26} color="var(--mantine-color-green-5)" />
          <Title order={2}>OSINT Harvester</Title>
          <Badge color="green" variant="light">P9</Badge>
        </Group>
        <Text c="dimmed" size="sm">
          Ekstrak email, akun sosial, nomor telepon, dan tautan cloud dari halaman web.
        </Text>
      </div>

      <Alert
        variant="light"
        color="yellow"
        icon={<IconAlertTriangle size={18} />}
        title="Etika penggunaan"
      >
        Tool ini untuk audit situs Anda sendiri atau yang sudah Anda dapat izin scan. Jangan pakai pada target tanpa persetujuan.
      </Alert>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <TextInput
            label="URL target"
            placeholder="https://contoh.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && !scanning && startScan()}
          />

          <SegmentedControl
            value={mode}
            onChange={(v) => setMode(v as Mode)}
            data={[
              { label: "Halaman tunggal", value: "single" },
              { label: "Crawl", value: "crawl" },
            ]}
          />

          {mode === "crawl" && (
            <Stack gap="sm">
              <Box>
                <Text size="sm" fw={500} mb={4}>Kedalaman crawl: {depth}</Text>
                <Slider
                  value={depth}
                  onChange={setDepth}
                  min={1}
                  max={3}
                  step={1}
                  marks={[
                    { value: 1, label: "1" },
                    { value: 2, label: "2" },
                    { value: 3, label: "3" },
                  ]}
                />
              </Box>
              <Group grow>
                <NumberInput
                  label="Maks halaman"
                  value={maxPages}
                  onChange={(v) => setMaxPages(typeof v === "number" ? v : 50)}
                  min={1}
                  max={500}
                />
                <Switch
                  label="Tetap di domain awal"
                  checked={stayOnDomain}
                  onChange={(e) => setStayOnDomain(e.currentTarget.checked)}
                  mt={24}
                />
              </Group>
            </Stack>
          )}

          <Box>
            <Text size="sm" fw={500} mb="xs">Kategori ekstraksi</Text>
            <Group gap="md" wrap="wrap">
              <Checkbox
                label="Email"
                checked={filters.emails}
                onChange={(e) => setFilters((f) => ({ ...f, emails: e.currentTarget.checked }))}
              />
              <Checkbox
                label="Akun sosial"
                checked={filters.socials}
                onChange={(e) => setFilters((f) => ({ ...f, socials: e.currentTarget.checked }))}
              />
              <Checkbox
                label="Telepon"
                checked={filters.phones}
                onChange={(e) => setFilters((f) => ({ ...f, phones: e.currentTarget.checked }))}
              />
              <Checkbox
                label="Cloud artifacts"
                checked={filters.cloud}
                onChange={(e) => setFilters((f) => ({ ...f, cloud: e.currentTarget.checked }))}
              />
              <Checkbox
                label="Pola kustom"
                checked={filters.custom}
                onChange={(e) => setFilters((f) => ({ ...f, custom: e.currentTarget.checked }))}
              />
            </Group>
            <Group gap="xs" mt="xs" align="flex-start">
              <Checkbox
                label="Secrets / API keys"
                checked={filters.secrets}
                onChange={(e) => setFilters((f) => ({ ...f, secrets: e.currentTarget.checked }))}
                color="red"
              />
              {filters.secrets && (
                <Text size="xs" c="red">
                  Pastikan ini situs Anda sendiri.
                </Text>
              )}
            </Group>
          </Box>

          <div>
            <Anchor size="sm" onClick={() => setAdvancedOpen((o) => !o)}>
              {advancedOpen ? "Sembunyikan" : "Tampilkan"} opsi lanjutan
            </Anchor>
            <Collapse in={advancedOpen}>
              <Textarea
                label="Pola regex kustom"
                description="Pattern Python regex, satu per baris. Pola yang tidak valid akan dilewati."
                placeholder={"\\bSKU-\\d{6}\\b\norder_id=[a-z0-9]{16}"}
                value={customPatterns}
                onChange={(e) => setCustomPatterns(e.currentTarget.value)}
                autosize
                minRows={3}
                maxRows={8}
                mt="sm"
              />
            </Collapse>
          </div>

          <Group>
            <Button
              color="green"
              leftSection={<IconSearch size={16} />}
              onClick={startScan}
              loading={scanning}
              disabled={!url.trim()}
            >
              Mulai scan
            </Button>
          </Group>
        </Stack>
      </Card>

      {scanning && (
        <Card withBorder radius="lg" p="md">
          <Stack gap="xs">
            <Group justify="space-between">
              <Text size="sm">
                Halaman dijelajah: <b>{pagesCrawled}</b> | Findings: <b>{findingsCount}</b>
              </Text>
              <Badge color="green" variant="light">Berjalan</Badge>
            </Group>
            <Progress
              value={mode === "single" ? (pagesCrawled > 0 ? 100 : 30) : Math.min(100, (pagesCrawled / Math.max(1, maxPages)) * 100)}
              animated
              color="green"
            />
          </Stack>
        </Card>
      )}

      {report && (
        <Card withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Group justify="space-between" wrap="wrap">
              <Group gap="xs" wrap="wrap">
                {Object.entries(report.stats).map(([k, v]) => (
                  <Badge
                    key={k}
                    color={k === "secrets" && v > 0 ? "red" : "green"}
                    variant="light"
                    size="lg"
                  >
                    {CATEGORY_LABELS[k] || k}: {v}
                  </Badge>
                ))}
                <Badge color="gray" variant="light" size="lg">
                  {report.pages_crawled} halaman
                </Badge>
              </Group>
              <Group gap="xs">
                <Button
                  variant="light"
                  size="xs"
                  leftSection={<IconDownload size={14} />}
                  component="a"
                  href={`/api/osint/export/${report.job_id}.csv`}
                >
                  CSV
                </Button>
                <Button
                  variant="light"
                  size="xs"
                  leftSection={<IconDownload size={14} />}
                  component="a"
                  href={`/api/osint/export/${report.job_id}.json`}
                >
                  JSON
                </Button>
              </Group>
            </Group>

            <TextInput
              placeholder="Filter findings..."
              value={filterText}
              onChange={(e) => setFilterText(e.currentTarget.value)}
              size="sm"
            />

            <Tabs value={activeTab} onChange={(v) => setActiveTab(v || "all")}>
              <Tabs.List>
                <Tabs.Tab value="all">Semua ({report.findings.length})</Tabs.Tab>
                {visibleCategories.map((cat) => (
                  <Tabs.Tab key={cat} value={cat}>
                    {CATEGORY_LABELS[cat] || cat} ({report.stats[cat as keyof typeof report.stats] || 0})
                  </Tabs.Tab>
                ))}
              </Tabs.List>
              <Tabs.Panel value={activeTab} pt="md">
                <FindingsTable findings={filteredFindings} />
              </Tabs.Panel>
            </Tabs>
          </Stack>
        </Card>
      )}
    </Stack>
  );
}

function FindingsTable({ findings }: { findings: OSINTFinding[] }) {
  if (findings.length === 0) {
    return (
      <Text c="dimmed" ta="center" py="md">
        Tidak ada findings.
      </Text>
    );
  }
  return (
    <Box style={{ overflowX: "auto" }}>
      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th style={{ width: 110 }}>Kategori</Table.Th>
            <Table.Th>Nilai</Table.Th>
            <Table.Th style={{ width: 260 }}>Sumber</Table.Th>
            <Table.Th>Konteks</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {findings.slice(0, 1000).map((f, i) => (
            <Table.Tr key={i}>
              <Table.Td>
                <Badge
                  size="sm"
                  variant="light"
                  color={f.category === "secrets" ? "red" : "green"}
                >
                  {f.subcategory || f.category}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Group gap={4} wrap="nowrap">
                  <Text ff="monospace" size="sm" style={{ wordBreak: "break-all" }}>
                    {f.value}
                  </Text>
                  <Tooltip label="Salin">
                    <ActionIcon
                      size="xs"
                      variant="subtle"
                      onClick={() => copyToClipboard(f.value)}
                    >
                      <IconCopy size={12} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Table.Td>
              <Table.Td>
                <Anchor
                  href={f.source_url}
                  target="_blank"
                  rel="noreferrer"
                  size="xs"
                  style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                >
                  <IconExternalLink size={12} />
                  <Text span size="xs" lineClamp={1} style={{ maxWidth: 220 }}>
                    {f.source_url}
                  </Text>
                </Anchor>
              </Table.Td>
              <Table.Td>
                <Text size="xs" c="dimmed" fs="italic" lineClamp={2}>
                  {f.context_snippet || ""}
                </Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      {findings.length > 1000 && (
        <Text size="xs" c="dimmed" ta="center" mt="xs">
          Menampilkan 1000 dari {findings.length} findings. Export CSV/JSON untuk lengkap.
        </Text>
      )}
    </Box>
  );
}
