import { notifyDone, notifyError } from "../lib/notify";
import { useEffect, useRef, useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Menu,
  NumberInput,
  Progress,
  ScrollArea,
  SimpleGrid,
  Slider,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconDownload,
  IconFileExport,
  IconFileTypePdf,
  IconPlayerPlay,
  IconPlayerStop,
  IconPackage,
} from "@tabler/icons-react";

import { api, subscribeRipperEvents } from "../lib/api";
import type { RipperStats } from "../types";

const emptyStats: RipperStats = {
  pages: 0,
  assets: 0,
  bytes_total: 0,
  broken: 0,
  failed: 0,
  by_kind: {},
};

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(2)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

const KIND_COLORS: Record<string, string> = {
  html: "cyan",
  css: "violet",
  js: "yellow",
  image: "pink",
  font: "teal",
  favicon: "grape",
  video: "orange",
  audio: "orange",
  iframe: "gray",
  other: "gray",
};

interface LogLine {
  ts: number;
  text: string;
}

export default function RipperPage() {
  // Form
  const [url, setUrl] = useState("https://example.com/");
  const [maxDepth, setMaxDepth] = useState<number>(1);
  const [maxPages, setMaxPages] = useState<number | string>(10);
  const [maxAssets, setMaxAssets] = useState<number | string>(500);
  const [rateLimit, setRateLimit] = useState<number | string>(4);
  const [concurrency, setConcurrency] = useState<number | string>(6);
  const [stayOnDomain, setStayOnDomain] = useState(true);
  const [respectRobots, setRespectRobots] = useState(true);
  const [includeExternal, setIncludeExternal] = useState(true);
  const [rewriteLinks, setRewriteLinks] = useState(true);
  const [generateReport, setGenerateReport] = useState(true);

  // Job state
  const [jobId, setJobId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [stats, setStats] = useState<RipperStats>(emptyStats);
  const [logs, setLogs] = useState<LogLine[]>([]);

  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => () => sseRef.current?.close(), []);

  const addLog = (text: string) =>
    setLogs((l) => [...l.slice(-200), { ts: Date.now(), text }]);

  const reset = () => {
    setStats(emptyStats);
    setLogs([]);
  };

  const onStart = async () => {
    reset();
    try {
      setRunning(true);
      const res = await api.startRipper({
        url,
        max_depth: maxDepth,
        max_pages: Number(maxPages),
        max_assets: Number(maxAssets),
        stay_on_domain: stayOnDomain,
        respect_robots: respectRobots,
        rate_limit_per_host: Number(rateLimit),
        concurrency: Number(concurrency),
        include_external_assets: includeExternal,
        rewrite_links: rewriteLinks,
        generate_report: generateReport,
      });
      setJobId(res.job_id);

      sseRef.current?.close();
      const source = subscribeRipperEvents(res.job_id);
      source.onmessage = (msg) => {
        try {
          const e = JSON.parse(msg.data);
          handleEvent(e);
        } catch {}
      };
      source.onerror = () => source.close();
      sseRef.current = source;
    } catch (err: any) {
      setRunning(false);
      notifications.show({ title: "Gagal start", message: err.message, color: "red" });
    }
  };

  const onStop = async () => {
    if (!jobId) return;
    await api.stopRipper(jobId);
  };

  const handleEvent = (e: any) => {
    switch (e.type) {
      case "status":
        addLog(`Status: ${e.status}`);
        break;
      case "log":
        addLog(e.message);
        break;
      case "page_done":
        addLog(`📄 ${e.url}`);
        if (e.stats) setStats((s) => ({ ...s, ...e.stats }));
        break;
      case "asset_done":
        if (e.stats) setStats((s) => ({ ...s, ...e.stats }));
        break;
      case "done":
        setRunning(false);
        if (e.stats) setStats((s) => ({ ...s, ...e.stats }));
        addLog("✓ Rip complete");
        notifications.show({
          title: "Done",
          message: "Site mirror siap di-download",
          color: "green",
        });
        break;
      case "stopped":
        setRunning(false);
        if (e.stats) setStats((s) => ({ ...s, ...e.stats }));
        addLog("⏹ Stopped by user");
        break;
      case "error":
        setRunning(false);
        addLog(`❌ ${e.message}`);
        notifications.show({ title: "Error", message: e.message, color: "red" });
        break;
    }
  };

  const hasJob = jobId !== null;
  const pageProgress =
    Number(maxPages) > 0 ? (stats.pages / Number(maxPages)) * 100 : 0;
  const assetProgress =
    Number(maxAssets) > 0 ? (stats.assets / Number(maxAssets)) * 100 : 0;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Site Ripper</Title>
          <Text c="dimmed" size="sm">
            Clone an entire site — HTML, CSS, JS, fonts, images — browsable offline.
          </Text>
        </div>
        {hasJob && !running && (
          <Menu shadow="md" width={220}>
            <Menu.Target>
              <Tooltip label="Download">
                <ActionIcon variant="light" color="cyan" size="lg" aria-label="Download">
                  <IconFileExport size={18} />
                </ActionIcon>
              </Tooltip>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Label>Artifacts</Menu.Label>
              <Menu.Item
                leftSection={<IconPackage size={14} />}
                component="a"
                href={api.ripperZipUrl(jobId!)}
              >
                Mirror ZIP
              </Menu.Item>
              <Menu.Item
                leftSection={<IconFileTypePdf size={14} />}
                component="a"
                href={api.ripperReportUrl(jobId!)}
                target="_blank"
              >
                PDF report
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        )}
      </Group>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <TextInput
            label="Target URL"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            size="md"
            placeholder="https://example.com/"
          />
          <Grid>
            <Grid.Col span={{ base: 12, md: 4 }}>
              <Text size="sm" fw={600} mb={4}>
                Max depth: {maxDepth}
              </Text>
              <Slider
                value={maxDepth}
                onChange={setMaxDepth}
                min={0}
                max={5}
                step={1}
                marks={[0, 1, 2, 3, 4, 5].map((v) => ({ value: v, label: String(v) }))}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <NumberInput label="Max pages" value={maxPages} onChange={setMaxPages} min={1} max={5000} />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <NumberInput label="Max assets" value={maxAssets} onChange={setMaxAssets} min={1} max={50000} />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <NumberInput label="Rate /s per host" value={rateLimit} onChange={setRateLimit} min={0.1} max={20} step={0.5} decimalScale={1} />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <NumberInput label="Concurrency" value={concurrency} onChange={setConcurrency} min={1} max={32} />
            </Grid.Col>
          </Grid>
          <Group gap="xl">
            <Switch label="Stay on domain" checked={stayOnDomain} onChange={(e) => setStayOnDomain(e.currentTarget.checked)} />
            <Switch label="Respect robots.txt" checked={respectRobots} onChange={(e) => setRespectRobots(e.currentTarget.checked)} />
            <Switch label="Include external assets" checked={includeExternal} onChange={(e) => setIncludeExternal(e.currentTarget.checked)} />
            <Switch label="Rewrite links" checked={rewriteLinks} onChange={(e) => setRewriteLinks(e.currentTarget.checked)} />
            <Switch label="Generate PDF report" checked={generateReport} onChange={(e) => setGenerateReport(e.currentTarget.checked)} />
          </Group>
          <Group>
            <Button
              leftSection={<IconPlayerPlay size={16} />}
              onClick={onStart}
              disabled={running}
              size="md"
            >
              Start rip
            </Button>
            <Button
              leftSection={<IconPlayerStop size={16} />}
              onClick={onStop}
              disabled={!running}
              color="pink"
              variant="light"
              size="md"
            >
              Stop
            </Button>
            {running && (
              <Badge color="teal" variant="dot" size="lg">
                Ripping
              </Badge>
            )}
          </Group>
        </Stack>
      </Card>

      <Grid>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="xs">
              <Text fw={600}>Progress</Text>
              <Text size="sm" c="dimmed">
                {fmtBytes(stats.bytes_total)}
              </Text>
            </Group>
            <Text size="xs" c="dimmed" mt="sm" mb={4}>
              Pages · {stats.pages} / {maxPages}
            </Text>
            <Progress value={pageProgress} size="sm" radius="xl" animated={running} color="cyan" />
            <Text size="xs" c="dimmed" mt="sm" mb={4}>
              Assets · {stats.assets} / {maxAssets}
            </Text>
            <Progress value={assetProgress} size="sm" radius="xl" animated={running} color="teal" />

            <SimpleGrid cols={4} mt="lg">
              <Stat label="Pages" value={stats.pages} color="cyan" />
              <Stat label="Assets" value={stats.assets} color="teal" />
              <Stat label="Broken" value={stats.broken} color="red" />
              <Stat label="Failed" value={stats.failed} color="orange" />
            </SimpleGrid>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Text fw={600} mb="xs">
              Live log
            </Text>
            <ScrollArea h={220} type="auto">
              <Stack gap={2}>
                {logs.length === 0 ? (
                  <Text size="xs" c="dimmed">// waiting…</Text>
                ) : (
                  logs.map((l, i) => (
                    <Text key={i} size="xs" ff="monospace" c="dimmed">
                      {l.text}
                    </Text>
                  ))
                )}
              </Stack>
            </ScrollArea>
          </Card>
        </Grid.Col>
      </Grid>

      {Object.keys(stats.by_kind).length > 0 && (
        <Card withBorder radius="lg" p="lg">
          <Text fw={600} mb="md">Asset breakdown</Text>
          <SimpleGrid cols={{ base: 2, sm: 3, md: 4, lg: 6 }}>
            {Object.entries(stats.by_kind)
              .sort(([, a], [, b]) => b.bytes - a.bytes)
              .map(([kind, data]) => (
                <Card key={kind} withBorder radius="md" p="sm">
                  <Badge color={KIND_COLORS[kind] || "gray"} variant="light" mb={4}>
                    {kind}
                  </Badge>
                  <Text size="xl" fw={800}>
                    {data.count}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {fmtBytes(data.bytes)}
                  </Text>
                </Card>
              ))}
          </SimpleGrid>
        </Card>
      )}
    </Stack>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text size="xl" fw={800} c={color}>
        {value}
      </Text>
    </div>
  );
}
