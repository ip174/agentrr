import type { ReactNode } from "react";
import { run as runCopy } from "../copy";

type Props = {
  children: ReactNode;
};

export default function TechDetails({ children }: Props) {
  return (
    <details className="tech-details">
      <summary>{runCopy.forEngineers}</summary>
      <div className="tech-details-inner">{children}</div>
    </details>
  );
}
