import { useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Code,
  Collapse,
  Group,
  Loader,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertTriangle,
  IconChevronDown,
  IconChevronUp,
  IconDoorEnter,
  IconDownload,
  IconSearch,
} from "@tabler/icons-react";
import type {
  ExposureFinding,
  ExposureScanResponse,
  ExposureSeverity,
} from "../types";

const SEVERITY_COLOR: Record<ExposureSeverity, string> = {
  critical: "red",
  high: "orange",
  medium: "yellow",
  low: "blue",
  info: "gray",
};

const SEVERITY_ORDER: ExposureSeverity[] = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
];

function FindingRow({ f }: { f: ExposureFinding }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Table.Tr>
        <Table.Td style={{ fontFamily: "monospace", fontSize: 12 }}>{f.path}</Table.Td>
        <Table.Td>
          <Badge variant="light" color="gray">
            {f.category}
          </Badge>
        </Table.Td>
        <Table.Td>
          <Badge color={SEVERITY_COLOR[f.severity]} variant="filled">
            {f.severity}
          </Badge>
        </Table.Td>
        <Table.Td>{f.status}</Table.Td>
        <Table.Td>
          {f.plausible ? (
            <Badge color="red" variant="light">
              valid
            </Badge>
          ) : (
            <Badge color="gray" variant="light">
              ragu
            </Badge>
          )}
        </Table.Td>
        <Table.Td>
          <Button
            size="compact-xs"
            variant="subtle"
            onClick={() => setOpen((o) => !o)}
            rightSection={
              open ? <IconChevronUp size={12} /> : <IconChevronDown size={12} />
            }
          >
            Preview
          </Button>
        </Table.Td>
      </Table.Tr>
      {open && (
        <Table.Tr>
          <Table.Td colSpan={6}>
            <Collapse in={open}>
              <Code block style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>
                {f.content_preview || "(kosong)"}
              </Code>
            </Collapse>
          </Table.Td>
        </Table.Tr>
      )}
    </>
  );
}

