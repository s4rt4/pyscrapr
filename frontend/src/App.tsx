import {
  ActionIcon,
  AppShell,
  Badge,
  Divider,
  Group,
  NavLink,
  ScrollArea,
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
  IconRobot,
  IconFilter,
  IconBook,
  IconCalendarRepeat,
  IconArrowsShuffle,
  IconCamera,
  IconCertificate,
  IconChartBar,
  IconCode,
  IconLink,
  IconLinkOff,
  IconMap2,
  IconShield,
  IconShieldCheck,
  IconStack2,
  IconSettings,
  IconSun,
  IconMoon,
  IconWorldSearch,
} from "@tabler/icons-react";
import { NavLink as RouterNavLink, Route, Routes, Navigate } from "react-router-dom";

import DashboardPage from "./pages/DashboardPage";
import HarvesterPage from "./pages/HarvesterPage";
import MapperPage from "./pages/MapperPage";
import RipperPage from "./pages/RipperPage";
import MediaPage from "./pages/MediaPage";
import AIToolsPage from "./pages/AIToolsPage";
import AIExtractPage from "./pages/AIExtractPage";
import PipelinePage from "./pages/PipelinePage";
import HistoryPage from "./pages/HistoryPage";
import ScheduledPage from "./pages/ScheduledPage";
import DiffPage from "./pages/DiffPage";
import PlaygroundPage from "./pages/PlaygroundPage";
import BypassPage from "./pages/BypassPage";
import TechPage from "./pages/TechPage";
import ScreenshotPage from "./pages/ScreenshotPage";
import SeoAuditPage from "./pages/SeoAuditPage";
import BrokenLinksPage from "./pages/BrokenLinksPage";
import SecurityPage from "./pages/SecurityPage";
import SslInspectorPage from "./pages/SslInspectorPage";
import IntelPage from "./pages/IntelPage";
import WaybackPage from "./pages/WaybackPage";
import SitemapPage from "./pages/SitemapPage";
import VaultPage from "./pages/VaultPage";
import SettingsPage from "./pages/SettingsPage";
import DocsPage from "./pages/DocsPage";
import SmartUrlInput from "./components/SmartUrlInput";
import SystemStatusBar from "./components/SystemStatusBar";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { usePageMeta } from "./hooks/usePageMeta";
import { useHotkeys } from "@mantine/hooks";

type NavItem = { to: string; label: string; icon: any; phase: number };
type NavGroup = { group: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  {
    group: "Tools",
    items: [
      { to: "/", label: "Dashboard", icon: IconDashboard, phase: 0 },
      { to: "/harvester", label: "Image Harvester", icon: IconPhoto, phase: 1 },
      { to: "/mapper", label: "URL Mapper", icon: IconSitemap, phase: 2 },
      { to: "/ripper", label: "Site Ripper", icon: IconDownload, phase: 3 },
      { to: "/media", label: "Media Downloader", icon: IconMovie, phase: 4 },
      { to: "/ai", label: "AI Tagger", icon: IconBrain, phase: 5 },
      { to: "/tech", label: "Tech Fingerprinter", icon: IconStack2, phase: 6 },
      { to: "/screenshot", label: "Screenshotter", icon: IconCamera, phase: 7 },
    ],
  },
  {
    group: "Audit & Intel",
    items: [
      { to: "/seo", label: "SEO Auditor", icon: IconChartBar, phase: 0 },
      { to: "/broken-links", label: "Broken Links", icon: IconLinkOff, phase: 0 },
      { to: "/security", label: "Security Headers", icon: IconShieldCheck, phase: 0 },
      { to: "/ssl", label: "SSL Inspector", icon: IconCertificate, phase: 0 },
      { to: "/intel", label: "Domain Intel", icon: IconWorldSearch, phase: 0 },
      { to: "/wayback", label: "Wayback Explorer", icon: IconHistory, phase: 0 },
      { to: "/sitemap", label: "Sitemap Analyzer", icon: IconMap2, phase: 0 },
    ],
  },
  {
    group: "Utilities",
    items: [
      { to: "/ai-extract", label: "AI Extract", icon: IconRobot, phase: 0 },
      { to: "/pipeline", label: "Pipeline", icon: IconFilter, phase: 0 },
      { to: "/playground", label: "Playground", icon: IconCode, phase: 0 },
      { to: "/bypass", label: "Link Bypass", icon: IconLink, phase: 0 },
      { to: "/vault", label: "Auth Vault", icon: IconShield, phase: 0 },
    ],
  },
  {
    group: "System",
    items: [
      { to: "/scheduled", label: "Scheduled", icon: IconCalendarRepeat, phase: 0 },
      { to: "/diff", label: "Diff", icon: IconArrowsShuffle, phase: 0 },
      { to: "/history", label: "History", icon: IconHistory, phase: 0 },
      { to: "/settings", label: "Settings", icon: IconSettings, phase: 0 },
    ],
  },
  {
    group: "Help",
    items: [
      { to: "/docs", label: "Docs", icon: IconBook, phase: 0 },
    ],
  },
];

