import { useEffect, useMemo, useState } from "react";
import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  CopyButton,
  Group,
  ScrollArea,
  SegmentedControl,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { Dropzone } from "@mantine/dropzone";
import { notifications } from "@mantine/notifications";
import {
  IconCheck,
  IconCopy,
  IconFileInfo,
  IconFileUpload,
  IconMapPin,
  IconSearch,
} from "@tabler/icons-react";
import { useLocation } from "react-router-dom";
import type { MetadataInspectionResponse } from "../types";

const BASE = "/api/metadata";
const MAX_UPLOAD = 100 * 1024 * 1024;

function formatBytes(n: number): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(2)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function notifyError(msg: string) {
  notifications.show({ color: "red", title: "Error", message: msg });
}
function notifySuccess(msg: string) {
  notifications.show({ color: "teal", title: "Sukses", message: msg });
}

async function parseErr(res: Response): Promise<string> {
  try {
    const txt = await res.text();
    try {
      const j = JSON.parse(txt);
      return j.detail || txt;
    } catch {
      return txt || `HTTP ${res.status}`;
    }
  } catch {
    return `HTTP ${res.status}`;
  }
}

const CATEGORY_LABEL: Record<string, string> = {
  generic: "Umum",
  exif: "EXIF",
  pdf: "PDF",
  office: "Office",
  media: "Media",
};

const CATEGORY_ORDER = ["generic", "exif", "pdf", "office", "media"];

