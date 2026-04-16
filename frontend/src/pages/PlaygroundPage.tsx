import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Code,
  Grid,
  Group,
  ScrollArea,
  SegmentedControl,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconCode,
  IconDownload,
  IconPlayerPlay,
  IconSearch,
} from "@tabler/icons-react";

interface MatchedEl {
  tag: string;
  text: string;
  html: string;
  attributes: Record<string, string>;
}

export default function PlaygroundPage() {
  const [url, setUrl] = useState("");
  const [html, setHtml] = useState("");
  const [loading, setLoading] = useState(false);
  const [pageInfo, setPageInfo] = useState<{ status_code: number; size: number } | null>(null);

  const [selector, setSelector] = useState("");
  const [mode, setMode] = useState<"css" | "xpath">("css");
  const [matches, setMatches] = useState<MatchedEl[]>([]);
  const [testing, setTesting] = useState(false);

  const onFetch = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      setHtml("");
      setMatches([]);
      setPageInfo(null);
      const r = await fetch("/api/playground/fetch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      setHtml(d.html);
      setPageInfo({ status_code: d.status_code, size: d.size });
    } catch (e: any) {
      notifications.show({ title: "Fetch failed", message: e.message, color: "red" });
    } finally {
      setLoading(false);
    }
  };

  const onTest = async () => {
    if (!html || !selector.trim()) return;
    try {
      setTesting(true);
      const r = await fetch("/api/playground/test-selector", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ html, selector, mode }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setMatches(data);
    } catch (e: any) {
      notifications.show({ title: "Selector error", message: e.message, color: "red" });
      setMatches([]);
    } finally {
      setTesting(false);
    }
  };

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Selector Playground</Title>
        <Text c="dimmed" size="sm">
          Fetch a page and test CSS / XPath selectors live before running a full scrape.
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Group align="flex-end" mb="md">
          <TextInput
            label="URL to inspect"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onFetch()}
            style={{ flex: 1 }}
            size="md"
          />
          <Button leftSection={<IconDownload size={16} />} onClick={onFetch} loading={loading} size="md">
            Fetch
          </Button>
        </Group>
        {pageInfo && (
          <Group gap="sm">
            <Badge color={pageInfo.status_code < 400 ? "teal" : "red"}>
              {pageInfo.status_code}
            </Badge>
            <Text size="xs" c="dimmed">
              {(pageInfo.size / 1024).toFixed(1)} KB HTML loaded
            </Text>
          </Group>
        )}
      </Card>

      {html && (
        <Grid>
          <Grid.Col span={{ base: 12, md: 5 }}>
            <Card withBorder radius="lg" p="lg" h="100%">
              <Text fw={600} mb="sm">Page source</Text>
              <ScrollArea h={500} type="auto">
                <Code block style={{ fontSize: 11, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                  {html.slice(0, 50000)}
                </Code>
              </ScrollArea>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 7 }}>
            <Card withBorder radius="lg" p="lg">
              <Group mb="md" align="flex-end">
                <TextInput
                  label="Selector"
                  placeholder={mode === "css" ? "div.content > h2, img.hero" : "//div[@class='content']//h2"}
                  value={selector}
                  onChange={(e) => setSelector(e.currentTarget.value)}
                  onKeyDown={(e) => e.key === "Enter" && onTest()}
                  style={{ flex: 1 }}
                />
                <SegmentedControl
                  value={mode}
                  onChange={(v) => setMode(v as "css" | "xpath")}
                  size="xs"
                  data={[
                    { label: "CSS", value: "css" },
                    { label: "XPath", value: "xpath" },
                  ]}
                />
                <Button leftSection={<IconSearch size={16} />} onClick={onTest} loading={testing}>
                  Test
                </Button>
              </Group>

              <Group mb="sm" gap="xs">
                <Badge color={matches.length > 0 ? "teal" : "gray"} variant="light">
                  {matches.length} match{matches.length !== 1 ? "es" : ""}
                </Badge>
                {matches.length > 0 && (
                  <Button
                    size="xs"
                    variant="subtle"
                    component="a"
                    href={`/harvester?url=${encodeURIComponent(url)}`}
                  >
                    Use in Harvester
                  </Button>
                )}
              </Group>

              <ScrollArea h={420} type="auto">
                {matches.length === 0 ? (
                  <Text size="sm" c="dimmed" ta="center" py="xl">
                    {selector ? "No matches found." : "Enter a selector and click Test."}
                  </Text>
                ) : (
                  <Table striped verticalSpacing="xs">
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th w={30}>#</Table.Th>
                        <Table.Th w={60}>Tag</Table.Th>
                        <Table.Th>Text content</Table.Th>
                        <Table.Th w={120}>Attributes</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {matches.map((m, i) => (
                        <Table.Tr key={i}>
                          <Table.Td><Text size="xs" c="dimmed">{i + 1}</Text></Table.Td>
                          <Table.Td>
                            <Badge size="xs" variant="light" color="violet">{m.tag}</Badge>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs" style={{ maxWidth: 400 }} truncate>
                              {m.text || "(empty)"}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs" c="dimmed" ff="monospace" truncate style={{ maxWidth: 120 }}>
                              {Object.entries(m.attributes).slice(0, 3).map(([k, v]) => `${k}="${v}"`).join(" ")}
                            </Text>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                )}
              </ScrollArea>
            </Card>
          </Grid.Col>
        </Grid>
      )}
    </Stack>
  );
}
