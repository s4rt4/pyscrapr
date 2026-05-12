import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Group,
  Loader,
  SegmentedControl,
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
  IconChevronDown,
  IconChevronRight,
  IconDownload,
  IconMessage,
  IconSearch,
  IconThumbUp,
} from "@tabler/icons-react";
import type { CommentHarvestReport, CommentNode } from "../types";

type SortMode = "newest" | "upvotes" | "depth";

function timeAgo(iso?: string | null): string {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "";
  const diff = Math.max(0, Date.now() - t) / 1000;
  if (diff < 60) return `${Math.floor(diff)} detik lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)} menit lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
  if (diff < 2592000) return `${Math.floor(diff / 86400)} hari lalu`;
  if (diff < 31536000) return `${Math.floor(diff / 2592000)} bulan lalu`;
  return `${Math.floor(diff / 31536000)} tahun lalu`;
}

function sentimentColor(label?: string): string {
  if (label === "positive") return "teal";
  if (label === "negative") return "red";
  if (label === "neutral") return "yellow";
  return "gray";
}

function matchesFilter(node: CommentNode, q: string): boolean {
  if (!q) return true;
  const needle = q.toLowerCase();
  if ((node.author || "").toLowerCase().includes(needle)) return true;
  if ((node.text || "").toLowerCase().includes(needle)) return true;
  return (node.replies || []).some((r) => matchesFilter(r, q));
}

function sortNodes(nodes: CommentNode[], mode: SortMode): CommentNode[] {
  const out = [...nodes];
  if (mode === "newest") {
    out.sort((a, b) => {
      const ta = a.timestamp ? Date.parse(a.timestamp) : 0;
      const tb = b.timestamp ? Date.parse(b.timestamp) : 0;
      return tb - ta;
    });
  } else if (mode === "upvotes") {
    out.sort((a, b) => (b.upvotes || 0) - (a.upvotes || 0));
  } else if (mode === "depth") {
    out.sort((a, b) => (b.replies?.length || 0) - (a.replies?.length || 0));
  }
  return out;
}

function CommentCard({
  node,
  sortMode,
  filterText,
}: {
  node: CommentNode;
  sortMode: SortMode;
  filterText: string;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const hasReplies = (node.replies || []).length > 0;
  const visibleReplies = useMemo(() => {
    const filtered = (node.replies || []).filter((r) => matchesFilter(r, filterText));
    return sortNodes(filtered, sortMode);
  }, [node.replies, sortMode, filterText]);

  const indent = Math.min(node.depth, 6) * 16;

  return (
    <Box style={{ marginLeft: indent }}>
      <Card withBorder radius="md" p="sm" mb="xs">
        <Stack gap={6}>
          <Group justify="space-between" wrap="nowrap" gap="xs">
            <Group gap="xs" wrap="wrap">
              <Badge variant="light" color="cyan" size="sm">
                {node.author || "anonim"}
              </Badge>
              {node.timestamp && (
                <Text size="xs" c="dimmed">
                  {timeAgo(node.timestamp)}
                </Text>
              )}
              {typeof node.upvotes === "number" && (
                <Group gap={2}>
                  <IconThumbUp size={12} />
                  <Text size="xs" c="dimmed">
                    {node.upvotes}
                  </Text>
                </Group>
              )}
              {node.sentiment && (
                <Badge
                  size="xs"
                  variant="light"
                  color={sentimentColor(node.sentiment.label)}
                >
                  {node.sentiment.label} ({Math.round((node.sentiment.confidence || 0) * 100)}%)
                </Badge>
              )}
            </Group>
            {hasReplies && (
              <Tooltip label={collapsed ? "Buka balasan" : "Tutup balasan"}>
                <ActionIcon
                  variant="subtle"
                  size="sm"
                  onClick={() => setCollapsed((c) => !c)}
                >
                  {collapsed ? <IconChevronRight size={14} /> : <IconChevronDown size={14} />}
                </ActionIcon>
              </Tooltip>
            )}
          </Group>
          <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
            {node.text}
          </Text>
          {hasReplies && (
            <Text size="xs" c="dimmed">
              {node.replies.length} balasan
            </Text>
          )}
        </Stack>
      </Card>
      {hasReplies && !collapsed && (
        <Stack gap={0}>
          {visibleReplies.map((r) => (
            <CommentCard
              key={r.id}
              node={r}
              sortMode={sortMode}
              filterText={filterText}
            />
          ))}
        </Stack>
      )}
    </Box>
  );
}

export default function CommentHarvesterPage() {
  const [url, setUrl] = useState("");
  const [maxComments, setMaxComments] = useState(200);
  const [includeReplies, setIncludeReplies] = useState(true);
  const [sentimentEnabled, setSentimentEnabled] = useState(false);

  const [scanning, setScanning] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [progressLog, setProgressLog] = useState<string>("");
  const [report, setReport] = useState<CommentHarvestReport | null>(null);

  const [filterText, setFilterText] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("upvotes");

  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      if (sseRef.current) sseRef.current.close();
    };
  }, []);

  const startScan = async () => {
    if (!url.trim()) return;
    setScanning(true);
    setReport(null);
    setProgressLog("Memulai...");

    try {
      const r = await fetch("/api/comment/harvest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          max_comments: maxComments,
          include_replies: includeReplies,
          sentiment_enabled: sentimentEnabled,
        }),
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }
      const data = await r.json();
      setJobId(data.job_id);
      subscribeSSE(data.job_id);
    } catch (e: any) {
      setScanning(false);
      notifications.show({
        title: "Scan gagal",
        message: e?.message || "Tidak dapat memulai scan",
        color: "red",
      });
    }
  };

  const subscribeSSE = (id: string) => {
    if (sseRef.current) sseRef.current.close();
    const es = new EventSource(`/api/comment/harvest/events/${id}`);
    sseRef.current = es;
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "log" && data.message) {
          setProgressLog(data.message);
        } else if (data.type === "progress" && data.stage === "sentiment") {
          setProgressLog(`Sentimen: ${data.processed}/${data.total}`);
        } else if (data.type === "done") {
          es.close();
          sseRef.current = null;
          fetchReport(id);
        } else if (data.type === "error") {
          es.close();
          sseRef.current = null;
          setScanning(false);
          notifications.show({
            title: "Harvest error",
            message: data.message || "Unknown error",
            color: "red",
          });
        }
      } catch {
        // ignore
      }
    };
    es.onerror = () => {
      es.close();
      sseRef.current = null;
      if (jobId) fetchReport(jobId);
    };
  };

  const fetchReport = async (id: string) => {
    try {
      const r = await fetch(`/api/comment/harvest/${id}`);
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      if (data.report) {
        setReport(data.report as CommentHarvestReport);
      }
      if (data.error_message) {
        notifications.show({
          title: "Job error",
          message: data.error_message,
          color: "red",
        });
      }
    } catch (e: any) {
      notifications.show({
        title: "Gagal ambil report",
        message: e?.message || "",
        color: "red",
      });
    } finally {
      setScanning(false);
    }
  };

  const visibleTopLevel = useMemo(() => {
    if (!report) return [];
    const filtered = (report.comments || []).filter((c) => matchesFilter(c, filterText));
    return sortNodes(filtered, sortMode);
  }, [report, filterText, sortMode]);

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconMessage size={26} />
          <Title order={2}>Comment Harvester</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Tarik komentar + pohon balasan dari YouTube, Reddit, atau forum
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="sm">
          <Group align="flex-end" wrap="wrap">
            <TextInput
              label="URL target"
              placeholder="https://www.youtube.com/watch?v=... atau https://reddit.com/r/.../comments/..."
              value={url}
              onChange={(e) => setUrl(e.currentTarget.value)}
              onKeyDown={(e) => e.key === "Enter" && !scanning && startScan()}
              style={{ flex: 1, minWidth: 280 }}
              disabled={scanning}
            />
            <Button
              color="grape"
              leftSection={<IconSearch size={16} />}
              onClick={startScan}
              loading={scanning}
              disabled={!url.trim()}
            >
              Scan
            </Button>
          </Group>

          <Box>
            <Group justify="space-between">
              <Text size="sm">Maksimum komentar: {maxComments}</Text>
            </Group>
            <Slider
              value={maxComments}
              onChange={setMaxComments}
              min={50}
              max={2000}
              step={50}
              marks={[
                { value: 100, label: "100" },
                { value: 500, label: "500" },
                { value: 1000, label: "1k" },
                { value: 2000, label: "2k" },
              ]}
              disabled={scanning}
            />
          </Box>

          <Group>
            <Switch
              label="Sertakan balasan"
              checked={includeReplies}
              onChange={(e) => setIncludeReplies(e.currentTarget.checked)}
              disabled={scanning}
            />
            <Switch
              label="Skor sentimen (Ollama, lebih lambat)"
              checked={sentimentEnabled}
              onChange={(e) => setSentimentEnabled(e.currentTarget.checked)}
              disabled={scanning}
            />
          </Group>
        </Stack>
      </Card>

      {scanning && (
        <Card withBorder radius="lg" p="md">
          <Group gap="sm">
            <Loader color="grape" size="sm" />
            <Text size="sm" c="dimmed">
              {progressLog || "Mengambil komentar..."}
            </Text>
          </Group>
        </Card>
      )}

      {report && !scanning && (
        <Stack gap="md">
          <Card withBorder radius="lg" p="md">
            <Group justify="space-between" wrap="wrap">
              <Group gap="xs" wrap="wrap">
                <Badge color="grape" size="lg" variant="light">
                  {report.platform}
                </Badge>
                <Badge color="cyan" size="lg" variant="light">
                  {report.total_comments} komentar
                </Badge>
                <Badge color="blue" size="lg" variant="light">
                  {report.total_replies} balasan
                </Badge>
                <Badge color="gray" size="lg" variant="light">
                  kedalaman maks: {report.max_depth}
                </Badge>
                {report.sentiment_summary && (
                  <>
                    <Badge color="teal" size="lg" variant="light">
                      + {report.sentiment_summary.positive}
                    </Badge>
                    <Badge color="yellow" size="lg" variant="light">
                      ~ {report.sentiment_summary.neutral}
                    </Badge>
                    <Badge color="red" size="lg" variant="light">
                      − {report.sentiment_summary.negative}
                    </Badge>
                  </>
                )}
              </Group>
              {jobId && (
                <Button
                  variant="light"
                  size="xs"
                  leftSection={<IconDownload size={14} />}
                  component="a"
                  href={`/api/comment/harvest/export/${jobId}.csv`}
                >
                  Ekspor CSV
                </Button>
              )}
            </Group>
            {report.title && (
              <Text size="sm" c="dimmed" mt={6}>
                {report.title}
              </Text>
            )}
          </Card>

          <Card withBorder radius="lg" p="md">
            <Group justify="space-between" wrap="wrap">
              <TextInput
                placeholder="Filter berdasarkan author atau teks..."
                value={filterText}
                onChange={(e) => setFilterText(e.currentTarget.value)}
                style={{ flex: 1, minWidth: 220 }}
              />
              <SegmentedControl
                value={sortMode}
                onChange={(v) => setSortMode(v as SortMode)}
                data={[
                  { value: "upvotes", label: "Terbanyak upvote" },
                  { value: "newest", label: "Terbaru" },
                  { value: "depth", label: "Banyak balasan" },
                ]}
              />
            </Group>
          </Card>

          {visibleTopLevel.length === 0 ? (
            <Card withBorder radius="lg" p="lg">
              <Text c="dimmed" ta="center">
                Tidak ada komentar untuk ditampilkan.
              </Text>
            </Card>
          ) : (
            <Stack gap={0}>
              {visibleTopLevel.map((c) => (
                <CommentCard
                  key={c.id}
                  node={c}
                  sortMode={sortMode}
                  filterText={filterText}
                />
              ))}
            </Stack>
          )}
        </Stack>
      )}
    </Stack>
  );
}
