import { useEffect, useMemo, useState } from "react";
import {
  Accordion,
  Badge,
  Button,
  Card,
  Code,
  Group,
  Loader,
  ScrollArea,
  SimpleGrid,
  Slider,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconApi,
  IconDownload,
  IconFilter,
  IconNetwork,
  IconPlayerPlay,
} from "@tabler/icons-react";
import type {
  ApiSnifferEndpoint,
  ApiSnifferGraphQLOp,
  ApiSnifferReport,
  ApiSnifferStatus,
  CapturedRequest,
} from "../types";

const METHOD_COLORS: Record<string, string> = {
  GET: "blue",
  POST: "green",
  PUT: "orange",
  PATCH: "yellow",
  DELETE: "red",
  HEAD: "gray",
  OPTIONS: "gray",
};

function methodColor(m: string): string {
  return METHOD_COLORS[m.toUpperCase()] || "gray";
}

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

function statusColor(s: number | null | undefined): string {
  if (!s) return "gray";
  if (s < 300) return "teal";
  if (s < 400) return "blue";
  if (s < 500) return "orange";
  return "red";
}

export default function ApiSnifferPage() {
  const [url, setUrl] = useState("");
  const [waitSeconds, setWaitSeconds] = useState(15);
  const [filterStatic, setFilterStatic] = useState(true);
  const [useStealth, setUseStealth] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<ApiSnifferStatus | null>(null);
  const [report, setReport] = useState<ApiSnifferReport | null>(null);
  const [filterText, setFilterText] = useState("");
  const [pollErr, setPollErr] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    if (status === "done" || status === "error") return;
    const t = setInterval(async () => {
      try {
        const r = await fetch(`/api/sniffer/scan/${jobId}`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        setStatus(data.status as ApiSnifferStatus);
        if (data.status === "done" && data.report) {
          setReport(data.report as ApiSnifferReport);
          setScanning(false);
        } else if (data.status === "error") {
          setPollErr(data.error_message || "Scan gagal");
          setScanning(false);
        }
      } catch (e: any) {
        setPollErr(e?.message || "Polling gagal");
      }
    }, 1500);
    return () => clearInterval(t);
  }, [jobId, status]);

  const onScan = async () => {
    if (!url.trim()) return;
    try {
      setScanning(true);
      setReport(null);
      setStatus(null);
      setPollErr(null);
      const r = await fetch("/api/sniffer/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          wait_seconds: waitSeconds,
          filter_static: filterStatic,
          use_stealth: useStealth,
        }),
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }
      const data = await r.json();
      setJobId(data.job_id);
      setStatus(data.status as ApiSnifferStatus);
    } catch (e: any) {
      notifications.show({
        title: "Scan gagal",
        message: e?.message || "Tidak dapat memulai sniffing",
        color: "red",
      });
      setScanning(false);
    }
  };

  const filteredEndpoints = useMemo(() => {
    if (!report) return [];
    const q = filterText.trim().toLowerCase();
    if (!q) return report.endpoints;
    return report.endpoints.filter(
      (e) =>
        e.host.toLowerCase().includes(q) ||
        e.path.toLowerCase().includes(q) ||
        e.method.toLowerCase().includes(q),
    );
  }, [report, filterText]);

  const endpointsByHost = useMemo(() => {
    const map = new Map<string, ApiSnifferEndpoint[]>();
    for (const ep of filteredEndpoints) {
      if (!map.has(ep.host)) map.set(ep.host, []);
      map.get(ep.host)!.push(ep);
    }
    return Array.from(map.entries());
  }, [filteredEndpoints]);

  const exportOpenApi = () => {
    if (!jobId) return;
    window.open(`/api/sniffer/scan/${jobId}/openapi.json`, "_blank");
  };
  const exportPostman = () => {
    if (!jobId) return;
    window.open(`/api/sniffer/scan/${jobId}/postman.json`, "_blank");
  };

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconNetwork size={26} />
          <Title order={2}>API Sniffer</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Bongkar endpoint REST/GraphQL dari aplikasi SPA dengan menyadap lalu lintas jaringan
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="sm">
          <Group align="flex-end" wrap="wrap">
            <TextInput
              label="URL target"
              placeholder="https://app.contoh.com"
              value={url}
              onChange={(e) => setUrl(e.currentTarget.value)}
              onKeyDown={(e) => e.key === "Enter" && onScan()}
              style={{ flex: 1, minWidth: 280 }}
            />
            <Button
              color="indigo"
              leftSection={<IconPlayerPlay size={16} />}
              onClick={onScan}
              loading={scanning}
            >
              Mulai Sniff
            </Button>
          </Group>
          <div>
            <Text size="sm" mb={4}>
              Durasi pengintaian: <b>{waitSeconds}</b> detik
            </Text>
            <Slider
              value={waitSeconds}
              onChange={setWaitSeconds}
              min={5}
              max={60}
              step={1}
              marks={[
                { value: 5, label: "5d" },
                { value: 15, label: "15d" },
                { value: 30, label: "30d" },
                { value: 60, label: "60d" },
              ]}
              mb={24}
            />
          </div>
          <Group mt="sm">
            <Switch
              label="Saring aset statis (.js, .css, gambar, font)"
              checked={filterStatic}
              onChange={(e) => setFilterStatic(e.currentTarget.checked)}
            />
            <Switch
              label="Mode stealth"
              checked={useStealth}
              onChange={(e) => setUseStealth(e.currentTarget.checked)}
            />
          </Group>
        </Stack>
      </Card>

      {scanning && (
        <Group justify="center" py="xl">
          <Loader color="indigo" />
          <Text c="dimmed" size="sm">
            Menyadap lalu lintas ({status || "memulai"})...
          </Text>
        </Group>
      )}

      {pollErr && !scanning && (
        <Card withBorder radius="lg" p="md">
          <Text c="red">Error: {pollErr}</Text>
        </Card>
      )}

      {report && !scanning && (
        <Stack gap="md">
          <Card withBorder radius="lg" p="md">
            <Group gap="sm" wrap="wrap">
              <Badge size="lg" color="indigo" variant="light">
                {report.stats.total_requests} permintaan
              </Badge>
              <Badge size="lg" color="grape" variant="light">
                {report.stats.unique_endpoints} endpoint unik
              </Badge>
              {report.stats.graphql_ops > 0 && (
                <Badge size="lg" color="pink" variant="light">
                  {report.stats.graphql_ops} operasi GraphQL
                </Badge>
              )}
              <Badge size="lg" color="gray" variant="light">
                total {fmtBytes(report.stats.total_response_bytes)}
              </Badge>
              <Badge size="lg" color="gray" variant="light">
                durasi {report.duration_seconds.toFixed(1)}s
              </Badge>
              <div style={{ marginLeft: "auto" }}>
                <Group gap="xs">
                  <Tooltip label="Unduh spesifikasi OpenAPI 3.0">
                    <Button
                      size="xs"
                      variant="light"
                      color="indigo"
                      leftSection={<IconDownload size={14} />}
                      onClick={exportOpenApi}
                    >
                      OpenAPI
                    </Button>
                  </Tooltip>
                  <Tooltip label="Unduh Postman Collection v2.1">
                    <Button
                      size="xs"
                      variant="light"
                      color="orange"
                      leftSection={<IconDownload size={14} />}
                      onClick={exportPostman}
                    >
                      Postman
                    </Button>
                  </Tooltip>
                </Group>
              </div>
            </Group>
          </Card>

          <Tabs defaultValue="endpoints" color="indigo">
            <Tabs.List>
              <Tabs.Tab value="endpoints" leftSection={<IconApi size={14} />}>
                Endpoint ({report.endpoints.length})
              </Tabs.Tab>
              {report.graphql_ops.length > 0 && (
                <Tabs.Tab value="graphql">
                  GraphQL ({report.graphql_ops.length})
                </Tabs.Tab>
              )}
              <Tabs.Tab value="timing">Timing</Tabs.Tab>
              <Tabs.Tab value="stats">Statistik</Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="endpoints" pt="md">
              <Stack gap="sm">
                <TextInput
                  placeholder="Filter berdasarkan host, path, atau method..."
                  value={filterText}
                  onChange={(e) => setFilterText(e.currentTarget.value)}
                  leftSection={<IconFilter size={14} />}
                />
                {endpointsByHost.map(([host, eps]) => (
                  <Card key={host} withBorder radius="md" p="sm">
                    <Group justify="space-between" mb="xs">
                      <Text fw={600} ff="monospace" size="sm">
                        {host}
                      </Text>
                      <Badge color="gray" variant="light">
                        {eps.length} endpoint
                      </Badge>
                    </Group>
                    <Accordion variant="separated" multiple>
                      {eps.map((ep, i) => (
                        <EndpointRow
                          key={`${ep.method}-${ep.path}-${i}`}
                          endpoint={ep}
                        />
                      ))}
                    </Accordion>
                  </Card>
                ))}
              </Stack>
            </Tabs.Panel>

            {report.graphql_ops.length > 0 && (
              <Tabs.Panel value="graphql" pt="md">
                <Stack gap="sm">
                  {report.graphql_ops.map((op, i) => (
                    <GraphQLOpCard key={`${op.operation_name}-${i}`} op={op} />
                  ))}
                </Stack>
              </Tabs.Panel>
            )}

            <Tabs.Panel value="timing" pt="md">
              <TimingChart requests={report.requests} />
            </Tabs.Panel>

            <Tabs.Panel value="stats" pt="md">
              <StatsView report={report} />
            </Tabs.Panel>
          </Tabs>
        </Stack>
      )}
    </Stack>
  );
}

