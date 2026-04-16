import { Alert, Badge, Card, Group, ScrollArea, Stack, Text } from "@mantine/core";
import { IconAlertTriangle, IconCheck } from "@tabler/icons-react";

import type { SitemapGraphNode } from "../types";

function statusColor(code: number | null): string {
  if (!code) return "gray";
  if (code < 400) return "teal";
  if (code < 500) return "orange";
  return "red";
}

export default function BrokenLinksPanel({ nodes }: { nodes: SitemapGraphNode[] }) {
  const broken = nodes.filter((n) => n.status_code && n.status_code >= 400);

  if (broken.length === 0) {
    return (
      <Alert
        icon={<IconCheck size={16} />}
        color="teal"
        variant="light"
        title="Tidak ada broken link"
      >
        Semua URL yang berhasil di-crawl mengembalikan status 2xx/3xx.
      </Alert>
    );
  }

  return (
    <Card withBorder radius="lg" p="lg">
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          <IconAlertTriangle size={18} color="var(--mantine-color-red-5)" />
          <Text fw={700}>Broken links</Text>
        </Group>
        <Badge color="red" variant="filled">
          {broken.length}
        </Badge>
      </Group>
      <ScrollArea h={200} type="auto">
        <Stack gap={4}>
          {broken.map((n) => (
            <Group
              key={n.id}
              gap="sm"
              wrap="nowrap"
              style={{ padding: "6px 8px", borderRadius: 6, background: "rgba(239,68,68,0.06)" }}
            >
              <Badge size="sm" color={statusColor(n.status_code)} variant="filled" style={{ minWidth: 42 }}>
                {n.status_code}
              </Badge>
              <Text size="xs" style={{ flex: 1, fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {n.url}
              </Text>
              <Text size="xs" c="dimmed">
                depth {n.depth}
              </Text>
            </Group>
          ))}
        </Stack>
      </ScrollArea>
    </Card>
  );
}
