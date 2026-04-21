import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  List,
  Loader,
  NumberInput,
  RingProgress,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconChartBar, IconSearch } from "@tabler/icons-react";
import type { SeoAuditResponse } from "../types";

function scoreColor(s: number) {
  if (s >= 75) return "teal";
  if (s >= 50) return "yellow";
  return "red";
}

function severityColor(s: string) {
  if (s === "error") return "red";
  if (s === "warning") return "yellow";
  return "blue";
}

export default function SeoAuditPage() {
  const [url, setUrl] = useState("");
  const [timeout, setTimeoutVal] = useState<number>(20);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SeoAuditResponse | null>(null);

  const onAudit = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      const r = await fetch("/api/seo/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), timeout }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data: SeoAuditResponse = await r.json();
      setResult(data);
    } catch (e: any) {
      notifications.show({ title: "Audit gagal", message: e?.message || "Gagal", color: "red" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconChartBar size={26} />
          <Title order={2}>SEO Auditor</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Audit sinyal SEO on-page dalam satu klik
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="URL target"
            placeholder="https://contoh.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onAudit()}
            style={{ flex: 1, minWidth: 260 }}
          />
          <NumberInput
            label="Timeout (detik)"
            value={timeout}
            onChange={(v) => setTimeoutVal(typeof v === "number" ? v : 20)}
            min={5}
            max={120}
            w={140}
          />
          <Button color="cyan" leftSection={<IconSearch size={16} />} onClick={onAudit} loading={loading}>
            Audit
          </Button>
        </Group>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="cyan" />
          <Text c="dimmed" size="sm">Menganalisis {url}...</Text>
        </Group>
      )}

      {result && !loading && (
        <Stack gap="md">
          <Card withBorder radius="lg" p="lg">
            <Group align="center" wrap="wrap">
              <RingProgress
                size={140}
                thickness={14}
                sections={[{ value: result.score, color: scoreColor(result.score) }]}
                label={
                  <Text ta="center" fw={700} size="xl" c={scoreColor(result.score)}>
                    {result.score}
                  </Text>
                }
              />
              <Stack gap={4} style={{ flex: 1 }}>
                <Title order={4}>Skor SEO</Title>
                <Text size="sm" c="dimmed">
                  {result.issues.length} isu ditemukan
                </Text>
                <Group gap="xs">
                  <Badge color="red" variant="light">{result.issues.filter(i => i.severity === "error").length} error</Badge>
                  <Badge color="yellow" variant="light">{result.issues.filter(i => i.severity === "warning").length} warning</Badge>
                  <Badge color="blue" variant="light">{result.issues.filter(i => i.severity === "info").length} info</Badge>
                </Group>
              </Stack>
            </Group>
          </Card>

          <Grid>
            <Grid.Col span={{ base: 6, md: 2.4 }}>
              <Card withBorder radius="md" p="sm"><Text size="xs" c="dimmed">Panjang Title</Text><Text fw={700} size="lg">{result.title_length}</Text></Card>
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2.4 }}>
              <Card withBorder radius="md" p="sm"><Text size="xs" c="dimmed">Panjang Desc</Text><Text fw={700} size="lg">{result.description_length}</Text></Card>
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2.4 }}>
              <Card withBorder radius="md" p="sm"><Text size="xs" c="dimmed">H1 Count</Text><Text fw={700} size="lg">{result.h1_count}</Text></Card>
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2.4 }}>
              <Card withBorder radius="md" p="sm"><Text size="xs" c="dimmed">Img tanpa alt</Text><Text fw={700} size="lg">{result.img_without_alt} / {result.img_total}</Text></Card>
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2.4 }}>
              <Card withBorder radius="md" p="sm"><Text size="xs" c="dimmed">Jumlah kata</Text><Text fw={700} size="lg">{result.word_count}</Text></Card>
            </Grid.Col>
          </Grid>

          {result.issues.length > 0 && (
            <Card withBorder radius="lg" p="md">
              <Title order={4} mb="sm">Daftar Isu</Title>
              <Stack gap="xs">
                {result.issues.map((i, idx) => (
                  <Alert key={idx} color={severityColor(i.severity)} title={i.code} variant="light">
                    {i.message}
                  </Alert>
                ))}
              </Stack>
            </Card>
          )}

          <Card withBorder radius="lg" p="md">
            <Title order={4} mb="sm">Meta Tag Utama</Title>
            <Table>
              <Table.Tbody>
                <Table.Tr><Table.Td><b>Title</b></Table.Td><Table.Td>{result.title || "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>Description</b></Table.Td><Table.Td>{result.description || "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>Canonical</b></Table.Td><Table.Td>{result.canonical || "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>Robots</b></Table.Td><Table.Td>{result.robots || "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>Lang</b></Table.Td><Table.Td>{result.lang || "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>Viewport</b></Table.Td><Table.Td>{result.viewport || "-"}</Table.Td></Table.Tr>
              </Table.Tbody>
            </Table>
          </Card>

          {(Object.keys(result.og).length > 0 || Object.keys(result.twitter).length > 0) && (
            <Grid>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card withBorder radius="lg" p="md">
                  <Title order={5} mb="sm">Open Graph</Title>
                  {Object.keys(result.og).length === 0 ? (
                    <Text c="dimmed" size="sm">Tidak ada OG tags</Text>
                  ) : (
                    <List size="sm">
                      {Object.entries(result.og).map(([k, v]) => (
                        <List.Item key={k}><b>{k}</b>: {v}</List.Item>
                      ))}
                    </List>
                  )}
                </Card>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card withBorder radius="lg" p="md">
                  <Title order={5} mb="sm">Twitter Card</Title>
                  {Object.keys(result.twitter).length === 0 ? (
                    <Text c="dimmed" size="sm">Tidak ada Twitter tags</Text>
                  ) : (
                    <List size="sm">
                      {Object.entries(result.twitter).map(([k, v]) => (
                        <List.Item key={k}><b>{k}</b>: {v}</List.Item>
                      ))}
                    </List>
                  )}
                </Card>
              </Grid.Col>
            </Grid>
          )}

          <Card withBorder radius="lg" p="md">
            <Title order={4} mb="sm">Outline Heading</Title>
            {result.h1.length === 0 && result.h2.length === 0 ? (
              <Text c="dimmed" size="sm">Tidak ada heading</Text>
            ) : (
              <Stack gap={4}>
                {result.h1.map((h, i) => <Text key={`h1-${i}`} size="sm"><Badge size="xs" color="cyan">H1</Badge> {h}</Text>)}
                {result.h2.map((h, i) => <Text key={`h2-${i}`} size="sm" ml="md"><Badge size="xs" color="gray">H2</Badge> {h}</Text>)}
              </Stack>
            )}
          </Card>
        </Stack>
      )}
    </Stack>
  );
}
