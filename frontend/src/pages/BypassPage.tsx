import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Code,
  Group,
  ScrollArea,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconArrowRight, IconLink, IconList } from "@tabler/icons-react";

interface Result {
  original: string;
  final: string;
  chain: string[];
  method: string;
  error: string | null;
}

export default function BypassPage() {
  const [singleUrl, setSingleUrl] = useState("");
  const [batchUrls, setBatchUrls] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);

  const onSingle = async () => {
    if (!singleUrl.trim()) return;
    try {
      setLoading(true);
      const r = await fetch("/api/bypass/single", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: singleUrl }),
      });
      const d = await r.json();
      setResults([d]);
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setLoading(false);
    }
  };

  const onBatch = async () => {
    const urls = batchUrls.split("\n").map((u) => u.trim()).filter((u) => u.startsWith("http"));
    if (urls.length === 0) return;
    try {
      setLoading(true);
      const r = await fetch("/api/bypass/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls }),
      });
      const d = await r.json();
      setResults(d);
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setLoading(false);
    }
  };

  const methodColor: Record<string, string> = {
    redirect: "teal",
    "adf.ly": "violet",
    "ouo.io": "pink",
    linkvertise: "orange",
    "shrinkme.io": "cyan",
    generic_js: "yellow",
    failed: "red",
  };

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Link Bypass</Title>
        <Text c="dimmed" size="sm">
          Resolve shortened URLs and bypass ad-gateways (adf.ly, ouo.io, linkvertise, etc.)
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Text fw={600} mb="sm">Single URL</Text>
        <Group align="flex-end">
          <TextInput
            placeholder="https://bit.ly/abc123 or https://adf.ly/xyz"
            value={singleUrl}
            onChange={(e) => setSingleUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onSingle()}
            style={{ flex: 1 }}
          />
          <Button leftSection={<IconLink size={16} />} onClick={onSingle} loading={loading}>
            Resolve
          </Button>
        </Group>
      </Card>

      <Card withBorder radius="lg" p="lg">
        <Text fw={600} mb="sm">Batch (one URL per line)</Text>
        <Textarea
          placeholder={"https://bit.ly/abc\nhttps://adf.ly/xyz\nhttps://ouo.io/abc"}
          value={batchUrls}
          onChange={(e) => setBatchUrls(e.currentTarget.value)}
          minRows={4}
          maxRows={10}
          autosize
        />
        <Button mt="sm" leftSection={<IconList size={16} />} onClick={onBatch} loading={loading} variant="light">
          Resolve all ({batchUrls.split("\n").filter((u) => u.trim().startsWith("http")).length})
        </Button>
      </Card>

      {results.length > 0 && (
        <Card withBorder radius="lg" p={0}>
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Original</Table.Th>
                <Table.Th w={80}>Method</Table.Th>
                <Table.Th>Final URL</Table.Th>
                <Table.Th w={60}>Hops</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {results.map((r, i) => (
                <Table.Tr key={i}>
                  <Table.Td style={{ maxWidth: 250 }}>
                    <Text size="xs" ff="monospace" truncate>{r.original}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={methodColor[r.method] || "gray"} variant="light" size="sm">
                      {r.method}
                    </Badge>
                  </Table.Td>
                  <Table.Td style={{ maxWidth: 400 }}>
                    {r.error ? (
                      <Text size="xs" c="red">{r.error}</Text>
                    ) : (
                      <Group gap={4} wrap="nowrap">
                        <Text size="xs" ff="monospace" c="teal" truncate style={{ flex: 1 }}>
                          {r.final}
                        </Text>
                        <CopyBtn text={r.final} />
                      </Group>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">{r.chain.length}</Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
}

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      size="compact-xs"
      variant="subtle"
      color={copied ? "teal" : "gray"}
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
    >
      {copied ? "Copied!" : "Copy"}
    </Button>
  );
}
