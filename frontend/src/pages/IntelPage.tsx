import { useMemo, useState } from "react";
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconExternalLink,
  IconMail,
  IconSearch,
  IconWorldSearch,
} from "@tabler/icons-react";
import type { DomainIntelResponse, EmailSecurityRecord } from "../types";

function gradeColor(g: string) {
  if (g === "A") return "teal";
  if (g === "B") return "cyan";
  if (g === "C") return "yellow";
  if (g === "D") return "orange";
  return "red";
}

function policyColor(p: string | null | undefined) {
  if (p === "reject" || p === "fail" || p === "-all") return "teal";
  if (p === "quarantine" || p === "soft_fail" || p === "~all") return "lime";
  if (p === "none" || p === "neutral" || p === "?all") return "yellow";
  if (p === "pass" || p === "+all") return "red";
  return "gray";
}

function EmailSecurityCard({ es }: { es: EmailSecurityRecord }) {
  const allWarnings = [
    ...(es.spf?.warnings || []),
    ...(es.dmarc?.warnings || []),
  ];
  return (
    <Card withBorder radius="lg" p="md">
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          <IconMail size={20} />
          <Title order={4}>Email Security</Title>
        </Group>
        <Badge color={gradeColor(es.grade)} size="lg" variant="filled">
          Grade {es.grade}
        </Badge>
      </Group>

      <Table withRowBorders={false}>
        <Table.Tbody>
          <Table.Tr>
            <Table.Td fw={600} w={120}>
              SPF
            </Table.Td>
            <Table.Td>
              <Group gap="xs">
                {es.spf.found ? (
                  <Badge color="teal" variant="light">
                    ditemukan
                  </Badge>
                ) : (
                  <Badge color="red" variant="light">
                    tidak ada
                  </Badge>
                )}
                {es.spf.all_directive && (
                  <Badge color={policyColor(es.spf.all_directive)} variant="filled">
                    {es.spf.all_directive}
                  </Badge>
                )}
                {es.spf.found && (
                  <Text size="xs" c="dimmed">
                    {es.spf.includes.length} include
                  </Text>
                )}
              </Group>
              {es.spf.raw && (
                <Text
                  size="xs"
                  ff="monospace"
                  c="dimmed"
                  mt={4}
                  style={{ wordBreak: "break-all" }}
                >
                  {es.spf.raw}
                </Text>
              )}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td fw={600}>DMARC</Table.Td>
            <Table.Td>
              <Group gap="xs">
                {es.dmarc.found ? (
                  <Badge color="teal" variant="light">
                    ditemukan
                  </Badge>
                ) : (
                  <Badge color="red" variant="light">
                    tidak ada
                  </Badge>
                )}
                {es.dmarc.policy && (
                  <Badge color={policyColor(es.dmarc.policy)} variant="filled">
                    p={es.dmarc.policy}
                  </Badge>
                )}
                {es.dmarc.pct !== null && es.dmarc.pct !== undefined && (
                  <Text size="xs" c="dimmed">
                    pct={es.dmarc.pct}
                  </Text>
                )}
              </Group>
              {es.dmarc.raw && (
                <Text
                  size="xs"
                  ff="monospace"
                  c="dimmed"
                  mt={4}
                  style={{ wordBreak: "break-all" }}
                >
                  {es.dmarc.raw}
                </Text>
              )}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td fw={600}>DKIM</Table.Td>
            <Table.Td>
              {es.dkim.selectors_found.length === 0 ? (
                <Text size="sm" c="dimmed">
                  Tidak ditemukan dari {es.dkim.selectors_checked.length} selector yang dicek
                </Text>
              ) : (
                <Group gap={4}>
                  {es.dkim.selectors_found.map((s) => (
                    <Badge key={s} color="teal" variant="light">
                      {s}
                    </Badge>
                  ))}
                </Group>
              )}
            </Table.Td>
          </Table.Tr>
        </Table.Tbody>
      </Table>

      {allWarnings.length > 0 && (
        <Alert color="yellow" mt="sm" title="Catatan">
          <Stack gap={2}>
            {allWarnings.map((w, i) => (
              <Text key={i} size="sm">
                {w}
              </Text>
            ))}
          </Stack>
        </Alert>
      )}
    </Card>
  );
}

