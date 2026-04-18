import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { Box, Text } from "@mantine/core";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import cola from "cytoscape-cola";

import type { SitemapGraphNode, SitemapGraphResponse } from "../types";

cytoscape.use(cola as any);

function statusToColor(code: number | null): string {
  if (!code) return "#6b7280"; // gray
  if (code < 300) return "#22c55e"; // green
  if (code < 400) return "#eab308"; // yellow
  if (code < 500) return "#f97316"; // orange
  return "#ef4444"; // red
}

export interface SitemapGraphHandle {
  exportPng: () => string | null;
}

interface Props {
  data: SitemapGraphResponse;
  onNodeClick?: (node: SitemapGraphNode) => void;
  searchQuery?: string;
}

const SitemapGraph = forwardRef<SitemapGraphHandle, Props>(
  ({ data, onNodeClick, searchQuery = "" }, ref) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const cyRef = useRef<Core | null>(null);

    useImperativeHandle(ref, () => ({
      exportPng: () => {
        if (!cyRef.current) return null;
        return cyRef.current.png({
          full: true,
          bg: "transparent",
          scale: 2,
        });
      },
    }));

    useEffect(() => {
      if (!containerRef.current || data.nodes.length === 0) return;

      const elements: ElementDefinition[] = [
        ...data.nodes.map((n) => ({
          data: {
            id: String(n.id),
            label: n.title || new URL(n.url).pathname || "/",
            status: n.status_code,
            depth: n.depth,
            url: n.url,
            title: n.title,
          },
        })),
        ...data.edges.map((e) => ({
          data: {
            id: `e_${e.source}_${e.target}`,
            source: String(e.source),
            target: String(e.target),
          },
        })),
      ];

      const cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: "node",
            style: {
              "background-color": (ele) => statusToColor(ele.data("status")),
              "border-color": "#1e2029",
              "border-width": 2,
              label: "data(label)",
              color: "#e2e4ed",
              "font-size": 10,
              "text-valign": "bottom",
              "text-margin-y": 4,
              "text-outline-color": "#0e0f13",
              "text-outline-width": 2,
              "text-wrap": "ellipsis",
              "text-max-width": "120px",
              width: (ele) => Math.max(14, 32 - ele.data("depth") * 4),
              height: (ele) => Math.max(14, 32 - ele.data("depth") * 4),
            },
          },
          {
            selector: "node.dimmed",
            style: {
              opacity: 0.15,
            },
          },
          {
            selector: "node.match",
            style: {
              "border-color": "#3b9eff",
              "border-width": 4,
              "z-index": 10,
            },
          },
          {
            selector: "edge",
            style: {
              width: 1.5,
              "line-color": "#2a2d3a",
              "target-arrow-color": "#2a2d3a",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              opacity: 0.7,
            },
          },
          {
            selector: "edge.dimmed",
            style: {
              opacity: 0.08,
            },
          },
          {
            selector: "node:selected",
            style: {
              "border-color": "#3b9eff",
              "border-width": 3,
            },
          },
        ],
        layout: {
          name: "cola",
          animate: true,
          fit: true,
          padding: 40,
          nodeSpacing: 20,
          edgeLength: 100,
          randomize: false,
        } as any,
        wheelSensitivity: 0.2,
      });

      cy.on("tap", "node", (evt) => {
        const nodeId = Number(evt.target.id());
        const hit = data.nodes.find((n) => n.id === nodeId);
        if (hit) onNodeClick?.(hit);
      });

      cyRef.current = cy;
      return () => {
        cy.destroy();
        cyRef.current = null;
      };
    }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

    // Apply search filter as CSS class - no re-layout needed
    useEffect(() => {
      const cy = cyRef.current;
      if (!cy) return;
      const q = searchQuery.trim().toLowerCase();
      if (!q) {
        cy.nodes().removeClass("dimmed match");
        cy.edges().removeClass("dimmed");
        return;
      }
      cy.nodes().forEach((n) => {
        const url = (n.data("url") || "").toLowerCase();
        const title = (n.data("title") || "").toLowerCase();
        const matches = url.includes(q) || title.includes(q);
        if (matches) {
          n.removeClass("dimmed").addClass("match");
        } else {
          n.removeClass("match").addClass("dimmed");
        }
      });
      cy.edges().addClass("dimmed");
    }, [searchQuery]);

    if (data.nodes.length === 0) {
      return (
        <Text size="sm" c="dimmed">
          Graph akan muncul setelah crawl mulai.
        </Text>
      );
    }

    return (
      <Box
        ref={containerRef}
        style={{
          width: "100%",
          height: 520,
          borderRadius: 10,
          background: "var(--mantine-color-body)",
          border: "1px solid var(--mantine-color-default-border)",
        }}
      />
    );
  }
);

SitemapGraph.displayName = "SitemapGraph";

export default SitemapGraph;
