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
  ScrollArea,
  SegmentedControl,
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
  IconBinaryTree,
  IconDownload,
  IconFileExport,
  IconGraph,
  IconPhoto,
  IconPlayerPause,
  IconPlayerPlay,
  IconRefresh,
  IconSearch,
} from "@tabler/icons-react";

import { api, subscribeMapperEvents } from "../lib/api";
import SitemapTree from "../components/SitemapTree";
import SitemapGraph, {
  type SitemapGraphHandle,
} from "../components/SitemapGraph";
import BrokenLinksPanel from "../components/BrokenLinksPanel";
import NodeDetailDrawer, {
  type NodeDetail,
} from "../components/NodeDetailDrawer";
import type {
  SSEEvent,
  SitemapGraphResponse,
  SitemapTreeNode,
} from "../types";

interface MapperStats {
  discovered: number;
  crawled: number;
  broken: number;
  external_skipped: number;
  avg_response_ms: number;
  frontier_size: number;
}

const emptyStats: MapperStats = {
  discovered: 0,
  crawled: 0,
  broken: 0,
  external_skipped: 0,
  avg_response_ms: 0,
  frontier_size: 0,
};

export default function MapperPage() {
  // Form state
  const [url, setUrl] = useState("https://fastapi.tiangolo.com/");
  const [maxDepth, setMaxDepth] = useState<number>(2);
  const [maxPages, setMaxPages] = useState<number | string>(100);
  const [rateLimit, setRateLimit] = useState<number | string>(3);
  const [concurrency, setConcurrency] = useState<number | string>(4);
  const [stayOnDomain, setStayOnDomain] = useState(true);
  const [respectRobots, setRespectRobots] = useState(true);
  const [usePlaywright, setUsePlaywright] = useState(false);

  // Job state
  const [jobId, setJobId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [stats, setStats] = useState<MapperStats>(emptyStats);
  const [logs, setLogs] = useState<string[]>([]);

  const addLog = (t: string) => setLogs((l) => [...l.slice(-200), t]);

  // View state
  const [view, setView] = useState<"tree" | "graph">("tree");
  const [tree, setTree] = useState<SitemapTreeNode[]>([]);
  const [graph, setGraph] = useState<SitemapGraphResponse>({ nodes: [], edges: [] });
  const [searchQuery, setSearchQuery] = useState("");
  const [drawerNode, setDrawerNode] = useState<NodeDetail | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const sseRef = useRef<EventSource | null>(null);
  const graphRef = useRef<SitemapGraphHandle | null>(null);

  const hasJob = jobId !== null;
  const canResume = paused && stats.frontier_size > 0;

  const refreshView = async (id: string) => {
    try {
      const [t, g] = await Promise.all([
        api.getMapperTree(id),
        api.getMapperGraph(id),
      ]);
      setTree(t);
      setGraph(g);
    } catch (err) {
      console.error("refresh failed", err);
    }
  };

  useEffect(() => {
    if (!jobId || !running) return;
    const interval = setInterval(() => refreshView(jobId), 2000);
    return () => clearInterval(interval);
  }, [jobId, running]);

  useEffect(
    () => () => {
      sseRef.current?.close();
    },
    []
  );

  const subscribeEvents = (id: string) => {
    sseRef.current?.close();
    const source = subscribeMapperEvents(id);
    source.onmessage = (msg) => {
      try {
        const e = JSON.parse(msg.data) as SSEEvent;
        handleEvent(e, id);
      } catch {}
    };
    source.onerror = () => source.close();
    sseRef.current = source;
  };

  const onStart = async () => {
    setStats(emptyStats);
    setTree([]);
    setGraph({ nodes: [], edges: [] });
    setSearchQuery("");
    setPaused(false);
    setLogs([]);
    try {
      setRunning(true);
      const res = await api.startMapper({
        url,
        max_depth: maxDepth,
        max_pages: Number(maxPages),
        stay_on_domain: stayOnDomain,
        respect_robots: respectRobots,
        rate_limit_per_host: Number(rateLimit),
        concurrency: Number(concurrency),
        exclude_patterns: [],
        strip_tracking_params: true,
        use_playwright: usePlaywright,
      });
      setJobId(res.job_id);
      subscribeEvents(res.job_id);
    } catch (err: any) {
      setRunning(false);
      notifications.show({ title: "Gagal start", message: err.message, color: "red" });
    }
  };

  const onPause = async () => {
    if (!jobId) return;
    await api.stopMapper(jobId);
    setPaused(true);
  };

  const onResume = async () => {
    if (!jobId) return;
    try {
      setRunning(true);
      setPaused(false);
      await api.resumeMapper(jobId);
      subscribeEvents(jobId);
    } catch (err: any) {
      setRunning(false);
      notifications.show({ title: "Gagal resume", message: err.message, color: "red" });
    }
  };

  const handleEvent = (e: SSEEvent, currentJobId: string) => {
    switch (e.type) {
      case "progress":
        setStats((s) => ({ ...s, ...(e.stats as any) }));
        addLog(`Crawled ${e.stats?.crawled || 0} pages`);
        break;
      case "log":
        addLog(e.message);
        break;
      case "node":
        break;
      case "done":
        setRunning(false);
        setPaused(false);
        setStats((s) => ({ ...s, ...(e.stats as any) }));
        refreshView(currentJobId);
        addLog("Crawl complete");
        notifyDone("Crawl complete");
        break;
      case "stopped":
        setRunning(false);
        setPaused(true);
        setStats((s) => ({ ...s, ...(e.stats as any) }));
        refreshView(currentJobId);
        addLog("Stopped by user");
        break;
      case "error":
        setRunning(false);
        setPaused(false);
        addLog(`Error: ${e.message}`);
        notifications.show({ title: "Error", message: e.message, color: "red" });
        break;
    }
  };

  const onExportPng = () => {
    const dataUrl = graphRef.current?.exportPng();
    if (!dataUrl) {
      notifications.show({ title: "PNG export", message: "Switch ke Graph view dulu", color: "yellow" });
      return;
    }
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = `sitemap-${jobId?.slice(0, 8)}.png`;
    a.click();
  };

  const openNode = (n: { id: number; url: string; status: number | null; title: string | null }) => {
    const full = graph.nodes.find((g) => g.id === n.id);
    setDrawerNode({
      id: n.id,
      url: n.url,
      status: n.status,
      title: n.title,
      depth: full?.depth,
    });
    setDrawerOpen(true);
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>URL Mapper</Title>
          <Text c="dimmed" size="sm">
            Crawl a site and visualize the sitemap: tree or interactive graph.
          </Text>
        </div>
        {hasJob && (
          <Menu shadow="md" width={200}>
            <Menu.Target>
              <Tooltip label="Export">
                <ActionIcon variant="light" color="cyan" size="lg" disabled={!hasJob} aria-label="Export">
                  <IconFileExport size={18} />
                </ActionIcon>
              </Tooltip>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Label>Export sitemap</Menu.Label>
              <Menu.Item
                leftSection={<IconDownload size={14} />}
                component="a"
                href={api.mapperExportJsonUrl(jobId!)}
              >
                JSON
              </Menu.Item>
              <Menu.Item
                leftSection={<IconDownload size={14} />}
                component="a"
                href={api.mapperExportXmlUrl(jobId!)}
              >
                XML sitemap
              </Menu.Item>
              <Menu.Item
                leftSection={<IconPhoto size={14} />}
                onClick={onExportPng}
              >
                PNG screenshot
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
            placeholder="https://example.com"
          />
          <Grid>
            <Grid.Col span={{ base: 12, md: 4 }}>
              <Text size="sm" fw={600} mb={4}>
                Max depth: {maxDepth}
              </Text>
              <Slider
                value={maxDepth}
                onChange={setMaxDepth}
                min={1}
                max={5}
                step={1}
                marks={[1, 2, 3, 4, 5].map((v) => ({ value: v, label: String(v) }))}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <NumberInput label="Max pages" value={maxPages} onChange={setMaxPages} min={1} max={20000} />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <NumberInput label="Rate /s per host" value={rateLimit} onChange={setRateLimit} min={0.1} max={20} step={0.5} decimalScale={1} />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <NumberInput label="Concurrency" value={concurrency} onChange={setConcurrency} min={1} max={16} />
            </Grid.Col>
          </Grid>
          <Group>
            <Switch label="Stay on domain" checked={stayOnDomain} onChange={(e) => setStayOnDomain(e.currentTarget.checked)} />
            <Switch label="Respect robots.txt" checked={respectRobots} onChange={(e) => setRespectRobots(e.currentTarget.checked)} />
            <Switch
              label="Render dengan browser (Playwright)"
              description="Untuk situs JS-heavy seperti React/Vue. Lebih lambat tapi dapat konten dinamis."
              checked={usePlaywright}
              onChange={(e) => setUsePlaywright(e.currentTarget.checked)}
            />
          </Group>
          <Group>
            <Button
              leftSection={<IconPlayerPlay size={16} />}
              onClick={onStart}
              disabled={running}
              size="md"
            >
              Start crawl
            </Button>
            <Button
              leftSection={<IconPlayerPause size={16} />}
              onClick={onPause}
              disabled={!running}
              color="yellow"
              variant="light"
              size="md"
            >
              Pause
            </Button>
            <Button
              leftSection={<IconRefresh size={16} />}
              onClick={onResume}
              disabled={!canResume}
              color="cyan"
              variant="light"
              size="md"
            >
              Resume ({stats.frontier_size})
            </Button>
            {running && (
              <Badge color="violet" variant="dot" size="lg">
                Crawling
              </Badge>
            )}
            {paused && !running && (
              <Badge color="yellow" variant="dot" size="lg">
                Paused
              </Badge>
            )}
          </Group>
        </Stack>
      </Card>

      <Card withBorder radius="lg" p="lg">
        <Group justify="space-between" mb="xs">
          <Text fw={600}>Stats</Text>
          {stats.avg_response_ms > 0 && (
            <Text size="xs" c="dimmed">
              avg response: {stats.avg_response_ms} ms
            </Text>
          )}
        </Group>
        <SimpleGrid cols={{ base: 2, md: 6 }}>
          <Stat label="Discovered" value={stats.discovered} color="violet" />
          <Stat label="Crawled" value={stats.crawled} color="cyan" />
          <Stat label="Broken" value={stats.broken} color="red" />
          <Stat label="External skipped" value={stats.external_skipped} color="yellow" />
          <Stat label="In queue" value={stats.frontier_size} color="gray" />
          <Stat label="Avg ms" value={stats.avg_response_ms} color="teal" />
        </SimpleGrid>
      </Card>

      <Card withBorder radius="lg" p="lg">
        <Text fw={600} mb="xs">Live log</Text>
        <ScrollArea h={180} type="auto">
          <Stack gap={2}>
            {logs.length === 0 ? (
              <Text size="xs" c="dimmed">// waiting…</Text>
            ) : (
              logs.map((l, i) => (
                <Text key={i} size="xs" ff="monospace" c="dimmed">
                  {l}
                </Text>
              ))
            )}
          </Stack>
        </ScrollArea>
      </Card>

      {graph.nodes.length > 0 && <BrokenLinksPanel nodes={graph.nodes} />}

      <Card withBorder radius="lg" p="lg">
        <Group justify="space-between" mb="md" wrap="nowrap">
          <Text fw={600}>Sitemap</Text>
          <Group gap="sm" wrap="nowrap">
            <TextInput
              size="xs"
              placeholder="Search url or title…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
              leftSection={<IconSearch size={13} />}
              w={{ base: 160, sm: 260 }}
            />
            <SegmentedControl
              value={view}
              onChange={(v) => setView(v as "tree" | "graph")}
              size="xs"
              data={[
                {
                  label: (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      <IconBinaryTree size={14} /> Tree
                    </span>
                  ) as any,
                  value: "tree",
                },
                {
                  label: (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      <IconGraph size={14} /> Graph
                    </span>
                  ) as any,
                  value: "graph",
                },
              ]}
            />
          </Group>
        </Group>
        {view === "tree" ? (
          <SitemapTree data={tree} searchQuery={searchQuery} onNodeClick={openNode} />
        ) : (
          <SitemapGraph
            ref={graphRef}
            data={graph}
            searchQuery={searchQuery}
            onNodeClick={(n) =>
              openNode({ id: n.id, url: n.url, status: n.status_code, title: n.title })
            }
          />
        )}
      </Card>

      <NodeDetailDrawer
        node={drawerNode}
        opened={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
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