export default function IntelPage() {
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DomainIntelResponse | null>(null);
  const [filter, setFilter] = useState("");

  const onAnalyze = async () => {
    if (!domain.trim()) return;
    try {
      setLoading(true);
      const r = await fetch("/api/intel/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: domain.trim() }),
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }
      const data: DomainIntelResponse = await r.json();
      setResult(data);
    } catch (e: any) {
      notifications.show({
        title: "Analisis gagal",
        message: e?.message || "Tidak dapat menganalisis domain",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  const filteredSubs = useMemo(() => {
    if (!result) return [];
    const q = filter.trim().toLowerCase();
    return q ? result.subdomains.filter((s) => s.includes(q)) : result.subdomains;
  }, [result, filter]);

  const dnsEntries = useMemo(() => {
    if (!result) return [] as [string, string[]][];
    return Object.entries(result.dns).filter(([k]) => !k.startsWith("_")) as [
      string,
      string[],
    ][];
  }, [result]);

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconWorldSearch size={26} />
          <Title order={2}>Domain Intel</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Lookup WHOIS, DNS, dan subdomain dalam satu tarikan napas
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Group align="flex-end" wrap="wrap">
          <TextInput
            label="Domain target"
            placeholder="contoh.com"
            value={domain}
            onChange={(e) => setDomain(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && onAnalyze()}
            style={{ flex: 1, minWidth: 260 }}
          />
          <Button
            color="cyan"
            leftSection={<IconSearch size={16} />}
            onClick={onAnalyze}
            loading={loading}
          >
            Analisis
          </Button>
        </Group>
      </Card>

      {loading && (
        <Group justify="center" py="xl">
          <Loader color="cyan" />
          <Text c="dimmed" size="sm">
            Mengumpulkan intel untuk {domain}...
          </Text>
        </Group>
      )}

      {result && !loading && result.email_security && (
        <EmailSecurityCard es={result.email_security} />
      )}

      {result && !loading && (
        <Card withBorder radius="lg" p="md">
          <Tabs defaultValue="whois">
            <Tabs.List>
              <Tabs.Tab value="whois">WHOIS</Tabs.Tab>
              <Tabs.Tab value="dns">
                DNS{" "}
                <Badge ml={6} size="xs" color="gray" variant="light">
                  {dnsEntries.filter(([, v]) => v.length > 0).length}
                </Badge>
              </Tabs.Tab>
              <Tabs.Tab value="subs">
                Subdomain{" "}
                <Badge ml={6} size="xs" color="gray" variant="light">
                  {result.subdomain_count}
                </Badge>
              </Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="whois" pt="md">
              {result.whois?.error ? (
                <Text c="red" size="sm">
                  {result.whois.error}
                </Text>
              ) : result.whois?.registered === false ? (
                <Text c="dimmed">Domain tidak terdaftar (atau tidak terindeks RDAP).</Text>
              ) : (
                <Table striped withRowBorders={false}>
                  <Table.Tbody>
                    <Table.Tr>
                      <Table.Td fw={600} w={220}>
                        Registrar
                      </Table.Td>
                      <Table.Td>{result.whois?.registrar || "—"}</Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td fw={600}>Tanggal registrasi</Table.Td>
                      <Table.Td>{result.whois?.registration_date || "—"}</Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td fw={600}>Tanggal kedaluwarsa</Table.Td>
                      <Table.Td>{result.whois?.expiration_date || "—"}</Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td fw={600}>Update terakhir</Table.Td>
                      <Table.Td>{result.whois?.last_updated || "—"}</Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td fw={600}>Nameservers</Table.Td>
                      <Table.Td>
                        <Stack gap={2}>
                          {(result.whois?.nameservers || []).map((ns) => (
                            <Text key={ns} ff="monospace" size="sm">
                              {ns}
                            </Text>
                          ))}
                          {(!result.whois?.nameservers ||
                            result.whois.nameservers.length === 0) && "—"}
                        </Stack>
                      </Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td fw={600}>Status</Table.Td>
                      <Table.Td>
                        <Group gap={4}>
                          {(result.whois?.status || []).map((s) => (
                            <Badge key={s} size="xs" variant="light" color="gray">
                              {s}
                            </Badge>
                          ))}
                          {(!result.whois?.status || result.whois.status.length === 0) &&
                            "—"}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td fw={600}>Negara registrant</Table.Td>
                      <Table.Td>{result.whois?.registrant_country || "—"}</Table.Td>
                    </Table.Tr>
                  </Table.Tbody>
                </Table>
              )}
            </Tabs.Panel>

            <Tabs.Panel value="dns" pt="md">
              <Stack gap="sm">
                {dnsEntries.length === 0 && (
                  <Text c="dimmed">Tidak ada record DNS ditemukan.</Text>
                )}
                {dnsEntries.map(([rtype, values]) => (
                  <Card key={rtype} withBorder radius="md" p="sm">
                    <Group justify="space-between" mb="xs">
                      <Text fw={600}>{rtype}</Text>
                      <Badge color="gray" variant="light">
                        {values.length}
                      </Badge>
                    </Group>
                    {values.length === 0 ? (
                      <Text size="xs" c="dimmed">
                        (tidak ada)
                      </Text>
                    ) : (
                      <Stack gap={2}>
                        {values.map((v, i) => (
                          <Text key={i} size="sm" ff="monospace" style={{ wordBreak: "break-all" }}>
                            {v}
                          </Text>
                        ))}
                      </Stack>
                    )}
                  </Card>
                ))}
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="subs" pt="md">
              <Stack gap="sm">
                <TextInput
                  placeholder="Filter subdomain..."
                  value={filter}
                  onChange={(e) => setFilter(e.currentTarget.value)}
                />
                <Text size="xs" c="dimmed">
                  Menampilkan {filteredSubs.length} dari {result.subdomain_count} subdomain
                </Text>
                {filteredSubs.length === 0 ? (
                  <Text c="dimmed">Tidak ada subdomain ditemukan di crt.sh.</Text>
                ) : (
                  <Stack gap={2}>
                    {filteredSubs.map((s) => (
                      <Group key={s} gap="xs">
                        <Anchor
                          href={`https://${s}`}
                          target="_blank"
                          rel="noreferrer"
                          size="sm"
                          ff="monospace"
                        >
                          {s}
                        </Anchor>
                        <IconExternalLink size={12} />
                      </Group>
                    ))}
                  </Stack>
                )}
              </Stack>
            </Tabs.Panel>
          </Tabs>
        </Card>
      )}
    </Stack>
  );
}
