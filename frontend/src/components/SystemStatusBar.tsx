import { useEffect, useState } from "react";
import {
  Group,
  Progress,
  RingProgress,
  Text,
  Tooltip,
} from "@mantine/core";
import {
  IconArrowDown,
  IconArrowUp,
  IconCpu,
  IconDeviceDesktop,
  IconWifi,
} from "@tabler/icons-react";

interface SystemStats {
  cpu: { percent: number; cores: number };
  ram: { percent: number; used_gb: number; total_gb: number };
  network: {
    upload_speed: number;
    download_speed: number;
    upload_today: number;
    download_today: number;
  };
  uptime_seconds: number;
}

function fmtSpeed(bytesPerSec: number): string {
  if (bytesPerSec < 1024) return `${bytesPerSec} B/s`;
  if (bytesPerSec < 1048576) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
  return `${(bytesPerSec / 1048576).toFixed(2)} MB/s`;
}

function fmtBytes(n: number): string {
  const abs = Math.max(0, Math.abs(n));
  if (abs < 1024) return `${abs} B`;
  if (abs < 1048576) return `${(abs / 1024).toFixed(1)} KB`;
  if (abs < 1073741824) return `${(abs / 1048576).toFixed(1)} MB`;
  return `${(abs / 1073741824).toFixed(2)} GB`;
}

function fmtUptime(secs: number): string {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function cpuColor(pct: number): string {
  if (pct < 50) return "teal";
  if (pct < 80) return "yellow";
  return "red";
}

function ramColor(pct: number): string {
  if (pct < 60) return "cyan";
  if (pct < 85) return "yellow";
  return "red";
}

export default function SystemStatusBar() {
  const [stats, setStats] = useState<SystemStats | null>(null);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const r = await fetch("/api/system/stats");
        if (r.ok && active) setStats(await r.json());
      } catch {}
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  if (!stats) return null;

  const { cpu, ram, network } = stats;

  return (
    <Group
      h="100%"
      px="md"
      gap="lg"
      justify="space-between"
      style={{ fontSize: 12, userSelect: "none" }}
    >
      {/* CPU */}
      <Tooltip label={`CPU: ${cpu.percent}% (${cpu.cores} cores)`}>
        <Group gap={6} wrap="nowrap">
          <IconCpu size={14} style={{ opacity: 0.6 }} />
          <Text size="xs" c="dimmed" fw={600}>
            CPU
          </Text>
          <RingProgress
            size={22}
            thickness={3}
            roundCaps
            sections={[{ value: cpu.percent, color: cpuColor(cpu.percent) }]}
          />
          <Text size="xs" c={cpuColor(cpu.percent)} fw={700} w={36}>
            {cpu.percent.toFixed(0)}%
          </Text>
        </Group>
      </Tooltip>

      {/* RAM */}
      <Tooltip label={`RAM: ${ram.used_gb} / ${ram.total_gb} GB`}>
        <Group gap={6} wrap="nowrap">
          <IconDeviceDesktop size={14} style={{ opacity: 0.6 }} />
          <Text size="xs" c="dimmed" fw={600}>
            RAM
          </Text>
          <RingProgress
            size={22}
            thickness={3}
            roundCaps
            sections={[{ value: ram.percent, color: ramColor(ram.percent) }]}
          />
          <Text size="xs" c={ramColor(ram.percent)} fw={700} w={36}>
            {ram.percent.toFixed(0)}%
          </Text>
        </Group>
      </Tooltip>

      {/* Network speed */}
      <Tooltip label="Current network speed">
        <Group gap={6} wrap="nowrap">
          <IconWifi size={14} style={{ opacity: 0.6 }} />
          <IconArrowDown size={12} color="var(--mantine-color-teal-5)" />
          <Text size="xs" c="teal" fw={700} w={80}>
            {fmtSpeed(network.download_speed)}
          </Text>
          <IconArrowUp size={12} color="var(--mantine-color-cyan-5)" />
          <Text size="xs" c="cyan" fw={700} w={80}>
            {fmtSpeed(network.upload_speed)}
          </Text>
        </Group>
      </Tooltip>

      {/* Traffic today - hidden on mobile */}
      <Tooltip label={`Traffic since app start (uptime: ${fmtUptime(stats.uptime_seconds)})`}>
        <Group gap={6} wrap="nowrap" visibleFrom="sm">
          <Text size="xs" c="dimmed" fw={600}>
            Traffic
          </Text>
          <IconArrowDown size={11} style={{ opacity: 0.5 }} />
          <Text size="xs" c="dimmed">
            {fmtBytes(network.download_today)}
          </Text>
          <IconArrowUp size={11} style={{ opacity: 0.5 }} />
          <Text size="xs" c="dimmed">
            {fmtBytes(network.upload_today)}
          </Text>
        </Group>
      </Tooltip>
    </Group>
  );
}
