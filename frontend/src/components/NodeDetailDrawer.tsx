import { Anchor, Badge, Code, Drawer, Group, Stack, Text, Title } from "@mantine/core";
import { IconExternalLink } from "@tabler/icons-react";

export interface NodeDetail {
  id: number;
  url: string;
  status: number | null;
  title: string | null;
  depth?: number;
}

interface Props {
  node: NodeDetail | null;
  opened: boolean;
  onClose: () => void;
}

function statusColor(code: number | null): string {
  if (!code) return "gray";
  if (code < 300) return "teal";
  if (code < 400) return "yellow";
  if (code < 500) return "orange";
  return "red";
}

export default function NodeDetailDrawer({ node, opened, onClose }: Props) {
  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="md"
      title={<Text fw={700}>Page detail</Text>}
    >
      {node ? (
        <Stack gap="md">
          <Group>
            <Badge color={statusColor(node.status)} variant="filled" size="lg">
              {node.status ?? "-"}
            </Badge>
            {typeof node.depth === "number" && (
              <Badge color="gray" variant="light">
                depth {node.depth}
              </Badge>
            )}
          </Group>

          {node.title && (
            <div>
              <Text size="xs" c="dimmed" tt="uppercase" fw={700} mb={2}>
                Title
              </Text>
              <Title order={4}>{node.title}</Title>
            </div>
          )}

          <div>
            <Text size="xs" c="dimmed" tt="uppercase" fw={700} mb={2}>
              URL
            </Text>
            <Code block style={{ fontSize: 11 }}>
              {node.url}
            </Code>
          </div>

          <Anchor
            href={node.url}
            target="_blank"
            rel="noopener noreferrer"
            size="sm"
          >
            <Group gap={4}>
              <IconExternalLink size={14} />
              Open in browser
            </Group>
          </Anchor>
        </Stack>
      ) : (
        <Text c="dimmed">No node selected.</Text>
      )}
    </Drawer>
  );
}
