import type { SSEEvent } from "../types";

export function subscribeJobEvents(
  jobId: string,
  onEvent: (e: SSEEvent) => void
): () => void {
  const source = new EventSource(`/api/harvester/jobs/${jobId}/events`);
  source.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data) as SSEEvent;
      onEvent(data);
      if (
        data.type === "done" ||
        data.type === "error" ||
        data.type === "stopped"
      ) {
        source.close();
      }
    } catch (err) {
      console.warn("SSE parse error", err);
    }
  };
  source.onerror = () => {
    source.close();
  };
  return () => source.close();
}
