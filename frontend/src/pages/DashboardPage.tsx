import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Progress,
  RingProgress,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconBrain,
  IconDownload,
  IconMovie,
  IconPhoto,
  IconSitemap,
} from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { timeAgo } from "../lib/utils";

interface DashboardData {
  jobs_by_type: Record<string, { total: number; done: number; error: number; running: number }>;
  recent_jobs: Array<{
    id: string;
    type: string;
    url: string;
    status: string;
    created_at: string;
    stats: Record<string, any>;
  }>;
  disk: {
    downloads_bytes: number;
    data_bytes: number;
    disk_free_gb: number;
    disk_total_gb: number;
  };
}

const TOOLS = [
  { key: "image_harvester", label: "Image Harvester", icon: IconPhoto, color: "cyan", route: "/harvester" },
  { key: "url_mapper", label: "URL Mapper", icon: IconSitemap, color: "violet", route: "/mapper" },
  { key: "site_ripper", label: "Site Ripper", icon: IconDownload, color: "teal", route: "/ripper" },
  { key: "media_downloader", label: "Media Downloader", icon: IconMovie, color: "pink", route: "/media" },
  { key: "ai_tagging", label: "AI Tools", icon: IconBrain, color: "grape", route: "/ai" },
];

const STATUS_COLOR: Record<string, string> = {
  done: "teal",
  running: "cyan",
  error: "red",
  stopped: "yellow",
  pending: "gray",
};

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1073741824) return `${(n / 1048576).toFixed(1)} MB`;
  return `${(n / 1073741824).toFixed(2)} GB`;
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const nav = useNavigate();

  useEffect(() => {
    fetch("/api/system/dashboard")
      .then((r) => r.json())
      .then(setData)
      .catch((e) =>
        notifications.show({
          title: "Gagal memuat data",
          message: e?.message || "Terjadi kesalahan tidak dikenal",
          color: "red",
        })
      );
  }, []);

  if (!data) return (
    <Stack gap="md">
      <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }}>
        {[1,2,3,4,5].map(i => <Skeleton key={i} h={120} radius="lg" />)}
      </SimpleGrid>
      <Grid>
        {Array.from({ length: 4 }).map((_, i) => (
          <Grid.Col key={i} span={{ base: 12, sm: 6, md: 3 }}>
            <Skeleton height={100} radius="md" />
          </Grid.Col>
        ))}
      </Grid>
    </Stack>
  );

  const totalJobs = Object.values(data.jobs_by_type).reduce((s, v) => s + v.total, 0);
  const totalDone = Object.values(data.jobs_by_type).reduce((s, v) => s + v.done, 0);
  const diskUsedPct =
    data.disk.disk_total_gb > 0
      ? ((data.disk.disk_total_gb - data.disk.disk_free_gb) / data.disk.disk_total_gb) * 100
      : 0;

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Dashboard</Title>
        <Text c="dimmed" size="sm">
          Overview of all PyScrapr activity.
        </Text>
      </div>

      {/* Quick actions */}
      <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }}>
        {TOOLS.map((t) => {
          const stats = data.jobs_by_type[t.key];
          return (
            <Card
              key={t.key}
              withBorder
              radius="lg"
              p="md"
              style={{ cursor: "pointer" }}
              onClick={() => nav(t.route)}
            >
              <Group justify="space-between" mb="xs">
                <t.icon size={20} color={`var(--mantine-color-${t.color}-5)`} />
                {stats?.running ? (
                  <Badge color="cyan" variant="dot" size="xs">
                    {stats.running} running
                  </Badge>
                ) : null}
              </Group>
              <Text fw={700} size="sm">
                {t.label}
              </Text>
              <Text size="xl" fw={800} c={t.color}>
                {stats?.total || 0}
              </Text>
              <Text size="xs" c="dimmed">
                {stats?.done || 0} done · {stats?.error || 0} error
              </Text>
            </Card>
          );
        })}
      </SimpleGrid>

      <Grid>
        {/* Summary stats */}
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Text fw={600} mb="md">
              Overall
            </Text>
            <SimpleGrid cols={2}>
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Total jobs
                </Text>
                <Text size="xl" fw={800}>
                  {totalJobs}
                </Text>
              </div>
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Completed
                </Text>
                <Text size="xl" fw={800} c="teal">
                  {totalDone}
                </Text>
              </div>
            </SimpleGrid>
            <Text size="sm" fw={600} mt="lg" mb="xs">
              Disk usage
            </Text>
            <Progress value={diskUsedPct} size="sm" radius="xl" color={diskUsedPct > 90 ? "red" : "cyan"} />
            <Group justify="space-between" mt={4}>
              <Text size="xs" c="dimmed">
                Downloads: {fmtBytes(data.disk.downloads_bytes)}
              </Text>
              <Text size="xs" c="dimmed">
                Free: {data.disk.disk_free_gb} GB / {data.disk.disk_total_gb} GB
              </Text>
            </Group>
          </Card>
        </Grid.Col>

        {/* Recent jobs */}
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Group justify="space-between" mb="md">
              <Text fw={600}>Recent jobs</Text>
              <Button variant="subtle" size="xs" onClick={() => nav("/history")}>
                View all
              </Button>
            </Group>
            <Stack gap="xs">
              {data.recent_jobs.length === 0 ? (
                <Stack align="center" py="xl" gap="md">
                  <Title order={3}>Welcome to PyScrapr!</Title>
                  <Text c="dimmed" ta="center" maw={500}>
                    Your modular web scraping toolkit is ready. Pick a tool to get started:
                  </Text>
                  <Group>
                    <Button component="a" href="/harvester" variant="light" color="cyan">Harvest Images</Button>
                    <Button component="a" href="/mapper" variant="light" color="violet">Map a Site</Button>
                    <Button component="a" href="/media" variant="light" color="pink">Download Media</Button>
                  </Group>
                </Stack>
              ) : (
                data.recent_jobs.map((j) => (
                  <Group
                    key={j.id}
                    gap="sm"
                    wrap="nowrap"
                    style={{
                      padding: "8px 10px",
                      borderRadius: 8,
                      background: "var(--mantine-color-default-hover)",
                    }}
                  >
                    <Badge
                      size="xs"
                      variant="light"
                      color={TOOLS.find((t) => t.key === j.type)?.color || "gray"}
                      style={{ minWidth: 100 }}
                    >
                      {j.type.replace("_", " ")}
                    </Badge>
                    <Text
                      size="xs"
                      style={{
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {j.url}
                    </Text>
                    <Badge color={STATUS_COLOR[j.status] || "gray"} variant="dot" size="sm">
                      {j.status}
                    </Badge>
                    <Text size="xs" c="dimmed" style={{ minWidth: 120 }}>
                      {timeAgo(j.created_at)}
                    </Text>
                  </Group>
                ))
              )}
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
