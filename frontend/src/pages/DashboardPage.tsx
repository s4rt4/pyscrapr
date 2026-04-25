import { useEffect, useState } from "react";
import {
  Badge,
  Box,
  Button,
  Card,
  Grid,
  Group,
  Progress,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { AreaChart, DonutChart } from "@mantine/charts";
import { notifications } from "@mantine/notifications";
import {
  IconActivity,
  IconAlertTriangle,
  IconBrain,
  IconCamera,
  IconCertificate,
  IconChartBar,
  IconCircleCheck,
  IconDownload,
  IconHistory,
  IconLinkOff,
  IconLoader,
  IconMap2,
  IconMovie,
  IconPhoto,
  IconShieldCheck,
  IconShieldLock,
  IconSitemap,
  IconStack2,
  IconWorldSearch,
} from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { timeAgo } from "../lib/utils";

interface JobTypeStats {
  total: number;
  done: number;
  error: number;
  running: number;
}

interface DashboardData {
  jobs_by_type: Record<string, JobTypeStats>;
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

interface TimeseriesDay {
  date: string;
  total: number;
  done: number;
  error: number;
}

interface DashboardTimeseries {
  days: TimeseriesDay[];
}

const TOOLS = [
  { key: "image_harvester", label: "Image Harvester", icon: IconPhoto, color: "cyan", route: "/harvester", phase: 1 },
  { key: "url_mapper", label: "URL Mapper", icon: IconSitemap, color: "violet", route: "/mapper", phase: 2 },
  { key: "site_ripper", label: "Site Ripper", icon: IconDownload, color: "teal", route: "/ripper", phase: 3 },
  { key: "media_downloader", label: "Media Downloader", icon: IconMovie, color: "pink", route: "/media", phase: 4 },
  { key: "ai_tagging", label: "AI Tagger", icon: IconBrain, color: "grape", route: "/ai", phase: 5 },
  { key: "tech_detector", label: "Tech Fingerprinter", icon: IconStack2, color: "blue", route: "/tech", phase: 6 },
  { key: "screenshot", label: "Screenshotter", icon: IconCamera, color: "yellow", route: "/screenshot", phase: 7 },
  { key: "threat_scan", label: "Threat Scanner", icon: IconShieldLock, color: "red", route: "/threat", phase: 8 },
];

const AUDIT_TOOLS = [
  { key: "seo_audit", label: "SEO", icon: IconChartBar, color: "orange", route: "/seo" },
  { key: "link_check", label: "Broken Links", icon: IconLinkOff, color: "red", route: "/broken-links" },
  { key: "security_scan", label: "Security Headers", icon: IconShieldCheck, color: "yellow", route: "/security" },
  { key: "ssl_inspect", label: "SSL", icon: IconCertificate, color: "teal", route: "/ssl" },
  { key: "domain_intel", label: "Domain Intel", icon: IconWorldSearch, color: "blue", route: "/intel" },
  { key: "wayback_lookup", label: "Wayback", icon: IconHistory, color: "grape", route: "/wayback" },
  { key: "sitemap_analyze", label: "Sitemap", icon: IconMap2, color: "cyan", route: "/sitemap" },
];

const ALL_TOOLS_BY_KEY: Record<string, { label: string; color: string }> = {};
[...TOOLS, ...AUDIT_TOOLS].forEach((t) => {
  ALL_TOOLS_BY_KEY[t.key] = { label: t.label, color: t.color };
});

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

function fmtChartDate(iso: string): string {
  // "2026-04-23" -> "23 Apr"
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
  return `${d.getDate().toString().padStart(2, "0")} ${months[d.getMonth()]}`;
}

interface ToolCardProps {
  toolKey: string;
  label: string;
  icon: React.ComponentType<{ size?: number; color?: string }>;
  color: string;
  route: string;
  phase?: number;
  stats?: JobTypeStats;
  compact?: boolean;
}

function ToolCard({ toolKey: _k, label, icon: Icon, color, route, phase, stats, compact }: ToolCardProps) {
  const nav = useNavigate();
  const total = stats?.total || 0;
  const done = stats?.done || 0;
  const err = stats?.error || 0;
  const donePct = total > 0 ? (done / total) * 100 : 0;
  const errPct = total > 0 ? (err / total) * 100 : 0;

  return (
    <Card
      withBorder
      radius="lg"
      p={compact ? "sm" : "md"}
      style={{
        cursor: "pointer",
        transition: "transform 120ms ease, box-shadow 120ms ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = "translateY(-2px)";
        e.currentTarget.style.boxShadow = "0 6px 16px rgba(0,0,0,0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = "";
      }}
      onClick={() => nav(route)}
    >
      <Group justify="space-between" mb={4} wrap="nowrap">
        <Icon size={compact ? 18 : 22} color={`var(--mantine-color-${color}-5)`} />
        {phase ? (
          <Badge size="xs" variant="light" color={color}>
            P{phase}
          </Badge>
        ) : null}
        {stats?.running ? (
          <Badge color="cyan" variant="dot" size="xs">
            {stats.running}
          </Badge>
        ) : null}
      </Group>
      <Text fw={600} size={compact ? "xs" : "sm"} lineClamp={1}>
        {label}
      </Text>
      <Text size={compact ? "lg" : "xl"} fw={800} c={color} mt={2}>
        {total}
      </Text>
      {!compact && (
        <>
          <Box mt={6} style={{ display: "flex", height: 4, borderRadius: 2, overflow: "hidden", background: "var(--mantine-color-default-hover)" }}>
            <div style={{ width: `${donePct}%`, background: "var(--mantine-color-teal-5)" }} />
            <div style={{ width: `${errPct}%`, background: "var(--mantine-color-red-5)" }} />
          </Box>
          <Group justify="space-between" mt={4} gap={4}>
            <Text size="xs" c="dimmed">
              {done} done
            </Text>
            <Text size="xs" c="dimmed">
              {err} error
            </Text>
          </Group>
        </>
      )}
    </Card>
  );
}

interface HeroStatProps {
  icon: React.ComponentType<{ size?: number; color?: string }>;
  label: string;
  value: number | string;
  sub?: string;
  color: string;
  pulse?: boolean;
}

function HeroStat({ icon: Icon, label, value, sub, color, pulse }: HeroStatProps) {
  return (
    <Card withBorder radius="md" p="md">
      <Group justify="space-between" mb={6}>
        <Group gap={6}>
          <Icon size={18} color={`var(--mantine-color-${color}-5)`} />
          <Text size="xs" c="dimmed" tt="uppercase" fw={700} lts={0.5}>
            {label}
          </Text>
        </Group>
        {pulse && (
          <Box
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--mantine-color-cyan-5)",
              animation: "pyscrapr-pulse 1.4s ease-in-out infinite",
            }}
          />
        )}
      </Group>
      <Text fw={800} size="xl" c={color}>
        {value}
      </Text>
      {sub && (
        <Text size="xs" c="dimmed" mt={2}>
          {sub}
        </Text>
      )}
    </Card>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [series, setSeries] = useState<DashboardTimeseries | null>(null);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    Promise.all([
      fetch("/api/system/dashboard").then((r) => r.json()),
      fetch("/api/system/dashboard/timeseries?days=14").then((r) => r.json()),
    ])
      .then(([d, s]) => {
        setData(d);
        setSeries(s);
      })
      .catch((e) =>
        notifications.show({
          title: "Gagal memuat data",
          message: e?.message || "Terjadi kesalahan tidak dikenal",
          color: "red",
        })
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return (
      <Stack gap="md">
        <SimpleGrid cols={{ base: 2, sm: 4 }}>
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} h={90} radius="md" />
          ))}
        </SimpleGrid>
        <SimpleGrid cols={{ base: 2, sm: 4, md: 8 }}>
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <Skeleton key={i} h={130} radius="lg" />
          ))}
        </SimpleGrid>
        <Grid>
          <Grid.Col span={{ base: 12, md: 7 }}>
            <Skeleton h={290} radius="lg" />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 5 }}>
            <Skeleton h={290} radius="lg" />
          </Grid.Col>
        </Grid>
      </Stack>
    );
  }

  const totalJobs = Object.values(data.jobs_by_type).reduce((s, v) => s + v.total, 0);
  const totalDone = Object.values(data.jobs_by_type).reduce((s, v) => s + v.done, 0);
  const totalError = Object.values(data.jobs_by_type).reduce((s, v) => s + v.error, 0);
  const totalRunning = Object.values(data.jobs_by_type).reduce((s, v) => s + v.running, 0);
  const donePct = totalJobs > 0 ? Math.round((totalDone / totalJobs) * 100) : 0;
  const errorPct = totalJobs > 0 ? Math.round((totalError / totalJobs) * 100) : 0;

  const diskUsedPct =
    data.disk.disk_total_gb > 0
      ? ((data.disk.disk_total_gb - data.disk.disk_free_gb) / data.disk.disk_total_gb) * 100
      : 0;

  // Empty state for new users
  if (totalJobs === 0 && data.recent_jobs.length === 0) {
    return (
      <Stack gap="md">
        <div>
          <Title order={2}>Dashboard</Title>
          <Text c="dimmed" size="sm">
            Overview of all PyScrapr activity.
          </Text>
        </div>
        <Card withBorder radius="lg" p="xl">
          <Stack align="center" py="xl" gap="md">
            <Title order={3}>Welcome to PyScrapr!</Title>
            <Text c="dimmed" ta="center" maw={500}>
              Your modular web scraping toolkit is ready. Pick a tool to get started:
            </Text>
            <Group>
              <Button component="a" href="/harvester" variant="light" color="cyan">
                Harvest Images
              </Button>
              <Button component="a" href="/mapper" variant="light" color="violet">
                Map a Site
              </Button>
              <Button component="a" href="/media" variant="light" color="pink">
                Download Media
              </Button>
            </Group>
          </Stack>
        </Card>
      </Stack>
    );
  }

  // Donut chart data
  const donutEntries = Object.entries(data.jobs_by_type)
    .map(([key, stats]) => ({
      key,
      label: ALL_TOOLS_BY_KEY[key]?.label || key.replace(/_/g, " "),
      color: ALL_TOOLS_BY_KEY[key]?.color || "gray",
      value: stats.total,
    }))
    .filter((e) => e.value > 0)
    .sort((a, b) => b.value - a.value);

  let donutData = donutEntries.slice(0, 8).map((e) => ({
    name: e.label,
    value: e.value,
    color: `${e.color}.5`,
  }));
  if (donutEntries.length > 8) {
    const otherTotal = donutEntries.slice(8).reduce((s, e) => s + e.value, 0);
    if (otherTotal > 0) {
      donutData.push({ name: "Other", value: otherTotal, color: "gray.5" });
    }
  }

  // Area chart data
  const areaData = (series?.days || []).map((d) => ({
    date: fmtChartDate(d.date),
    done: d.done,
    error: d.error,
  }));

  return (
    <Stack gap="md">
      <style>{`@keyframes pyscrapr-pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.8); } }`}</style>

      <div>
        <Title order={2}>Dashboard</Title>
        <Text c="dimmed" size="sm">
          Ringkasan aktivitas PyScrapr Anda.
        </Text>
      </div>

      {/* Hero stat strip */}
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        <HeroStat
          icon={IconActivity}
          label="Total Jobs"
          value={totalJobs}
          sub="Sepanjang waktu"
          color="violet"
        />
        <HeroStat
          icon={IconCircleCheck}
          label="Selesai"
          value={totalDone}
          sub={`${donePct}% berhasil`}
          color="teal"
        />
        <HeroStat
          icon={IconAlertTriangle}
          label="Error"
          value={totalError}
          sub={`${errorPct}% gagal`}
          color="red"
        />
        <HeroStat
          icon={IconLoader}
          label="Berjalan"
          value={totalRunning}
          sub={totalRunning > 0 ? "Sedang aktif" : "Tidak ada job aktif"}
          color="cyan"
          pulse={totalRunning > 0}
        />
      </SimpleGrid>

      {/* Tools grid */}
      <div>
        <Group justify="space-between" mb="xs">
          <Text fw={600} size="sm" tt="uppercase" c="dimmed" lts={1}>
            Tools
          </Text>
        </Group>
        <SimpleGrid cols={{ base: 2, sm: 4, md: 8 }}>
          {TOOLS.map((t) => (
            <ToolCard
              key={t.key}
              toolKey={t.key}
              label={t.label}
              icon={t.icon}
              color={t.color}
              route={t.route}
              phase={t.phase}
              stats={data.jobs_by_type[t.key]}
            />
          ))}
        </SimpleGrid>
      </div>

      {/* Charts row */}
      <Grid>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Group justify="space-between" mb="md">
              <Text fw={600}>Aktivitas 14 hari terakhir</Text>
              <Badge variant="light" color="gray" size="sm">
                {areaData.reduce((s, d) => s + d.done + d.error, 0)} job
              </Badge>
            </Group>
            {areaData.length > 0 ? (
              <AreaChart
                h={250}
                data={areaData}
                dataKey="date"
                type="stacked"
                withGradient
                withLegend
                series={[
                  { name: "done", label: "Selesai", color: "teal.5" },
                  { name: "error", label: "Error", color: "red.5" },
                ]}
                curveType="monotone"
                tickLine="x"
                gridAxis="y"
              />
            ) : (
              <Stack align="center" py="xl">
                <Text c="dimmed" size="sm">
                  Belum ada data aktivitas.
                </Text>
              </Stack>
            )}
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Group justify="space-between" mb="md">
              <Text fw={600}>Distribusi job per tool</Text>
              <Badge variant="light" color="gray" size="sm">
                {donutEntries.length} tool
              </Badge>
            </Group>
            {donutData.length > 0 ? (
              <Group justify="center">
                <DonutChart
                  h={250}
                  data={donutData}
                  withLabelsLine
                  withLabels
                  withTooltip
                  size={180}
                  thickness={28}
                  paddingAngle={2}
                  chartLabel={`${totalJobs}`}
                />
              </Group>
            ) : (
              <Stack align="center" py="xl">
                <Text c="dimmed" size="sm">
                  Belum ada job tercatat.
                </Text>
              </Stack>
            )}
          </Card>
        </Grid.Col>
      </Grid>

      {/* Audit & Intel row */}
      <div>
        <Group justify="space-between" mb="xs">
          <Text fw={600} size="sm" tt="uppercase" c="dimmed" lts={1}>
            Audit & Intel
          </Text>
        </Group>
        <SimpleGrid cols={{ base: 3, sm: 4, md: 7 }}>
          {AUDIT_TOOLS.map((t) => (
            <ToolCard
              key={t.key}
              toolKey={t.key}
              label={t.label}
              icon={t.icon}
              color={t.color}
              route={t.route}
              stats={data.jobs_by_type[t.key]}
              compact
            />
          ))}
        </SimpleGrid>
      </div>

      {/* Bottom row: disk + recent jobs */}
      <Grid>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Text fw={600} mb="md">
              Penyimpanan
            </Text>
            <Progress
              value={diskUsedPct}
              size="md"
              radius="xl"
              color={diskUsedPct > 90 ? "red" : diskUsedPct > 70 ? "yellow" : "cyan"}
            />
            <Group justify="space-between" mt="xs">
              <Text size="xs" c="dimmed">
                {Math.round(diskUsedPct)}% terpakai
              </Text>
              <Text size="xs" c="dimmed">
                {data.disk.disk_free_gb} / {data.disk.disk_total_gb} GB
              </Text>
            </Group>
            <Stack gap={4} mt="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed">
                  Downloads
                </Text>
                <Text size="xs" fw={600}>
                  {fmtBytes(data.disk.downloads_bytes)}
                </Text>
              </Group>
              <Group justify="space-between">
                <Text size="xs" c="dimmed">
                  Data
                </Text>
                <Text size="xs" fw={600}>
                  {fmtBytes(data.disk.data_bytes)}
                </Text>
              </Group>
              <Group justify="space-between">
                <Text size="xs" c="dimmed">
                  Sisa disk
                </Text>
                <Text size="xs" fw={600}>
                  {data.disk.disk_free_gb} GB
                </Text>
              </Group>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 8 }}>
          <Card withBorder radius="lg" p="lg" h="100%">
            <Group justify="space-between" mb="md">
              <Text fw={600}>Aktivitas terbaru</Text>
              <Button variant="subtle" size="xs" onClick={() => nav("/history")}>
                Lihat semua
              </Button>
            </Group>
            <Stack gap="xs">
              {data.recent_jobs.length === 0 ? (
                <Text c="dimmed" size="sm" ta="center" py="md">
                  Belum ada job tercatat.
                </Text>
              ) : (
                data.recent_jobs.slice(0, 5).map((j) => {
                  const toolMeta = ALL_TOOLS_BY_KEY[j.type];
                  return (
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
                        color={toolMeta?.color || "gray"}
                        style={{ minWidth: 110 }}
                      >
                        {toolMeta?.label || j.type.replace(/_/g, " ")}
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
                      <Text size="xs" c="dimmed" style={{ minWidth: 100, textAlign: "right" }}>
                        {timeAgo(j.created_at)}
                      </Text>
                    </Group>
                  );
                })
              )}
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

