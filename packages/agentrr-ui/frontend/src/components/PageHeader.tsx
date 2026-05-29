import type { ReactNode } from "react";
import Tooltip from "./Tooltip";

type Props = {
  title: string;
  subtitle?: string;
  helpTip?: string;
  children?: ReactNode;
};

export default function PageHeader({ title, subtitle, helpTip, children }: Props) {
  return (
    <header className="page-header">
      <div>
        <h1 className="page-header-title">
          {title}
          {helpTip ? (
            <Tooltip label="About" tip={helpTip}>
              <button type="button" className="help-icon" aria-label="About this page">
                ?
              </button>
            </Tooltip>
          ) : null}
        </h1>
        {subtitle ? <p className="page-header-sub">{subtitle}</p> : null}
      </div>
      {children ? <div className="page-header-actions">{children}</div> : null}
    </header>
  );
}
