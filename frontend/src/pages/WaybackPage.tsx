import { useMemo, useState } from "react";
import {
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  NumberInput,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconDeviceFloppy,
  IconExternalLink,
  IconHistory,
  IconSearch,
} from "@tabler/icons-react";
import type { WaybackSnapshot, WaybackSnapshotsResponse } from "../types";

function formatTs(ts: string): string {
  if (!ts || ts.length < 8) return ts;
  const y = ts.slice(0, 4);
  const m = ts.slice(4, 6);
  const d = ts.slice(6, 8);
  const hh = ts.slice(8, 10) || "00";
  const mm = ts.slice(10, 12) || "00";
  return `${y}-${m}-${d} ${hh}:${mm}`;
}

function formatSize(s: string | number): string {
  const n = typeof s === "number" ? s : parseInt(s || "0", 10);
  if (!n) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export default function WaybackPage() {
  const [url, setUrl] = useState("");
  const [fromYear, setFromYear] = useState<number | null>(null);
  const [toYear, setToYear] = useState<number | null>(null);
  const [limit, setLimit] = useState<number>(200);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<WaybackSnapshotsResponse | null>(null);

  const onSearch = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      const params = new URLSearchParams({ url: url.trim(), limit: String(limit) });
      if (fromYear) params.set("from", String(fromYear));
      if (toYear) params.set("to", String(toYear));
      const r = await fetch(`/api/wayback/snapshots?${params.toString()}`);
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }
      const data: WaybackSnapshotsResponse = await r.json();
      setResult(data);
    } catch (e: any) {
      notifications.show({
        title: "Pencarian gagal",
        message: e?.message || "Tidak dapat mengambil snapshot",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const onSave = async () => {
    if (!url.trim()) return;
    try {
      setSaving(true);
      const r = await fetch("/api/wayback/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      const data = await r.json();
      if (!r.ok || !data.saved) {
        throw new Error(data?.error || `HTTP ${r.status}`);
      }
      notifications.show({
        title: "Berhasil diarsipkan",
        message: `Snapshot baru: ${data.timestamp}`,
        color: "teal",
      });
    } catch (e: any) {
      notifications.show({
        title: "Arsip gagal",
        message: e?.message || "Tidak dapat mengarsipkan URL",
        color: "red",
      });
    } finally {
      setSaving(false);
    }
  };

  const byYear = useMemo(() => {
    const map = new Map<string, WaybackSnapshot[]>();
    if (!result) return map;
    for (const s of result.snapshots) {
      const y = s.timestamp.slice(0, 4) || "????";
      const arr = map.get(y) || [];
      arr.push(s);
      map.set(y, arr);
    }
    return map;
  }, [result]);

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconHistory size={26} />
          <Title order={2}>Wayback Machine Explorer</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Telusuri arsip historis halaman web dari web.archive.org
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="sm">
          <Group align="flex-end" wrap="wrap">
            <TextInput
              label="URL target"
              placeholder="https://contoh.com/halaman"
              value={url}
              onChange={(e) => setUrl(e.currentTarget.value)}
              onKeyDown={(e) => e.key === "Enter" && onSearch()}
              style={{ flex: 1, minWidth: 260 }}
            />
            <NumberInput
              label="Dari tahun"
              value={fromYear ?? ""}
              onChange={(v) => setFromYear(typeof v === "number" ? v : null)}
              min={1996}
              max={2100}
              w={120}
            />
            <NumberInput
              label="Sampai tahun"
              value={toYear ?? ""}
              onChange={(v) => setToYear(typeof v === "number" ? v : null)}
              min={1996}
              max={2100}
              w={120}
            />
            <NumberInput
              label="Limit"
              value={limit}
              onChange={(v) => setLimit(typeof v === "number" ? v : 200)}
              min={1}
              max={10000}
              w={120}
            />
            <Button
              color="cyan"
              leftSection={<IconSearch size={16} />}
              onClick={onSearch}
              loading={loading}
            >
              Cari
            </Button>
            <Button
              color="teal"
              variant="light"
              leftSection={<IconDeviceFloppy size={16} />}
              onClick={onSave}
              loading={saving}
            >
              Arsipkan sekarang
            </Button>
          </Group>
        </Stack>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="cyan" />
          <Text c="dimmed" size="sm">
            Mengambil snapshot...
          </Text>
        </Group>
      )}

      {result && !loading && (
        <Stack gap="md">
          <Card withBorder radius="lg" p="md">
            <Group>
              <Badge size="lg" color="cyan" variant="light">
                {result.count} snapshot
              </Badge>
              <Text size="sm" c="dimmed" ff="monospace" style={{ wordBreak: "break-all" }}>
                {result.url}
              </Text>
            </Group>
          </Card>

          {result.count === 0 && (
            <Card withBorder radius="lg" p="lg">
              <Text c="dimmed" ta="center">
                Tidak ada snapshot untuk URL ini.
              </Text>
            </Card>
          )}

          {Array.from(byYear.entries())
            .sort((a, b) => b[0].localeCompare(a[0]))
            .map(([year, snaps]) => (
              <Card key={year} withBorder radius="lg" p="md">
                <Group justify="space-between" mb="sm">
                  <Title order={4}>{year}</Title>
                  <Badge color="gray" variant="light">
                    {snaps.length}
                  </Badge>
                </Group>
                <Table.ScrollContainer minWidth={600}>
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Waktu</Table.Th>
                        <Table.Th>Status</Table.Th>
                        <Table.Th>Ukuran</Table.Th>
                        <Table.Th>Aksi</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {snaps.map((s, i) => (
                        <Table.Tr key={`${s.timestamp}-${i}`}>
                          <Table.Td ff="monospace">{formatTs(s.timestamp)}</Table.Td>
                          <Table.Td>
                            <Badge
                              size="xs"
                              color={s.status && s.status.startsWith("2") ? "teal" : "gray"}
                              variant="light"
                            >
                              {s.status || "—"}
                            </Badge>
                          </Table.Td>
                          <Table.Td>{formatSize(s.length)}</Table.Td>
                          <Table.Td>
                            <Anchor
                              href={s.snapshot_url}
                              target="_blank"
                              rel="noreferrer"
                              size="sm"
                            >
                              <Group gap={4} wrap="nowrap">
                                <IconExternalLink size={14} />
                                Lihat
                              </Group>
                            </Anchor>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
              </Card>
            ))}
        </Stack>
      )}
    </Stack>
  );
}
