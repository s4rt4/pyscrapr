import { ActionIcon, Badge, Button, Card, Group, Menu, Skeleton, Stack, Table, Text, Title, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDownload, IconHistory, IconRefresh, IconTrash } from "@tabler/icons-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
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
  const navigate = useNavigate();
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

  const onDelete = async (jobId: string, jobUrl: string) => {
    const shortUrl = jobUrl.length > 60 ? jobUrl.slice(0, 60) + "..." : jobUrl;
    if (!window.confirm(`Hapus job ini?\n\n${shortUrl}\n\nAksi ini tidak bisa di-undo.`)) {
      return;
    }
    try {
      const res = await fetch(`/api/history/${jobId}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      notifications.show({
        title: "Job dihapus",
        message: `${jobId.slice(0, 8)}…`,
        color: "teal",
      });
      queryClient.invalidateQueries({ queryKey: ["history"] });
    } catch (e: any) {
      notifications.show({ title: "Hapus gagal", message: e.message, color: "red" });
    }
  };

  const onClearAllDone = async () => {
    if (!window.confirm("Hapus SEMUA job dengan status 'done'?\n\nAksi ini tidak bisa di-undo.")) {
      return;
    }
    try {
      const res = await fetch(`/api/history?status=done`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const d = await res.json();
      notifications.show({
        title: "Bulk delete sukses",
        message: `${d.deleted_count} job dihapus`,
        color: "teal",
      });
      queryClient.invalidateQueries({ queryKey: ["history"] });
    } catch (e: any) {
      notifications.show({ title: "Bulk delete gagal", message: e.message, color: "red" });
    }
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>History</Title>
          <Text c="dimmed" size="sm">
            All past and running jobs across every tool.
          </Text>
        </div>
        <Tooltip label="Hapus semua job dengan status done">
          <Button
            variant="subtle"
            color="red"
            size="xs"
            leftSection={<IconTrash size={14} />}
            onClick={onClearAllDone}
            disabled={!data || data.length === 0}
          >
            Hapus semua done
          </Button>
        </Tooltip>
      </Group>

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
                  <Stack gap="xs">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} height={40} radius="sm" />
                    ))}
                  </Stack>
                </Table.Td>
              </Table.Tr>
            )}
            {!isLoading && data?.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Stack align="center" py="xl" gap="sm">
                    <IconHistory size={48} color="var(--mantine-color-dimmed)" />
                    <Text fw={600}>Belum ada job</Text>
                    <Text c="dimmed" size="sm" ta="center">
                      Mulai dengan menjalankan Image Harvester, URL Mapper, atau tool lain.
                    </Text>
                    <Button variant="light" size="xs" onClick={() => navigate("/harvester")}>
                      Ke Harvester
                    </Button>
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
                    <Tooltip label="Hapus job">
                      <ActionIcon
                        variant="subtle"
                        color="red"
                        size="sm"
                        onClick={() => onDelete(job.id, job.url)}
                        disabled={job.status === "running"}
                        aria-label="Hapus job"
                      >
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
    </Stack>
  );
}
