import { Link, Route, Routes, useLocation } from "react-router-dom";
import { brand } from "./copy";
import RunDetailPage from "./RunDetailPage";
import RunsPage from "./RunsPage";

export default function App() {
  const { pathname } = useLocation();
  const isHome = pathname === "/";

  return (
    <div className="layout">
      <header className="site-header">
        <Link to="/" className="site-brand">
          <span className="site-title">{brand.name}</span>
          {isHome ? <p className="site-tagline">{brand.tagline}</p> : null}
        </Link>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<RunsPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
