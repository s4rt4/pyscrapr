import { ActionIcon, Badge, Button, Card, Group, Menu, Stack, Table, Text, Title, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDownload, IconRefresh } from "@tabler/icons-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { timeAgo } from "../lib/utils";
import type { JobStatus } from "../types";

const statusColor: Record<JobStatus, string> = {
  pending: "gray",
  running: "cyan",
  done: "teal",
  error: "red",
  stopped: "yellow",
};

const TYPE_COLOR: Record<string, string> = {
  image_harvester: "cyan",
  url_mapper: "violet",
  site_ripper: "teal",
  media_downloader: "pink",
  ai_tagging: "grape",
};

export default function HistoryPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["history"],
    queryFn: api.listHistory,
    refetchInterval: 3000,
  });

  const onRerun = async (jobId: string) => {
    try {
      const res = await fetch(`/api/history/rerun/${jobId}`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const d = await res.json();
      notifications.show({
        title: "Re-run started",
        message: `New job: ${d.job_id.slice(0, 8)}…`,
        color: "cyan",
      });
      queryClient.invalidateQueries({ queryKey: ["history"] });
    } catch (e: any) {
      notifications.show({ title: "Re-run failed", message: e.message, color: "red" });
    }
  };

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>History</Title>
        <Text c="dimmed" size="sm">
          All past and running jobs across every tool.
        </Text>
      </div>

      <Card withBorder radius="lg" p={0}>
        <Table striped highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Type</Table.Th>
              <Table.Th>URL</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Downloaded</Table.Th>
              <Table.Th>Created</Table.Th>
              <Table.Th w={50}></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text c="dimmed" size="sm">Loading…</Text>
                </Table.Td>
              </Table.Tr>
            )}
            {data?.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Stack align="center" py="xl" gap="sm">
                    <Text c="dimmed" size="sm">No jobs yet.</Text>
                    <Button component="a" href="/harvester" variant="light" size="xs">Start your first harvest</Button>
                  </Stack>
                </Table.Td>
              </Table.Tr>
            )}
            {data?.map((job) => (
              <Table.Tr key={job.id}>
                <Table.Td>
                  <Badge variant="light" color={TYPE_COLOR[job.type] || "gray"} size="sm">
                    {job.type.replace(/_/g, " ")}
                  </Badge>
                </Table.Td>
                <Table.Td style={{ maxWidth: 350, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  <Text size="sm">{job.url}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={statusColor[job.status]} variant="dot">
                    {job.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">
                    {(job.stats as any)?.downloaded ?? (job.stats as any)?.pages ?? (job.stats as any)?.tagged ?? 0}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {timeAgo(job.created_at)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Group gap={4} wrap="nowrap">
                    <Menu shadow="sm" width={130} position="bottom-end">
                      <Menu.Target>
                        <ActionIcon variant="subtle" color="teal" size="sm" disabled={job.status !== "done"} aria-label="Export">
                          <IconDownload size={14} />
                        </ActionIcon>
                      </Menu.Target>
                      <Menu.Dropdown>
                        <Menu.Item component="a" href={`/api/export/${job.id}?format=csv`}>CSV</Menu.Item>
                        <Menu.Item component="a" href={`/api/export/${job.id}?format=json`}>JSON</Menu.Item>
                        <Menu.Item component="a" href={`/api/export/${job.id}?format=xlsx`}>Excel</Menu.Item>
                      </Menu.Dropdown>
                    </Menu>
                    <Tooltip label="Re-run with same config">
                      <ActionIcon
                        variant="subtle"
                        color="cyan"
                        size="sm"
                        onClick={() => onRerun(job.id)}
                        disabled={job.status === "running" || job.status === "pending"}
                        aria-label="Re-run job"
                      >
                        <IconRefresh size={14} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Stack>
  );
}
