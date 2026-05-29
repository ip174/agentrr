import type { SessionVerdict } from "../storyModel";
import { run as runCopy } from "../copy";

type Props = {
  verdict: SessionVerdict;
  playing: boolean;
  stepLoading: boolean;
  playbackDone: boolean;
  storyProgress: string | null;
  onCheckReplay: () => void;
  onNext: () => void;
  onStop: () => void;
};

export default function VerdictBand({
  verdict,
  playing,
  stepLoading,
  playbackDone,
  storyProgress,
  onCheckReplay,
  onNext,
  onStop,
}: Props) {
  const chipClass = `verdict-chip verdict-${verdict.status}`;

  return (
    <section className="card verdict-card">
      <div className="verdict-top">
        <span className={chipClass}>{verdict.statusLabel}</span>
        <p className="verdict-outcome">{verdict.outcome}</p>
      </div>

      {!playing ? (
        <div className="verdict-actions">
          <p className="verdict-help">{runCopy.replayHelp}</p>
          <button type="button" className="btn btn-primary" onClick={onCheckReplay}>
            {runCopy.checkReplay}
          </button>
        </div>
      ) : (
        <div className="verdict-actions">
          {storyProgress ? <p className="verdict-progress">{storyProgress}</p> : null}
          {stepLoading ? <p className="verdict-hint">{runCopy.statusWorkingHint}</p> : null}
          <div className="playback-buttons">
            <button
              type="button"
              className="btn btn-primary"
              onClick={onNext}
              disabled={stepLoading || playbackDone}
            >
              {stepLoading ? runCopy.nextWorking : runCopy.next}
            </button>
            <button type="button" className="btn btn-ghost" onClick={onStop}>
              {runCopy.end}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
