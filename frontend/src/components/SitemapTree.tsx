import { Badge, ScrollArea, Text, Tree, useTree, type TreeNodeData } from "@mantine/core";
import { IconChevronDown, IconChevronRight, IconFile } from "@tabler/icons-react";
import { useEffect, useMemo } from "react";

import type { SitemapTreeNode } from "../types";

function statusColor(code: number | null): string {
  if (!code) return "gray";
  if (code < 300) return "teal";
  if (code < 400) return "yellow";
  if (code < 500) return "orange";
  return "red";
}

function filterTree(nodes: SitemapTreeNode[], query: string): SitemapTreeNode[] {
  if (!query) return nodes;
  const q = query.toLowerCase();
  const keep = (n: SitemapTreeNode): SitemapTreeNode | null => {
    const selfMatch =
      n.url.toLowerCase().includes(q) || (n.title || "").toLowerCase().includes(q);
    const keptChildren = n.children
      .map(keep)
      .filter((c): c is SitemapTreeNode => c !== null);
    if (selfMatch || keptChildren.length > 0) {
      return { ...n, children: keptChildren };
    }
    return null;
  };
  return nodes.map(keep).filter((n): n is SitemapTreeNode => n !== null);
}

function toTreeData(nodes: SitemapTreeNode[]): TreeNodeData[] {
  return nodes.map((n) => ({
    value: String(n.id),
    label: n.url,
    nodeProps: { status: n.status_code, title: n.title, url: n.url, nodeId: n.id },
    children: n.children.length > 0 ? toTreeData(n.children) : undefined,
  })) as TreeNodeData[];
}

interface Props {
  data: SitemapTreeNode[];
  searchQuery?: string;
  onNodeClick?: (node: { id: number; url: string; status: number | null; title: string | null }) => void;
}

export default function SitemapTree({ data, searchQuery = "", onNodeClick }: Props) {
  const filtered = useMemo(() => filterTree(data, searchQuery), [data, searchQuery]);
  const treeData = useMemo(() => toTreeData(filtered), [filtered]);
  const tree = useTree();

  useEffect(() => {
    if (treeData.length === 0) return;
    const expandRecursive = (nodes: TreeNodeData[], depth: number) => {
      for (const n of nodes) {
        tree.expand(n.value);
        if (n.children && depth > 0) expandRecursive(n.children, depth - 1);
      }
    };
    // Expand all when searching (show matches), else first 2 levels
    expandRecursive(treeData, searchQuery ? 10 : 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [treeData, searchQuery]);

  if (data.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        Tree akan muncul setelah crawl mulai.
      </Text>
    );
  }
  if (treeData.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        Tidak ada hasil untuk "{searchQuery}".
      </Text>
    );
  }

  return (
    <ScrollArea h={520} type="auto">
      <Tree
        data={treeData}
        tree={tree}
        levelOffset={22}
        renderNode={({ node, expanded, hasChildren, elementProps }) => {
          const status = (node.nodeProps as any)?.status as number | null;
          const title = (node.nodeProps as any)?.title as string | null;
          const url = (node.nodeProps as any)?.url as string;
          const nodeId = (node.nodeProps as any)?.nodeId as number;
          const isBroken = !!status && status >= 400;
          return (
            <div
              {...elementProps}
              style={{
                padding: "4px 6px",
                borderRadius: 6,
                background: isBroken ? "rgba(239, 68, 68, 0.08)" : undefined,
              }}
              onClick={(e) => {
                elementProps.onClick?.(e);
                onNodeClick?.({ id: nodeId, url, status, title });
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {hasChildren ? (
                  expanded ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />
                ) : (
                  <IconFile size={12} style={{ opacity: 0.4 }} />
                )}
                <Badge size="xs" color={statusColor(status)} variant={isBroken ? "filled" : "light"} style={{ minWidth: 38 }}>
                  {status ?? "—"}
                </Badge>
                <Text size="xs" fw={title ? 600 : 400} style={{ flex: 1 }}>
                  {title || url}
                </Text>
                {title && (
                  <Text size="xs" c="dimmed" style={{ fontFamily: "monospace", maxWidth: 340, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {url}
                  </Text>
                )}
              </div>
            </div>
          );
        }}
      />
    </ScrollArea>
  );
}
