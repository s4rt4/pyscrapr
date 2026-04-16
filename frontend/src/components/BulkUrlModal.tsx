import { useState } from "react";
import { Button, Group, Modal, Select, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconList } from "@tabler/icons-react";

interface Props {
  opened: boolean;
  onClose: () => void;
  defaultTool?: string;
}

export default function BulkUrlModal({ opened, onClose, defaultTool = "media" }: Props) {
  const [tool, setTool] = useState(defaultTool);
  const [urls, setUrls] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    const list = urls
      .split("\n")
      .map((u) => u.trim())
      .filter((u) => u && u.startsWith("http"));
    if (list.length === 0) {
      notifications.show({ title: "No URLs", message: "Paste at least one valid URL", color: "yellow" });
      return;
    }
    try {
      setLoading(true);
      const r = await fetch("/api/bulk/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls: list, tool, config: {} }),
      });
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      notifications.show({
        title: "Bulk submitted",
        message: `${d.count} job(s) queued`,
        color: "teal",
      });
      setUrls("");
      onClose();
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setLoading(false);
    }
  };

  const count = urls
    .split("\n")
    .filter((u) => u.trim().startsWith("http")).length;

  return (
    <Modal opened={opened} onClose={onClose} title="Bulk URL Queue" centered size="lg">
      <Stack gap="md">
        <Select
          label="Tool"
          value={tool}
          onChange={(v) => setTool(v || "media")}
          data={[
            { value: "harvester", label: "Image Harvester" },
            { value: "mapper", label: "URL Mapper" },
            { value: "ripper", label: "Site Ripper" },
            { value: "media", label: "Media Downloader" },
          ]}
        />
        <Textarea
          label="URLs (one per line)"
          placeholder={"https://www.youtube.com/watch?v=abc123\nhttps://www.youtube.com/watch?v=def456\nhttps://www.youtube.com/watch?v=ghi789"}
          value={urls}
          onChange={(e) => setUrls(e.currentTarget.value)}
          minRows={6}
          maxRows={15}
          autosize
        />
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            {count} URL{count !== 1 ? "s" : ""} detected
          </Text>
          <Button
            leftSection={<IconList size={16} />}
            onClick={onSubmit}
            loading={loading}
            disabled={count === 0}
          >
            Queue {count} job{count !== 1 ? "s" : ""}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
