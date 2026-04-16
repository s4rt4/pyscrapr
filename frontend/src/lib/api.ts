import type {
  AssetDTO,
  HarvesterStartRequest,
  JobDTO,
  MapperStartRequest,
  MediaProbeResponse,
  MediaStartRequest,
  RipperStartRequest,
  SitemapGraphResponse,
  SitemapTreeNode,
  TaggingResponse,
} from "../types";

const BASE = "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async health(): Promise<{ status: string; version: string }> {
    return json(await fetch(`${BASE}/health`));
  },

  async startHarvester(
    payload: HarvesterStartRequest
  ): Promise<{ job_id: string; status: string }> {
    return json(
      await fetch(`${BASE}/harvester/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  async stopHarvester(jobId: string): Promise<void> {
    await fetch(`${BASE}/harvester/stop/${jobId}`, { method: "POST" });
  },

  async getJob(jobId: string): Promise<JobDTO> {
    return json(await fetch(`${BASE}/harvester/jobs/${jobId}`));
  },

  async listAssets(jobId: string): Promise<AssetDTO[]> {
    return json(await fetch(`${BASE}/harvester/jobs/${jobId}/assets`));
  },

  async listHistory(): Promise<JobDTO[]> {
    return json(await fetch(`${BASE}/history`));
  },

  downloadZipUrl(jobId: string): string {
    return `${BASE}/downloads/${jobId}/zip`;
  },

  // ─────── Mapper ───────
  async startMapper(payload: MapperStartRequest): Promise<{ job_id: string; status: string }> {
    return json(
      await fetch(`${BASE}/mapper/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  async stopMapper(jobId: string): Promise<void> {
    await fetch(`${BASE}/mapper/stop/${jobId}`, { method: "POST" });
  },

  async resumeMapper(jobId: string): Promise<void> {
    await fetch(`${BASE}/mapper/resume/${jobId}`, { method: "POST" });
  },

  async getMapperJob(jobId: string): Promise<JobDTO> {
    return json(await fetch(`${BASE}/mapper/jobs/${jobId}`));
  },

  async getMapperTree(jobId: string): Promise<SitemapTreeNode[]> {
    return json(await fetch(`${BASE}/mapper/jobs/${jobId}/tree`));
  },

  async getMapperGraph(jobId: string): Promise<SitemapGraphResponse> {
    return json(await fetch(`${BASE}/mapper/jobs/${jobId}/graph`));
  },

  mapperExportJsonUrl(jobId: string): string {
    return `${BASE}/mapper/jobs/${jobId}/export/json`;
  },

  mapperExportXmlUrl(jobId: string): string {
    return `${BASE}/mapper/jobs/${jobId}/export/xml`;
  },

  // ─────── Ripper ───────
  async startRipper(payload: RipperStartRequest): Promise<{ job_id: string; status: string }> {
    return json(
      await fetch(`${BASE}/ripper/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  async stopRipper(jobId: string): Promise<void> {
    await fetch(`${BASE}/ripper/stop/${jobId}`, { method: "POST" });
  },

  async getRipperJob(jobId: string): Promise<JobDTO> {
    return json(await fetch(`${BASE}/ripper/jobs/${jobId}`));
  },

  ripperReportUrl(jobId: string): string {
    return `${BASE}/ripper/jobs/${jobId}/report`;
  },

  ripperZipUrl(jobId: string): string {
    return `${BASE}/ripper/jobs/${jobId}/zip`;
  },

  // ─────── Media ───────
  async probeMedia(
    url: string,
    cookies?: string
  ): Promise<MediaProbeResponse> {
    return json(
      await fetch(`${BASE}/media/probe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, use_browser_cookies: cookies }),
      })
    );
  },

  async startMedia(
    payload: MediaStartRequest
  ): Promise<{ job_id: string; status: string }> {
    return json(
      await fetch(`${BASE}/media/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  async stopMedia(jobId: string): Promise<void> {
    await fetch(`${BASE}/media/stop/${jobId}`, { method: "POST" });
  },

  async getMediaJob(jobId: string): Promise<JobDTO> {
    return json(await fetch(`${BASE}/media/jobs/${jobId}`));
  },

  async listMediaItems(jobId: string): Promise<AssetDTO[]> {
    return json(await fetch(`${BASE}/media/jobs/${jobId}/items`));
  },

  mediaFileUrl(jobId: string, assetId: number): string {
    return `${BASE}/media/jobs/${jobId}/file/${assetId}`;
  },

  // ─────── AI ───────
  async listHarvesterJobs(): Promise<JobDTO[]> {
    return json(await fetch(`${BASE}/ai/harvester-jobs`));
  },

  async startTagging(harvesterJobId: string, labels: string[]): Promise<{ job_id: string }> {
    return json(
      await fetch(`${BASE}/ai/tag/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ harvester_job_id: harvesterJobId, labels }),
      })
    );
  },

  async stopTagging(jobId: string): Promise<void> {
    await fetch(`${BASE}/ai/tag/stop/${jobId}`, { method: "POST" });
  },

  async getTaggingResults(jobId: string): Promise<TaggingResponse> {
    return json(await fetch(`${BASE}/ai/tag/jobs/${jobId}/results`));
  },
};

export function subscribeRipperEvents(jobId: string): EventSource {
  return new EventSource(`${BASE}/ripper/jobs/${jobId}/events`);
}

export function subscribeMediaEvents(jobId: string): EventSource {
  return new EventSource(`${BASE}/media/jobs/${jobId}/events`);
}

export function subscribeAIEvents(jobId: string): EventSource {
  return new EventSource(`${BASE}/ai/tag/jobs/${jobId}/events`);
}

export function subscribeMapperEvents(jobId: string): EventSource {
  return new EventSource(`${BASE}/mapper/jobs/${jobId}/events`);
}
