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
  current_downloaded_bytes?: number;
  current_total_bytes?: number;
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

// ───── Tech Detector types ─────
export interface TechMatch {
  name: string;
  version: string | null;
  confidence: number;
  categories: string[];
  icon: string | null;
  website: string | null;
  cpe: string | null;
  matched_on: string[];
}

export interface TechScanResponse {
  url: string;
  final_url: string;
  status_code: number;
  fetched_at: string;
  technologies: TechMatch[];
  by_category: Record<string, TechMatch[]>;
}

// ───── Screenshot types ─────
export type ScreenshotColorScheme = "light" | "dark" | "both";
export type ScreenshotOutputFormat = "png" | "jpeg" | "webp" | "pdf";
export type ScreenshotWaitUntil = "load" | "domcontentloaded" | "networkidle";
export type WatermarkPosition =
  | "top-left"
  | "top-right"
  | "bottom-left"
  | "bottom-right"
  | "center";

export interface ScreenshotRequest {
  url: string;
  viewports: string[];
  custom_width?: number | null;
  custom_height?: number | null;
  full_page: boolean;
  color_scheme: ScreenshotColorScheme;
  device_scale: number;
  output_format: ScreenshotOutputFormat;
  jpeg_quality: number;
  element_selector?: string | null;
  multiple_elements: boolean;
  hide_selectors?: string[];
  wait_for_selector?: string | null;
  wait_until: ScreenshotWaitUntil;
  scroll_through: boolean;
  timeout_ms: number;
  custom_css?: string | null;
  watermark_text?: string | null;
  watermark_position: WatermarkPosition;
  watermark_opacity: number;
  use_auth_vault: boolean;
}

export interface ScreenshotCapture {
  file_path: string;
  file_url: string | null;
  file_size_bytes: number;
  dimensions: { width: number; height: number };
  viewport_used: string;
  color_scheme_used: string;
  format: string;
  element_index?: number | null;
}

export interface ScreenshotResponse {
  job_id: string;
  url: string;
  final_url: string;
  title: string;
  status: number;
  captures: ScreenshotCapture[];
  duration_ms: number;
}

export interface ScreenshotViewport {
  key: string;
  label: string;
  width?: number | null;
  height?: number | null;
  custom: boolean;
}

export interface BatchScreenshotRequest extends Omit<ScreenshotRequest, "url"> {
  urls: string[];
}

export interface BatchResult {
  url: string;
  final_url?: string | null;
  status: number;
  captures: ScreenshotCapture[];
  error?: string | null;
}

export interface BatchScreenshotResponse {
  job_id: string;
  results: BatchResult[];
  duration_ms: number;
}

export interface GalleryFile {
  filename: string;
  file_url: string;
  file_size_bytes: number;
  dimensions?: { width: number; height: number } | null;
  format?: string | null;
  viewport_used?: string | null;
  color_scheme_used?: string | null;
}

export interface GalleryItem {
  job_id: string;
  url: string;
  title?: string | null;
  created_at: string;
  file_count: number;
  files: GalleryFile[];
  thumbnail_url?: string | null;
}

export interface GalleryResponse {
  total: number;
  limit: number;
  offset: number;
  items: GalleryItem[];
}

export interface CompareRequest {
  job_id_a: string;
  filename_a: string;
  job_id_b: string;
  filename_b: string;
  mode: "side_by_side" | "overlay";
}

export interface CompareStats {
  width: number;
  height: number;
  total_pixels: number;
  different_pixels: number;
  diff_ratio: number;
  bbox?: [number, number, number, number] | null;
}

export interface CompareResponse {
  comparison_id: string;
  diff_image_url: string;
  stats: CompareStats;
}

export interface VideoRequest {
  url: string;
  viewport: string;
  scroll_duration_ms: number;
  fps: number;
  output_format: "mp4" | "gif" | "webm";
  use_auth_vault: boolean;
}

export interface VideoResponse {
  job_id: string;
  file_url: string;
  file_path: string;
  file_size_bytes: number;
  duration_ms: number;
  output_format: string;
  viewport_used: string;
  final_url: string;
  title: string;
  status: number;
}

// ───── SEO Auditor types ─────
export interface SeoIssue {
  severity: "error" | "warning" | "info";
  code: string;
  message: string;
}

