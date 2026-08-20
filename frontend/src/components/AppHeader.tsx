import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

interface AppHeaderProps {
  backHref?: string;
  rightLabel?: string;
}

export function AppHeader({
  backHref,
  rightLabel = "YouTube · Shorts · Square",
}: AppHeaderProps) {
  return (
    <header className="topbar">
      <div className="header-left">
        {backHref ? (
          <Link className="back-link" to={backHref} aria-label="Back to new project">
            <ArrowLeft size={16} aria-hidden="true" />
          </Link>
        ) : null}
        <Link className="brand" to="/" aria-label="Framecraft home">
          <span className="brand-mark">F</span>
          <span>Framecraft</span>
        </Link>
      </div>
      <div className="topbar-meta">{rightLabel}</div>
    </header>
  );
}
