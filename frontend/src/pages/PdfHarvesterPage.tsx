import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActionIcon,
  Anchor,
  Badge,
  Box,
  Button,
  Card,
  Code,
  Group,
  Modal,
  NumberInput,
  Progress,
  ScrollArea,
  Slider,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconDownload,
  IconFileTypePdf,
  IconInfoCircle,
  IconSearch,
} from "@tabler/icons-react";
import type { PdfDocument, PdfHarvestReport, PdfSearchHit } from "../types";

function formatBytes(n: number): string {
  if (!n) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(1)} ${units[i]}`;
}

export default function PdfHarvesterPage() {
  const [url, setUrl] = useState("");
  const [maxDepth, setMaxDepth] = useState(2);
  const [maxPages, setMaxPages] = useState(50);
  const [maxPdfs, setMaxPdfs] = useState(100);
  const [download, setDownload] = useState(true);
  const [extractText, setExtractText] = useState(true);

  const [scanning, setScanning] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [pagesCrawled, setPagesCrawled] = useState(0);
  const [pdfsFound, setPdfsFound] = useState(0);
  const [pdfsDownloaded, setPdfsDownloaded] = useState(0);
  const [report, setReport] = useState<PdfHarvestReport | null>(null);

  const [filterText, setFilterText] = useState("");
  const [authorFilter, setAuthorFilter] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [searchHits, setSearchHits] = useState<PdfSearchHit[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [modalDoc, setModalDoc] = useState<PdfDocument | null>(null);

  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      if (sseRef.current) sseRef.current.close();
    };
  }, []);

  const startScan = async () => {
    if (!url.trim()) return;
    setScanning(true);
    setReport(null);
    setSearchHits(null);
    setPagesCrawled(0);
    setPdfsFound(0);
    setPdfsDownloaded(0);

    try {
      const r = await fetch("/api/pdf-harvester/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          max_depth: maxDepth,
          max_pages: maxPages,
          max_pdfs: maxPdfs,
          download,
          extract_text: extractText,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setJobId(data.job_id);
      subscribeSSE(data.job_id);
    } catch (e: any) {
      setScanning(false);
      notifications.show({
        title: "Scan gagal",
        message: e?.message || "Tidak dapat memulai scan",
        color: "red",
      });
    }
  };

  const subscribeSSE = (id: string) => {
    if (sseRef.current) sseRef.current.close();
    const es = new EventSource(`/api/pdf-harvester/scan/events/${id}`);
    sseRef.current = es;
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "progress") {
          if (typeof data.pages_crawled === "number") setPagesCrawled(data.pages_crawled);
          if (typeof data.pdfs_found === "number") setPdfsFound(data.pdfs_found);
          if (typeof data.pdfs_downloaded === "number") setPdfsDownloaded(data.pdfs_downloaded);
        } else if (data.type === "done") {
          es.close();
          sseRef.current = null;
          fetchReport(id);
        } else if (data.type === "error") {
          es.close();
          sseRef.current = null;
          setScanning(false);
          notifications.show({ title: "Scan error", message: data.message, color: "red" });
        }
      } catch {
        // ignore
      }
    };
    es.onerror = () => {
      es.close();
      sseRef.current = null;
      fetchReport(id);
    };
  };

  const fetchReport = async (id: string) => {
    try {
      const r = await fetch(`/api/pdf-harvester/scan/${id}`);
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      if (data.report) setReport(data.report as PdfHarvestReport);
    } catch (e: any) {
      notifications.show({
        title: "Gagal mengambil laporan",
        message: e?.message || "",
        color: "red",
      });
    } finally {
      setScanning(false);
    }
  };

  const runSearch = async () => {
    if (!jobId || !searchQ.trim()) {
      setSearchHits(null);
      return;
    }
    setSearching(true);
    try {
      const r = await fetch(
        `/api/pdf-harvester/scan/${jobId}/search?q=${encodeURIComponent(searchQ.trim())}`,
      );
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setSearchHits(data.hits || []);
    } catch (e: any) {
      notifications.show({
        title: "Pencarian gagal",
        message: e?.message || "",
        color: "red",
      });
    } finally {
      setSearching(false);
    }
  };

  const visibleDocs = useMemo(() => {
    if (!report) return [];
    let list = report.documents;
    if (filterText.trim()) {
      const q = filterText.trim().toLowerCase();
      list = list.filter(
        (d) =>
          (d.filename || "").toLowerCase().includes(q) ||
          (d.title || "").toLowerCase().includes(q) ||
          (d.url || "").toLowerCase().includes(q),
      );
    }
    if (authorFilter.trim()) {
      const q = authorFilter.trim().toLowerCase();
      list = list.filter((d) => (d.author || "").toLowerCase().includes(q));
    }
    if (searchHits) {
      const ids = new Set(searchHits.map((h) => h.pdf_id));
      list = list.filter((d) => ids.has(d.pdf_id));
    }
    return list;
  }, [report, filterText, authorFilter, searchHits]);

  const downloadCsv = () => {
    if (!jobId) return;
    window.open(`/api/pdf-harvester/scan/${jobId}/export.csv`, "_blank");
  };

  const totalSize = report?.stats.total_size ?? 0;
  const uniqueAuthors = report?.stats.unique_authors ?? 0;

  return (
    <Stack gap="md">
      <div>
        <Group gap="xs">
          <IconFileTypePdf size={26} color="var(--mantine-color-pink-5)" />
          <Title order={2}>PDF Harvester</Title>
        </Group>
        <Text c="dimmed" size="sm">
          Telusuri situs untuk file PDF, unduh otomatis, ekstrak metadata dan pratinjau teks.
        </Text>
      </div>

      <Card withBorder radius="lg" p="lg">
        <Stack gap="md">
          <TextInput
            label="URL target"
            placeholder="https://contoh.com"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            onKeyDown={(e) => e.key === "Enter" && !scanning && startScan()}
          />

          <Box>
            <Text size="sm" fw={500} mb={4}>Kedalaman crawl: {maxDepth}</Text>
            <Slider value={maxDepth} onChange={setMaxDepth} min={0} max={4} step={1}
              marks={[{ value: 0, label: "0" }, { value: 2, label: "2" }, { value: 4, label: "4" }]}
              mb={24} />
          </Box>

          <Group grow mt="sm">
            <NumberInput
              label="Maks halaman crawl"
              value={maxPages}
              onChange={(v) => setMaxPages(typeof v === "number" ? v : 50)}
              min={1}
              max={500}
            />
            <NumberInput
              label="Maks PDF"
              value={maxPdfs}
              onChange={(v) => setMaxPdfs(typeof v === "number" ? v : 100)}
              min={1}
              max={500}
            />
          </Group>

          <Group>
            <Switch
              label="Unduh file PDF"
              checked={download}
              onChange={(e) => setDownload(e.currentTarget.checked)}
            />
            <Switch
              label="Ekstrak teks (untuk pencarian)"
              checked={extractText}
              onChange={(e) => setExtractText(e.currentTarget.checked)}
            />
          </Group>

          <Group>
            <Button
              onClick={startScan}
              loading={scanning}
              disabled={!url.trim()}
              leftSection={<IconFileTypePdf size={16} />}
              color="pink"
            >
              Mulai scan
            </Button>
          </Group>

          {scanning && (
            <Stack gap={4}>
              <Group justify="space-between">
                <Text size="sm">Halaman: {pagesCrawled} / {maxPages}</Text>
                <Text size="sm">PDF ditemukan: {pdfsFound}</Text>
                <Text size="sm">Diunduh: {pdfsDownloaded}</Text>
              </Group>
              <Progress value={Math.min(100, (pagesCrawled / maxPages) * 100)} animated />
            </Stack>
          )}
        </Stack>
      </Card>

      {report && (
        <>
          <Card withBorder radius="lg" p="lg">
            <Group justify="space-between" wrap="wrap">
              <Group gap="lg">
                <Box>
                  <Text size="xs" c="dimmed">PDF ditemukan</Text>
                  <Text fw={700} size="xl">{report.pdfs_found}</Text>
                </Box>
                <Box>
                  <Text size="xs" c="dimmed">Diunduh</Text>
                  <Text fw={700} size="xl">{report.pdfs_downloaded}</Text>
                </Box>
                <Box>
                  <Text size="xs" c="dimmed">Total ukuran</Text>
                  <Text fw={700} size="xl">{formatBytes(totalSize)}</Text>
                </Box>
                <Box>
                  <Text size="xs" c="dimmed">Penulis unik</Text>
                  <Text fw={700} size="xl">{uniqueAuthors}</Text>
                </Box>
              </Group>
              <Button variant="light" leftSection={<IconDownload size={16} />} onClick={downloadCsv}>
                Ekspor CSV
              </Button>
            </Group>
          </Card>

          <Card withBorder radius="lg" p="lg">
            <Stack gap="md">
              <Group gap="sm" wrap="wrap">
                <TextInput
                  placeholder="Cari dalam isi PDF..."
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.currentTarget.value)}
                  onKeyDown={(e) => e.key === "Enter" && runSearch()}
                  leftSection={<IconSearch size={14} />}
                  style={{ flex: 1, minWidth: 240 }}
                />
                <Button variant="light" onClick={runSearch} loading={searching}>
                  Cari teks
                </Button>
                {searchHits && (
                  <Button variant="subtle" onClick={() => { setSearchHits(null); setSearchQ(""); }}>
                    Reset
                  </Button>
                )}
                <TextInput
                  placeholder="Filter nama/judul"
                  value={filterText}
                  onChange={(e) => setFilterText(e.currentTarget.value)}
                  style={{ minWidth: 180 }}
                />
                <TextInput
                  placeholder="Filter penulis"
                  value={authorFilter}
                  onChange={(e) => setAuthorFilter(e.currentTarget.value)}
                  style={{ minWidth: 160 }}
                />
              </Group>

              {searchHits !== null && (
                <Text size="sm" c="dimmed">
                  Pencarian "{searchQ}": {searchHits.length} hasil
                </Text>
              )}

              <ScrollArea>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>File</Table.Th>
                      <Table.Th>Judul</Table.Th>
                      <Table.Th>Penulis</Table.Th>
                      <Table.Th>Halaman</Table.Th>
                      <Table.Th>Ukuran</Table.Th>
                      <Table.Th>Tanggal</Table.Th>
                      <Table.Th>Aksi</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {visibleDocs.map((d) => (
                      <Table.Tr key={d.pdf_id}>
                        <Table.Td>
                          <Tooltip label={d.url}>
                            <Text size="sm" lineClamp={1} style={{ maxWidth: 220 }}>
                              {d.filename}
                            </Text>
                          </Tooltip>
                          {d.error && (
                            <Badge color="red" size="xs" mt={2}>{d.error.slice(0, 30)}</Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" lineClamp={2} style={{ maxWidth: 220 }}>
                            {d.title || "-"}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" lineClamp={1} style={{ maxWidth: 140 }}>
                            {d.author || "-"}
                          </Text>
                        </Table.Td>
                        <Table.Td>{d.page_count ?? "-"}</Table.Td>
                        <Table.Td>{formatBytes(d.file_size)}</Table.Td>
                        <Table.Td>
                          <Text size="xs">{d.creation_date || "-"}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Group gap={4}>
                            <Tooltip label="Detail metadata">
                              <ActionIcon variant="subtle" onClick={() => setModalDoc(d)}>
                                <IconInfoCircle size={16} />
                              </ActionIcon>
                            </Tooltip>
                            {d.downloaded && jobId && (
                              <Tooltip label="Unduh PDF">
                                <ActionIcon
                                  variant="subtle"
                                  component="a"
                                  href={`/api/pdf-harvester/scan/${jobId}/file/${d.pdf_id}`}
                                  target="_blank"
                                >
                                  <IconDownload size={16} />
                                </ActionIcon>
                              </Tooltip>
                            )}
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                    {visibleDocs.length === 0 && (
                      <Table.Tr>
                        <Table.Td colSpan={7}>
                          <Text c="dimmed" ta="center" py="md">
                            Tidak ada PDF yang cocok dengan filter.
                          </Text>
                        </Table.Td>
                      </Table.Tr>
                    )}
                  </Table.Tbody>
                </Table>
              </ScrollArea>
            </Stack>
          </Card>
        </>
      )}

      <Modal
        opened={!!modalDoc}
        onClose={() => setModalDoc(null)}
        title="Detail metadata PDF"
        size="lg"
      >
        {modalDoc && (
          <Stack gap="sm">
            <Group>
              <Text fw={600}>{modalDoc.filename}</Text>
              {modalDoc.downloaded && <Badge color="green">Terunduh</Badge>}
            </Group>
            <Anchor href={modalDoc.url} target="_blank" size="sm">
              {modalDoc.url}
            </Anchor>
            <Table>
              <Table.Tbody>
                {[
                  ["Judul", modalDoc.title],
                  ["Penulis", modalDoc.author],
                  ["Subjek", modalDoc.subject],
                  ["Keywords", modalDoc.keywords],
                  ["Creator", modalDoc.creator],
                  ["Producer", modalDoc.producer],
                  ["Tanggal buat", modalDoc.creation_date],
                  ["Tanggal modif", modalDoc.mod_date],
                  ["Jumlah halaman", modalDoc.page_count?.toString()],
                  ["Ukuran", formatBytes(modalDoc.file_size)],
                  ["Ditemukan dari", modalDoc.discovered_from],
                ].map(([k, v]) => (
                  <Table.Tr key={k as string}>
                    <Table.Td style={{ width: 160 }}>
                      <Text size="sm" c="dimmed">{k}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{v || "-"}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            {modalDoc.preview_text && (
              <Box>
                <Text size="sm" fw={600} mb={4}>Pratinjau halaman pertama</Text>
                <Code block style={{ whiteSpace: "pre-wrap", maxHeight: 220, overflow: "auto" }}>
                  {modalDoc.preview_text}
                </Code>
              </Box>
            )}
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
