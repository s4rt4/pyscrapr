import { useEffect, useState } from "react";
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Code,
  Grid,
  Group,
  JsonInput,
  Modal,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import Editor from "@monaco-editor/react";
import {
  IconAlertTriangle,
  IconCode,
  IconDeviceFloppy,
  IconPlayerPlay,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";
import { timeAgo } from "../lib/utils";

interface Pipeline {
  id: string;
  name: string;
  description: string;
  code: string;
  enabled: boolean;
  auto_run_on?: string[];
}

const JOB_TYPES = [
  { value: "image_harvester", label: "Image Harvester" },
  { value: "url_mapper", label: "URL Mapper" },
  { value: "site_ripper", label: "Site Ripper" },
  { value: "media_downloader", label: "Media Downloader" },
];

const DEFAULT_CODE = `# Custom pipeline - transforms scraped data
# Variables available:
#   data       - list of dicts from job (or sample_data)
#   url        - original job URL
#   job_id     - job ID
#   re, json, datetime, math, statistics (pre-imported)
#
# Output: modify 'data' in place, or assign to 'output' for different shape
# print() output captured in logs panel

# Example: keep only large images and normalize URLs
for item in data:
    if "url" in item:
        item["url"] = item["url"].strip().lower()

# Filter: keep only items with size > 50KB
data = [d for d in data if (d.get("size_bytes") or 0) > 50000]

print(f"Kept {len(data)} items after filtering")
`;

const PRESET_SNIPPETS: Record<string, string> = {
  "filter_size": `# Keep only items larger than 50KB
data = [d for d in data if (d.get("size_bytes") or 0) > 50000]
print(f"Kept {len(data)} items")`,

  "regex_clean": `# Strip tracking params from URLs with regex
import re
for item in data:
    if "url" in item:
        item["url"] = re.sub(r"[?&](utm_\\w+|fbclid|gclid)=[^&]*", "", item["url"])`,

  "extract_domain": `# Add domain column parsed from URL
from urllib.parse import urlparse
for item in data:
    if "url" in item:
        item["domain"] = urlparse(item["url"]).netloc`,

  "aggregate_stats": `# Summary stats instead of per-item list
total_size = sum(d.get("size_bytes") or 0 for d in data)
by_kind = {}
for d in data:
    k = d.get("kind", "unknown")
    by_kind[k] = by_kind.get(k, 0) + 1
output = {
    "total_items": len(data),
    "total_bytes": total_size,
    "total_mb": round(total_size / 1048576, 2),
    "by_kind": by_kind,
}`,
};

export default function PipelinePage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Pipeline | null>(null);

  // Editor form
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [code, setCode] = useState(DEFAULT_CODE);
  const [enabled, setEnabled] = useState(true);
  const [autoRunOn, setAutoRunOn] = useState<string[]>([]);
  const [preset, setPreset] = useState<string | null>(null);

  // Run panel
  const [jobId, setJobId] = useState("");
  const [sampleData, setSampleData] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);

  const refresh = () => {
    fetch("/api/pipeline")
      .then((r) => r.json())
      .then(setPipelines)
      .catch((e) => console.error(e));
  };

  useEffect(refresh, []);

  const openNew = () => {
    setEditing(null);
    setName("");
    setDescription("");
    setCode(DEFAULT_CODE);
    setEnabled(true);
    setAutoRunOn([]);
    setModalOpen(true);
  };

  const openEdit = (p: Pipeline) => {
    setEditing(p);
    setName(p.name);
    setDescription(p.description);
    setCode(p.code);
    setEnabled(p.enabled);
    setAutoRunOn(p.auto_run_on || []);
    setModalOpen(true);
  };

  const onSave = async () => {
    try {
      const body = JSON.stringify({ name, description, code, enabled, auto_run_on: autoRunOn });
      const url = editing ? `/api/pipeline/${editing.id}` : "/api/pipeline";
      const method = editing ? "PUT" : "POST";
      const r = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body });
      if (!r.ok) throw new Error(await r.text());
      notifications.show({ title: "Saved", message: name, color: "teal" });
      setModalOpen(false);
      refresh();
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    }
  };

  const onDelete = async (p: Pipeline) => {
    if (!window.confirm(`Delete pipeline "${p.name}"?`)) return;
    await fetch(`/api/pipeline/${p.id}`, { method: "DELETE" });
    refresh();
  };

  const onRun = async () => {
    try {
      setRunning(true);
      setResult(null);
      let sd;
      if (sampleData.trim()) {
        try {
          sd = JSON.parse(sampleData);
        } catch {
          notifications.show({ title: "Invalid JSON", message: "Sample data must be valid JSON array", color: "red" });
          setRunning(false);
          return;
        }
      }
      const body = JSON.stringify({
        code,
        job_id: jobId.trim() || null,
        sample_data: sd,
      });
      const r = await fetch("/api/pipeline/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      const d = await r.json();
      setResult(d);
      if (d.success) {
        notifications.show({ title: "Pipeline ran", message: `Output type: ${d.output_type}`, color: "teal" });
      }
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setRunning(false);
    }
  };

  const applyPreset = (key: string | null) => {
    setPreset(key);
    if (key && PRESET_SNIPPETS[key]) {
      setCode(PRESET_SNIPPETS[key]);
    }
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Custom Pipeline</Title>
          <Text c="dimmed" size="sm">
            Write Python snippets to transform scraped data before storage/export.
          </Text>
        </div>
        <Button leftSection={<IconPlus size={16} />} onClick={openNew}>
          New pipeline
        </Button>
      </Group>

      <Alert icon={<IconAlertTriangle size={16} />} color="yellow" variant="light">
        <Text size="sm" fw={600}>⚠️ Only run code you trust</Text>
        <Text size="xs">
          Scripts execute with full Python access (no sandbox). Don't paste untrusted code.
          For personal/offline use only.
        </Text>
      </Alert>

      <Card withBorder radius="lg" p={0}>
        <Table striped highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Description</Table.Th>
              <Table.Th w={80}>Enabled</Table.Th>
              <Table.Th w={120}>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {pipelines.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={4}>
                  <Text c="dimmed" size="sm" ta="center" py="md">
                    No pipelines yet. Click "New pipeline" to create one.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
            {pipelines.map((p) => (
              <Table.Tr key={p.id}>
                <Table.Td>
                  <Group gap="xs">
                    <IconCode size={14} color="var(--mantine-color-cyan-5)" />
                    <Text fw={600} size="sm">{p.name}</Text>
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed" truncate style={{ maxWidth: 400 }}>
                    {p.description || <em>No description</em>}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={p.enabled ? "teal" : "gray"} variant="light" size="sm">
                    {p.enabled ? "enabled" : "disabled"}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    <Tooltip label="Edit">
                      <ActionIcon variant="subtle" color="cyan" size="sm" onClick={() => openEdit(p)} aria-label="Edit pipeline">
                        <IconCode size={14} />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Delete">
                      <ActionIcon variant="subtle" color="red" size="sm" onClick={() => onDelete(p)} aria-label="Delete pipeline">
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Editor Modal */}
      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit pipeline: ${editing.name}` : "New pipeline"}
        size="90%"
        centered
      >
        <Stack gap="md">
          <Grid>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <TextInput
                label="Name"
                value={name}
                onChange={(e) => setName(e.currentTarget.value)}
                placeholder="Filter large images"
                required
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Select
                label="Load preset snippet"
                value={preset}
                onChange={applyPreset}
                data={[
                  { value: "filter_size", label: "Filter by size" },
                  { value: "regex_clean", label: "RegEx: strip tracking params" },
                  { value: "extract_domain", label: "Extract domain from URL" },
                  { value: "aggregate_stats", label: "Aggregate to summary stats" },
                ]}
                placeholder="Select a preset…"
                clearable
              />
            </Grid.Col>
          </Grid>

          <TextInput
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
            placeholder="What does this pipeline do?"
          />

          <div>
            <Text size="sm" fw={600} mb={4}>Python code</Text>
            <div style={{ border: "1px solid var(--mantine-color-default-border)", borderRadius: 8, overflow: "hidden" }}>
              <Editor
                height="400px"
                language="python"
                theme="vs-dark"
                value={code}
                onChange={(v) => setCode(v || "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  tabSize: 4,
                  wordWrap: "on",
                }}
              />
            </div>
          </div>

          <Group align="flex-start">
            <Switch
              label="Enabled"
              checked={enabled}
              onChange={(e) => setEnabled(e.currentTarget.checked)}
            />
            <Select
              label="Auto-run on job type"
              description="Pipeline runs automatically when a matching job completes"
              value={autoRunOn[0] || null}
              onChange={(v) => setAutoRunOn(v ? [v] : [])}
              data={JOB_TYPES}
              placeholder="Never auto-run (manual only)"
              clearable
              style={{ flex: 1 }}
            />
          </Group>

          {/* Run Panel */}
          <Card withBorder radius="md" p="md">
            <Text fw={600} mb="xs">Test run</Text>
            <Group grow align="flex-start">
              <TextInput
                label="Job ID (optional)"
                description="Run against a completed job's data"
                value={jobId}
                onChange={(e) => setJobId(e.currentTarget.value)}
                placeholder="e.g. abc-123-..."
              />
              <Textarea
                label="Or paste sample data (JSON array)"
                value={sampleData}
                onChange={(e) => setSampleData(e.currentTarget.value)}
                placeholder='[{"url": "...", "size_bytes": 100000}]'
                autosize
                minRows={2}
                maxRows={5}
                styles={{ input: { fontFamily: "monospace", fontSize: 11 } }}
              />
            </Group>
            <Button
              mt="sm"
              size="xs"
              leftSection={<IconPlayerPlay size={14} />}
              onClick={onRun}
              loading={running}
            >
              Run
            </Button>

            {result && (
              <Stack gap="xs" mt="md">
                {result.success ? (
                  <>
                    <Group gap="xs">
                      <Badge color="teal" variant="light">Success</Badge>
                      <Text size="xs" c="dimmed">
                        Type: {result.output_type} · Count: {result.output_count ?? "-"}
                      </Text>
                    </Group>
                    <JsonInput
                      value={JSON.stringify(result.output, null, 2)}
                      autosize
                      minRows={4}
                      maxRows={15}
                      readOnly
                      formatOnBlur
                      styles={{ input: { fontFamily: "monospace", fontSize: 11 } }}
                    />
                  </>
                ) : (
                  <Alert color="red" variant="light" icon={<IconAlertTriangle size={16} />}>
                    <Text size="sm" fw={600}>{result.error}</Text>
                    {result.traceback && (
                      <Code block style={{ fontSize: 11, maxHeight: 150, overflow: "auto", marginTop: 8 }}>
                        {result.traceback}
                      </Code>
                    )}
                  </Alert>
                )}
                {result.logs && (
                  <>
                    <Text size="xs" c="dimmed">print() output:</Text>
                    <Code block style={{ fontSize: 11, maxHeight: 100, overflow: "auto" }}>{result.logs}</Code>
                  </>
                )}
              </Stack>
            )}
          </Card>

          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button leftSection={<IconDeviceFloppy size={16} />} onClick={onSave}>
              {editing ? "Update" : "Create"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
