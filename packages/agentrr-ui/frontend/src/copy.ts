/** Plain-language UI copy. */

export const brand = {
  name: "agentrr",
  tagline: "See what your AI agent did—and where it started doing something different",
} as const;

export const home = {
  title: "Saved agent sessions",
  aboutTip:
    "agentrr records what an AI agent does during a run—like a flight recorder. Later, you can open that recording and play it back to see if the agent still behaves the same way. If something changed (a bug, an update, a bad prompt), this tool shows you where it first went off track.",
  refresh: "Refresh",
  emptyTitle: "No sessions yet",
  emptyBody:
    "When your team records an agent run, it will show up here. Ask engineering to run a test, then click Refresh.",
  loadErrorTitle: "Could not load sessions",
  incomplete: "Incomplete",
} as const;

export const run = {
  back: "Back",
  /** Shown at top of session page — what this screen is for. */
  pageLead:
    "This is a saved recording of one agent run. The list below is what happened, in order. “Check replay” re-runs the agent to see if it still does the same thing.",
  storyTitle: "What happened",
  storyHint: "Each row is one step. Expand a row only if you need technical detail.",
  checkReplay: "Check replay",
  replayHelp:
    "Runs the agent again using saved answers from this recording (not live API calls for past steps). Stops at the first step that behaves differently.",
  next: "Next",
  end: "Stop checking",
  statusWorking: "Checking…",
  statusWorkingHint: "Each step can take a few seconds.",
  statusPressNext: (total: number, firstTitle: string) =>
    `Press Next to check step 1 of ${total} (${firstTitle}).`,
  statusCheckingNamed: (n: number, total: number, title: string) =>
    `Checking step ${n} of ${total}: ${title}…`,
  statusCheckedAdvance: (done: number, total: number, nextTitle: string) =>
    `Checked ${done} of ${total}. Press Next for ${nextTitle}.`,
  statusPressNextToFinish: "All steps matched. Press Next to finish.",
  statusReplayReady: "Press Next to check each important step one at a time.",
  statusDifference: "Stopped—a difference was found. See the highlighted step below.",
  statusFinished: "Replay matched the full recording.",
  statusFinishedEarly:
    "Replay finished without pausing on individual steps. Try a newly recorded session.",
  statusError: "Replay stopped due to an error.",
  nextWorking: "Please wait…",
  forEngineers: "Advanced",
  showSetup: "Show system setup steps",
  hideSetup: "Hide system setup",
} as const;

export function friendlySessionName(runId: string): string {
  const base = runId.replace(/-[a-f0-9]{8,}$/i, "").replace(/-/g, " ");
  if (!base) return runId;
  return base.charAt(0).toUpperCase() + base.slice(1);
}
