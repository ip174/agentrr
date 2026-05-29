export type RunSummary = {
  run_id: string;
  path: string;
  mtime_iso: string;
  truncated: boolean;
  event_count: number;
  entrypoint: string | null;
};

export type AgentEvent = {
  seq: number;
  type: string;
  request: Record<string, unknown>;
  response: Record<string, unknown> | null;
  error: { type: string; message: string } | null;
  status: string;
  meta: Record<string, unknown>;
};

async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  const r = await fetch(url, init);
  if (!r.ok) {
    const body = await r.text();
    if (body.includes("Error code explanation") || body.startsWith("<!DOCTYPE")) {
      throw new Error(
        "The app could not reach the server. Ask engineering to start agentrr-ui on this computer (not a generic file server)."
      );
    }
    throw new Error(body || `${r.status} ${r.statusText}`);
  }
  const ct = r.headers.get("content-type") ?? "";
  if (!ct.includes("application/json")) {
    throw new Error(
      "The server did not respond correctly. Engineering should run the agentrr-ui command, then open http://127.0.0.1:8765"
    );
  }
  return r;
}

export async function fetchRuns(): Promise<RunSummary[]> {
  const r = await apiFetch("/api/runs");
  return r.json();
}

export async function fetchRun(runId: string) {
  const r = await apiFetch(`/api/runs/${encodeURIComponent(runId)}`);
  return r.json();
}

export async function fetchEvents(runId: string, fromSeq = 0, limit = 500) {
  const r = await apiFetch(
    `/api/runs/${encodeURIComponent(runId)}/events?from_seq=${fromSeq}&limit=${limit}`
  );
  return r.json() as Promise<{ events: AgentEvent[] }>;
}

export async function startReplay(runId: string, mode: string) {
  const r = await apiFetch("/api/replay/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, mode }),
  });
  return r.json() as Promise<{ session_id: string }>;
}

export type WorkerMessage = {
  type: string;
  seq?: number;
  event_type?: string;
  message?: string;
  report?: {
    divergences?: Array<{
      seq: number;
      diff?: { expected_preview?: string; observed_preview?: string };
    }>;
  };
};

export async function stepReplay(sessionId: string): Promise<WorkerMessage> {
  const r = await apiFetch(`/api/replay/${encodeURIComponent(sessionId)}/step`, {
    method: "POST",
  });
  return r.json();
}

export async function stopReplay(sessionId: string): Promise<void> {
  await apiFetch("/api/replay/stop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}
