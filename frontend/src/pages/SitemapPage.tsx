import { useMemo, useState } from "react";
import {
  Anchor,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Loader,
  Progress,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconDownload,
  IconExternalLink,
  IconSearch,
  IconSitemap,
} from "@tabler/icons-react";
import type { SitemapAnalyzeResponse } from "../types";

export default function SitemapPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SitemapAnalyzeResponse | null>(null);
  const [filter, setFilter] = useState("");

  const onAnalyze = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      const r = await fetch("/api/sitemap/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }
      const data: SitemapAnalyzeResponse = await r.json();
      setResult(data);
      if (data.error) {
        notifications.show({
          title: "Sitemap tidak ditemukan",
          message: data.error,
          color: "yellow",
        });
      }
    } catch (e: any) {
      notifications.show({
        title: "Analisis gagal",
        message: e?.message || "Tidak dapat menganalisis sitemap",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const onDownload = (format: "csv" | "json") => {
    if (!url.trim()) return;
    const params = new URLSearchParams({ url: url.trim(), format });
    window.open(`/api/sitemap/download?${params.toString()}`, "_blank");
  };

  const filteredUrls = useMemo(() => {
    if (!result) return [];
    const q = filter.trim().toLowerCase();
    return q
      ? result.sample_urls.filter((u) => u.loc.toLowerCase().includes(q))
      : result.sample_urls;
  }, [result, filter]);

  const maxLastmod = useMemo(() => {
    if (!result) return 1;
    return Math.max(1, ...Object.values(result.stats.lastmod_distribution || {}));
  }, [result]);

  const maxPriority = useMemo(() => {
    if (!result) return 1;
    return Math.max(1, ...Object.values(result.stats.priority_distribution || {}));
  }, [result]);

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconSitemap size={26} />
          <Title order={2}>Sitemap Analyzer</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Auto-detect sitemap.xml, urai struktur, dan statistik URL
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="URL situs atau sitemap"
            placeholder="https://contoh.com atau https://contoh.com/sitemap.xml"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onAnalyze()}
            style={{ flex: 1, minWidth: 260 }}
          />
          <Button
            color="cyan"
            leftSection={<IconSearch size={16} />}
            onClick={onAnalyze}
            loading={loading}
          >
            Analisis
          </Button>
        </Group>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="cyan" />
          <Text c="dimmed" size="sm">
            Menelusuri sitemap...
          </Text>
        </Group>
      )}

      {result && !loading && (
        <Stack gap="md">
          <Card withBorder radius="lg" p="md">
            <Grid>
              <Grid.Col span={{ base: 12, md: 4 }}>
                <Text size="xs" c="dimmed">
                  Total URL
                </Text>
                <Title order={3}>{result.total_urls.toLocaleString()}</Title>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 4 }}>
                <Text size="xs" c="dimmed">
                  Sumber deteksi
                </Text>
                <Badge size="lg" color="cyan" variant="light">
                  {result.source}
                </Badge>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 4 }}>
                <Text size="xs" c="dimmed">
                  Sitemap URL
                </Text>
                {result.sitemap_url ? (
                  <Anchor
                    href={result.sitemap_url}
                    target="_blank"
                    rel="noreferrer"
                    size="sm"
                    ff="monospace"
                  >
                    {result.sitemap_url}
                  </Anchor>
                ) : (
                  <Text size="sm">—</Text>
                )}
              </Grid.Col>
            </Grid>
            <Group mt="md">
              <Button
                variant="light"
                leftSection={<IconDownload size={14} />}
                onClick={() => onDownload("csv")}
                size="xs"
              >
                Export CSV
              </Button>
              <Button
                variant="light"
                leftSection={<IconDownload size={14} />}
                onClick={() => onDownload("json")}
                size="xs"
              >
                Export JSON
              </Button>
            </Group>
          </Card>

          {result.total_urls > 0 && (
            <Grid>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card withBorder radius="lg" p="md" h="100%">
                  <Title order={5} mb="sm">
                    Distribusi lastmod
                  </Title>
                  <Stack gap="xs">
                    {Object.entries(result.stats.lastmod_distribution || {}).map(
                      ([k, v]) => (
                        <div key={k}>
                          <Group justify="space-between" mb={2}>
                            <Text size="xs">{k}</Text>
                            <Text size="xs" c="dimmed">
                              {v}
                            </Text>
                          </Group>
                          <Progress value={(v / maxLastmod) * 100} color="cyan" size="sm" />
                        </div>
                      ),
                    )}
                  </Stack>
                </Card>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card withBorder radius="lg" p="md" h="100%">
                  <Title order={5} mb="sm">
                    Distribusi priority
                  </Title>
                  <Stack gap="xs">
                    {Object.entries(result.stats.priority_distribution || {}).map(
                      ([k, v]) => (
                        <div key={k}>
                          <Group justify="space-between" mb={2}>
                            <Text size="xs">{k}</Text>
                            <Text size="xs" c="dimmed">
                              {v}
                            </Text>
                          </Group>
                          <Progress value={(v / maxPriority) * 100} color="teal" size="sm" />
                        </div>
                      ),
                    )}
                  </Stack>
                </Card>
              </Grid.Col>
            </Grid>
          )}

          {result.stats?.by_path && result.stats.by_path.length > 0 && (
            <Card withBorder radius="lg" p="md">
              <Title order={5} mb="sm">
                Top path prefix
              </Title>
              <Stack gap={4}>
                {result.stats.by_path.map((p) => (
                  <Group key={p.path} justify="space-between">
                    <Text size="sm" ff="monospace">
                      {p.path}
                    </Text>
                    <Badge color="gray" variant="light">
                      {p.count}
                    </Badge>
                  </Group>
                ))}
              </Stack>
            </Card>
          )}

          {result.sample_urls.length > 0 && (
            <Card withBorder radius="lg" p="md">
              <Group justify="space-between" mb="sm">
                <Title order={5}>URL (100 pertama)</Title>
                <TextInput
                  placeholder="Filter..."
                  value={filter}
                  onChange={(e) => setFilter(e.currentTarget.value)}
                  size="xs"
                  w={200}
                />
              </Group>
              <Table.ScrollContainer minWidth={600}>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>URL</Table.Th>
                      <Table.Th>Lastmod</Table.Th>
                      <Table.Th>Priority</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {filteredUrls.map((u, i) => (
                      <Table.Tr key={`${u.loc}-${i}`}>
                        <Table.Td>
                          <Anchor
                            href={u.loc}
                            target="_blank"
                            rel="noreferrer"
                            size="sm"
                            ff="monospace"
                          >
                            <Group gap={4} wrap="nowrap">
                              <IconExternalLink size={12} />
                              {u.loc}
                            </Group>
                          </Anchor>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" c="dimmed">
                            {u.lastmod || "—"}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{u.priority || "—"}</Text>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            </Card>
          )}
        </Stack>
      )}
    </Stack>
  );
}