export default function App() {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const isDark = colorScheme === "dark";
  usePageMeta();

  useHotkeys([
    ["mod+1", () => (window.location.href = "/harvester")],
    ["mod+2", () => (window.location.href = "/mapper")],
    ["mod+3", () => (window.location.href = "/ripper")],
    ["mod+4", () => (window.location.href = "/media")],
    ["mod+5", () => (window.location.href = "/ai")],
    ["mod+6", () => (window.location.href = "/tech")],
    ["mod+k", () => document.querySelector<HTMLInputElement>("[placeholder*='Paste URL']")?.focus()],
    ["mod+d", () => toggleColorScheme()],
  ]);

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
        <ScrollArea type="never" style={{ flex: 1 }}>
          {navGroups.map((group, gi) => (
            <div key={group.group}>
              {gi > 0 && (
                <Divider
                  my={6}
                  label={<Text size="xs" c="dimmed" tt="uppercase" fw={700} lts={1}>{group.group}</Text>}
                  labelPosition="left"
                />
              )}
              {group.items.map((item) => (
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
                  style={{ borderRadius: rem(8), marginBottom: rem(2) }}
                />
              ))}
            </div>
          ))}
        </ScrollArea>
      </AppShell.Navbar>

      <AppShell.Main>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/harvester" element={<HarvesterPage />} />
            <Route path="/mapper" element={<MapperPage />} />
            <Route path="/ripper" element={<RipperPage />} />
            <Route path="/media" element={<MediaPage />} />
            <Route path="/ai" element={<AIToolsPage />} />
            <Route path="/ai-extract" element={<AIExtractPage />} />
            <Route path="/pipeline" element={<PipelinePage />} />
            <Route path="/playground" element={<PlaygroundPage />} />
            <Route path="/bypass" element={<BypassPage />} />
            <Route path="/tech" element={<TechPage />} />
            <Route path="/screenshot" element={<ScreenshotPage />} />
            <Route path="/seo" element={<SeoAuditPage />} />
            <Route path="/broken-links" element={<BrokenLinksPage />} />
            <Route path="/security" element={<SecurityPage />} />
            <Route path="/ssl" element={<SslInspectorPage />} />
            <Route path="/intel" element={<IntelPage />} />
            <Route path="/wayback" element={<WaybackPage />} />
            <Route path="/sitemap" element={<SitemapPage />} />
            <Route path="/vault" element={<VaultPage />} />
            <Route path="/scheduled" element={<ScheduledPage />} />
            <Route path="/diff" element={<DiffPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/docs" element={<DocsPage />} />
            <Route path="/docs/*" element={<DocsPage />} />
          </Routes>
        </ErrorBoundary>
      </AppShell.Main>

      <AppShell.Footer>
        <SystemStatusBar />
      </AppShell.Footer>
    </AppShell>
  );
}
