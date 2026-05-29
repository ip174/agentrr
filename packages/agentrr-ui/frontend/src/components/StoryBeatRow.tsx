import type { StoryBeat } from "../storyModel";

type Diff = {
  expected_preview?: string;
  observed_preview?: string;
};

type Props = {
  beat: StoryBeat;
  stepNumber: number;
  expanded: boolean;
  isPlayingHere: boolean;
  isChecked: boolean;
  isMismatch: boolean;
  diff?: Diff | null;
  onToggle: () => void;
};

export default function StoryBeatRow({
  beat,
  stepNumber,
  expanded,
  isPlayingHere,
  isChecked,
  isMismatch,
  diff,
  onToggle,
}: Props) {
  const rowClass = [
    "step-row",
    expanded ? "expanded" : "",
    isPlayingHere ? "playing" : "",
    isChecked ? "checked" : "",
    isMismatch ? "mismatch" : "",
    beat.kind === "setup" ? "setup-beat" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={rowClass}>
      <button type="button" className="step-row-header" onClick={onToggle} aria-expanded={expanded}>
        <span className="step-num">{stepNumber}</span>
        <span className="step-main">
          <span className="step-title">{beat.title}</span>
          <span className="step-preview">{beat.subtitle}</span>
        </span>
        {isPlayingHere ? <span className="step-tag">Checking now</span> : null}
        {isChecked ? <span className="step-tag step-tag-ok">Matched</span> : null}
        {isMismatch ? <span className="step-tag step-tag-warn">Changed here</span> : null}
        <span className="step-chevron" aria-hidden>
          {expanded ? "▾" : "▸"}
        </span>
      </button>
      {expanded ? (
        <div className="step-row-body">
          {isMismatch && diff ? (
            <div className="beat-diff">
              <p className="beat-diff-lead">Saved recording vs this replay:</p>
              <div className="compare compare-compact">
                <div>
                  <h4 className="compare-label">Saved</h4>
                  <pre className="compare-body">{diff.expected_preview}</pre>
                </div>
                <div>
                  <h4 className="compare-label">This replay</h4>
                  <pre className="compare-body">{diff.observed_preview}</pre>
                </div>
              </div>
            </div>
          ) : null}
          {beat.events.map((event) => (
            <details key={event.seq} className="step-raw">
              <summary>
                Technical · {event.type} (seq {event.seq})
              </summary>
              <div className="step-raw-blocks">
                <pre>{JSON.stringify(event.request, null, 2)}</pre>
                <pre>{JSON.stringify(event.response ?? event.error, null, 2)}</pre>
              </div>
            </details>
          ))}
        </div>
      ) : null}
    </div>
  );
}
