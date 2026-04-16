import {
  ActionIcon,
  AppShell,
  Badge,
  Group,
  NavLink,
  Text,
  Title,
  rem,
  useMantineColorScheme,
} from "@mantine/core";
import {
  IconDashboard,
  IconPhoto,
  IconSitemap,
  IconDownload,
  IconHistory,
  IconMovie,
  IconBrain,
  IconCalendarRepeat,
  IconArrowsShuffle,
  IconCode,
  IconLink,
  IconShield,
  IconSettings,
  IconSun,
  IconMoon,
} from "@tabler/icons-react";
import { NavLink as RouterNavLink, Route, Routes, Navigate } from "react-router-dom";

import DashboardPage from "./pages/DashboardPage";
import HarvesterPage from "./pages/HarvesterPage";
import MapperPage from "./pages/MapperPage";
import RipperPage from "./pages/RipperPage";
import MediaPage from "./pages/MediaPage";
import AIToolsPage from "./pages/AIToolsPage";
import HistoryPage from "./pages/HistoryPage";
import ScheduledPage from "./pages/ScheduledPage";
import DiffPage from "./pages/DiffPage";
import PlaygroundPage from "./pages/PlaygroundPage";
import BypassPage from "./pages/BypassPage";
import VaultPage from "./pages/VaultPage";
import SettingsPage from "./pages/SettingsPage";
import SmartUrlInput from "./components/SmartUrlInput";
import SystemStatusBar from "./components/SystemStatusBar";

const navItems = [
  { to: "/", label: "Dashboard", icon: IconDashboard, phase: 0 },
  { to: "/harvester", label: "Image Harvester", icon: IconPhoto, phase: 1 },
  { to: "/mapper", label: "URL Mapper", icon: IconSitemap, phase: 2 },
  { to: "/ripper", label: "Site Ripper", icon: IconDownload, phase: 3 },
  { to: "/media", label: "Media Downloader", icon: IconMovie, phase: 4 },
  { to: "/ai", label: "AI Tools", icon: IconBrain, phase: 5 },
  { to: "/playground", label: "Playground", icon: IconCode, phase: 0 },
  { to: "/bypass", label: "Link Bypass", icon: IconLink, phase: 0 },
  { to: "/vault", label: "Auth Vault", icon: IconShield, phase: 0 },
  { to: "/scheduled", label: "Scheduled", icon: IconCalendarRepeat, phase: 0 },
  { to: "/diff", label: "Diff", icon: IconArrowsShuffle, phase: 0 },
  { to: "/history", label: "History", icon: IconHistory, phase: 0 },
  { to: "/settings", label: "Settings", icon: IconSettings, phase: 0 },
];

export default function App() {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const isDark = colorScheme === "dark";

  return (
    <AppShell
      header={{ height: 64 }}
      navbar={{ width: 260, breakpoint: "sm" }}
      footer={{ height: 36 }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="lg" justify="space-between">
          <Group gap="sm">
            <img
              src="/spider.svg"
              alt="PyScrapr"
              width={32}
              height={32}
              style={{ display: "block" }}
            />
            <Title order={3} style={{ letterSpacing: "-0.02em" }}>
              Py<span style={{ color: "var(--mantine-color-cyan-5)" }}>Scrapr</span>
            </Title>
            <Badge variant="light" color="cyan" size="sm">
              v0.1
            </Badge>
          </Group>
          <Group gap="md">
            <SmartUrlInput />
            <ActionIcon
              variant="subtle"
              color="gray"
              onClick={() => toggleColorScheme()}
              title="Toggle theme"
              aria-label="Toggle theme"
            >
              {isDark ? <IconSun size={18} /> : <IconMoon size={18} />}
            </ActionIcon>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            component={RouterNavLink}
            to={item.to}
            label={item.label}
            leftSection={<item.icon size={18} />}
            rightSection={
              item.phase > 0 ? (
                <Badge size="xs" variant="light" color={item.phase === 1 ? "cyan" : "gray"}>
                  P{item.phase}
                </Badge>
              ) : null
            }
            style={{ borderRadius: rem(8), marginBottom: rem(4) }}
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/harvester" element={<HarvesterPage />} />
          <Route path="/mapper" element={<MapperPage />} />
          <Route path="/ripper" element={<RipperPage />} />
          <Route path="/media" element={<MediaPage />} />
          <Route path="/ai" element={<AIToolsPage />} />
          <Route path="/playground" element={<PlaygroundPage />} />
          <Route path="/bypass" element={<BypassPage />} />
          <Route path="/vault" element={<VaultPage />} />
          <Route path="/scheduled" element={<ScheduledPage />} />
          <Route path="/diff" element={<DiffPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </AppShell.Main>

      <AppShell.Footer>
        <SystemStatusBar />
      </AppShell.Footer>
    </AppShell>
  );
}