export interface SeoAuditResponse {
  url: string;
  final_url: string;
  status_code: number;
  fetched_at: string;
  score: number;
  title: string | null;
  title_length: number;
  description: string | null;
  description_length: number;
  canonical: string | null;
  robots: string | null;
  lang: string | null;
  viewport: string | null;
  has_favicon: boolean;
  og: Record<string, string>;
  twitter: Record<string, string>;
  h1: string[];
  h2: string[];
  h1_count: number;
  h2_count: number;
  h3_count: number;
  h4_count: number;
  img_total: number;
  img_without_alt: number;
  a_internal: number;
  a_external: number;
  structured_data: string[];
  word_count: number;
  issues: SeoIssue[];
}

// ───── Broken Link Checker types ─────
export interface LinkEntry {
  url: string;
  status: number;
  ok: boolean;
  latency_ms: number;
  redirect_chain: string[];
  reason: string;
  source_page: string;
}

export interface LinkCheckResponse {
  url: string;
  fetched_at: string;
  elapsed_sec: number;
  total_pages: number;
  total_links: number;
  unique_links: number;
  ok_count: number;
  broken_count: number;
  redirect_count: number;
  by_status: Record<string, number>;
  broken_list: LinkEntry[];
  all_links: LinkEntry[];
}

// ───── Security Headers types ─────
export interface SecurityCookie {
  name: string;
  httponly: boolean;
  secure: boolean;
  samesite: string | null;
  path: string;
}

export interface SecurityIssue {
  severity: "error" | "warning" | "info";
  header: string;
  message: string;
}

export interface SecurityScanResponse {
  url: string;
  final_url: string;
  status_code: number;
  fetched_at: string;
  score: number;
  grade: string;
  headers_found: Record<string, string>;
  headers_missing: string[];
  all_response_headers: Record<string, string>;
  cookies: SecurityCookie[];
  issues: SecurityIssue[];
}

// ───── SSL Inspector types ─────
export interface SslIssue {
  severity: "error" | "warning" | "info";
  message: string;
}

export interface SslCipher {
  name: string | null;
  protocol: string | null;
  bits: number | null;
}

export interface SslInspectResponse {
  hostname: string;
  port: number;
  fetched_at: string;
  subject: Record<string, string>;
  issuer: Record<string, string>;
  valid_from: string | null;
  valid_to: string | null;
  valid_from_iso: string | null;
  valid_to_iso: string | null;
  serial_number: string | null;
  version: number | null;
  san: string[];
  days_until_expiry: number | null;
  is_expired: boolean;
  is_self_signed: boolean;
  hostname_match: boolean;
  tls_version: string | null;
  cipher: SslCipher | null;
  cert_size_bytes: number;
  issues: SslIssue[];
}

// ───── Domain Intel types ─────
export interface WhoisData {
  registered?: boolean | null;
  domain?: string;
  registrar?: string | null;
  registration_date?: string | null;
  expiration_date?: string | null;
  last_updated?: string | null;
  nameservers?: string[];
  status?: string[];
  registrant_country?: string | null;
  error?: string | null;
}

export interface SpfRecord {
  found: boolean;
  raw: string | null;
  policy: string;
  all_directive: string | null;
  includes: string[];
  mechanisms: string[];
  warnings: string[];
}

export interface DmarcRecord {
  found: boolean;
  raw: string | null;
  policy: string | null;
  subdomain_policy: string | null;
  pct: number | null;
  rua: string[];
  ruf: string[];
  warnings: string[];
}

export interface DkimRecord {
  selectors_checked: string[];
  selectors_found: string[];
}

export interface EmailSecurityRecord {
  spf: SpfRecord;
  dmarc: DmarcRecord;
  dkim: DkimRecord;
  grade: string;
}

export interface DomainIntelResponse {
  domain: string;
  whois: WhoisData;
  dns: Record<string, string[]>;
  subdomains: string[];
  subdomain_count: number;
  fetched_at: string;
  email_security?: EmailSecurityRecord | null;
}

// ───── Exposure Scanner types ─────
export type ExposureSeverity = "critical" | "high" | "medium" | "low" | "info";

export interface ExposureFinding {
  path: string;
  category: string;
  severity: ExposureSeverity;
  status: number;
  content_preview: string | null;
  plausible: boolean;
}

export interface ExposureScanResponse {
  base_url: string;
  scanned_at: string;
  total_checked: number;
  total_found: number;
  findings: ExposureFinding[];
  error: string | null;
}

// ───── Wayback Machine types ─────
export interface WaybackSnapshot {
  timestamp: string;
  url: string;
  status: string;
  digest: string;
  length: string;
  mimetype?: string;
  snapshot_url: string;
}

