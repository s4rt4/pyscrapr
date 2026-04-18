import { notifyDone, notifyError } from "../lib/notify";
import { useEffect, useRef, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Image,
  Progress,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  TagsInput,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconBrain,
  IconPlayerPlay,
  IconPlayerStop,
  IconTag,
} from "@tabler/icons-react";

import { api, subscribeAIEvents } from "../lib/api";
import type { JobDTO, TaggingResponse, TagResult } from "../types";

const DEFAULT_LABELS = ["logo", "hero image", "product", "icon", "background", "portrait", "food", "text"];

export default function AIToolsPage() {
  const [harvesterJobs, setHarvesterJobs] = useState<JobDTO[]>([]);
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [labels, setLabels] = useState<string[]>(DEFAULT_LABELS);

  const [jobId, setJobId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0, filename: "", topTag: "" });
  const [results, setResults] = useState<TaggingResponse | null>(null);
  const [filterTag, setFilterTag] = useState<string | null>(null);

  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => {
    api.listHarvesterJobs().then(setHarvesterJobs).catch((e) => console.error(e));
    return () => sseRef.current?.close();
  }, []);

  const onStart = async () => {
    if (!selectedJob || labels.length === 0) {
      notifications.show({ title: "Missing", message: "Select a job and add labels", color: "yellow" });
      return;
    }
    setResults(null);
    setProgress({ done: 0, total: 0, filename: "", topTag: "" });
    try {
      setRunning(true);
      const res = await api.startTagging(selectedJob, labels);
      setJobId(res.job_id);

      sseRef.current?.close();
      const source = subscribeAIEvents(res.job_id);
      source.onmessage = (msg) => {
        try {
          const e = JSON.parse(msg.data);
          handleEvent(e, res.job_id);
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
    if (jobId) await api.stopTagging(jobId);
  };

  const handleEvent = (e: any, currentJobId: string) => {
    switch (e.type) {
      case "log":
        break;
      case "progress":
        setProgress({
          done: e.done || 0,
          total: e.total || 0,
          filename: e.filename || "",
          topTag: e.top_tag || "",
        });
        break;
      case "done":
        setRunning(false);
        notifyDone("AI tagging complete");
        api.getTaggingResults(currentJobId).then(setResults).catch((e) => console.error(e));
        break;
      case "stopped":
        setRunning(false);
        break;
      case "error":
        setRunning(false);
        notifications.show({ title: "Error", message: e.message, color: "red" });
        break;
    }
  };

  const pct = progress.total > 0 ? (progress.done / progress.total) * 100 : 0;
  const displayResults = results?.results || [];
  const filtered = filterTag
    ? displayResults.filter((r) => r.top_tag === filterTag)
    : displayResults;

  const tagCounts: Record<string, number> = {};
  for (const r of displayResults) {
    if (r.top_tag) tagCounts[r.top_tag] = (tagCounts[r.top_tag] || 0) + 1;
  }

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>AI Tools</Title>
        <Text c="dimmed" size="sm">
          Auto-tag harvested images using CLIP zero-shot classification.
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Select
            label="Select Image Harvester job"
            placeholder="Pick a completed harvester job"
            value={selectedJob}
            onChange={setSelectedJob}
            data={harvesterJobs.map((j) => ({
              value: j.id,
              label: `${j.url} - ${(j.stats as any)?.downloaded || "?"} images (${new Date(j.created_at).toLocaleDateString()})`,
            }))}
          />
          {harvesterJobs.length === 0 && !running && (
            <Text size="sm" c="dimmed">No Image Harvester jobs found. <a href="/harvester">Run one first</a> to get images for tagging.</Text>
          )}
          <TagsInput
            label="Labels for classification"
            description="Type a label and press Enter. CLIP will score each image against all labels."
            placeholder="Add tag…"
            value={labels}
            onChange={setLabels}
          />
          <Group>
            <Button leftSection={<IconPlayerPlay size={16} />} onClick={onStart} disabled={running} size="md">
              Start tagging
            </Button>
            <Button leftSection={<IconPlayerStop size={16} />} onClick={onStop} disabled={!running} color="pink" variant="light" size="md">
              Stop
            </Button>
            {running && <Badge color="grape" variant="dot" size="lg">Tagging</Badge>}
          </Group>
        </Stack>
      </Card>

      {(running || results) && (
        <Card withBorder radius="lg" p="lg">
          <Group justify="space-between" mb="xs">
            <Text fw={600}>Progress</Text>
            <Text size="sm" c="dimmed">
              {progress.done} / {progress.total}
            </Text>
          </Group>
          <Progress value={pct} size="md" radius="xl" animated={running} color="grape" />
          {progress.filename && (
            <Text size="xs" c="dimmed" mt="xs" truncate>
              {progress.filename} → <Badge size="xs" color="grape" variant="light">{progress.topTag}</Badge>
            </Text>
          )}
        </Card>
      )}

      {displayResults.length > 0 && (
        <>
          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="md">
              <Text fw={600}>Tag distribution</Text>
              <Badge variant="light">{displayResults.length} images tagged</Badge>
            </Group>
            <Group gap="xs">
              <Badge
                color={filterTag === null ? "grape" : "gray"}
                variant={filterTag === null ? "filled" : "light"}
                style={{ cursor: "pointer" }}
                onClick={() => setFilterTag(null)}
              >
                All ({displayResults.length})
              </Badge>
              {Object.entries(tagCounts)
                .sort(([, a], [, b]) => b - a)
                .map(([tag, count]) => (
                  <Badge
                    key={tag}
                    color={filterTag === tag ? "grape" : "gray"}
                    variant={filterTag === tag ? "filled" : "light"}
                    style={{ cursor: "pointer" }}
                    onClick={() => setFilterTag(filterTag === tag ? null : tag)}
                  >
                    {tag} ({count})
                  </Badge>
                ))}
            </Group>
          </Card>

          <Card withBorder radius="lg" p="lg">
            <Text fw={600} mb="md">
              Results {filterTag ? `- filtered: "${filterTag}"` : ""}
            </Text>
            <SimpleGrid cols={{ base: 2, sm: 3, md: 4, lg: 6 }} spacing="xs">
              {filtered.map((r, i) => (
                <ImageTagCard key={i} result={r} labels={labels} />
              ))}
            </SimpleGrid>
          </Card>
        </>
      )}
    </Stack>
  );
}

function ImageTagCard({ result, labels }: { result: TagResult; labels: string[] }) {
  const sorted = Object.entries(result.scores).sort(([, a], [, b]) => b - a);
  return (
    <Card withBorder radius="md" p="xs">
      <Image
        src={result.path}
        h={120}
        fit="cover"
        radius="sm"
        fallbackSrc="data:image/svg+xml;base64,PHN2Zy8+"
      />
      <Group mt={6} gap={4} wrap="nowrap">
        <IconTag size={12} />
        <Text size="xs" fw={700} truncate>
          {result.top_tag}
        </Text>
        <Text size="xs" c="dimmed">
          {(result.top_score * 100).toFixed(0)}%
        </Text>
      </Group>
      <ScrollArea h={50} type="auto" mt={4}>
        {sorted.slice(0, 5).map(([tag, score]) => (
          <Group key={tag} gap={4} wrap="nowrap">
            <Progress
              value={score * 100}
              size="xs"
              style={{ flex: 1, minWidth: 40 }}
              color={tag === result.top_tag ? "grape" : "gray"}
            />
            <Text size={9} c="dimmed" style={{ minWidth: 60 }} truncate>
              {tag}
            </Text>
          </Group>
        ))}
      </ScrollArea>
    </Card>
  );
}
