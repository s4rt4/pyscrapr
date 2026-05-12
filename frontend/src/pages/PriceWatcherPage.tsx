import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Center,
  Grid,
  Group,
  Loader,
  Menu,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertTriangle,
  IconCurrencyDollar,
  IconDotsVertical,
  IconExternalLink,
  IconPlus,
  IconRefresh,
  IconSparkles,
  IconTrash,
  IconTrendingDown,
  IconTrendingUp,
} from "@tabler/icons-react";
import type {
  PriceExtractPreview,
  PriceHistory,
  PriceProduct,
  PriceProductInput,
  PriceSelectorType,
} from "../types";

// Lazy load chart bundle (constraint)
const LineChartLazy = lazy(() =>
  import("@mantine/charts").then((m) => ({ default: m.LineChart })),
);

const CURRENCIES = ["IDR", "USD", "EUR", "SGD", "MYR", "GBP", "JPY"];

const INTERVAL_OPTIONS = [
  { value: "15", label: "Setiap 15 menit" },
  { value: "60", label: "Setiap 1 jam" },
  { value: "360", label: "Setiap 6 jam" },
  { value: "720", label: "Setiap 12 jam" },
  { value: "1440", label: "Setiap 24 jam" },
];

const SELECTOR_TYPE_OPTIONS: { value: PriceSelectorType; label: string }[] = [
  { value: "auto", label: "Auto-detect" },
  { value: "css", label: "CSS selector" },
  { value: "xpath", label: "XPath" },
];

function formatPrice(price: number | null | undefined, currency: string): string {
  if (price == null || Number.isNaN(price)) return "—";
  try {
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency,
      maximumFractionDigits: currency === "IDR" ? 0 : 2,
    }).format(price);
  } catch {
    return `${price.toLocaleString("id-ID")} ${currency}`;
  }
}

