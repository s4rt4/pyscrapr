import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Anchor,
  Badge,
  Box,
  Breadcrumbs,
  Card,
  Code,
  Grid,
  Group,
  Loader,
  Paper,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useHotkeys } from "@mantine/hooks";
import { useNavigate, useParams } from "react-router-dom";
import {
  IconAlertTriangle,
  IconBook,
  IconBulb,
  IconChevronRight,
  IconExclamationCircle,
  IconFileText,
  IconFolder,
  IconInfoCircle,
  IconSearch,
} from "@tabler/icons-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import Fuse from "fuse.js";

interface DocNode {
  type: "file" | "folder";
  name: string;
  path: string;
  title?: string;
  children?: DocNode[];
}

interface SearchResult {
  path: string;
  title: string;
  snippet: string;
}

function flattenTree(tree: DocNode[]): DocNode[] {
  const out: DocNode[] = [];
  const walk = (items: DocNode[]) => {
    for (const item of items) {
      if (item.type === "file") out.push(item);
      if (item.children) walk(item.children);
    }
  };
  walk(tree);
  return out;
}

function prettyFolderName(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1).replace(/-/g, " ");
}

function DocTreeNav({
  tree,
  currentPath,
  onSelect,
  depth = 0,
}: {
  tree: DocNode[];
  currentPath: string;
  onSelect: (path: string) => void;
  depth?: number;
}) {
  return (
    <Stack gap={2}>
      {tree.map((node) => (
        <Box key={node.path} style={{ paddingLeft: depth * 12 }}>
          {node.type === "folder" ? (
            <>
              <Group gap={6} py={4}>
                <IconFolder size={14} style={{ opacity: 0.6 }} />
                <Text size="xs" fw={700} c="dimmed" tt="uppercase" lts={0.5}>
                  {prettyFolderName(node.name)}
                </Text>
              </Group>
              {node.children && (
                <DocTreeNav
                  tree={node.children}
                  currentPath={currentPath}
                  onSelect={onSelect}
                  depth={depth + 1}
                />
              )}
            </>
          ) : (
            <Box
              onClick={() => onSelect(node.path)}
              style={{
                cursor: "pointer",
                padding: "4px 8px",
                borderRadius: 6,
                background: currentPath === node.path ? "var(--mantine-color-cyan-light)" : undefined,
                color: currentPath === node.path ? "var(--mantine-color-cyan-filled)" : undefined,
              }}
            >
              <Group gap={6} wrap="nowrap">
                <IconFileText size={12} style={{ opacity: 0.5, flexShrink: 0 }} />
                <Text size="xs" truncate>{node.title || node.name}</Text>
              </Group>
            </Box>
          )}
        </Box>
      ))}
    </Stack>
  );
}

function TOC({ headings, onJump }: { headings: Array<{ level: number; text: string; id: string }>; onJump: (id: string) => void }) {
  if (headings.length === 0) return null;
  return (
    <Paper withBorder radius="md" p="sm">
      <Text size="xs" fw={700} c="dimmed" tt="uppercase" lts={0.5} mb={6}>
        On this page
      </Text>
      <Stack gap={2}>
        {headings.map((h, i) => (
          <Anchor
            key={i}
            size="xs"
            c="dimmed"
            onClick={() => onJump(h.id)}
            style={{
              cursor: "pointer",
              paddingLeft: (h.level - 2) * 10,
              fontWeight: h.level === 2 ? 600 : 400,
            }}
          >
            {h.text}
          </Anchor>
        ))}
      </Stack>
    </Paper>
  );
}