function EndpointRow({ endpoint }: { endpoint: ApiSnifferEndpoint }) {
  const sample = endpoint.sample_request;
  return (
    <Accordion.Item value={`${endpoint.method}-${endpoint.path}`}>
      <Accordion.Control>
        <Group gap="sm" wrap="nowrap">
          <Badge color={methodColor(endpoint.method)} variant="filled" w={70}>
            {endpoint.method}
          </Badge>
          <Text ff="monospace" size="sm" style={{ flex: 1, minWidth: 0 }}>
            {endpoint.path}
          </Text>
          {endpoint.is_graphql && (
            <Badge color="pink" size="xs" variant="light">
              GraphQL
            </Badge>
          )}
          <Badge color="gray" variant="light" size="sm">
            {endpoint.count}x
          </Badge>
          {Object.entries(endpoint.statuses).map(([s, c]) => (
            <Badge key={s} color={statusColor(parseInt(s))} size="sm" variant="light">
              {s} ({c})
            </Badge>
          ))}
        </Group>
      </Accordion.Control>
      <Accordion.Panel>
        <Stack gap="xs">
          <Text size="xs" c="dimmed" fw={600}>
            URL contoh
          </Text>
          <Code block style={{ wordBreak: "break-all" }}>
            {sample.full_url}
          </Code>
          {Object.keys(sample.request_headers).length > 0 && (
            <>
              <Text size="xs" c="dimmed" fw={600}>
                Request headers
              </Text>
              <ScrollArea.Autosize mah={150}>
                <Code block>
                  {Object.entries(sample.request_headers)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join("\n")}
                </Code>
              </ScrollArea.Autosize>
            </>
          )}
          {sample.request_body && (
            <>
              <Text size="xs" c="dimmed" fw={600}>
                Request body
              </Text>
              <ScrollArea.Autosize mah={200}>
                <Code block>{sample.request_body}</Code>
              </ScrollArea.Autosize>
            </>
          )}
          {sample.response_body && (
            <>
              <Text size="xs" c="dimmed" fw={600}>
                Response sample ({sample.response_content_type || "?"}) -{" "}
                {fmtBytes(sample.response_size_bytes)}
              </Text>
              <ScrollArea.Autosize mah={300}>
                <Code block>{sample.response_body}</Code>
              </ScrollArea.Autosize>
            </>
          )}
        </Stack>
      </Accordion.Panel>
    </Accordion.Item>
  );
}