function relativeTime(iso: string | null): string {
  if (!iso) return "belum pernah";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "belum pernah";
  const diff = (Date.now() - then) / 1000;
  if (diff < 60) return `${Math.floor(diff)} detik lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)} menit lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
  return `${Math.floor(diff / 86400)} hari lalu`;
}

function statusBadge(status: string) {
  switch (status) {
    case "ok":
      return <Badge color="teal" variant="light" size="sm">OK</Badge>;
    case "pending":
      return <Badge color="gray" variant="light" size="sm">Menunggu</Badge>;
    case "not_found":
      return <Badge color="yellow" variant="light" size="sm">Tidak ketemu</Badge>;
    case "error":
      return <Badge color="red" variant="light" size="sm">Error</Badge>;
    default:
      return <Badge color="gray" variant="light" size="sm">{status}</Badge>;
  }
}

interface ProductCardProps {
  product: PriceProduct;
  onCheckNow: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

function ProductCard({ product, onCheckNow, onDelete }: ProductCardProps) {
  const [history, setHistory] = useState<PriceHistory[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [checking, setChecking] = useState(false);

  const loadHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const r = await fetch(`/api/price/products/${product.id}/history?days=30`);
      if (r.ok) {
        const data: PriceHistory[] = await r.json();
        setHistory(data);
      }
    } catch {
      // ignore
    } finally {
      setLoadingHistory(false);
    }
  }, [product.id]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const chartData = useMemo(() => {
    return history
      .filter((h) => h.status === "ok" && h.price > 0)
      .map((h) => ({
        date: new Date(h.checked_at).toLocaleDateString("id-ID", {
          day: "2-digit",
          month: "short",
        }),
        price: h.price,
      }));
  }, [history]);

  const avg7d = useMemo(() => {
    const cutoff = Date.now() - 7 * 86400 * 1000;
    const recent = history.filter(
      (h) => h.status === "ok" && h.price > 0 && new Date(h.checked_at).getTime() >= cutoff,
    );
    if (recent.length === 0) return null;
    return recent.reduce((s, h) => s + h.price, 0) / recent.length;
  }, [history]);

  const trendColor = useMemo(() => {
    if (avg7d == null || product.last_price == null) return "gray";
    if (product.last_price < avg7d) return "teal";
    if (product.last_price > avg7d) return "red";
    return "gray";
  }, [avg7d, product.last_price]);

  const trendIcon =
    trendColor === "teal" ? (
      <IconTrendingDown size={14} />
    ) : trendColor === "red" ? (
      <IconTrendingUp size={14} />
    ) : null;

  const handleCheck = async () => {
    setChecking(true);
    try {
      await onCheckNow(product.id);
      await loadHistory();
    } finally {
      setChecking(false);
    }
  };

  const trendBadge =
    avg7d != null && product.last_price != null ? (
      <Badge color={trendColor} variant="light" leftSection={trendIcon}>
        {product.last_price < avg7d ? "Lebih murah" : product.last_price > avg7d ? "Lebih mahal" : "Stabil"}{" "}
        vs rata-rata 7 hari
      </Badge>
    ) : null;

  return (
    <Card withBorder radius="lg" p="md" h="100%">
      <Stack gap="sm" h="100%">
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
            <Text fw={600} size="sm" lineClamp={2}>
              {product.title || "(tanpa judul)"}
            </Text>
            <Anchor
              href={product.url}
              target="_blank"
              rel="noreferrer"
              size="xs"
              c="dimmed"
              truncate
            >
              <Group gap={4} wrap="nowrap">
                <IconExternalLink size={12} />
                <Text span size="xs" ff="monospace" truncate>
                  {product.url}
                </Text>
              </Group>
            </Anchor>
          </Stack>
          <Menu shadow="md" position="bottom-end" withinPortal>
            <Menu.Target>
              <ActionIcon variant="subtle" color="gray">
                <IconDotsVertical size={16} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item
                leftSection={<IconRefresh size={14} />}
                onClick={handleCheck}
              >
                Cek sekarang
              </Menu.Item>
              <Menu.Divider />
              <Menu.Item
                color="red"
                leftSection={<IconTrash size={14} />}
                onClick={() => onDelete(product.id)}
              >
                Hapus
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>

        <Group gap="xs" align="flex-end">
          <Title order={2} c={trendColor === "gray" ? undefined : trendColor}>
            {formatPrice(product.last_price, product.currency)}
          </Title>
          {statusBadge(product.last_status)}
        </Group>

        {trendBadge}

        {product.last_error && product.last_status !== "ok" && (
          <Tooltip label={product.last_error} multiline w={300}>
            <Group gap={4} c="orange">
              <IconAlertTriangle size={14} />
              <Text size="xs" c="orange" lineClamp={1}>
                {product.last_error}
              </Text>
            </Group>
          </Tooltip>
        )}

        <div style={{ flex: 1, minHeight: 100 }}>
          {loadingHistory ? (
            <Center h={100}>
              <Loader size="xs" />
            </Center>
          ) : chartData.length < 2 ? (
            <Center h={100}>
              <Text size="xs" c="dimmed">
                Data belum cukup untuk grafik
              </Text>
            </Center>
          ) : (
            <Suspense fallback={<Center h={100}><Loader size="xs" /></Center>}>
              <LineChartLazy
                h={100}
                data={chartData}
                dataKey="date"
                series={[{ name: "price", color: trendColor === "red" ? "red.6" : "teal.6" }]}
                curveType="linear"
                withDots={false}
                withXAxis={false}
                withYAxis={false}
                withTooltip
                gridAxis="none"
              />
            </Suspense>
          )}
        </div>

        <Group justify="space-between">
          <Text size="xs" c="dimmed">
            Diperiksa: {relativeTime(product.last_checked_at)}
          </Text>
          <Button
            size="compact-xs"
            variant="light"
            leftSection={<IconRefresh size={12} />}
            onClick={handleCheck}
            loading={checking}
          >
            Cek
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

// ───── Add product modal ─────

interface AddModalProps {
  opened: boolean;
  onClose: () => void;
  onCreated: () => void;
}

function AddProductModal({ opened, onClose, onCreated }: AddModalProps) {
  const [url, setUrl] = useState("");
  const [selector, setSelector] = useState("");
  const [selectorType, setSelectorType] = useState<PriceSelectorType>("auto");
  const [title, setTitle] = useState("");
  const [interval, setInterval] = useState("60");
  const [currency, setCurrency] = useState("IDR");
  const [alertBelow, setAlertBelow] = useState<number | string>("");
  const [alertAbove, setAlertAbove] = useState<number | string>("");

  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState<PriceExtractPreview | null>(null);
  const [saving, setSaving] = useState(false);

  const reset = () => {
    setUrl("");
    setSelector("");
    setSelectorType("auto");
    setTitle("");
    setInterval("60");
    setCurrency("IDR");
    setAlertBelow("");
    setAlertAbove("");
    setPreview(null);
  };

  const doPreview = async () => {
    if (!url.trim()) {
      notifications.show({ title: "URL kosong", message: "Isi URL dulu", color: "yellow" });
      return;
    }
    setPreviewing(true);
    setPreview(null);
    try {
      const params = new URLSearchParams({
        url: url.trim(),
        selector,
        selector_type: selectorType,
      });
      const r = await fetch(`/api/price/extract-preview?${params}`);
      const data: PriceExtractPreview = await r.json();
      setPreview(data);
      if (data.title && !title.trim()) {
        setTitle(data.title);
      }
      if (data.price == null) {
        notifications.show({
          title: "Tidak ketemu harga",
          message: data.error || "Coba pakai CSS selector manual",
          color: "yellow",
        });
      }
    } catch (e: any) {
      notifications.show({
        title: "Preview gagal",
        message: e?.message || "Tidak bisa menghubungi server",
        color: "red",
      });
    } finally {
      setPreviewing(false);
    }
  };

  const doSave = async () => {
    if (!url.trim()) {
      notifications.show({ title: "URL kosong", message: "Isi URL dulu", color: "yellow" });
      return;
    }
    setSaving(true);
    try {
      const body: PriceProductInput = {
        url: url.trim(),
        title: title.trim(),
        selector: selector.trim(),
        selector_type: selectorType,
        interval_minutes: parseInt(interval, 10),
        enabled: true,
        currency,
        alert_below: alertBelow === "" ? null : Number(alertBelow),
        alert_above: alertAbove === "" ? null : Number(alertAbove),
      };
      const r = await fetch("/api/price/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(txt || `HTTP ${r.status}`);
      }
      notifications.show({
        title: "Produk ditambahkan",
        message: "Cek otomatis berjalan di latar belakang",
        color: "teal",
      });
      reset();
      onCreated();
      onClose();
    } catch (e: any) {
      notifications.show({
        title: "Gagal simpan",
        message: e?.message || "Server menolak",
        color: "red",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={() => {
        reset();
        onClose();
      }}
      title="Tambah produk baru"
      size="lg"
    >
      <Stack gap="md">
        <TextInput
          label="URL produk"
          placeholder="https://www.tokopedia.com/..."
          value={url}
          onChange={(e) => setUrl(e.currentTarget.value)}
          required
        />

        <Group grow>
          <Select
            label="Tipe selector"
            data={SELECTOR_TYPE_OPTIONS}
            value={selectorType}
            onChange={(v) => setSelectorType((v as PriceSelectorType) || "auto")}
          />
          <TextInput
            label="Selector (opsional)"
            placeholder=".price atau //span[@class='harga']"
            value={selector}
            onChange={(e) => setSelector(e.currentTarget.value)}
            disabled={selectorType === "auto"}
          />
        </Group>

        <Group>
          <Button
            variant="light"
            leftSection={<IconSparkles size={14} />}
            onClick={doPreview}
            loading={previewing}
          >
            Auto-detect / Tes selector
          </Button>
          {preview && (
            <Badge color={preview.price != null ? "teal" : "yellow"} variant="light">
              {preview.price != null
                ? `Harga: ${formatPrice(preview.price, currency)}`
                : `Tidak ketemu: ${preview.error || ""}`}
            </Badge>
          )}
        </Group>

        {preview?.raw_text && (
          <Card withBorder p="xs" radius="md" bg="dark.6">
            <Text size="xs" c="dimmed">
              Teks mentah: <Text span ff="monospace">{preview.raw_text}</Text>
            </Text>
            {preview.matched_on && (
              <Text size="xs" c="dimmed">
                Cocok via: <Text span ff="monospace">{preview.matched_on}</Text>
              </Text>
            )}
          </Card>
        )}

        <TextInput
          label="Judul produk"
          placeholder="Otomatis terisi setelah preview"
          value={title}
          onChange={(e) => setTitle(e.currentTarget.value)}
        />

        <Group grow>
          <Select
            label="Interval cek"
            data={INTERVAL_OPTIONS}
            value={interval}
            onChange={(v) => setInterval(v || "60")}
            allowDeselect={false}
          />
          <Select
            label="Mata uang"
            data={CURRENCIES}
            value={currency}
            onChange={(v) => setCurrency(v || "IDR")}
            allowDeselect={false}
          />
        </Group>

        <Group grow>
          <NumberInput
            label="Alert jika di bawah"
            placeholder="opsional"
            value={alertBelow}
            onChange={(v) => setAlertBelow(v)}
            min={0}
            thousandSeparator="."
            decimalSeparator=","
            leftSection={<IconCurrencyDollar size={14} />}
          />
          <NumberInput
            label="Alert jika di atas"
            placeholder="opsional"
            value={alertAbove}
            onChange={(v) => setAlertAbove(v)}
            min={0}
            thousandSeparator="."
            decimalSeparator=","
            leftSection={<IconCurrencyDollar size={14} />}
          />
        </Group>

        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Batal
          </Button>
          <Button onClick={doSave} loading={saving} color="cyan">
            Simpan
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

// ───── Main page ─────

export default function PriceWatcherPage() {
  const [products, setProducts] = useState<PriceProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, { open: openModal, close: closeModal }] = useDisclosure(false);

  const loadProducts = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/price/products");
      if (r.ok) {
        const data: PriceProduct[] = await r.json();
        setProducts(data);
      }
    } catch (e: any) {
      notifications.show({
        title: "Gagal muat",
        message: e?.message || "Tidak bisa baca daftar produk",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProducts();
    const t = window.setInterval(loadProducts, 30000);
    return () => window.clearInterval(t);
  }, [loadProducts]);

  const handleCheckNow = async (id: string) => {
    try {
      const r = await fetch(`/api/price/products/${id}/check-now`, { method: "POST" });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      notifications.show({
        title: "Cek selesai",
        message:
          data.status === "ok"
            ? `Harga: ${data.price}`
            : `Status: ${data.status}${data.error ? " — " + data.error : ""}`,
        color: data.status === "ok" ? "teal" : "yellow",
      });
      await loadProducts();
    } catch (e: any) {
      notifications.show({
        title: "Cek gagal",
        message: e?.message || "Server error",
        color: "red",
      });
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Hapus produk dan riwayat harganya?")) return;
    try {
      const r = await fetch(`/api/price/products/${id}`, { method: "DELETE" });
      if (!r.ok) throw new Error(await r.text());
      notifications.show({ title: "Terhapus", message: "Produk dihapus", color: "teal" });
      await loadProducts();
    } catch (e: any) {
      notifications.show({
        title: "Gagal hapus",
        message: e?.message || "Server error",
        color: "red",
      });
    }
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Group gap="xs">
            <IconCurrencyDollar size={26} />
            <Title order={2}>Price Watcher</Title>
          </Group>
          <Text c="dimmed" size="sm">
            Pantau harga produk e-commerce dari waktu ke waktu, terima alert saat harga turun.
          </Text>
        </div>
        <Button leftSection={<IconPlus size={16} />} onClick={openModal} color="cyan">
          Tambah produk
        </Button>
      </Group>

      {loading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : products.length === 0 ? (
        <Card withBorder radius="lg" p="xl">
          <Center>
            <Stack align="center" gap="sm">
              <IconCurrencyDollar size={48} opacity={0.3} />
              <Title order={4}>Belum ada produk yang dipantau</Title>
              <Text c="dimmed" size="sm" ta="center" maw={420}>
                Tambahkan URL produk dari Shopee, Tokopedia, Amazon, atau toko online lainnya.
                PyScrapr akan otomatis cek harga sesuai interval yang kamu pilih.
              </Text>
              <Button leftSection={<IconPlus size={16} />} onClick={openModal} color="cyan" mt="sm">
                Tambah produk pertama
              </Button>
            </Stack>
          </Center>
        </Card>
      ) : (
        <Grid>
          {products.map((p) => (
            <Grid.Col key={p.id} span={{ base: 12, sm: 6, lg: 4 }}>
              <ProductCard product={p} onCheckNow={handleCheckNow} onDelete={handleDelete} />
            </Grid.Col>
          ))}
        </Grid>
      )}

      <AddProductModal opened={modalOpen} onClose={closeModal} onCreated={loadProducts} />
    </Stack>
  );
}