export default function ExposureScannerPage() {
  const [url, setUrl] = useState("");
  const [throttle, setThrottle] = useState<number | string>(1);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExposureScanResponse | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string | null>(null);

  const onScan = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      const r = await fetch("/api/exposure/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          throttle_seconds: Number(throttle) || 0,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data: ExposureScanResponse = await r.json();
      setResult(data);
      if (data.error) {
        notifications.show({
          title: "Scan selesai dengan peringatan",
          message: data.error,
          color: "yellow",
        });
      }
    } catch (e: any) {
      notifications.show({
        title: "Scan gagal",
        message: e?.message || "Gagal",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const filteredFindings = useMemo(() => {
    if (!result) return [] as ExposureFinding[];
    let list = [...result.findings];
    list.sort(
      (a, b) =>
        SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
    );
    if (filterSeverity) list = list.filter((f) => f.severity === filterSeverity);
    return list;
  }, [result, filterSeverity]);

  const counts = useMemo(() => {
    const c = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    if (!result) return c;
    for (const f of result.findings) {
      c[f.severity] += 1;
    }
    return c;
  }, [result]);

  const criticalFindings = useMemo(
    () =>
      result?.findings.filter((f) => f.severity === "critical" && f.plausible) ||
      [],
    [result],
  );

  const exportJSON = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `exposure-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconDoorEnter size={26} color="var(--mantine-color-lime-5)" />
          <Title order={2}>Exposure Scanner</Title>
          <Badge color="lime" variant="light">
            Audit
          </Badge>
        </Group>
        <Text c="dimmed" size="sm">
          Cek path tersembunyi yang sering ter-expose karena salah konfigurasi
        </Text>
      </div>

      <Alert
        color="yellow"
        title="Peringatan"
        icon={<IconAlertTriangle size={16} />}
      >
        Tool ini cuma cek path yang sering ter-expose karena salah konfigurasi.
        Hanya untuk audit situs Anda sendiri.
      </Alert>

      <Card withBorder radius="lg" p="lg">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="URL target"
            placeholder="https://contoh.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onScan()}
            style={{ flex: 1, minWidth: 260 }}
          />
          <NumberInput
            label="Jeda antar request (detik)"
            value={throttle}
            onChange={setThrottle}
            min={0}
            max={10}
            step={0.5}
            decimalScale={2}
            w={180}
          />
          <Button
            color="lime"
            leftSection={<IconSearch size={16} />}
            onClick={onScan}
            loading={loading}
          >
            Scan
          </Button>
        </Group>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="lime" />
          <Text c="dimmed" size="sm">
            Memeriksa path tersembunyi...
          </Text>
        </Group>
      )}

      {result && !loading && (
        <Stack gap="md">
          {result.error && (
            <Alert color="red" title="Catatan">
              {result.error}
            </Alert>
          )}

          <SimpleGrid cols={{ base: 2, md: 5 }}>
            <Card withBorder radius="md" p="sm">
              <Text size="xs" c="dimmed">
                Total dicek
              </Text>
              <Title order={3}>{result.total_checked}</Title>
            </Card>
            <Card withBorder radius="md" p="sm">
              <Text size="xs" c="dimmed">
                Total ditemukan
              </Text>
              <Title order={3}>{result.total_found}</Title>
            </Card>
            <Card withBorder radius="md" p="sm">
              <Text size="xs" c="dimmed">
                Critical
              </Text>
              <Title order={3} c="red">
                {counts.critical}
              </Title>
            </Card>
            <Card withBorder radius="md" p="sm">
              <Text size="xs" c="dimmed">
                High
              </Text>
              <Title order={3} c="orange">
                {counts.high}
              </Title>
            </Card>
            <Card withBorder radius="md" p="sm">
              <Text size="xs" c="dimmed">
                Lain-lain
              </Text>
              <Title order={3}>
                {counts.medium + counts.low + counts.info}
              </Title>
            </Card>
          </SimpleGrid>

          {criticalFindings.length > 0 && (
            <Card
              withBorder
              radius="lg"
              p="md"
              style={{ borderColor: "var(--mantine-color-red-6)", borderWidth: 2 }}
            >
              <Group gap="xs" mb="sm">
                <IconAlertTriangle size={20} color="var(--mantine-color-red-6)" />
                <Title order={4} c="red">
                  Temuan kritis
                </Title>
              </Group>
              <Stack gap="xs">
                {criticalFindings.map((f) => (
                  <Alert key={f.path} color="red" variant="light" title={f.path}>
                    Kategori {f.category} - status {f.status}. Segera tutup
                    akses publik ke path ini.
                  </Alert>
                ))}
              </Stack>
            </Card>
          )}

          <Card withBorder radius="lg" p="md">
            <Group justify="space-between" mb="sm">
              <Title order={4}>Daftar temuan</Title>
              <Group gap="xs">
                <Select
                  placeholder="Semua severity"
                  data={SEVERITY_ORDER.map((s) => ({ value: s, label: s }))}
                  value={filterSeverity}
                  onChange={setFilterSeverity}
                  clearable
                  w={180}
                />
                <Button
                  variant="light"
                  color="gray"
                  leftSection={<IconDownload size={14} />}
                  onClick={exportJSON}
                >
                  Export JSON
                </Button>
              </Group>
            </Group>

            {filteredFindings.length === 0 ? (
              <Text c="dimmed" size="sm">
                Tidak ada temuan yang cocok.
              </Text>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Path</Table.Th>
                    <Table.Th>Kategori</Table.Th>
                    <Table.Th>Severity</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Plausibel</Table.Th>
                    <Table.Th>Aksi</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {filteredFindings.map((f) => (
                    <FindingRow key={f.path} f={f} />
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Stack>
      )}
    </Stack>
  );
}
