import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Anchor,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Image,
  Loader,
  NumberInput,
  Progress,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconExternalLink,
  IconSearch,
  IconStack2,
} from "@tabler/icons-react";
import type { TechMatch, TechScanResponse } from "../types";

const PINNED_CATEGORIES = [
  "CMS",
  "Programming Languages",
  "Web Frameworks",
  "Web Servers",
  "JavaScript Frameworks",
  "JavaScript Libraries",
];

const ICON_BASE =
  "https://cdn.jsdelivr.net/gh/enthec/webappanalyzer/src/images/icons/";

function confidenceColor(c: number) {
  if (c >= 75) return "teal";
  if (c >= 50) return "yellow";
  return "gray";
}

function sortCategories(by_category: Record<string, TechMatch[]>): string[] {
  const keys = Object.keys(by_category);
  const pinned = PINNED_CATEGORIES.filter((c) => keys.includes(c));
  const rest = keys
    .filter((c) => !PINNED_CATEGORIES.includes(c))
    .sort(
      (a, b) =>
        (by_category[b]?.length || 0) - (by_category[a]?.length || 0),
    );
  return [...pinned, ...rest];
}

export default function TechPage() {
  const [searchParams] = useSearchParams();
  const [url, setUrl] = useState(searchParams.get("url") || "");
  const [timeout, setTimeoutVal] = useState<number>(20);
  const [usePlaywright, setUsePlaywright] = useState(false);
  const [loading, setLoading] = useState(false);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [result, setResult] = useState<TechScanResponse | null>(null);
  const [stats, setStats] = useState<{
    technologies_count: number;
    categories_count: number;
  } | null>(null);

  useEffect(() => {
    fetch("/api/tech/stats")
      .then((r) => r.json())
      .then((d) => setStats(d))
      .catch(() => {});
  }, []);

  const onScan = async () => {
    if (!url.trim()) return;
    const started = performance.now();
    try {
      setLoading(true);
      setElapsedMs(null);
      const r = await fetch("/api/tech/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          timeout,
          use_playwright: usePlaywright,
        }),
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }
      const data: TechScanResponse = await r.json();
      setResult(data);
      setElapsedMs(Math.round(performance.now() - started));
    } catch (e: any) {
      notifications.show({
        title: "Scan gagal",
        message: e?.message || "Tidak dapat memindai URL",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const orderedCategories = useMemo(
    () => (result ? sortCategories(result.by_category) : []),
    [result],
  );

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconStack2 size={26} />
          <Title order={2}>Tech Fingerprinter</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Bongkar teknologi yang dipakai sebuah website
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="sm">
          <Group align="flex-end" wrap="wrap">
            <TextInput
              label="URL target"
              placeholder="https://contoh.com"
              value={url}
              onChange={(e) => setUrl(e.currentTarget.value)}
              onKeyDown={(e) => e.key === "Enter" && onScan()}
              style={{ flex: 1, minWidth: 260 }}
            />
            <NumberInput
              label="Timeout (detik)"
              value={timeout}
              onChange={(v) => setTimeoutVal(typeof v === "number" ? v : 20)}
              min={5}
              max={120}
              w={140}
            />
            <Button
              color="cyan"
              leftSection={<IconSearch size={16} />}
              onClick={onScan}
              loading={loading}
            >
              Scan
            </Button>
          </Group>
          <Switch
            label="Render dengan browser (Playwright)"
            description="Gunakan untuk situs yang sangat bergantung pada JavaScript"
            checked={usePlaywright}
            onChange={(e) => setUsePlaywright(e.currentTarget.checked)}
          />
          {stats && (
            <Text size="xs" c="dimmed">
              Database: {stats.technologies_count.toLocaleString()} teknologi di{" "}
              {stats.categories_count} kategori
            </Text>
          )}
        </Stack>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="cyan" />
          <Text c="dimmed" size="sm">
            Memindai {url}...
          </Text>
        </Group>
      )}

      {result && !loading && (
        <Stack gap="md">
          <Card withBorder radius="lg" p="md">
            <Group gap="sm" wrap="wrap">
              <Badge
                size="lg"
                color={result.status_code < 400 ? "teal" : "red"}
                variant="light"
              >
                HTTP {result.status_code}
              </Badge>
              <Anchor
                href={result.final_url}
                target="_blank"
                rel="noreferrer"
                size="sm"
              >
                <Group gap={4} wrap="nowrap">
                  <IconExternalLink size={14} />
                  <Text span size="sm" ff="monospace">
                    {result.final_url}
                  </Text>
                </Group>
              </Anchor>
              <Badge color="cyan" variant="light" size="lg">
                {result.technologies.length} teknologi terdeteksi
              </Badge>
              {elapsedMs !== null && (
                <Badge color="gray" variant="light" size="lg">
                  waktu: {elapsedMs}ms
                </Badge>
              )}
            </Group>
          </Card>

          {orderedCategories.length === 0 && (
            <Card withBorder radius="lg" p="lg">
              <Text c="dimmed" ta="center">
                Tidak ada teknologi yang terdeteksi.
              </Text>
            </Card>
          )}

          {orderedCategories.map((cat) => {
            const techs = result.by_category[cat] || [];
            return (
              <Card key={cat} withBorder radius="lg" p="lg">
                <Group justify="space-between" mb="sm">
                  <Title order={4}>{cat}</Title>
                  <Badge color="gray" variant="light">
                    {techs.length}
                  </Badge>
                </Group>
                <Grid>
                  {techs.map((t, i) => (
                    <Grid.Col
                      key={`${t.name}-${i}`}
                      span={{ base: 12, sm: 6, md: 4 }}
                    >
                      <Card withBorder radius="md" p="sm" h="100%">
                        <Stack gap="xs">
                          <Group gap="sm" wrap="nowrap" align="flex-start">
                            {t.icon && (
                              <Image
                                src={`${ICON_BASE}${t.icon}`}
                                alt={t.name}
                                w={28}
                                h={28}
                                fit="contain"
                                fallbackSrc="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'/>"
                              />
                            )}
                            <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
                              <Group gap={6} wrap="wrap">
                                {t.website ? (
                                  <Anchor
                                    href={t.website}
                                    target="_blank"
                                    rel="noreferrer"
                                    fw={600}
                                    size="sm"
                                  >
                                    {t.name}
                                  </Anchor>
                                ) : (
                                  <Text fw={600} size="sm">
                                    {t.name}
                                  </Text>
                                )}
                                {t.version && (
                                  <Badge
                                    size="xs"
                                    color="cyan"
                                    variant="light"
                                  >
                                    v{t.version}
                                  </Badge>
                                )}
                              </Group>
                            </Stack>
                          </Group>
                          <div>
                            <Group justify="space-between" mb={2}>
                              <Text size="xs" c="dimmed">
                                confidence
                              </Text>
                              <Text size="xs" c="dimmed">
                                {t.confidence}%
                              </Text>
                            </Group>
                            <Progress
                              value={t.confidence}
                              color={confidenceColor(t.confidence)}
                              size="xs"
                            />
                          </div>
                          {t.matched_on.length > 0 && (
                            <Text size="xs" c="dimmed" lineClamp={2}>
                              matched on: {t.matched_on.join(", ")}
                            </Text>
                          )}
                        </Stack>
                      </Card>
                    </Grid.Col>
                  ))}
                </Grid>
              </Card>
            );
          })}
        </Stack>
      )}
    </Stack>
  );
}
