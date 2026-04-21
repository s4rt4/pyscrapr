import { useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Loader,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDownload, IconLinkOff, IconSearch } from "@tabler/icons-react";
import type { LinkCheckResponse } from "../types";

export default function BrokenLinksPage() {
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState<number>(50);
  const [timeout, setTimeoutVal] = useState<number>(10);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LinkCheckResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const onScan = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      const r = await fetch("/api/linkcheck/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), max_pages: maxPages, timeout, stay_on_domain: true }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data: LinkCheckResponse = await r.json();
      setResult(data);
    } catch (e: any) {
      notifications.show({ title: "Scan gagal", message: e?.message || "Gagal", color: "red" });
    } finally {
      setLoading(false);
    }
  };

  const filtered = useMemo(() => {
    if (!result) return [];
    if (!statusFilter) return result.broken_list;
    return result.broken_list.filter((l) => String(l.status) === statusFilter);
  }, [result, statusFilter]);

  const exportCsv = () => {
    if (!result) return;
    const header = "url,status,source_page,reason\n";
    const rows = result.broken_list
      .map((r) => `"${r.url}",${r.status},"${r.source_page}","${(r.reason || "").replace(/"/g, "'")}"`)
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "broken-links.csv";
    a.click();
  };

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconLinkOff size={26} />
          <Title order={2}>Broken Link Checker</Title>
        </Group>
        <Text c="dimmed" size="sm">Cari link rusak di seluruh situs</Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="URL awal"
            placeholder="https://contoh.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onScan()}
            style={{ flex: 1, minWidth: 260 }}
          />
          <NumberInput label="Max halaman" value={maxPages} onChange={(v) => setMaxPages(typeof v === "number" ? v : 50)} min={1} max={500} w={130} />
          <NumberInput label="Timeout (detik)" value={timeout} onChange={(v) => setTimeoutVal(typeof v === "number" ? v : 10)} min={3} max={60} w={140} />
          <Button color="cyan" leftSection={<IconSearch size={16} />} onClick={onScan} loading={loading}>
            Scan
          </Button>
        </Group>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="cyan" />
          <Text c="dimmed" size="sm">Memeriksa link...</Text>
        </Group>
      )}

      {result && !loading && (
        <Stack gap="md">
          <Grid>
            <Grid.Col span={{ base: 6, md: 3 }}><Card withBorder p="sm"><Text size="xs" c="dimmed">Halaman di-crawl</Text><Text fw={700} size="xl">{result.total_pages}</Text></Card></Grid.Col>
            <Grid.Col span={{ base: 6, md: 3 }}><Card withBorder p="sm"><Text size="xs" c="dimmed">Total link</Text><Text fw={700} size="xl">{result.total_links}</Text></Card></Grid.Col>
            <Grid.Col span={{ base: 6, md: 3 }}><Card withBorder p="sm"><Text size="xs" c="dimmed">Rusak</Text><Text fw={700} size="xl" c="red">{result.broken_count}</Text></Card></Grid.Col>
            <Grid.Col span={{ base: 6, md: 3 }}><Card withBorder p="sm"><Text size="xs" c="dimmed">Redirect</Text><Text fw={700} size="xl" c="yellow">{result.redirect_count}</Text></Card></Grid.Col>
          </Grid>

          <Card withBorder radius="lg" p="md">
            <Group justify="space-between" mb="sm" wrap="wrap">
              <Title order={4}>Daftar Link Rusak</Title>
              <Group gap="xs">
                <Select
                  placeholder="Filter status"
                  data={Object.keys(result.by_status).map((s) => ({ value: s, label: `${s} (${result.by_status[s]})` }))}
                  value={statusFilter}
                  onChange={setStatusFilter}
                  clearable
                  w={200}
                />
                <Button variant="light" leftSection={<IconDownload size={16} />} onClick={exportCsv}>
                  Export CSV
                </Button>
              </Group>
            </Group>
            {filtered.length === 0 ? (
              <Text c="dimmed" ta="center" py="md">Tidak ada link rusak</Text>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>URL</Table.Th>
                    <Table.Th>Sumber</Table.Th>
                    <Table.Th>Alasan</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {filtered.map((l, i) => (
                    <Table.Tr key={i}>
                      <Table.Td><Badge color="red" variant="light">{l.status || "ERR"}</Badge></Table.Td>
                      <Table.Td style={{ fontFamily: "monospace", fontSize: 12 }}>{l.url}</Table.Td>
                      <Table.Td style={{ fontFamily: "monospace", fontSize: 12 }}>{l.source_page}</Table.Td>
                      <Table.Td>{l.reason || "-"}</Table.Td>
                    </Table.Tr>
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