export interface WaybackSnapshotsResponse {
  url: string;
  count: number;
  snapshots: WaybackSnapshot[];
}

// ───── Sitemap Analyzer types ─────
export interface SitemapUrlEntry {
  loc: string;
  lastmod?: string | null;
  changefreq?: string | null;
  priority?: string | null;
}

export interface SitemapStats {
  lastmod_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  by_path: { path: string; count: number }[];
  unique_domains: string[];
}

export interface SitemapSubSitemap {
  url: string;
  depth: number;
  kind?: string;
  urls?: number;
  sub_count?: number;
  status?: string;
}

export interface SitemapAnalyzeResponse {
  sitemap_url: string | null;
  source: string;
  total_urls: number;
  stats: SitemapStats;
  sample_urls: SitemapUrlEntry[];
  sub_sitemaps: SitemapSubSitemap[];
  fetched_at?: string;
  error?: string;
}

// ───── Threat Scanner types ─────
export type ThreatSeverity = "critical" | "high" | "medium" | "low" | "info";
export type ThreatVerdict = "clean" | "suspicious" | "dangerous";
export type ThreatDepth = "quick" | "standard" | "deep";

export interface ThreatFinding {
  category: string;
  severity: ThreatSeverity;
  title: string;
  description: string;
  score_delta: number;
}

export interface AIExplanation {
  analysis: string;
  model_used: string;
  tokens_used: number;
  cost_usd: number;
  cached: boolean;
}

export interface AIUsageStats {
  total_calls_30d: number;
  total_tokens_30d: number;
  total_cost_30d: number;
}

export interface ThreatScanResponse {
  job_id: string;
  file_path: string;
  file_size: number;
  sha256: string;
  detected_type: string | null;
  claimed_type: string;
  type_spoof: boolean;
  entropy: number;
  findings: ThreatFinding[];
  risk_score: number;
  verdict: ThreatVerdict;
  scanned_at: string;
  scan_duration_ms: number;
  ai_explanation?: AIExplanation | null;
}

export interface TopThreat {
  category: string;
  count: number;
}

export interface FolderScanResponse {
  job_id: string;
  folder_path: string;
  files_total: number;
  files_clean: number;
  files_suspicious: number;
  files_dangerous: number;
  top_threats: TopThreat[];
  files: ThreatScanResponse[];
}

export interface QuarantineEntry {
  id: string;
  original_path: string;
  quarantine_path: string;
  sha256: string;
  moved_at: string;
  reason: string;
}

export interface YaraRule {
  name: string;
  namespace: string;
  tags: string[];
  source: string;
}

export interface ThreatStats {
  total_scans: number;
  total_findings: number;
  verdict_breakdown: { clean: number; suspicious: number; dangerous: number };
  top_categories: TopThreat[];
}

export interface MetadataInspectionResponse {
  file_type: string;
  size_bytes: number;
  modified_at: string | null;
  categories: {
    exif?: Record<string, any> | null;
    pdf?: Record<string, any> | null;
    office?: Record<string, any> | null;
    media?: Record<string, any> | null;
    generic: Record<string, any>;
  };
}

export interface OSINTFinding {
  category: "emails" | "socials" | "cloud" | "phones" | "secrets" | "custom";
  subcategory: string | null;
  value: string;
  source_url: string;
  context_snippet: string | null;
}

export interface OSINTReport {
  job_id: string;
  url: string;
  started_at: string;
  finished_at: string | null;
  pages_crawled: number;
  findings: OSINTFinding[];
  stats: {
    emails: number;
    socials: number;
    cloud: number;
    phones: number;
    secrets: number;
    custom: number;
  };
}

export interface OSINTRequest {
  url: string;
  max_depth: number;
  max_pages: number;
  stay_on_domain: boolean;
  filters?: Record<string, boolean>;
  custom_patterns: string[];
}

// ───── Price Watcher types ─────
export type PriceSelectorType = "auto" | "css" | "xpath";

export interface PriceProductInput {
  url: string;
  title?: string;
  selector?: string;
  selector_type?: PriceSelectorType;
  interval_minutes?: number;
  enabled?: boolean;
  alert_below?: number | null;
  alert_above?: number | null;
  currency?: string;
}

