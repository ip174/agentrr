import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { friendlySessionName, run as runCopy } from "./copy";
import StoryBeatRow from "./components/StoryBeatRow";
import TechDetails from "./components/TechDetails";
import VerdictBand from "./components/VerdictBand";
import {
  buildStory,
  buildVerdict,
  findBeatForSeq,
  replayBeatIndexForBoundary,
  replayStoryBeats,
} from "./storyModel";
import {
  fetchEvents,
  fetchRun,
  startReplay,
  stepReplay,
  stopReplay,
  type AgentEvent,
  type WorkerMessage,
} from "./api";

type ReplayStatus = "none" | "in_progress" | "matched" | "difference" | "error";

function formatReplayProgress(
  playing: boolean,
  stepLoading: boolean,
  playbackDone: boolean,
  completed: number,
  replayBeats: { id: string; title: string }[],
  checkingBeatId: string | null
): string | null {
  const total = replayBeats.length;
  if (!playing || playbackDone || total === 0) return null;

  if (stepLoading) {
    const beat =
      replayBeats.find((b) => b.id === checkingBeatId) ?? replayBeats[completed];
    const stepNum = Math.min(completed + 1, total);
    return beat
      ? runCopy.statusCheckingNamed(stepNum, total, beat.title)
      : runCopy.statusCheckingNamed(stepNum, total, "step");
  }

  if (completed === 0) {
    return runCopy.statusPressNext(total, replayBeats[0]?.title ?? "step");
  }
  if (completed < total) {
    const next = replayBeats[completed];
    return runCopy.statusCheckedAdvance(
      completed,
      total,
      next?.title ?? "next step"
    );
  }
  return runCopy.statusPressNextToFinish;
}

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [meta, setMeta] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [expandedBeatId, setExpandedBeatId] = useState<string | null>(null);
  const [activeSeq, setActiveSeq] = useState<number | null>(null);
  const [hideSetup, setHideSetup] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [divergence, setDivergence] = useState<WorkerMessage | null>(null);
  const [playing, setPlaying] = useState(false);
  const [stepLoading, setStepLoading] = useState(false);
  const [replayStatus, setReplayStatus] = useState<ReplayStatus>("none");
  const [replayMessage, setReplayMessage] = useState<string | undefined>();
  const [playbackDone, setPlaybackDone] = useState(false);
  /** Story beats successfully checked so far (0..N). */
  const [completedStorySteps, setCompletedStorySteps] = useState(0);
  const [checkingBeatId, setCheckingBeatId] = useState<string | null>(null);

  const allBeats = useMemo(() => buildStory(events), [events]);
  const visibleBeats = useMemo(
    () => (hideSetup ? allBeats.filter((b) => b.kind !== "setup") : allBeats),
    [allBeats, hideSetup]
  );
  const replayBeats = useMemo(() => replayStoryBeats(visibleBeats), [visibleBeats]);
  const replayBeatsRef = useRef(replayBeats);
  replayBeatsRef.current = replayBeats;

  const verdict = useMemo(
    () =>
      buildVerdict(events, allBeats, {
        truncated: Boolean(meta?.truncated),
        replayStatus,
        replayMessage,
      }),
    [events, allBeats, meta?.truncated, replayStatus, replayMessage]
  );

  useEffect(() => {
    if (!runId) return;
    fetchRun(runId).then(setMeta);
    fetchEvents(runId).then((d) => setEvents(d.events));
  }, [runId]);

  const highlightBeat = (seq: number) => {
    setActiveSeq(seq);
    const beat = findBeatForSeq(allBeats, seq);
    if (beat) {
      setExpandedBeatId(beat.id);
      if (hideSetup && beat.kind === "setup") setHideSetup(false);
    }
  };

  const applyWorkerMessage = (msg: WorkerMessage) => {
    const beats = replayBeatsRef.current;

    if (msg.type === "boundary" && msg.seq != null) {
      highlightBeat(msg.seq);
      const rIdx = replayBeatIndexForBoundary(beats, msg.seq, msg.event_type);
      if (rIdx >= 0) {
        setCompletedStorySteps(rIdx + 1);
      }
      setCheckingBeatId(null);
      setReplayStatus("in_progress");
      setPlaybackDone(false);
    } else if (msg.type === "divergence") {
      setDivergence(msg);
      const divSeq = msg.report?.divergences?.[0]?.seq;
      if (divSeq != null) highlightBeat(divSeq);
      setCheckingBeatId(null);
      setReplayStatus("difference");
      setReplayMessage(runCopy.statusDifference);
      setPlaybackDone(true);
    } else if (msg.type === "complete") {
      setCheckingBeatId(null);
      setReplayStatus("matched");
      setCompletedStorySteps((prev) => {
        setReplayMessage(
          prev > 0 || beats.length === 0
            ? runCopy.statusFinished
            : runCopy.statusFinishedEarly
        );
        return beats.length;
      });
      setPlaybackDone(true);
    } else if (msg.type === "error") {
      setCheckingBeatId(null);
      setReplayStatus("error");
      setReplayMessage(msg.message ?? runCopy.statusError);
      setPlaybackDone(true);
    }
  };

  const beginPlayback = async () => {
    if (!runId) return;
    setDivergence(null);
    setPlaybackDone(false);
    setActiveSeq(null);
    setCompletedStorySteps(0);
    setCheckingBeatId(null);
    setReplayStatus("in_progress");
    setReplayMessage(undefined);
    try {
      const { session_id } = await startReplay(runId, "strict");
      setSessionId(session_id);
      setPlaying(true);
    } catch (e) {
      setReplayStatus("error");
      setReplayMessage(String(e));
      setPlaying(false);
    }
  };

  const handleNextStep = async () => {
    if (!sessionId || stepLoading || playbackDone) return;
    const beats = replayBeatsRef.current;
    const nextBeat = beats[completedStorySteps];
    setCheckingBeatId(nextBeat?.id ?? null);
    setStepLoading(true);
    try {
      const msg = await stepReplay(sessionId);
      applyWorkerMessage(msg);
    } catch (e) {
      setReplayStatus("error");
      setReplayMessage(String(e));
      setPlaybackDone(true);
      setCheckingBeatId(null);
    } finally {
      setStepLoading(false);
    }
  };

  const endPlayback = async () => {
    if (sessionId) {
      try {
        await stopReplay(sessionId);
      } catch {
        /* ok */
      }
    }
    setSessionId(null);
    setPlaying(false);
    setPlaybackDone(false);
    setStepLoading(false);
    setActiveSeq(null);
    setCompletedStorySteps(0);
    setCheckingBeatId(null);
    setReplayStatus("none");
    setReplayMessage(undefined);
    setDivergence(null);
  };

  if (!runId) return null;

  const div = divergence?.report?.divergences?.[0];
  const displayName = friendlySessionName(runId);
  const hasSetup = allBeats.some((b) => b.kind === "setup");

  const storyProgress = formatReplayProgress(
    playing,
    stepLoading,
    playbackDone,
    completedStorySteps,
    replayBeats,
    checkingBeatId
  );

  const checkedBeatIds = new Set(
    replayBeats.slice(0, completedStorySteps).map((b) => b.id)
  );

  return (
    <div className="page">
      <Link to="/" className="back-link">
        ← {runCopy.back}
      </Link>

      <h1 className="page-h1">{displayName}</h1>
      <p className="page-lead">{runCopy.pageLead}</p>

      <VerdictBand
        verdict={verdict}
        playing={playing}
        stepLoading={stepLoading}
        playbackDone={playbackDone}
        storyProgress={storyProgress}
        onCheckReplay={beginPlayback}
        onNext={handleNextStep}
        onStop={endPlayback}
      />

      <section className="card timeline-card">
        <div className="story-header">
          <div>
            <h2 className="card-title">{runCopy.storyTitle}</h2>
            <p className="card-hint">{runCopy.storyHint}</p>
          </div>
          {hasSetup ? (
            <button
              type="button"
              className="btn-text"
              onClick={() => setHideSetup((v) => !v)}
            >
              {hideSetup ? runCopy.showSetup : runCopy.hideSetup}
            </button>
          ) : null}
        </div>
        <div className="step-list">
          {visibleBeats.map((beat, i) => {
            const diff =
              div && beat.events.some((e) => e.seq === div.seq) ? div.diff : null;
            const isReplayBeat = beat.kind === "ask_ai" || beat.kind === "use_tool";
            const isChecking =
              playing && isReplayBeat && checkingBeatId === beat.id;
            const isChecked =
              playing && isReplayBeat && checkedBeatIds.has(beat.id);
            const isActive =
              activeSeq != null && beat.events.some((e) => e.seq === activeSeq);
            return (
              <StoryBeatRow
                key={beat.id}
                beat={beat}
                stepNumber={i + 1}
                expanded={expandedBeatId === beat.id}
                isPlayingHere={isChecking || (isActive && playing && stepLoading)}
                isChecked={isChecked && !isChecking}
                isMismatch={Boolean(diff)}
                diff={diff}
                onToggle={() =>
                  setExpandedBeatId((id) => (id === beat.id ? null : beat.id))
                }
              />
            );
          })}
        </div>
      </section>

      <TechDetails>
        <dl className="meta-list">
          <div>
            <dt>Log steps</dt>
            <dd>{String(meta?.event_count ?? events.length)}</dd>
          </div>
          <div>
            <dt>Story steps</dt>
            <dd>{visibleBeats.length}</dd>
          </div>
          <div>
            <dt>Replay checks</dt>
            <dd>
              {playing
                ? `${completedStorySteps} / ${replayBeats.length}`
                : replayBeats.length}
            </dd>
          </div>
          {meta?.truncated ? (
            <div>
              <dt>Recording</dt>
              <dd>Incomplete</dd>
            </div>
          ) : null}
          <div>
            <dt>Session ID</dt>
            <dd>
              <code>{runId}</code>
            </dd>
          </div>
          <div>
            <dt>Entrypoint</dt>
            <dd>
              <code>{String(meta?.entrypoint ?? "—")}</code>
            </dd>
          </div>
        </dl>
      </TechDetails>
    </div>
  );
}
