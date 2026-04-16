import { notifyDone, notifyError } from "../lib/notify";
import { useEffect, useRef, useState } from "react";
import {
  Button,
  Card,
  Grid,
  Group,
  NumberInput,
  Progress,
  ScrollArea,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
  Badge,
  Image,
  Divider,
  ActionIcon,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconPlayerPlay, IconPlayerStop, IconDownload, IconRefresh } from "@tabler/icons-react";

import { api } from "../lib/api";
import { subscribeJobEvents } from "../lib/sse";
import type { SSEEvent } from "../types";

interface LogLine {
  ts: number;
  text: string;
  kind: "info" | "ok" | "warn" | "err";
}

interface LiveAsset {
  url: string;
  width?: number;
  height?: number;
  size: number;
}

export default function HarvesterPage() {
  const [url, setUrl] = useState("https://example.com");
  const [concurrency, setConcurrency] = useState<number | string>(8);
  const [minWidth, setMinWidth] = useState<number | string>(100);
  const [minHeight, setMinHeight] = useState<number | string>(100);
  const [minBytes, setMinBytes] = useState<number | string>(5120);
  const [includeCss, setIncludeCss] = useState(false);
  const [deduplicate, setDeduplicate] = useState(true);

  const [jobId, setJobId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [discovered, setDiscovered] = useState(0);
  const [stats, setStats] = useState({
    downloaded: 0,
    skipped: 0,
    failed: 0,
    bytes_total: 0,
  });
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [liveAssets, setLiveAssets] = useState<LiveAsset[]>([]);

  const unsubRef = useRef<(() => void) | null>(null);

  useEffect(() => () => unsubRef.current?.(), []);

  const addLog = (text: string, kind: LogLine["kind"] = "info") =>
    setLogs((l) => [...l.slice(-200), { ts: Date.now(), text, kind }]);

  const reset = () => {
    setDiscovered(0);
    setStats({ downloaded: 0, skipped: 0, failed: 0, bytes_total: 0 });
    setLogs([]);
    setLiveAssets([]);
  };

  const handleEvent = (e: SSEEvent) => {
    switch (e.type) {
      case "status":
        addLog(`Status: ${e.status}`, "info");
        break;
      case "log":
        addLog(e.message, "info");
        break;
      case "discovered":
        setDiscovered(e.count);
        addLog(`Discovered ${e.count} image candidates`, "info");
        break;
      case "asset_done":
        setStats((s) => ({
          ...s,
          downloaded: (e.stats.downloaded as number) ?? s.downloaded + 1,
          skipped: (e.stats.skipped as number) ?? s.skipped,
          failed: (e.stats.failed as number) ?? s.failed,
          bytes_total: (e.stats.bytes_total as number) ?? s.bytes_total + e.size,
        }));
        setLiveAssets((a) => [
          { url: e.url, size: e.size, width: e.width, height: e.height },
          ...a.slice(0, 99),
        ]);
        break;
      case "asset_failed":
        addLog(`Failed: ${e.url} — ${e.error}`, "err");
        setStats((s) => ({ ...s, failed: s.failed + 1 }));
        break;
      case "done":
        setRunning(false);
        addLog("Harvest complete", "ok");
        notifyDone("Image harvest finished");
        break;
      case "stopped":
        setRunning(false);
        addLog("Stopped by user", "warn");
        break;
      case "error":
        setRunning(false);
        addLog(`Error: ${e.message}`, "err");
        notifications.show({ title: "Error", message: e.message, color: "red" });
        break;
    }
  };

  const onStart = async () => {
    reset();
    try {
      setRunning(true);
      const res = await api.startHarvester({
        url,
        filters: {
          allowed_types: ["jpg", "jpeg", "png", "webp", "gif", "svg"],
          min_width: Number(minWidth),
          min_height: Number(minHeight),
          min_bytes: Number(minBytes),
          exclude_patterns: [],
        },
        concurrency: Number(concurrency),
        include_background_css: includeCss,
        deduplicate,
      });
      setJobId(res.job_id);
      unsubRef.current = subscribeJobEvents(res.job_id, handleEvent);
    } catch (e: any) {
      setRunning(false);
      notifications.show({ title: "Failed to start", message: e.message, color: "red" });
    }
  };

  const onStop = async () => {
    if (!jobId) return;
    await api.stopHarvester(jobId);
  };

  const progressValue = discovered > 0 ? (stats.downloaded / discovered) * 100 : 0;
  const mb = (stats.bytes_total / 1024 / 1024).toFixed(2);

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Image Harvester</Title>
          <Text c="dimmed" size="sm">
            Extract every image from a page — filtered, deduplicated, organized.
          </Text>
        </div>
        {jobId && (
          <Tooltip label="Download ZIP">
            <ActionIcon
              component="a"
              href={api.downloadZipUrl(jobId)}
              variant="light"
              color="cyan"
              size="lg"
              disabled={running}
              aria-label="Download ZIP"
            >
              <IconDownload size={18} />
            </ActionIcon>
          </Tooltip>
        )}
      </Group>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <TextInput
            label="Target URL"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            size="md"
          />
          <Grid>
            <Grid.Col span={{ base: 6, md: 3 }}>
              <NumberInput label="Concurrency" value={concurrency} onChange={setConcurrency} min={1} max={32} />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 3 }}>
              <NumberInput label="Min width (px)" value={minWidth} onChange={setMinWidth} min={0} />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 3 }}>
              <NumberInput label="Min height (px)" value={minHeight} onChange={setMinHeight} min={0} />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 3 }}>
              <NumberInput label="Min size (bytes)" value={minBytes} onChange={setMinBytes} min={0} />
            </Grid.Col>
          </Grid>
          <Group>
            <Switch label="Parse CSS background-image" checked={includeCss} onChange={(e) => setIncludeCss(e.currentTarget.checked)} />
            <Switch label="Deduplicate (hash)" checked={deduplicate} onChange={(e) => setDeduplicate(e.currentTarget.checked)} />
          </Group>
          <Group>
            <Button
              leftSection={<IconPlayerPlay size={16} />}
              onClick={onStart}
              disabled={running}
              size="md"
            >
              Start
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
              <Badge color="cyan" variant="dot" size="lg">
                Running
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
                {stats.downloaded} / {discovered || "?"} · {mb} MB
              </Text>
            </Group>
            <Progress value={progressValue} size="lg" radius="xl" animated={running} />
            <Divider my="md" />
            <SimpleGrid cols={4}>
              <StatBox label="Discovered" value={discovered} />
              <StatBox label="Downloaded" value={stats.downloaded} color="cyan" />
              <StatBox label="Skipped" value={stats.skipped} color="yellow" />
              <StatBox label="Failed" value={stats.failed} color="red" />
            </SimpleGrid>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Group justify="space-between" mb="xs">
              <Text fw={600}>Live log</Text>
              <ActionIcon variant="subtle" size="sm" onClick={() => setLogs([])} aria-label="Clear log">
                <IconRefresh size={14} />
              </ActionIcon>
            </Group>
            <ScrollArea h={180} type="auto">
              <Stack gap={2}>
                {logs.length === 0 ? (
                  <Text size="xs" c="dimmed">// waiting…</Text>
                ) : (
                  logs.map((l, i) => (
                    <Text
                      key={i}
                      size="xs"
                      ff="monospace"
                      c={
                        l.kind === "err"
                          ? "red"
                          : l.kind === "warn"
                          ? "yellow"
                          : l.kind === "ok"
                          ? "teal"
                          : "dimmed"
                      }
                    >
                      {l.text}
                    </Text>
                  ))
                )}
              </Stack>
            </ScrollArea>
          </Card>
        </Grid.Col>
      </Grid>

      <Card withBorder radius="lg" p="lg">
        <Text fw={600} mb="sm">Live preview</Text>
        {liveAssets.length === 0 ? (
          <Text size="sm" c="dimmed">Images will appear here as they download.</Text>
        ) : (
          <SimpleGrid cols={{ base: 3, sm: 5, md: 8, lg: 10 }} spacing="xs">
            {liveAssets.map((a, i) => (
              <Tooltip key={i} label={`${a.width || "?"}×${a.height || "?"} · ${(a.size / 1024).toFixed(1)} KB`}>
                <Image
                  src={a.url}
                  h={80}
                  fit="cover"
                  radius="sm"
                  fallbackSrc="data:image/svg+xml;base64,PHN2Zy8+"
                />
              </Tooltip>
            ))}
          </SimpleGrid>
        )}
      </Card>
    </Stack>
  );
}

function StatBox({ label, value, color = "gray" }: { label: string; value: number; color?: string }) {
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
