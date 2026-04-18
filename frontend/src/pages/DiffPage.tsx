import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Grid,
  Group,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconArrowsShuffle } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { JobDTO } from "../types";

interface DiffResult {
  type: string;
  job_a: string;
  job_b: string;
  new: Array<{ url: string }>;
  removed: Array<{ url: string }>;
  status_changed?: Array<{ url: string; was: number; now: number }>;
  new_count: number;
  removed_count: number;
  status_changed_count?: number;
  unchanged_count: number;
  total_a: number;
  total_b: number;
}

export default function DiffPage() {
  const { data: jobs } = useQuery({
    queryKey: ["history"],
    queryFn: api.listHistory,
  });

  const [jobA, setJobA] = useState<string | null>(null);
  const [jobB, setJobB] = useState<string | null>(null);
  const [result, setResult] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(false);

  const doneJobs = (jobs || []).filter((j) => j.status === "done");
  const jobOptions = doneJobs.map((j) => ({
    value: j.id,
    label: `${j.type.replace(/_/g, " ")} - ${j.url.slice(0, 50)} (${new Date(j.created_at).toLocaleDateString()})`,
  }));

  const onCompare = async () => {
    if (!jobA || !jobB) return;
    try {
      setLoading(true);
      const r = await fetch(`/api/diff?job_a=${jobA}&job_b=${jobB}`);
      if (!r.ok) throw new Error(await r.text());
      setResult(await r.json());
    } catch (e: any) {
      notifications.show({ title: "Diff failed", message: e.message, color: "red" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Diff / Change Detection</Title>
        <Text c="dimmed" size="sm">
          Compare two job runs to see what changed: new items, removed items, status changes.
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Grid align="flex-end">
          <Grid.Col span={{ base: 12, md: 5 }}>
            <Select
              label="Job A (before)"
              placeholder="Select first job"
              value={jobA}
              onChange={setJobA}
              data={jobOptions}
              searchable
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 5 }}>
            <Select
              label="Job B (after)"
              placeholder="Select second job"
              value={jobB}
              onChange={setJobB}
              data={jobOptions}
              searchable
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 2 }}>
            <Button
              fullWidth
              leftSection={<IconArrowsShuffle size={16} />}
              onClick={onCompare}
              loading={loading}
              disabled={!jobA || !jobB || jobA === jobB}
            >
              Compare
            </Button>
          </Grid.Col>
        </Grid>
      </Card>

      {result && (
        <>
          <SimpleGrid cols={{ base: 2, md: 4 }}>
            <StatCard label="New" value={result.new_count} color="teal" />
            <StatCard label="Removed" value={result.removed_count} color="red" />
            {result.status_changed_count != null && (
              <StatCard label="Status changed" value={result.status_changed_count} color="yellow" />
            )}
            <StatCard label="Unchanged" value={result.unchanged_count} color="gray" />
          </SimpleGrid>

          <Grid>
            {result.new.length > 0 && (
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card withBorder radius="lg" p="lg">
                  <Group justify="space-between" mb="sm">
                    <Text fw={600} c="teal">New items</Text>
                    <Badge color="teal">{result.new_count}</Badge>
                  </Group>
                  <ScrollArea h={250} type="auto">
                    <Stack gap={2}>
                      {result.new.map((item, i) => (
                        <Text key={i} size="xs" ff="monospace" style={{ wordBreak: "break-all" }}>
                          + {item.url}
                        </Text>
                      ))}
                    </Stack>
                  </ScrollArea>
                </Card>
              </Grid.Col>
            )}

            {result.removed.length > 0 && (
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card withBorder radius="lg" p="lg">
                  <Group justify="space-between" mb="sm">
                    <Text fw={600} c="red">Removed items</Text>
                    <Badge color="red">{result.removed_count}</Badge>
                  </Group>
                  <ScrollArea h={250} type="auto">
                    <Stack gap={2}>
                      {result.removed.map((item, i) => (
                        <Text key={i} size="xs" ff="monospace" c="red" style={{ wordBreak: "break-all" }}>
                          - {item.url}
                        </Text>
                      ))}
                    </Stack>
                  </ScrollArea>
                </Card>
              </Grid.Col>
            )}

            {result.status_changed && result.status_changed.length > 0 && (
              <Grid.Col span={12}>
                <Card withBorder radius="lg" p="lg">
                  <Group justify="space-between" mb="sm">
                    <Text fw={600} c="yellow">Status changed</Text>
                    <Badge color="yellow">{result.status_changed_count}</Badge>
                  </Group>
                  <ScrollArea h={200} type="auto">
                    <Stack gap={2}>
                      {result.status_changed.map((item, i) => (
                        <Group key={i} gap="xs" wrap="nowrap">
                          <Badge size="xs" color="gray" variant="light">{item.was}</Badge>
                          <Text size="xs">→</Text>
                          <Badge size="xs" color={item.now >= 400 ? "red" : "teal"} variant="light">{item.now}</Badge>
                          <Text size="xs" ff="monospace" style={{ wordBreak: "break-all" }}>{item.url}</Text>
                        </Group>
                      ))}
                    </Stack>
                  </ScrollArea>
                </Card>
              </Grid.Col>
            )}

            {result.new.length === 0 && result.removed.length === 0 && (!result.status_changed || result.status_changed.length === 0) && (
              <Grid.Col span={12}>
                <Card withBorder radius="lg" p="lg">
                  <Text c="teal" fw={600} ta="center">
                    No changes detected between these two runs.
                  </Text>
                </Card>
              </Grid.Col>
            )}
          </Grid>
        </>
      )}
    </Stack>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <Card withBorder radius="lg" p="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>{label}</Text>
      <Text size="xl" fw={800} c={color}>{value}</Text>
    </Card>
  );
}