export default function DocsPage() {
  const params = useParams();
  const nav = useNavigate();

  const [tree, setTree] = useState<DocNode[]>([]);
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);

  const contentRef = useRef<HTMLDivElement | null>(null);
  const searchRef = useRef<HTMLInputElement | null>(null);

  // Current path from URL (everything after /docs/)
  const currentPath = useMemo(() => {
    const splat = (params["*"] || "").trim();
    return splat || "index.md";
  }, [params]);

  // Load tree once
  useEffect(() => {
    fetch("/api/docs/tree")
      .then((r) => r.json())
      .then((d) => setTree(d.tree || []))
      .catch((e) => console.error(e));
  }, []);

  // Load content on path change
  useEffect(() => {
    setLoading(true);
    fetch(`/api/docs/content?path=${encodeURIComponent(currentPath)}`)
      .then((r) => {
        if (!r.ok) throw new Error("not found");
        return r.text();
      })
      .then((text) => {
        setContent(text);
        setLoading(false);
        // Scroll to top of content
        contentRef.current?.scrollTo({ top: 0 });
      })
      .catch(() => {
        setContent(
          `# Halaman belum ada\n\n\`${currentPath}\` — dokumentasi untuk halaman ini belum ditulis.\n\n[Kembali ke index](/docs)`
        );
        setLoading(false);
      });
  }, [currentPath]);

  // Client-side fuzzy search using flattened titles
  const flatDocs = useMemo(() => flattenTree(tree), [tree]);
  const fuse = useMemo(
    () => new Fuse(flatDocs, { keys: ["title", "name", "path"], threshold: 0.4 }),
    [flatDocs]
  );

  // Server-side full-text search (runs on query change)
  useEffect(() => {
    if (searchQ.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    const handle = setTimeout(() => {
      fetch(`/api/docs/search?q=${encodeURIComponent(searchQ)}`)
        .then((r) => r.json())
        .then((d) => setSearchResults(d.results || []))
        .catch(() => {});
    }, 200);
    return () => clearTimeout(handle);
  }, [searchQ]);

  const fuseMatches = useMemo(() => {
    if (searchQ.trim().length < 2) return [];
    return fuse.search(searchQ).slice(0, 5).map((r) => r.item);
  }, [fuse, searchQ]);

  useHotkeys([["mod+/", () => searchRef.current?.focus()]]);

  const selectDoc = (path: string) => {
    setSearchQ("");
    nav(`/docs/${path}`);
  };

  // Extract headings from content for TOC
  const headings = useMemo(() => {
    const out: Array<{ level: number; text: string; id: string }> = [];
    const lines = content.split("\n");
    let inCode = false;
    for (const line of lines) {
      if (line.trim().startsWith("```")) {
        inCode = !inCode;
        continue;
      }
      if (inCode) continue;
      const m = line.match(/^(#{2,4})\s+(.+)$/);
      if (m) {
        const level = m[1].length;
        const text = m[2].trim();
        const id = text
          .toLowerCase()
          .replace(/[^\w\s-]/g, "")
          .replace(/\s+/g, "-");
        out.push({ level, text, id });
      }
    }
    return out;
  }, [content]);

  const jumpToHeading = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Breadcrumb parts
  const crumbs = currentPath.replace(/\.md$/, "").split("/");

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Group gap="sm">
          <IconBook size={24} color="var(--mantine-color-cyan-5)" />
          <div>
            <Title order={2}>Documentation</Title>
            <Text c="dimmed" size="sm">Panduan lengkap semua fitur PyScrapr.</Text>
          </div>
        </Group>
        <TextInput
          ref={searchRef}
          size="sm"
          leftSection={<IconSearch size={14} />}
          placeholder="Search docs (Ctrl+/)"
          value={searchQ}
          onChange={(e) => setSearchQ(e.currentTarget.value)}
          w={{ base: 180, sm: 320 }}
        />
      </Group>

      {/* Search results */}
      {searchQ.trim().length >= 2 && (
        <Card withBorder radius="md" p="sm">
          <Text size="xs" c="dimmed" fw={600} mb="xs">Hasil pencarian</Text>
          {[...fuseMatches.map((m) => ({ path: m.path, title: m.title || m.name, snippet: "" })), ...searchResults]
            .filter((r, i, a) => a.findIndex((x) => x.path === r.path) === i)
            .slice(0, 10)
            .map((r) => (
              <Box
                key={r.path}
                p="xs"
                style={{ cursor: "pointer", borderRadius: 6 }}
                onClick={() => selectDoc(r.path)}
                className="docs-search-item"
              >
                <Group gap={6}>
                  <IconFileText size={12} style={{ opacity: 0.5 }} />
                  <Text size="sm" fw={600}>{r.title}</Text>
                  <Badge size="xs" variant="light" color="gray">{r.path}</Badge>
                </Group>
                {r.snippet && (
                  <Text size="xs" c="dimmed" mt={2} style={{ fontStyle: "italic" }}>
                    …{r.snippet}…
                  </Text>
                )}
              </Box>
            ))}
          {fuseMatches.length === 0 && searchResults.length === 0 && (
            <Text size="sm" c="dimmed">Tidak ada hasil untuk "{searchQ}".</Text>
          )}
        </Card>
      )}

      <Grid>
        {/* Left: inline docs tree */}
        <Grid.Col span={{ base: 12, md: 3 }}>
          <Paper withBorder radius="md" p="sm" style={{ position: "sticky", top: 80 }}>
            <ScrollArea h="calc(100vh - 220px)" type="auto">
              <DocTreeNav tree={tree} currentPath={currentPath} onSelect={selectDoc} />
            </ScrollArea>
          </Paper>
        </Grid.Col>

        {/* Middle: content */}
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Paper withBorder radius="md" p="xl" ref={contentRef}>
            <Breadcrumbs separator={<IconChevronRight size={12} />} mb="md">
              <Anchor size="xs" onClick={() => nav("/docs")}>docs</Anchor>
              {crumbs.map((c, i) => (
                <Text key={i} size="xs" c="dimmed">{c}</Text>
              ))}
            </Breadcrumbs>

            {loading ? (
              <Group justify="center" py="xl"><Loader size="sm" /></Group>
            ) : (
              <div className="docs-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ children, ...props }) => <Title order={1} mb="md" {...(props as any)}>{children}</Title>,
                    h2: ({ children, ...props }) => {
                      const text = String(children);
                      const id = text.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-");
                      return <Title order={2} mt="xl" mb="sm" id={id} {...(props as any)}>{children}</Title>;
                    },
                    h3: ({ children, ...props }) => {
                      const text = String(children);
                      const id = text.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-");
                      return <Title order={3} mt="lg" mb="xs" id={id} {...(props as any)}>{children}</Title>;
                    },
                    h4: ({ children, ...props }) => {
                      const text = String(children);
                      const id = text.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-");
                      return <Title order={4} mt="md" mb="xs" id={id} {...(props as any)}>{children}</Title>;
                    },
                    p: ({ children }) => <Text mb="sm" style={{ lineHeight: 1.7 }}>{children}</Text>,
                    a: ({ href, children }) => {
                      if (href?.startsWith("/docs") || href?.endsWith(".md") || !href?.startsWith("http")) {
                        return <Anchor onClick={(e) => { e.preventDefault(); if (href) nav(href.startsWith("/") ? href : `/docs/${href}`); }} style={{ cursor: "pointer" }}>{children}</Anchor>;
                      }
                      return <Anchor href={href} target="_blank" rel="noopener noreferrer">{children}</Anchor>;
                    },
                    code: (props: any) => {
                      const { inline, className, children } = props;
                      const match = /language-(\w+)/.exec(className || "");
                      if (!inline && match) {
                        return (
                          <SyntaxHighlighter
                            style={vscDarkPlus as any}
                            language={match[1]}
                            PreTag="div"
                            customStyle={{ borderRadius: 8, fontSize: 13 }}
                          >
                            {String(children).replace(/\n$/, "")}
                          </SyntaxHighlighter>
                        );
                      }
                      return <Code>{children}</Code>;
                    },
                    table: ({ children }) => (
                      <Box style={{ overflowX: "auto" }} my="md">
                        <table className="docs-table">{children}</table>
                      </Box>
                    ),
                    blockquote: ({ children }) => {
                      // GitHub-style callouts: [!NOTE] [!TIP] [!WARNING] [!DANGER] [!IMPORTANT]
                      const extractText = (nodes: any): string => {
                        if (typeof nodes === "string") return nodes;
                        if (Array.isArray(nodes)) return nodes.map(extractText).join("");
                        if (nodes?.props?.children) return extractText(nodes.props.children);
                        return "";
                      };
                      const txt = extractText(children).trim();
                      const calloutMatch = txt.match(/^\[!(NOTE|TIP|WARNING|DANGER|IMPORTANT)\]\s*/i);
                      if (calloutMatch) {
                        const kind = calloutMatch[1].toUpperCase();
                        const map: Record<string, { color: string; icon: any; title: string }> = {
                          NOTE: { color: "blue", icon: <IconInfoCircle size={18} />, title: "Catatan" },
                          TIP: { color: "teal", icon: <IconBulb size={18} />, title: "Tip" },
                          WARNING: { color: "yellow", icon: <IconAlertTriangle size={18} />, title: "Perhatian" },
                          DANGER: { color: "red", icon: <IconExclamationCircle size={18} />, title: "Bahaya" },
                          IMPORTANT: { color: "grape", icon: <IconExclamationCircle size={18} />, title: "Penting" },
                        };
                        const cfg = map[kind];
                        // Strip the marker line from children — replace first text node
                        const cleanChildren = React.Children.map(children, (child: any) => {
                          if (typeof child === "string") {
                            return child.replace(/^\[!(NOTE|TIP|WARNING|DANGER|IMPORTANT)\]\s*/i, "");
                          }
                          if (child?.props?.children) {
                            const firstChild = React.Children.toArray(child.props.children)[0];
                            if (typeof firstChild === "string" && /^\[!(NOTE|TIP|WARNING|DANGER|IMPORTANT)\]/i.test(firstChild)) {
                              const rest = [firstChild.replace(/^\[!(NOTE|TIP|WARNING|DANGER|IMPORTANT)\]\s*/i, ""), ...React.Children.toArray(child.props.children).slice(1)];
                              return React.cloneElement(child, {}, ...rest);
                            }
                          }
                          return child;
                        });
                        return (
                          <Alert color={cfg.color} variant="light" icon={cfg.icon} title={cfg.title} my="md">
                            {cleanChildren}
                          </Alert>
                        );
                      }
                      return <Alert color="cyan" variant="light" my="md">{children}</Alert>;
                    },
                    img: ({ src, alt }) => {
                      // Inline brand icons (Simple Icons CDN) — render small, no border
                      if (src?.includes("cdn.simpleicons.org") || src?.includes("simpleicons.org")) {
                        return (
                          <img
                            src={src}
                            alt={alt}
                            style={{
                              display: "inline-block",
                              width: 16,
                              height: 16,
                              verticalAlign: "text-bottom",
                              margin: "0 4px",
                            }}
                          />
                        );
                      }
                      // Local screenshots — render full-width with frame
                      const realSrc = src?.startsWith("images/") || src?.startsWith("./images/")
                        ? `/api/docs/image/${src.replace("./images/", "").replace("images/", "")}`
                        : src;
                      return <img src={realSrc} alt={alt} style={{ maxWidth: "100%", borderRadius: 8, border: "1px solid var(--mantine-color-default-border)", margin: "12px 0" }} />;
                    },
                    ul: ({ children }) => <ul style={{ lineHeight: 1.7, paddingLeft: 24 }}>{children}</ul>,
                    ol: ({ children }) => <ol style={{ lineHeight: 1.7, paddingLeft: 24 }}>{children}</ol>,
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            )}
          </Paper>
        </Grid.Col>

        {/* Right: TOC */}
        <Grid.Col span={{ base: 12, md: 2 }} visibleFrom="md">
          <Box style={{ position: "sticky", top: 80 }}>
            <TOC headings={headings} onJump={jumpToHeading} />
          </Box>
        </Grid.Col>
      </Grid>

      <style>{`
        .docs-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
        }
        .docs-table th, .docs-table td {
          border: 1px solid var(--mantine-color-default-border);
          padding: 8px 12px;
          text-align: left;
        }
        .docs-table th {
          background: var(--mantine-color-default-hover);
          font-weight: 600;
        }
        .docs-content hr {
          border: none;
          border-top: 1px solid var(--mantine-color-default-border);
          margin: 24px 0;
        }
        .docs-search-item:hover {
          background: var(--mantine-color-default-hover);
        }
      `}</style>
    </Stack>
  );
}
