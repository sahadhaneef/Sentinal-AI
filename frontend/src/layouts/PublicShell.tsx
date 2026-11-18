import { Link, Outlet, useLocation } from 'react-router-dom';
import { ArrowUpRight, ShieldCheck, Moon, Sun } from 'lucide-react';
import { Suspense } from 'react';
import { usePreferences } from '../app/preferences';
import { QuickActions } from '../components/QuickActions';
export function PublicShell() {
  const { preferences, setPreference } = usePreferences();
  const location = useLocation();
  return (
    <div className="public-site">
      <a className="skip-link" href="#public-main">
        Skip to content
      </a>
      <header className="public-nav">
        <Link className="brand" to="/">
          <span className="brand-mark">
            <ShieldCheck size={25} />
          </span>
          <span>
            SENTINEL <b>AI</b>
            <small>CLARITY BEFORE CHANGE</small>
          </span>
        </Link>
        <nav aria-label="Product navigation">
          {[
            ['#how-it-works', 'How it works'],
            ['#team', 'The agents'],
            ['#faq', 'FAQ'],
          ].map(([hash, label]) => (
            <Link key={hash} to={`/${hash}`}
              aria-current={location.pathname === '/' && location.hash === hash ? 'location' : undefined}>
              {label}
            </Link>
          ))}
        </nav>
        <div className="public-nav-actions">
          <button
            className="icon-button"
            aria-label="Toggle theme"
            onClick={() => setPreference('theme', preferences.theme === 'dark' ? 'light' : 'dark')}
          >
            {preferences.theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <Link className="button nav-workspace" to="/dashboard">
            Workspace <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </header>
      <main id="public-main" className="public-main" tabIndex={-1}>
        <Suspense
          fallback={
            <p role="status" className="route-loading">
              Loading experience…
            </p>
          }
        >
          <Outlet />
        </Suspense>
      </main>
      <footer className="public-footer">
        <Link to="/" className="text-link">
          <ShieldCheck size={18} /> SENTINEL AI
        </Link>
        <p>A local prototype. Thoughtful assistance. Human decisions.</p>
        <Link to="/docs">Documentation</Link>
        <Link to="/dashboard">Open workspace</Link>
      </footer>
      <QuickActions
        onHelp={() => {
          window.location.href = '/#faq';
        }}
        publicHelp
      />
    </div>
  );
}