export default function MetadataInspectorPage() {
  const location = useLocation();
  const [mode, setMode] = useState<"upload" | "path">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [path, setPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MetadataInspectionResponse | null>(null);

  // Read ?path= on mount; if present switch to path mode and auto-extract
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const qp = params.get("path");
    if (qp) {
      setMode("path");
      setPath(qp);
      void runExtractFromPath(qp);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runExtractFromPath(p: string) {
    if (!p.trim()) {
      notifyError("Masukkan path absolut.");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const url = `${BASE}/inspect?path=${encodeURIComponent(p.trim())}`;
      const res = await fetch(url);
      if (!res.ok) {
        notifyError(await parseErr(res));
        return;
      }
      const data = (await res.json()) as MetadataInspectionResponse;
      setResult(data);
      notifySuccess("Metadata diekstrak.");
    } catch (e: any) {
      notifyError(e?.message || "Gagal ekstrak metadata.");
    } finally {
      setLoading(false);
    }
  }

  async function runExtract() {
    if (mode === "upload") {
      if (!file) {
        notifyError("Pilih berkas terlebih dahulu.");
        return;
      }
      if (file.size > MAX_UPLOAD) {
        notifyError("Berkas melebihi 100 MB.");
        return;
      }
      setLoading(true);
      setResult(null);
      try {
        const fd = new FormData();
        fd.append("file", file);
        const res = await fetch(`${BASE}/inspect`, { method: "POST", body: fd });
        if (!res.ok) {
          notifyError(await parseErr(res));
          return;
        }
        const data = (await res.json()) as MetadataInspectionResponse;
        setResult(data);
        notifySuccess("Metadata diekstrak.");
      } catch (e: any) {
        notifyError(e?.message || "Gagal ekstrak metadata.");
      } finally {
        setLoading(false);
      }
    } else {
      await runExtractFromPath(path);
    }
  }

  const availableCategories = useMemo(() => {
    if (!result) return [];
    return CATEGORY_ORDER.filter((k) => {
      const v = (result.categories as any)[k];
      if (k === "generic") return true;
      return v && typeof v === "object" && Object.keys(v).length > 0;
    });
  }, [result]);

  return (
    <Stack gap="md">
      <Group gap="sm">
        <IconFileInfo size={28} color="var(--mantine-color-cyan-5)" />
        <Title order={2}>Metadata Inspector</Title>
        <Badge variant="light" color="cyan">
          Util
        </Badge>
      </Group>
      <Text c="dimmed" size="sm">
        Ekstrak metadata EXIF, PDF, Office, dan media dari berkas lokal. Berguna untuk
        memeriksa informasi tersembunyi seperti GPS foto, penulis dokumen, atau codec video.
      </Text>

      <Card withBorder padding="md">
        <Stack gap="sm">
          <Group>
            <Text fw={600}>Mode input</Text>
            <SegmentedControl
              value={mode}
              onChange={(v) => setMode(v as "upload" | "path")}
              data={[
                { value: "upload", label: "Unggah" },
                { value: "path", label: "Path Lokal" },
              ]}
            />
          </Group>

          {mode === "upload" ? (
            <Dropzone
              onDrop={(files) => files[0] && setFile(files[0])}
              onReject={() => notifyError("Berkas ditolak.")}
              maxFiles={1}
              maxSize={MAX_UPLOAD}
              activateOnClick
              styles={{
                root: {
                  borderRadius: 8,
                  borderStyle: "dashed",
                  padding: "32px 16px",
                },
              }}
            >
              <Stack align="center" gap="xs" style={{ pointerEvents: "none" }}>
                <IconFileUpload size={36} stroke={1.5} color="var(--mantine-color-cyan-5)" />
                {file ? (
                  <>
                    <Text size="sm" fw={600}>
                      {file.name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {formatBytes(file.size)}
                    </Text>
                    <Text size="xs" c="dimmed">
                      Klik atau drop berkas lain untuk ganti
                    </Text>
                  </>
                ) : (
                  <>
                    <Text size="sm" fw={600}>
                      Drop berkas di sini atau klik untuk pilih
                    </Text>
                    <Text size="xs" c="dimmed">
                      Gambar, PDF, dokumen Office, video, atau audio. Maksimum 100 MB.
                    </Text>
                  </>
                )}
              </Stack>
            </Dropzone>
          ) : (
            <TextInput
              label="Path absolut"
              placeholder="C:\\path\\ke\\berkas.jpg"
              value={path}
              onChange={(e) => setPath(e.currentTarget.value)}
              description="Path harus dapat dibaca oleh proses backend. Hanya berkas, bukan folder."
            />
          )}

          <Group>
            <Button
              leftSection={<IconSearch size={16} />}
              onClick={runExtract}
              loading={loading}
            >
              Inspeksi
            </Button>
          </Group>
        </Stack>
      </Card>

      {!result && !loading && (
        <Card withBorder padding="lg">
          <Text c="dimmed" ta="center">
            Pilih berkas untuk inspeksi metadata.
          </Text>
        </Card>
      )}

      {result && (
        <Card withBorder padding="md">
          <Stack gap="sm">
            <Group justify="space-between">
              <Title order={4}>Hasil</Title>
              <Group gap="xs">
                <Badge variant="light" color="cyan">
                  {result.file_type}
                </Badge>
                <Badge variant="light">{formatBytes(result.size_bytes)}</Badge>
              </Group>
            </Group>

            <Tabs defaultValue={availableCategories[0] || "generic"} keepMounted={false}>
              <Tabs.List>
                {availableCategories.map((cat) => (
                  <Tabs.Tab key={cat} value={cat}>
                    {CATEGORY_LABEL[cat] || cat}
                  </Tabs.Tab>
                ))}
              </Tabs.List>

              {availableCategories.map((cat) => {
                const fields = (result.categories as any)[cat] || {};
                return (
                  <Tabs.Panel key={cat} value={cat} pt="md">
                    <CategoryTable category={cat} fields={fields} />
                  </Tabs.Panel>
                );
              })}
            </Tabs>
          </Stack>
        </Card>
      )}
    </Stack>
  );
}

function CategoryTable({
  category,
  fields,
}: {
  category: string;
  fields: Record<string, any>;
}) {
  const entries = Object.entries(fields || {});
  if (entries.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        Tidak ada data.
      </Text>
    );
  }

  // Special-case: media streams shown as nested list
  const lat = category === "exif" ? (fields.GPSLatitude as number | undefined) : undefined;
  const lon = category === "exif" ? (fields.GPSLongitude as number | undefined) : undefined;

  return (
    <Stack gap="sm">
      {category === "exif" && lat !== undefined && lon !== undefined && (
        <Group gap="xs">
          <IconMapPin size={16} color="var(--mantine-color-cyan-6)" />
          <Anchor
            href={`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=16/${lat}/${lon}`}
            target="_blank"
            rel="noreferrer"
            size="sm"
          >
            Lihat lokasi di OpenStreetMap ({lat}, {lon})
          </Anchor>
        </Group>
      )}

      <ScrollArea>
        <Table striped withTableBorder highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th style={{ width: 220 }}>Label</Table.Th>
              <Table.Th>Nilai</Table.Th>
              <Table.Th style={{ width: 60 }}></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {entries.map(([k, v]) => {
              if (k === "streams" && Array.isArray(v)) {
                return (
                  <Table.Tr key={k}>
                    <Table.Td>
                      <Text size="sm" fw={600}>
                        streams
                      </Text>
                    </Table.Td>
                    <Table.Td colSpan={2}>
                      <Stack gap={4}>
                        {v.map((s: any, idx: number) => (
                          <Card key={idx} withBorder padding="xs">
                            <Group gap="xs" wrap="wrap">
                              <Badge size="xs" variant="light">
                                {s.codec_type || "stream"} #{s.index ?? idx}
                              </Badge>
                              {s.codec_name && (
                                <Badge size="xs" variant="outline">
                                  {s.codec_name}
                                </Badge>
                              )}
                              {s.width && s.height && (
                                <Text size="xs">
                                  {s.width}x{s.height}
                                </Text>
                              )}
                              {s.sample_rate && (
                                <Text size="xs">{s.sample_rate} Hz</Text>
                              )}
                              {s.channels && (
                                <Text size="xs">{s.channels} ch</Text>
                              )}
                              {s.r_frame_rate && (
                                <Text size="xs">{s.r_frame_rate} fps</Text>
                              )}
                            </Group>
                          </Card>
                        ))}
                      </Stack>
                    </Table.Td>
                  </Table.Tr>
                );
              }
              const valueStr =
                v === null || v === undefined
                  ? "-"
                  : typeof v === "object"
                  ? JSON.stringify(v)
                  : String(v);
              return (
                <Table.Tr key={k}>
                  <Table.Td>
                    <Text size="sm" ff="monospace">
                      {k}
                    </Text>
                  </Table.Td>
                  <Table.Td style={{ wordBreak: "break-all" }}>
                    <Text size="sm">{valueStr}</Text>
                  </Table.Td>
                  <Table.Td>
                    <CopyButton value={valueStr}>
                      {({ copied, copy }) => (
                        <Tooltip label={copied ? "Disalin" : "Salin"} withArrow>
                          <ActionIcon size="sm" variant="subtle" onClick={copy}>
                            {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
                          </ActionIcon>
                        </Tooltip>
                      )}
                    </CopyButton>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </ScrollArea>
    </Stack>
  );
}
