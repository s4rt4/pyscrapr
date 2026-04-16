import { useEffect, useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  JsonInput,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDownload, IconPlus, IconTrash } from "@tabler/icons-react";
import { timeAgo } from "../lib/utils";

interface Profile {
  domain: string;
  cookies: Record<string, string>;
  headers: Record<string, string>;
  notes: string;
  updated_at: string;
}

export default function VaultPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  // Create form
  const [domain, setDomain] = useState("");
  const [cookies, setCookies] = useState("{}");
  const [headers, setHeaders] = useState("{}");
  const [notes, setNotes] = useState("");

  // Import form
  const [importBrowser, setImportBrowser] = useState("chrome");
  const [importDomain, setImportDomain] = useState("");

  const refresh = () =>
    fetch("/api/vault/profiles")
      .then((r) => r.json())
      .then(setProfiles)
      .catch((e) => console.error(e));

  useEffect(() => { refresh(); }, []);

  const onCreate = async () => {
    try {
      await fetch("/api/vault/profiles", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain,
          cookies: JSON.parse(cookies),
          headers: JSON.parse(headers),
          notes,
        }),
      });
      notifications.show({ title: "Saved", message: `Profile for ${domain}`, color: "teal" });
      setCreateOpen(false);
      setDomain("");
      setCookies("{}");
      setHeaders("{}");
      setNotes("");
      refresh();
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    }
  };

  const onDelete = async (d: string) => {
    await fetch(`/api/vault/profiles/${d}`, { method: "DELETE" });
    refresh();
  };

  const onImport = async () => {
    try {
      const r = await fetch("/api/vault/import-cookies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ browser: importBrowser, domain_filter: importDomain }),
      });
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      notifications.show({
        title: "Imported",
        message: `${d.total_cookies} cookies from ${d.domains} domains`,
        color: "teal",
      });
      setImportOpen(false);
      refresh();
    } catch (e: any) {
      notifications.show({ title: "Import failed", message: e.message, color: "red" });
    }
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Auth Vault</Title>
          <Text c="dimmed" size="sm">
            Store per-site cookies, headers, and tokens for authenticated scraping.
          </Text>
        </div>
        <Group>
          <Button variant="light" leftSection={<IconDownload size={16} />} onClick={() => setImportOpen(true)}>
            Import from browser
          </Button>
          <Button leftSection={<IconPlus size={16} />} onClick={() => setCreateOpen(true)}>
            Add profile
          </Button>
        </Group>
      </Group>

      <Card withBorder radius="lg" p={0}>
        <Table striped highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Domain</Table.Th>
              <Table.Th>Cookies</Table.Th>
              <Table.Th>Headers</Table.Th>
              <Table.Th>Notes</Table.Th>
              <Table.Th>Updated</Table.Th>
              <Table.Th w={50}></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {profiles.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text c="dimmed" size="sm" ta="center" py="md">
                    No profiles yet. Add one manually or import from browser.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
            {profiles.map((p) => (
              <Table.Tr key={p.domain}>
                <Table.Td>
                  <Text size="sm" fw={600}>{p.domain}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge size="sm" variant="light">
                    {Object.keys(p.cookies).length}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Badge size="sm" variant="light" color="violet">
                    {Object.keys(p.headers).length}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed" truncate style={{ maxWidth: 200 }}>
                    {p.notes || "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {timeAgo(p.updated_at)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Tooltip label="Delete">
                    <ActionIcon variant="subtle" color="red" size="sm" onClick={() => { if (window.confirm("Delete profile for " + p.domain + "?")) onDelete(p.domain); }} aria-label="Delete profile">
                      <IconTrash size={14} />
                    </ActionIcon>
                  </Tooltip>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Create modal */}
      <Modal opened={createOpen} onClose={() => setCreateOpen(false)} title="Add auth profile" centered>
        <Stack gap="md">
          <TextInput label="Domain" placeholder="instagram.com" value={domain} onChange={(e) => setDomain(e.currentTarget.value)} />
          <JsonInput label="Cookies (JSON)" value={cookies} onChange={setCookies} minRows={3} formatOnBlur autosize />
          <JsonInput label="Headers (JSON)" value={headers} onChange={setHeaders} minRows={2} formatOnBlur autosize />
          <TextInput label="Notes" value={notes} onChange={(e) => setNotes(e.currentTarget.value)} />
          <Button onClick={onCreate}>Save profile</Button>
        </Stack>
      </Modal>

      {/* Import modal */}
      <Modal opened={importOpen} onClose={() => setImportOpen(false)} title="Import cookies from browser" centered>
        <Stack gap="md">
          <Select
            label="Browser"
            value={importBrowser}
            onChange={(v) => setImportBrowser(v || "chrome")}
            data={[
              { value: "chrome", label: "Chrome" },
              { value: "firefox", label: "Firefox" },
              { value: "edge", label: "Edge" },
              { value: "brave", label: "Brave" },
            ]}
          />
          <TextInput
            label="Domain filter (optional)"
            placeholder="instagram.com (leave empty for all)"
            value={importDomain}
            onChange={(e) => setImportDomain(e.currentTarget.value)}
          />
          <Button onClick={onImport}>Import cookies</Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
