import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Loader,
  NumberInput,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCertificate, IconSearch } from "@tabler/icons-react";
import type { SslInspectResponse } from "../types";

function expiryColor(days: number | null, expired: boolean): string {
  if (expired) return "red";
  if (days === null) return "gray";
  if (days < 7) return "red";
  if (days < 30) return "yellow";
  return "teal";
}

function severityColor(s: string) {
  if (s === "error") return "red";
  if (s === "warning") return "yellow";
  return "blue";
}

export default function SslInspectorPage() {
  const [hostname, setHostname] = useState("");
  const [port, setPort] = useState<number>(443);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SslInspectResponse | null>(null);

  const onInspect = async () => {
    if (!hostname.trim()) return;
    try {
      setLoading(true);
      const r = await fetch("/api/ssl/inspect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hostname: hostname.trim(), port }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data: SslInspectResponse = await r.json();
      setResult(data);
    } catch (e: any) {
      notifications.show({ title: "Inspeksi gagal", message: e?.message || "Gagal", color: "red" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconCertificate size={26} />
          <Title order={2}>SSL Certificate Inspector</Title>
        </Group>
        <Text c="dimmed" size="sm">Periksa sertifikat TLS, masa berlaku, dan SAN</Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="Hostname atau URL"
            placeholder="contoh.com atau https://contoh.com"
            value={hostname}
            onChange={(e) => setHostname(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onInspect()}
            style={{ flex: 1, minWidth: 260 }}
          />
          <NumberInput label="Port" value={port} onChange={(v) => setPort(typeof v === "number" ? v : 443)} min={1} max={65535} w={120} />
          <Button color="cyan" leftSection={<IconSearch size={16} />} onClick={onInspect} loading={loading}>
            Inspect
          </Button>
        </Group>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="cyan" />
          <Text c="dimmed" size="sm">Menghubungi host...</Text>
        </Group>
      )}

      {result && !loading && (
        <Stack gap="md">
          <Card withBorder radius="lg" p="lg">
            <Group align="center" wrap="wrap">
              <div
                style={{
                  width: 150,
                  height: 150,
                  borderRadius: 75,
                  background: `var(--mantine-color-${expiryColor(result.days_until_expiry, result.is_expired)}-6)`,
                  color: "white",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                }}
              >
                <Text c="white" size="xl" fw={800}>
                  {result.is_expired ? "EXPIRED" : `${result.days_until_expiry ?? "?"}`}
                </Text>
                <Text c="white" size="xs">{result.is_expired ? "" : "hari lagi"}</Text>
              </div>
              <Stack gap={4} style={{ flex: 1 }}>
                <Title order={4}>{result.hostname}:{result.port}</Title>
                <Group gap="xs">
                  <Badge color={result.hostname_match ? "teal" : "red"}>Hostname {result.hostname_match ? "cocok" : "tidak cocok"}</Badge>
                  {result.is_self_signed && <Badge color="yellow">Self-signed</Badge>}
                  {result.tls_version && <Badge color="blue" variant="light">{result.tls_version}</Badge>}
                </Group>
                <Text size="sm" c="dimmed">Berlaku sampai: {result.valid_to || "-"}</Text>
              </Stack>
            </Group>
          </Card>

          <Grid>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Card withBorder radius="lg" p="md">
                <Title order={4} mb="sm">Subject</Title>
                <Table>
                  <Table.Tbody>
                    {Object.entries(result.subject).map(([k, v]) => (
                      <Table.Tr key={k}><Table.Td><b>{k}</b></Table.Td><Table.Td>{v}</Table.Td></Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Card>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Card withBorder radius="lg" p="md">
                <Title order={4} mb="sm">Issuer</Title>
                <Table>
                  <Table.Tbody>
                    {Object.entries(result.issuer).map(([k, v]) => (
                      <Table.Tr key={k}><Table.Td><b>{k}</b></Table.Td><Table.Td>{v}</Table.Td></Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Card>
            </Grid.Col>
          </Grid>

          <Card withBorder radius="lg" p="md">
            <Title order={4} mb="sm">Detail Sertifikat</Title>
            <Table>
              <Table.Tbody>
                <Table.Tr><Table.Td><b>Valid from</b></Table.Td><Table.Td>{result.valid_from || "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>Valid to</b></Table.Td><Table.Td>{result.valid_to || "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>Serial</b></Table.Td><Table.Td style={{ fontFamily: "monospace", fontSize: 12 }}>{result.serial_number || "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>Version</b></Table.Td><Table.Td>{result.version ?? "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>TLS</b></Table.Td><Table.Td>{result.tls_version || "-"}</Table.Td></Table.Tr>
                <Table.Tr><Table.Td><b>Cipher</b></Table.Td><Table.Td>{result.cipher ? `${result.cipher.name} (${result.cipher.bits} bit)` : "-"}</Table.Td></Table.Tr>
              </Table.Tbody>
            </Table>
          </Card>

          {result.san.length > 0 && (
            <Card withBorder radius="lg" p="md">
              <Title order={4} mb="sm">Subject Alternative Names</Title>
              <Group gap="xs">
                {result.san.map((s) => (
                  <Badge key={s} color="cyan" variant="light">{s}</Badge>
                ))}
              </Group>
            </Card>
          )}

          {result.issues.length > 0 && (
            <Card withBorder radius="lg" p="md">
              <Title order={4} mb="sm">Isu</Title>
              <Stack gap="xs">
                {result.issues.map((i, idx) => (
                  <Alert key={idx} color={severityColor(i.severity)} variant="light">
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