function GraphQLOpCard({ op }: { op: ApiSnifferGraphQLOp }) {
  return (
    <Card withBorder radius="md" p="md">
      <Group justify="space-between" mb="xs">
        <Group gap="xs">
          <Badge color="pink" variant="light">
            {op.operation_type || "query"}
          </Badge>
          <Text fw={600}>{op.operation_name}</Text>
        </Group>
        <Group gap="xs">
          <Badge color="gray" variant="light">
            {op.count}x
          </Badge>
          <Text size="xs" c="dimmed" ff="monospace">
            {op.host}
            {op.path}
          </Text>
        </Group>
      </Group>
      {op.query && (
        <>
          <Text size="xs" c="dimmed" fw={600} mb={4}>
            Query
          </Text>
          <ScrollArea.Autosize mah={250} mb="xs">
            <Code block>{op.query}</Code>
          </ScrollArea.Autosize>
        </>
      )}
      {op.variables !== null && op.variables !== undefined && (
        <>
          <Text size="xs" c="dimmed" fw={600} mb={4}>
            Variables
          </Text>
          <ScrollArea.Autosize mah={150} mb="xs">
            <Code block>{JSON.stringify(op.variables, null, 2)}</Code>
          </ScrollArea.Autosize>
        </>
      )}
      {op.response_sample !== null && op.response_sample !== undefined && (
        <>
          <Text size="xs" c="dimmed" fw={600} mb={4}>
            Contoh response
          </Text>
          <ScrollArea.Autosize mah={250}>
            <Code block>
              {typeof op.response_sample === "string"
                ? op.response_sample
                : JSON.stringify(op.response_sample, null, 2)}
            </Code>
          </ScrollArea.Autosize>
        </>
      )}
    </Card>
  );
}

