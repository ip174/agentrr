import type { AgentEvent } from "./api";

export type StoryBeatKind = "start" | "setup" | "ask_ai" | "use_tool" | "finish" | "other";

export type StoryBeat = {
  id: string;
  kind: StoryBeatKind;
  title: string;
  subtitle: string;
  events: AgentEvent[];
  /** Seq used for replay highlight (first boundary in this beat). */
  primarySeq: number;
};

export type SessionVerdict = {
  status: "recorded" | "complete" | "incomplete" | "replay_matched" | "replay_difference" | "replay_error";
  statusLabel: string;
  outcome: string;
};

const PLUMBING = new Set(["clock_read", "rng_draw", "id_gen", "step_marker"]);

function asString(v: unknown): string | null {
  if (typeof v === "string" && v.trim()) return v.trim();
  return null;
}

function pick(obj: Record<string, unknown>, keys: string[]): string | null {
  for (const k of keys) {
    const s = asString(obj[k]);
    if (s) return s;
  }
  return null;
}

function lastUserMessage(event: AgentEvent): string | null {
  const messages = event.request?.messages;
  if (!Array.isArray(messages)) return null;
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i] as { role?: string; content?: string };
    if (m?.role === "user" && m.content) return m.content;
  }
  return null;
}

function llmResponseSnippet(event: AgentEvent): string | null {
  const res = event.response;
  if (!res || typeof res !== "object") return null;
  const content = pick(res as Record<string, unknown>, ["content", "text", "output"]);
  if (content) return content.length > 120 ? `${content.slice(0, 117)}…` : content;
  const tc = (res as { tool_calls?: unknown[] }).tool_calls;
  if (Array.isArray(tc) && tc.length > 0) {
    const first = tc[0] as { function?: { name?: string } };
    const name = first?.function?.name;
    return name ? `Model chose to call ${name}.` : "Model returned tool calls.";
  }
  return null;
}

function toolResultSnippet(event: AgentEvent): string | null {
  const res = event.response;
  if (!res || typeof res !== "object") return null;
  const value = (res as { value?: unknown }).value ?? res;
  if (value && typeof value === "object") {
    const v = value as Record<string, unknown>;
    const parts: string[] = [];
    const status = asString(v.status);
    const total = v.total;
    const oid = asString(v.order_id);
    if (oid) parts.push(`order ${oid}`);
    if (status) parts.push(status);
    if (total != null) parts.push(`$${total}`);
    if (parts.length) return parts.join(" · ");
  }
  return "Tool completed.";
}

/** Plain description of what the user asked the model—never used as a “verdict”. */
function describePrompt(prompt: string): string {
  const p = prompt.toLowerCase();
  if (p.includes("look up") && p.includes("order")) {
    return "Asked the AI to look up an order.";
  }
  if (p.includes("order")) {
    return "Asked the AI about an order.";
  }
  if (p.includes("summarize")) {
    return "Asked the AI to write a short summary for the customer.";
  }
  if (prompt.length <= 72) {
    return `Asked the AI (“${prompt}”).`;
  }
  return "Asked the AI a question—expand this row for the exact text.";
}

function beatFromLlm(event: AgentEvent): StoryBeat {
  const prompt = lastUserMessage(event);
  const model = pick(event.request ?? {}, ["model"]);
  const toolPlan = llmResponseSnippet(event);
  let subtitle = "Called the language model.";
  if (prompt) {
    subtitle = describePrompt(prompt);
  } else if (model) {
    subtitle = `Called ${model}.`;
  }
  if (toolPlan?.includes("chose to call")) {
    subtitle += " It chose to run a tool next.";
  }
  return {
    id: `llm-${event.seq}`,
    kind: "ask_ai",
    title: "Asked AI",
    subtitle,
    events: [event],
    primarySeq: event.seq,
  };
}

function beatFromTool(event: AgentEvent): StoryBeat {
  const name = pick(event.request ?? {}, ["name", "tool", "tool_name"]) ?? "tool";
  const result = toolResultSnippet(event);
  return {
    id: `tool-${event.seq}`,
    kind: "use_tool",
    title: `Used ${name}`,
    subtitle: result ?? (event.error ? `Failed: ${event.error.message}` : "Completed."),
    events: [event],
    primarySeq: event.seq,
  };
}