export interface PriceProduct {
  id: string;
  url: string;
  title: string;
  selector: string;
  selector_type: PriceSelectorType;
  interval_minutes: number;
  enabled: boolean;
  alert_below: number | null;
  alert_above: number | null;
  currency: string;
  last_checked_at: string | null;
  last_price: number | null;
  last_status: string;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface PriceHistory {
  id: number;
  product_id: string;
  price: number;
  status: string;
  raw_text: string | null;
  checked_at: string;
}

export interface PriceExtractPreview {
  price: number | null;
  status: string;
  raw_text: string | null;
  error: string | null;
  matched_on: string | null;
  title: string;
}

// ─── Comment Harvester (P11) ───
export interface SentimentScore {
  label: "positive" | "neutral" | "negative";
  confidence: number;
}

export interface CommentNode {
  id: string;
  author?: string | null;
  text: string;
  timestamp?: string | null;
  upvotes?: number | null;
  depth: number;
  sentiment?: SentimentScore | null;
  replies: CommentNode[];
}

export interface CommentHarvestRequest {
  url: string;
  max_comments: number;
  include_replies: boolean;
  sentiment_enabled: boolean;
}

export interface CommentHarvestReport {
  url: string;
  platform: "youtube" | "reddit" | "forum" | "unknown" | string;
  title?: string | null;
  fetched_at: string;
  total_comments: number;
  total_replies: number;
  max_depth: number;
  sentiment_summary?: {
    positive: number;
    neutral: number;
    negative: number;
  } | null;
  comments: CommentNode[];
}

export interface CommentHarvestResponse {
  job_id: string;
  status: string;
  report?: CommentHarvestReport | null;
  error_message?: string | null;
}


// ─── API Sniffer (P12) ───
export type ApiSnifferStatus = "pending" | "running" | "done" | "error" | "stopped";

export interface CapturedRequest {
  request_id: string;
  method: string;
  url: string;
  full_url: string;
  host: string;
  path: string;
  resource_type?: string | null;
  request_headers: Record<string, string>;
  request_body?: string | null;
  request_body_json?: any;
  status?: number | null;
  response_content_type?: string | null;
  response_body?: string | null;
  response_body_json?: any;
  response_size_bytes: number;
  started_at: number;
  duration_ms?: number | null;
  is_graphql: boolean;
  graphql_operation?: string | null;
}

export interface ApiSnifferEndpoint {
  host: string;
  method: string;
  path: string;
  count: number;
  statuses: Record<string, number>;
  content_types: Record<string, number>;
  sample_request: CapturedRequest;
  is_graphql: boolean;
}

export interface ApiSnifferGraphQLOp {
  operation_name: string;
  operation_type?: string | null;
  query?: string | null;
  variables?: any;
  response_sample?: any;
  count: number;
  host: string;
  path: string;
}

export interface ApiSnifferStats {
  total_requests: number;
  unique_endpoints: number;
  graphql_ops: number;
  content_type_breakdown: Record<string, number>;
  status_breakdown: Record<string, number>;
  total_response_bytes: number;
}

export interface ApiSnifferReport {
  url: string;
  final_url: string;
  started_at: string;
  finished_at: string;
  duration_seconds: number;
  stats: ApiSnifferStats;
  endpoints: ApiSnifferEndpoint[];
  graphql_ops: ApiSnifferGraphQLOp[];
  requests: CapturedRequest[];
}

export interface PdfDocument {
  pdf_id: string;
  url: string;
  filename: string;
  discovered_from: string | null;
  downloaded: boolean;
  local_path: string | null;
  file_size: number;
  page_count: number | null;
  title: string | null;
  author: string | null;
  subject: string | null;
  keywords: string | null;
  creator: string | null;
  producer: string | null;
  creation_date: string | null;
  mod_date: string | null;
  preview_text: string | null;
  text_content: string | null;
  error: string | null;
}

export interface PdfHarvestReport {
  job_id: string;
  url: string;
  started_at: string;
  finished_at: string | null;
  pages_crawled: number;
  pdfs_found: number;
  pdfs_downloaded: number;
  total_size: number;
  documents: PdfDocument[];
  stats: {
    pages_crawled: number;
    pdfs_found: number;
    pdfs_downloaded: number;
    total_size: number;
    unique_authors: number;
  };
}

export interface PdfHarvestRequest {
  url: string;
  max_depth: number;
  max_pages: number;
  max_pdfs: number;
  download: boolean;
  extract_text: boolean;
}

export interface PdfSearchHit {
  pdf_id: string;
  snippet: string;
  match_count: number;
}