function TimingChart({ requests }: { requests: CapturedRequest[] }) {
  if (requests.length === 0) {
    return <Text c="dimmed">Tidak ada data timing.</Text>;
  }
  const sorted = [...requests].sort((a, b) => a.started_at - b.started_at);
  const t0 = sorted[0].started_at;
  const tN = sorted[sorted.length - 1].started_at;
  const span = Math.max(0.001, tN - t0);

  // Bin requests into 30 buckets
  const BINS = 30;
  const bins = new Array(BINS).fill(0);
  for (const r of sorted) {
    const idx = Math.min(BINS - 1, Math.floor(((r.started_at - t0) / span) * BINS));
    bins[idx]++;
  }
  const maxBin = Math.max(...bins, 1);

  return (
    <Card withBorder radius="md" p="md">
      <Text size="sm" mb="xs" c="dimmed">
        Distribusi permintaan sepanjang {span.toFixed(1)}s
      </Text>
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: 2,
          height: 160,
          padding: "0 4px",
        }}
      >
        {bins.map((v, i) => (
          <Tooltip key={i} label={`${v} req`}>
            <div
              style={{
                flex: 1,
                height: `${(v / maxBin) * 100}%`,
                background: "var(--mantine-color-indigo-5)",
                borderRadius: 2,
                minHeight: v > 0 ? 2 : 0,
              }}
            />
          </Tooltip>
        ))}
      </div>
      <Group justify="space-between" mt={4}>
        <Text size="xs" c="dimmed">
          0s
        </Text>
        <Text size="xs" c="dimmed">
          {span.toFixed(1)}s
        </Text>
      </Group>
    </Card>
  );
}

function StatsView({ report }: { report: ApiSnifferReport }) {
  const s = report.stats;
  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
      <Card withBorder radius="md" p="md">
        <Title order={5} mb="xs">
          Content-Type
        </Title>
        <Table fz="sm">
          <Table.Tbody>
            {Object.entries(s.content_type_breakdown)
              .sort((a, b) => b[1] - a[1])
              .map(([ct, n]) => (
                <Table.Tr key={ct}>
                  <Table.Td>
                    <Code>{ct}</Code>
                  </Table.Td>
                  <Table.Td ta="right">{n}</Table.Td>
                </Table.Tr>
              ))}
          </Table.Tbody>
        </Table>
      </Card>
      <Card withBorder radius="md" p="md">
        <Title order={5} mb="xs">
          Status
        </Title>
        <Table fz="sm">
          <Table.Tbody>
            {Object.entries(s.status_breakdown)
              .sort((a, b) => a[0].localeCompare(b[0]))
              .map(([st, n]) => (
                <Table.Tr key={st}>
                  <Table.Td>
                    <Badge color={statusColor(parseInt(st))} variant="light">
                      {st}
                    </Badge>
                  </Table.Td>
                  <Table.Td ta="right">{n}</Table.Td>
                </Table.Tr>
              ))}
          </Table.Tbody>
        </Table>
      </Card>
    </SimpleGrid>
  );
}
