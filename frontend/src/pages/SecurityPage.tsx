import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconSearch, IconShieldCheck } from "@tabler/icons-react";
import type { SecurityScanResponse } from "../types";

function gradeColor(g: string) {
  if (g === "A") return "teal";
  if (g === "B") return "lime";
  if (g === "C") return "yellow";
  if (g === "D") return "orange";
  return "red";
}

function severityColor(s: string) {
  if (s === "error") return "red";
  if (s === "warning") return "yellow";
  return "blue";
}

export default function SecurityPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SecurityScanResponse | null>(null);

  const onScan = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      const r = await fetch("/api/security/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data: SecurityScanResponse = await r.json();
      setResult(data);
    } catch (e: any) {
      notifications.show({ title: "Scan gagal", message: e?.message || "Gagal", color: "red" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconShieldCheck size={26} />
          <Title order={2}>Security Headers Scanner</Title>
        </Group>
        <Text c="dimmed" size="sm">Cek header keamanan dan flag cookie</Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="URL target"
            placeholder="https://contoh.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onScan()}
            style={{ flex: 1, minWidth: 260 }}
          />
          <Button color="cyan" leftSection={<IconSearch size={16} />} onClick={onScan} loading={loading}>
            Scan
          </Button>
        </Group>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="cyan" />
          <Text c="dimmed" size="sm">Memeriksa header...</Text>
        </Group>
      )}

      {result && !loading && (
        <Stack gap="md">
          <Card withBorder radius="lg" p="lg">
            <Group align="center" wrap="wrap">
              <div
                style={{
                  width: 120,
                  height: 120,
                  borderRadius: 60,
                  background: `var(--mantine-color-${gradeColor(result.grade)}-6)`,
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 64,
                  fontWeight: 700,
                }}
              >
                {result.grade}
              </div>
              <Stack gap={4} style={{ flex: 1 }}>
                <Title order={3}>Skor: {result.score} / 100</Title>
                <Text size="sm" c="dimmed">
                  {result.headers_missing.length} header hilang, {result.cookies.length} cookie terdeteksi
                </Text>
              </Stack>
            </Group>
          </Card>

          <Grid>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Card withBorder radius="lg" p="md">
                <Title order={4} mb="sm">Header Ditemukan</Title>
                {Object.keys(result.headers_found).length === 0 ? (
                  <Text c="dimmed" size="sm">Tidak ada header security</Text>
                ) : (
                  <Table>
                    <Table.Tbody>
                      {Object.entries(result.headers_found).map(([k, v]) => (
                        <Table.Tr key={k}>
                          <Table.Td><Badge color="teal" variant="light">{k}</Badge></Table.Td>
                          <Table.Td style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all" }}>{v}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                )}
              </Card>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Card withBorder radius="lg" p="md">
                <Title order={4} mb="sm">Header Hilang</Title>
                {result.headers_missing.length === 0 ? (
                  <Text c="dimmed" size="sm">Semua header penting ada</Text>
                ) : (
                  <Stack gap={4}>
                    {result.headers_missing.map((h) => (
                      <Badge key={h} color="red" variant="light" size="lg">{h}</Badge>
                    ))}
                  </Stack>
                )}
              </Card>
            </Grid.Col>
          </Grid>

          {result.cookies.length > 0 && (
            <Card withBorder radius="lg" p="md">
              <Title order={4} mb="sm">Cookie</Title>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Nama</Table.Th>
                    <Table.Th>HttpOnly</Table.Th>
                    <Table.Th>Secure</Table.Th>
                    <Table.Th>SameSite</Table.Th>
                    <Table.Th>Path</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {result.cookies.map((c, i) => (
                    <Table.Tr key={i}>
                      <Table.Td style={{ fontFamily: "monospace" }}>{c.name}</Table.Td>
                      <Table.Td>{c.httponly ? <Badge color="teal">yes</Badge> : <Badge color="red">no</Badge>}</Table.Td>
                      <Table.Td>{c.secure ? <Badge color="teal">yes</Badge> : <Badge color="red">no</Badge>}</Table.Td>
                      <Table.Td>{c.samesite || <Badge color="yellow">none</Badge>}</Table.Td>
                      <Table.Td>{c.path}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Card>
          )}

          {result.issues.length > 0 && (
            <Card withBorder radius="lg" p="md">
              <Title order={4} mb="sm">Rekomendasi</Title>
              <Stack gap="xs">
                {result.issues.map((i, idx) => (
                  <Alert key={idx} color={severityColor(i.severity)} title={i.header} variant="light">
                    {i.message}
                  </Alert>
                ))}
              </Stack>
            </Card>
          )}
        </Stack>
      )}
    </Stack>
  );
}
