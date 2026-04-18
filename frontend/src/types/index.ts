export type JobStatus = "pending" | "running" | "done" | "error" | "stopped";
export type JobType = "image_harvester" | "url_mapper" | "site_ripper" | "media_downloader";

export interface JobDTO {
  id: string;
  type: JobType;
  url: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  stats: Record<string, number>;
  output_dir?: string | null;
  error_message?: string | null;
}

export interface AssetDTO {
  id: number;
  job_id: string;
  url: string;
  status: string;
  local_path?: string | null;
  size_bytes?: number | null;
  width?: number | null;
  height?: number | null;
  alt_text?: string | null;
}

export interface HarvesterStartRequest {
  url: string;
  filters: {
    allowed_types: string[];
    min_width: number;
    min_height: number;
    min_bytes: number;
    exclude_patterns: string[];
  };
  concurrency: number;
  include_background_css: boolean;
  deduplicate: boolean;
  use_playwright?: boolean;
}

export type SSEEvent =
  | { type: "status"; status: JobStatus }
  | { type: "log"; message: string }
  | { type: "discovered"; count: number }
  | {
      type: "asset_done";
      url: string;
      size: number;
      width?: number;
      height?: number;
      stats: Record<string, number>;
    }
  | { type: "asset_failed"; url: string; error: string }
  | {
      type: "node";
      id: number;
      url: string;
      depth: number;
      parent_id: number | null;
      status_code: number | null;
      title: string | null;
    }
  | { type: "progress"; stats: Record<string, number> }
  | { type: "done"; stats: Record<string, number> }
  | { type: "stopped"; stats: Record<string, number> }
  | { type: "error"; message: string };

// ───── Mapper types ─────
export interface MapperStartRequest {
  url: string;
  max_depth: number;
  max_pages: number;
  stay_on_domain: boolean;
  respect_robots: boolean;
  rate_limit_per_host: number;
  concurrency: number;
  exclude_patterns: string[];
  strip_tracking_params: boolean;
  use_playwright?: boolean;
}

export interface SitemapTreeNode {
  id: number;
  url: string;
  depth: number;
  status_code: number | null;
  title: string | null;
  children: SitemapTreeNode[];
}

export interface SitemapGraphNode {
  id: number;
  url: string;
  depth: number;
  status_code: number | null;
  title: string | null;
}

export interface SitemapGraphEdge {
  source: number;
  target: number;
}

export interface SitemapGraphResponse {
  nodes: SitemapGraphNode[];
  edges: SitemapGraphEdge[];
}

// ───── Ripper types ─────
export interface RipperStartRequest {
  url: string;
  max_depth: number;
  max_pages: number;
  max_assets: number;
  stay_on_domain: boolean;
  respect_robots: boolean;
  rate_limit_per_host: number;
  concurrency: number;
  include_external_assets: boolean;
  rewrite_links: boolean;
  generate_report: boolean;
  use_playwright?: boolean;
}

export interface RipperKindStats {
  count: number;
  bytes: number;
}

export interface RipperStats {
  pages: number;
  assets: number;
  bytes_total: number;
  broken: number;
  failed: number;
  by_kind: Record<string, RipperKindStats>;
}

// ───── Media types ─────
export type QualityPreset = "best" | "4k" | "1080p" | "720p" | "480p" | "audio";
export type FormatPreset = "mp4" | "webm" | "mkv" | "mp3" | "m4a" | "flac" | "opus";
export type SubtitleMode = "skip" | "download" | "embed";
export type BrowserName = "chrome" | "firefox" | "edge" | "brave";

export interface MediaStartRequest {
  url: string;
  quality: QualityPreset;
  format: FormatPreset;
  subtitles: SubtitleMode;
  subtitle_langs: string[];
  embed_thumbnail: boolean;
  embed_metadata: boolean;
  use_browser_cookies?: BrowserName | null;
  playlist_start?: number | null;
  playlist_end?: number | null;
  max_items?: number | null;
}

export interface MediaProbeEntry {
  id: string;
  title: string;
  url?: string | null;
  duration?: number | null;
  uploader?: string | null;
  thumbnail?: string | null;
}

export interface MediaProbeResponse {
  kind: "video" | "playlist" | "channel";
  extractor: string;
  title?: string | null;
  uploader?: string | null;
  total: number;
  entries: MediaProbeEntry[];
  duration?: number | null;
  thumbnail?: string | null;
  webpage_url?: string | null;
}

export interface MediaStats {
  total_items: number;
  downloaded: number;
  failed: number;
  bytes_total: number;
  current_speed: number;
  current_eta?: number | null;
  current_filename?: string | null;
  current_percent: number;
}

// ───── AI types ─────
export interface TagResult {
  path: string;
  filename: string;
  scores: Record<string, number>;
  top_tag: string | null;
  top_score: number;
}

export interface TaggingResponse {
  job_id: string;
  harvester_job_id: string;
  total_images: number;
  tagged: number;
  results: TagResult[];
}
