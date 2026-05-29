import type { ReactNode } from "react";

type Props = {
  label: string;
  children: ReactNode;
  /** Wider hint text shown on hover (defaults to label). */
  tip?: string;
};

/** Accessible control with a hover/focus tooltip. */
export default function Tooltip({ label, tip, children }: Props) {
  const text = tip ?? label;
  return (
    <span className="tooltip-wrap" data-tooltip={text}>
      {children}
      <span className="sr-only">{label}</span>
    </span>
  );
}

type LabelProps = {
  title: string;
  tip?: string;
};

/** Section label with an info (?) affordance. */
export function LabelWithTip({ title, tip }: LabelProps) {
  if (!tip) return <span className="section-label">{title}</span>;
  return (
    <Tooltip label={title} tip={tip}>
      <span className="section-label with-tip">
        {title}
        <span className="tip-icon" aria-hidden>
          ?
        </span>
      </span>
    </Tooltip>
  );
}
