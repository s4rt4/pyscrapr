import { notifyDone, notifyError } from "../lib/notify";
import { useEffect, useRef, useState } from "react";
import BulkUrlModal from "../components/BulkUrlModal";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Divider,
  Grid,
  Group,
  Image,
  NumberInput,
  Progress,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconEye,
  IconFolderOpen,
  IconPlayerPlay,
  IconPlayerStop,
  IconVideo,
  IconMusic,
  IconList,
} from "@tabler/icons-react";

import { api, subscribeMediaEvents } from "../lib/api";
import type {
  BrowserName,
  FormatPreset,
  MediaProbeResponse,
  MediaStats,
  QualityPreset,
  SubtitleMode,
} from "../types";

const emptyStats: MediaStats = {
  total_items: 0,
  downloaded: 0,
  failed: 0,
  bytes_total: 0,
  current_speed: 0,
  current_eta: null,
  current_filename: null,
  current_percent: 0,
};

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(2)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function fmtDur(seconds?: number | null): string {
  if (!seconds) return "";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function fmtEta(seconds?: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

interface DownloadedItem {
  filename: string;
  title: string;
  thumbnail?: string;
  duration?: number;
  size: number;
  status: "done" | "failed";
}

export default function MediaPage() {
  // Form
  const [url, setUrl] = useState("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
  const [quality, setQuality] = useState<QualityPreset>("1080p");
  const [format, setFormat] = useState<FormatPreset>("mp4");
  const [subtitles, setSubtitles] = useState<SubtitleMode>("skip");
  const [subtitleLangs, setSubtitleLangs] = useState("en,id");
  const [embedThumbnail, setEmbedThumbnail] = useState(true);
  const [embedMetadata, setEmbedMetadata] = useState(true);
  const [cookies, setCookies] = useState<BrowserName | "">("");
  const [playlistStart, setPlaylistStart] = useState<number | string>("");
  const [playlistEnd, setPlaylistEnd] = useState<number | string>("");
  const [maxItems, setMaxItems] = useState<number | string>("");

  // Probe
  const [probing, setProbing] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [probe, setProbe] = useState<MediaProbeResponse | null>(null);

  // Job
  const [jobId, setJobId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [stats, setStats] = useState<MediaStats>(emptyStats);
  const [items, setItems] = useState<DownloadedItem[]>([]);
  const [logs, setLogs] = useState<string[]>([]);

  const sseRef = useRef<EventSource | null>(null);
  useEffect(() => () => sseRef.current?.close(), []);

  const addLog = (t: string) => setLogs((l) => [...l.slice(-200), t]);

  const onProbe = async () => {
    setProbe(null);
    try {
      setProbing(true);
      const r = await api.probeMedia(url, cookies || undefined);
      setProbe(r);
    } catch (e: any) {
      notifications.show({ title: "Probe failed", message: e.message, color: "red" });
    } finally {
      setProbing(false);
    }
  };

  const onStart = async () => {
    setStats(emptyStats);
    setItems([]);
    setLogs([]);
    try {
      setRunning(true);
      const res = await api.startMedia({
        url,
        quality,
        format,
        subtitles,
        subtitle_langs: subtitleLangs.split(",").map((s) => s.trim()).filter(Boolean),
        embed_thumbnail: embedThumbnail,
        embed_metadata: embedMetadata,
        use_browser_cookies: cookies || null,
        playlist_start: playlistStart ? Number(playlistStart) : null,
        playlist_end: playlistEnd ? Number(playlistEnd) : null,
        max_items: maxItems ? Number(maxItems) : null,
      });
      setJobId(res.job_id);
      sseRef.current?.close();
      const source = subscribeMediaEvents(res.job_id);
      source.onmessage = (msg) => {
        try {
          handleEvent(JSON.parse(msg.data));
        } catch {}
      };
      source.onerror = () => source.close();
      sseRef.current = source;
    } catch (e: any) {
      setRunning(false);
      notifications.show({ title: "Gagal start", message: e.message, color: "red" });
    }
  };

  const onStop = async () => {
    if (jobId) await api.stopMedia(jobId);
  };

  const onOpenFolder = async () => {
    if (!jobId) return;
    try {
      await fetch(`/api/media/jobs/${jobId}/open-folder`, { method: "POST" });
    } catch {}
  };

  const handleEvent = (e: any) => {
    switch (e.type) {
      case "log":
        addLog(e.message);
        break;
      case "progress":
        if (e.stats) setStats((s) => ({ ...s, ...e.stats }));
        break;
      case "item_done":
        setItems((prev) => [
          ...prev,
          {
            filename: e.filename,
            title: e.title || e.filename,
            thumbnail: e.thumbnail,
            duration: e.duration,
            size: e.size,
            status: "done",
          },
        ]);
        if (e.stats) setStats((s) => ({ ...s, ...e.stats }));
        break;
      case "done":
        setRunning(false);
        if (e.stats) setStats((s) => ({ ...s, ...e.stats }));
        notifyDone("Media downloaded");
        break;
      case "stopped":
        setRunning(false);
        break;
      case "error":
        setRunning(false);
        addLog(`Error: ${e.message}`);
        notifications.show({ title: "Error", message: e.message, color: "red" });
        break;
    }
  };

  const isAudio = quality === "audio" || ["mp3", "m4a", "flac", "opus"].includes(format);

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Media Downloader</Title>
          <Text c="dimmed" size="sm">
            YouTube, Instagram, TikTok, and 1000+ sites via yt-dlp.
          </Text>
        </div>
        {jobId && !running && (
          <Tooltip label="Open download folder">
            <ActionIcon variant="light" color="cyan" size="lg" onClick={onOpenFolder} aria-label="Open folder">
              <IconFolderOpen size={18} />
            </ActionIcon>
          </Tooltip>
        )}
      </Group>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Group align="flex-end">
            <TextInput
              style={{ flex: 1 }}
              label="Media URL"
              value={url}
              onChange={(e) => setUrl(e.currentTarget.value)}
              size="md"
              placeholder="https://www.youtube.com/watch?v=..."
            />
            <Button leftSection={<IconEye size={16} />} onClick={onProbe} loading={probing} variant="light" size="md">
              Probe
            </Button>
          </Group>

          <Grid>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <Select label="Quality" value={quality} onChange={(v) => setQuality((v as QualityPreset) || "1080p")}
                data={[
                  { value: "best", label: "Best" }, { value: "4k", label: "4K" },
                  { value: "1080p", label: "1080p" }, { value: "720p", label: "720p" },
                  { value: "480p", label: "480p" }, { value: "audio", label: "Audio only" },
                ]}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <Select label="Format" value={format} onChange={(v) => setFormat((v as FormatPreset) || "mp4")}
                data={isAudio
                  ? [{ value: "mp3", label: "MP3" }, { value: "m4a", label: "M4A" }, { value: "flac", label: "FLAC" }, { value: "opus", label: "Opus" }]
                  : [{ value: "mp4", label: "MP4" }, { value: "webm", label: "WebM" }, { value: "mkv", label: "MKV" }]
                }
              />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <Select label="Subtitles" value={subtitles} onChange={(v) => setSubtitles((v as SubtitleMode) || "skip")}
                data={[{ value: "skip", label: "Skip" }, { value: "download", label: "Download (.srt)" }, { value: "embed", label: "Embed" }]}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 6, md: 2 }}>
              <TextInput label="Subtitle langs" value={subtitleLangs} onChange={(e) => setSubtitleLangs(e.currentTarget.value)} placeholder="en,id" disabled={subtitles === "skip"} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 4 }}>
              <Select label="Cookies from browser" value={cookies} onChange={(v) => setCookies((v as BrowserName) || "")} clearable
                data={[{ value: "", label: "None" }, { value: "chrome", label: "Chrome" }, { value: "firefox", label: "Firefox" }, { value: "edge", label: "Edge" }, { value: "brave", label: "Brave" }]}
              />
            </Grid.Col>
          </Grid>
          <Group gap="lg">
            <Switch label="Embed thumbnail" checked={embedThumbnail} onChange={(e) => setEmbedThumbnail(e.currentTarget.checked)} />
            <Switch label="Embed metadata" checked={embedMetadata} onChange={(e) => setEmbedMetadata(e.currentTarget.checked)} />
          </Group>
          <Divider label="Playlist / channel options" labelPosition="left" />
          <Grid>
            <Grid.Col span={{ base: 4, md: 2 }}>
              <NumberInput label="Start #" value={playlistStart} onChange={setPlaylistStart} min={1} placeholder="1" />
            </Grid.Col>
            <Grid.Col span={{ base: 4, md: 2 }}>
              <NumberInput label="End #" value={playlistEnd} onChange={setPlaylistEnd} min={1} placeholder="20" />
            </Grid.Col>
            <Grid.Col span={{ base: 4, md: 2 }}>
              <NumberInput label="Max items" value={maxItems} onChange={setMaxItems} min={1} placeholder="50" />
            </Grid.Col>
          </Grid>
          <Group>
            <Button leftSection={<IconPlayerPlay size={16} />} onClick={onStart} disabled={running} size="md">Start download</Button>
            <Button variant="light" size="md" onClick={() => setBulkOpen(true)}>Bulk</Button>
            <Button leftSection={<IconPlayerStop size={16} />} onClick={onStop} disabled={!running} color="pink" variant="light" size="md">Stop</Button>
            {running && <Badge color="pink" variant="dot" size="lg">Downloading</Badge>}
          </Group>
        </Stack>
      </Card>

      {probe && <ProbeCard probe={probe} />}

      <Grid>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="xs">
              <Text fw={600}>Progress</Text>
              <Text size="sm" c="dimmed">{fmtBytes(stats.bytes_total)} · {fmtBytes(stats.current_speed)}/s · ETA {fmtEta(stats.current_eta)}</Text>
            </Group>
            <Text size="xs" c="dimmed" mt="sm" mb={4} truncate>{stats.current_filename || "Waiting…"}</Text>
            <Progress value={stats.current_percent} size="md" radius="xl" animated={running} color="pink" />
            <SimpleGrid cols={3} mt="lg">
              <Stat label="Downloaded" value={stats.downloaded} color="cyan" />
              <Stat label="Failed" value={stats.failed} color="red" />
              <Stat label="Total" text={fmtBytes(stats.bytes_total)} color="teal" />
            </SimpleGrid>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Text fw={600} mb="xs">Live log</Text>
            <ScrollArea h={200} type="auto">
              <Stack gap={2}>
                {logs.length === 0 ? <Text size="xs" c="dimmed">// waiting…</Text> : logs.map((l, i) => <Text key={i} size="xs" ff="monospace" c="dimmed">{l}</Text>)}
              </Stack>
            </ScrollArea>
          </Card>
        </Grid.Col>
      </Grid>

      {items.length > 0 && (
        <Card withBorder radius="lg" p={0}>
          <Group justify="space-between" p="md" pb={0}>
            <Text fw={600}>Downloaded files</Text>
            <Badge variant="light">{items.length} file{items.length > 1 ? "s" : ""}</Badge>
          </Group>
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={60}>#</Table.Th>
                <Table.Th>Title</Table.Th>
                <Table.Th w={80}>Duration</Table.Th>
                <Table.Th w={100}>Size</Table.Th>
                <Table.Th w={80}>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((it, i) => (
                <Table.Tr key={i}>
                  <Table.Td>
                    {it.thumbnail ? (
                      <Image src={it.thumbnail} h={28} w={48} fit="cover" radius={2} />
                    ) : (
                      <Text size="xs" c="dimmed">{i + 1}</Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" truncate style={{ maxWidth: 400 }}>{it.title}</Text>
                    <Text size="xs" c="dimmed" ff="monospace" truncate style={{ maxWidth: 400 }}>{it.filename}</Text>
                  </Table.Td>
                  <Table.Td><Text size="xs">{fmtDur(it.duration)}</Text></Table.Td>
                  <Table.Td><Text size="xs">{fmtBytes(it.size)}</Text></Table.Td>
                  <Table.Td>
                    <Badge color={it.status === "done" ? "teal" : "red"} variant="dot" size="sm">{it.status}</Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <BulkUrlModal opened={bulkOpen} onClose={() => setBulkOpen(false)} defaultTool="media" />
    </Stack>
  );
}

function ProbeCard({ probe }: { probe: MediaProbeResponse }) {
  const icon = probe.kind === "video" ? <IconVideo size={16} /> : probe.kind === "playlist" ? <IconList size={16} /> : <IconMusic size={16} />;
  return (
    <Card withBorder radius="lg" p="lg">
      <Group justify="space-between" mb="sm">
        <Group gap="xs">{icon}<Text fw={700}>{probe.title || "(untitled)"}</Text></Group>
        <Badge variant="light" color="pink">{probe.extractor} · {probe.kind}</Badge>
      </Group>
      {probe.uploader && <Text size="sm" c="dimmed">by {probe.uploader}</Text>}
      <Text size="sm" c="dimmed" mb="md">{probe.total} item{probe.total > 1 ? "s" : ""}</Text>
      {probe.entries.length > 0 && (
        <ScrollArea h={160} type="auto">
          <Stack gap={4}>
            {probe.entries.slice(0, 50).map((e, i) => (
              <Group key={e.id} gap="xs" wrap="nowrap">
                <Text size="xs" c="dimmed" w={24}>{i + 1}</Text>
                {e.thumbnail && <Image src={e.thumbnail} h={28} w={48} fit="cover" radius={2} />}
                <Text size="xs" style={{ flex: 1 }} truncate>{e.title}</Text>
                <Text size="xs" c="dimmed">{fmtDur(e.duration)}</Text>
              </Group>
            ))}
          </Stack>
        </ScrollArea>
      )}
    </Card>
  );
}

function Stat({ label, value, color, text }: { label: string; value?: number; color: string; text?: string }) {
  return (
    <div>
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>{label}</Text>
      <Text size="xl" fw={800} c={color}>{text ?? value}</Text>
    </div>
  );
}