/** Build narrative beats from raw log events (4–8 rows for a typical agent). */
export function buildStory(events: AgentEvent[]): StoryBeat[] {
  const beats: StoryBeat[] = [];
  const plumbing: AgentEvent[] = [];

  for (const e of events) {
    if (PLUMBING.has(e.type)) {
      plumbing.push(e);
      continue;
    }
    if (e.type === "run_start") {
      beats.push({
        id: `start-${e.seq}`,
        kind: "start",
        title: "Started",
        subtitle: "Agent run began.",
        events: [e],
        primarySeq: e.seq,
      });
    } else if (e.type === "run_end") {
      beats.push({
        id: `end-${e.seq}`,
        kind: "finish",
        title: "Finished",
        subtitle:
          asString(e.request?.status) === "ok"
            ? "Run completed successfully."
            : `Run ended (${asString(e.request?.status) ?? "unknown"}).`,
        events: [e],
        primarySeq: e.seq,
      });
    } else if (e.type === "llm_call") {
      beats.push(beatFromLlm(e));
    } else if (e.type === "tool_call") {
      beats.push(beatFromTool(e));
    } else {
      beats.push({
        id: `other-${e.seq}`,
        kind: "other",
        title: e.type.replace(/_/g, " "),
        subtitle: "Recorded step.",
        events: [e],
        primarySeq: e.seq,
      });
    }
  }

  if (plumbing.length > 0) {
    const insertAt = beats.findIndex((b) => b.kind === "ask_ai" || b.kind === "use_tool");
    const setup: StoryBeat = {
      id: "setup",
      kind: "setup",
      title: "System setup",
      subtitle: "Time, random values, and IDs (deterministic shims).",
      events: plumbing,
      primarySeq: plumbing[0].seq,
    };
    if (insertAt >= 0) {
      beats.splice(insertAt, 0, setup);
    } else if (beats.length > 0 && beats[0].kind === "start") {
      beats.splice(1, 0, setup);
    } else {
      beats.unshift(setup);
    }
  }

  const start = beats.find((b) => b.kind === "start");
  const firstLlm = beats.find((b) => b.kind === "ask_ai");
  if (start && firstLlm) {
    const prompt = lastUserMessage(firstLlm.events[0]);
    if (prompt?.toLowerCase().includes("order")) {
      const m = prompt.match(/order\s+(\d+)/i);
      if (m) start.subtitle = `Support run for order ${m[1]}.`;
    }
  }

  return beats;
}

export function findBeatForSeq(beats: StoryBeat[], seq: number): StoryBeat | undefined {
  return beats.find(
    (b) =>
      b.primarySeq === seq || b.events.some((e) => e.seq === seq)
  );
}

function recordedOutcome(beats: StoryBeat[], truncated: boolean): string {
  if (truncated) {
    return "Recording stopped before the run finished.";
  }
  const finish = beats.find((b) => b.kind === "finish");
  const ok =
    !finish || finish.subtitle.toLowerCase().includes("success");
  if (!ok) {
    return "The saved run did not finish cleanly. See the timeline below.";
  }
  const asks = beats.filter((b) => b.kind === "ask_ai").length;
  const tools = beats.filter((b) => b.kind === "use_tool").length;
  const parts: string[] = ["This session was saved after a completed agent run."];
  if (asks || tools) {
    const detail: string[] = [];
    if (asks) detail.push(`${asks} AI step${asks === 1 ? "" : "s"}`);
    if (tools) detail.push(`${tools} tool step${tools === 1 ? "" : "s"}`);
    parts.push(`The timeline has ${detail.join(" and ")}.`);
  }
  parts.push("Use Check replay when you want to test whether the agent still behaves the same way.");
  return parts.join(" ");
}

export function buildVerdict(
  _events: AgentEvent[],
  beats: StoryBeat[],
  opts: {
    truncated?: boolean;
    replayStatus: "none" | "in_progress" | "matched" | "difference" | "error";
    replayMessage?: string;
  }
): SessionVerdict {
  if (opts.truncated) {
    return {
      status: "incomplete",
      statusLabel: "Incomplete recording",
      outcome: recordedOutcome(beats, true),
    };
  }

  switch (opts.replayStatus) {
    case "difference":
      return {
        status: "replay_difference",
        statusLabel: "Replay found a difference",
        outcome:
          opts.replayMessage ??
          "The agent did something different from the recording. See the row marked “Changed here”.",
      };
    case "matched":
      return {
        status: "replay_matched",
        statusLabel: "Replay matched",
        outcome:
          "Good news: re-running the agent today followed the same steps as this recording.",
      };
    case "error":
      return {
        status: "replay_error",
        statusLabel: "Replay problem",
        outcome: opts.replayMessage ?? "Replay could not finish. Engineering may need to look at logs.",
      };
    case "in_progress":
      return {
        status: "complete",
        statusLabel: "Checking replay…",
        outcome: opts.replayMessage ?? "Walking through the recording step by step.",
      };
    default:
      return {
        status: "recorded",
        statusLabel: "Saved session",
        outcome: recordedOutcome(beats, false),
      };
  }
}

/** Story beats that advance during replay stepping (meaningful boundaries). */
export function replayStoryBeats(beats: StoryBeat[]): StoryBeat[] {
  return beats.filter((b) => b.kind === "ask_ai" || b.kind === "use_tool");
}

/** Map a replay boundary (seq + type) to an index in replayStoryBeats(). */
export function replayBeatIndexForBoundary(
  replayBeats: StoryBeat[],
  seq: number,
  eventType?: string
): number {
  const bySeq = replayBeats.findIndex(
    (b) => b.primarySeq === seq || b.events.some((e) => e.seq === seq)
  );
  if (bySeq >= 0) return bySeq;
  if (eventType === "llm_call") {
    return replayBeats.findIndex((b) => b.kind === "ask_ai");
  }
  if (eventType === "tool_call") {
    return replayBeats.findIndex((b) => b.kind === "use_tool");
  }
  return -1;
}
