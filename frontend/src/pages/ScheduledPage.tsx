import { useEffect, useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Modal,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconClock, IconPlus, IconTrash } from "@tabler/icons-react";

interface Schedule {
  id: string;
  tool: string;
  url: string;
  cron: string;
  label: string;
  enabled: boolean;
  last_run: string | null;
  runs: number;
  created_at: string;
}

const TOOL_COLOR: Record<string, string> = {
  harvester: "cyan",
  mapper: "violet",
  ripper: "teal",
  media: "pink",
};

export default function ScheduledPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [createOpen, setCreateOpen] = useState(false);

  // Create form
  const [tool, setTool] = useState<string>("harvester");
  const [url, setUrl] = useState("");
  const [cron, setCron] = useState("0 3 * * *");
  const [label, setLabel] = useState("");

  const refresh = () =>
    fetch("/api/scheduled/list")
      .then((r) => r.json())
      .then(setSchedules)
      .catch((e) => console.error(e));

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  const onCreate = async () => {
    try {
      const r = await fetch("/api/scheduled/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool, url, cron, label, config: {} }),
      });
      if (!r.ok) throw new Error(await r.text());
      notifications.show({ title: "Created", message: "Schedule added", color: "teal" });
      setCreateOpen(false);
      setUrl("");
      setLabel("");
      refresh();
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    }
  };

  const onDelete = async (id: string) => {
    await fetch(`/api/scheduled/${id}`, { method: "DELETE" });
    refresh();
  };

  const onToggle = async (id: string, enabled: boolean) => {
    await fetch(`/api/scheduled/${id}/toggle?enabled=${enabled}`, { method: "POST" });
    refresh();
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Scheduled Jobs</Title>
          <Text c="dimmed" size="sm">
            Automate recurring scraping/download tasks with cron schedules.
          </Text>
        </div>
        <Button leftSection={<IconPlus size={16} />} onClick={() => setCreateOpen(true)}>
          New schedule
        </Button>
      </Group>

      <Card withBorder radius="lg" p={0}>
        <Table striped highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Tool</Table.Th>
              <Table.Th>Label / URL</Table.Th>
              <Table.Th>Cron</Table.Th>
              <Table.Th>Runs</Table.Th>
              <Table.Th>Last run</Table.Th>
              <Table.Th>Enabled</Table.Th>
              <Table.Th w={50}></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {schedules.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text c="dimmed" size="sm">
                    No schedules yet. Click "New schedule" to create one.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
            {schedules.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td>
                  <Badge color={TOOL_COLOR[s.tool] || "gray"} variant="light" size="sm">
                    {s.tool}
                  </Badge>
                </Table.Td>
                <Table.Td style={{ maxWidth: 300 }}>
                  <Text size="sm" fw={600} truncate>
                    {s.label}
                  </Text>
                  <Text size="xs" c="dimmed" truncate>
                    {s.url}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="outline" color="gray" size="sm" ff="monospace">
                    <IconClock size={10} style={{ marginRight: 4 }} />
                    {s.cron}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{s.runs}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {s.last_run ? new Date(s.last_run).toLocaleString() : "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Switch
                    checked={s.enabled}
                    onChange={(e) => onToggle(s.id, e.currentTarget.checked)}
                    size="xs"
                  />
                </Table.Td>
                <Table.Td>
                  <Tooltip label="Delete">
                    <ActionIcon variant="subtle" color="red" size="sm" onClick={() => onDelete(s.id)} aria-label="Delete schedule">
                      <IconTrash size={14} />
                    </ActionIcon>
                  </Tooltip>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal opened={createOpen} onClose={() => setCreateOpen(false)} title="New scheduled job" centered>
        <Stack gap="md">
          <Select
            label="Tool"
            value={tool}
            onChange={(v) => setTool(v || "harvester")}
            data={[
              { value: "harvester", label: "Image Harvester" },
              { value: "mapper", label: "URL Mapper" },
              { value: "ripper", label: "Site Ripper" },
              { value: "media", label: "Media Downloader" },
            ]}
          />
          <TextInput label="URL" value={url} onChange={(e) => setUrl(e.currentTarget.value)} placeholder="https://example.com" />
          <TextInput
            label="Cron expression"
            value={cron}
            onChange={(e) => setCron(e.currentTarget.value)}
            placeholder="0 3 * * *"
            description="minute hour day month weekday — e.g. '0 3 * * *' = daily 3am, '0 */6 * * *' = every 6h"
          />
          <TextInput label="Label (optional)" value={label} onChange={(e) => setLabel(e.currentTarget.value)} placeholder="Daily image harvest" />
          <Button onClick={onCreate}>Create schedule</Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
