import { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Code,
  Grid,
  Group,
  JsonInput,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconCheck,
  IconPlayerPlay,
  IconRefresh,
  IconRobot,
} from "@tabler/icons-react";

interface HealthStatus {
  running: boolean;
  url: string;
  models?: string[];
  error?: string;
}

const PRESETS: Record<string, { label: string; schema: string; example: string }> = {
  product: {
    label: "Product info",
    schema:
      "Extract: name (string), brand (string), price (number, no currency symbol), currency (string, 3-letter code), in_stock (boolean), description (string, 1-sentence summary)",
    example:
      "iPhone 15 Pro Max 256GB Natural Titanium, Rp 21.999.000, Stok: Tersedia. Smartphone flagship Apple dengan chip A17 Pro, kamera 48MP, dan titanium frame.",
  },
  article: {
    label: "Article summary",
    schema:
      "Extract: title (string), author (string or null), published_date (ISO date string or null), summary (string, 2-3 sentences), key_points (array of strings), sentiment (string: positive/negative/neutral)",
    example: "Paste any news article or blog post here...",
  },
  entities: {
    label: "Named entities",
    schema:
      "Extract: people (array of strings), organizations (array of strings), locations (array of strings), dates (array of strings), money_amounts (array of strings)",
    example:
      "John Doe, CEO of Acme Corp, announced yesterday in New York that the company raised $50M in Series B funding on January 15, 2026.",
  },
  contact: {
    label: "Contact info",
    schema:
      "Extract: name (string), email (string or null), phone (string or null), address (string or null), company (string or null), role (string or null)",
    example: "Dr. Jane Smith — Senior Engineer at TechCorp. Email: jane@techcorp.com | +1-555-1234",
  },
};

export default function AIExtractPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [preset, setPreset] = useState<string>("product");
  const [schema, setSchema] = useState(PRESETS.product.schema);
  const [text, setText] = useState(PRESETS.product.example);
  const [result, setResult] = useState<any>(null);
  const [running, setRunning] = useState(false);

  const loadHealth = () => {
    fetch("/api/llm/health")
      .then((r) => r.json())
      .then((d: HealthStatus) => {
        setHealth(d);
        if (d.running && d.models && d.models.length && !model) {
          setModel(d.models[0]);
        }
      })
      .catch((e) => console.error(e));
  };

  useEffect(loadHealth, []);

  const onPresetChange = (key: string | null) => {
    if (!key) return;
    setPreset(key);
    setSchema(PRESETS[key].schema);
    setText(PRESETS[key].example);
    setResult(null);
  };

  const onExtract = async () => {
    if (!text.trim() || !schema.trim()) {
      notifications.show({ title: "Missing input", message: "Add both schema and text", color: "yellow" });
      return;
    }
    try {
      setRunning(true);
      setResult(null);
      const r = await fetch("/api/llm/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, schema_description: schema, model }),
      });
      const d = await r.json();
      setResult(d);
      if (d.success) {
        notifications.show({ title: "Extracted", message: `Model: ${d.model}`, color: "teal" });
      } else {
        notifications.show({ title: "Extract failed", message: d.error?.slice(0, 200), color: "red" });
      }
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    } finally {
      setRunning(false);
    }
  };

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>AI Extract (LLM)</Title>
        <Text c="dimmed" size="sm">
          Extract structured JSON from raw text using a local Ollama LLM.
        </Text>
      </div>

      {/* Ollama status */}
      <Card withBorder radius="lg" p="md">
        <Group justify="space-between" wrap="nowrap">
          <Group gap="sm">
            <IconRobot size={20} color={health?.running ? "var(--mantine-color-teal-5)" : "var(--mantine-color-red-5)"} />
            <div>
              <Text size="sm" fw={600}>
                Ollama status:{" "}
                {health === null
                  ? "checking…"
                  : health.running
                  ? <Badge color="teal" variant="light" size="xs" ml={4}>running</Badge>
                  : <Badge color="red" variant="light" size="xs" ml={4}>offline</Badge>}
              </Text>
              <Text size="xs" c="dimmed">{health?.url || "…"}</Text>
            </div>
          </Group>
          <Button size="xs" variant="subtle" leftSection={<IconRefresh size={14} />} onClick={loadHealth}>
            Refresh
          </Button>
        </Group>

        {health && !health.running && (
          <Alert icon={<IconAlertCircle size={16} />} color="yellow" variant="light" mt="md">
            Ollama not running. Install from{" "}
            <a href="https://ollama.com" target="_blank" rel="noreferrer">ollama.com</a>, then run{" "}
            <Code>ollama serve</Code> and <Code>ollama pull llama3.2</Code>.
            {health.error && <Text size="xs" c="dimmed" mt={4}>{health.error}</Text>}
          </Alert>
        )}

        {health?.running && (
          <Group gap="sm" mt="md">
            <Text size="sm" c="dimmed">Model:</Text>
            <Select
              size="xs"
              value={model}
              onChange={setModel}
              data={(health.models || []).map((m) => ({ value: m, label: m }))}
              placeholder="Select a model"
              w={260}
            />
            {(!health.models || health.models.length === 0) && (
              <Text size="xs" c="dimmed">No models installed. Run <Code>ollama pull llama3.2</Code></Text>
            )}
          </Group>
        )}
      </Card>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="lg" p="md" h="100%">
            <Group justify="space-between" mb="xs">
              <Text fw={600}>Input</Text>
              <Select
                size="xs"
                value={preset}
                onChange={onPresetChange}
                data={Object.entries(PRESETS).map(([k, v]) => ({ value: k, label: v.label }))}
                w={180}
              />
            </Group>
            <Textarea
              label="Schema description"
              description="Plain-language description of what to extract"
              value={schema}
              onChange={(e) => setSchema(e.currentTarget.value)}
              autosize
              minRows={3}
              maxRows={6}
            />
            <Textarea
              label="Text to analyze"
              value={text}
              onChange={(e) => setText(e.currentTarget.value)}
              autosize
              minRows={6}
              maxRows={20}
              mt="sm"
            />
            <Group mt="md">
              <Button
                leftSection={<IconPlayerPlay size={16} />}
                onClick={onExtract}
                loading={running}
                disabled={!health?.running || !model}
              >
                Extract
              </Button>
              <Text size="xs" c="dimmed">
                {text.length} chars
              </Text>
            </Group>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="lg" p="md" h="100%">
            <Group justify="space-between" mb="xs">
              <Text fw={600}>Result</Text>
              {result?.success && (
                <Badge leftSection={<IconCheck size={10} />} color="teal" variant="light">
                  {result.model}
                </Badge>
              )}
            </Group>

            {!result && (
              <Text size="sm" c="dimmed">Click Extract to run the LLM.</Text>
            )}

            {result?.success && result.data && (
              <JsonInput
                value={JSON.stringify(result.data, null, 2)}
                autosize
                minRows={10}
                maxRows={30}
                formatOnBlur
                readOnly
                styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
              />
            )}

            {result && !result.success && (
              <Alert color="red" variant="light" icon={<IconAlertCircle size={16} />}>
                <Text size="sm" fw={600}>Failed</Text>
                <Text size="xs" mt={4}>{result.error}</Text>
                {result.raw && (
                  <>
                    <Text size="xs" c="dimmed" mt="sm">LLM raw output:</Text>
                    <Code block style={{ fontSize: 11, maxHeight: 200, overflow: "auto" }}>{result.raw}</Code>
                  </>
                )}
              </Alert>
            )}
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
