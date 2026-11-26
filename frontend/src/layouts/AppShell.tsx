import { Suspense, useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  Activity,
  ArrowUpRight,
  Bot,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  FileClock,
  LayoutDashboard,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  SquareStack,
  Wrench,
} from 'lucide-react';
import { isDemo } from '../api/client';
import { useHealth } from '../hooks/queries';
import { Dialog } from '../components/ui';
import { QuickActions } from '../components/QuickActions';

const navigation = [
  ['/dashboard', 'Dashboard', LayoutDashboard],
  ['/applications', 'Applications', SquareStack],
  ['/incidents', 'Incidents', Activity],
  ['/agents', 'AI Agents', Bot],
  ['/repair-testing', 'Repair & Testing', Wrench],
  ['/approval-recovery', 'Approval & Recovery', ClipboardCheck],
  ['/history', 'Incident History', FileClock],
  ['/settings', 'Settings', Settings],
] as const;
export function AppShell() {
  const location = useLocation(),
    [drawer, setDrawer] = useState(false),
    [help, setHelp] = useState(false);
  const menu = useRef<HTMLButtonElement>(null);
  const health = useHealth();
  const name = navigation.find(([path]) => location.pathname.startsWith(path))?.[1] || 'Workspace';
  useEffect(() => {
    document.getElementById('main')?.focus();
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [location.pathname]);
  const sidebar = (
    <>
      <Link className="brand" to="/dashboard" onClick={() => setDrawer(false)}>
        <span className="brand-mark">
          <ShieldCheck size={25} />
        </span>
        <span>
          SENTINEL <b>AI</b>
          <small>INTELLIGENT RESILIENCE</small>
        </span>
      </Link>
      <div className="nav-caption">WORKSPACE</div>
      <nav aria-label="Main navigation">
        {navigation.map(([path, title, Icon]) => (
          <NavLink
            key={path}
            to={path}
            onClick={() => setDrawer(false)}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <Icon size={19} aria-hidden />
            {title}
            {path === '/agents' && (
              <span className="nav-count" aria-hidden="true">
                6
              </span>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="safety-card">
          <ShieldCheck size={22} />
          <strong>Human-led. AI-assisted.</strong>
          <p>You stay in control of every change.</p>
          <button
            onClick={() => {
              setHelp(true);
              setDrawer(false);
            }}
          >
            How it works <ArrowUpRight size={14} />
          </button>
        </div>
        <div className="profile">
          <div className="avatar">{isDemo ? 'DR' : 'U'}</div>
          <div>
            <strong>{isDemo ? 'Demo reviewer' : 'Read-only workspace'}</strong>
            <small>{isDemo ? 'Local demonstration identity' : 'Local prototype access'}</small>
          </div>
        </div>
      </div>
    </>
  );
  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">{sidebar}</aside>
      <Dialog
        open={drawer}
        title="Workspace navigation"
        onClose={() => {
          setDrawer(false);
          menu.current?.focus();
        }}
      >
        <div className="drawer-nav">{sidebar}</div>
      </Dialog>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              ref={menu}
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setDrawer(true)}
            >
              <Menu />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{name}</strong>
          </div>
          <div className="topbar-right">
            <Link className="top-search" to="/incidents">
              <Search size={16} /> Find an incident
            </Link>
            <span className="environment">
              <span /> {isDemo ? 'Demo workspace' : 'API workspace'}
            </span>
            <button className="icon-button" aria-label="Open help" onClick={() => setHelp(true)}>
              <CircleHelp size={19} />
            </button>
          </div>
        </header>
        <div
          className={`mode-banner ${!isDemo && health.isError ? 'backend-error' : ''}`}
          role="status"
        >
          <span>
            <Sparkles size={14} aria-hidden />
            {isDemo ? 'Demo mode — simulated data' : 'API mode — backend session required'}
          </span>
          <span>
            {isDemo
              ? 'Explore safely. No code is executed.'
              : health.isError
                ? 'Backend unavailable'
                : health.isPending
                  ? 'Checking backend…'
                  : health.data?.data.status === 'ok'
                    ? 'Backend available'
                    : 'Backend degraded'}
          </span>
        </div>
        <main id="main" tabIndex={-1}>
          <Suspense
            fallback={
              <div className="route-loading" role="status">
                Loading page…
              </div>
            }
          >
            <div className="page-content" key={location.pathname}>
              <Outlet />
            </div>
          </Suspense>
        </main>
        <footer className="footer">
          <span>
            SENTINEL AI <span className="footer-dot">•</span> Built for clarity. Guided by you.
          </span>
          <span>
            Local prototype <ShieldCheck size={13} />
          </span>
        </footer>
      </div>
      <QuickActions onHelp={() => setHelp(true)} />
      <Dialog
        open={help}
        title="A clear path from error to evidence"
        onClose={() => setHelp(false)}
      >
        <p>
          Six logical agents help you detect, diagnose, propose, test and document a supported
          failure in one local sample application.
        </p>
        <ol className="help-steps">
          <li>Open an incident and inspect its diagnosis and source evidence.</li>
          <li>Review the exact candidate diff and passing validation checks.</li>
          <li>Choose to approve or reject. Approval does not apply a patch.</li>
          <li>
            Separately apply the approved patch and inspect simulated verification and its report.
          </li>
        </ol>
        <p className="notice">
          Demo mode never runs code, changes a repository or calls an LLM. The demo reviewer is a
          sample identity.
        </p>
        <Link className="button primary" to="/incidents/inc_001" onClick={() => setHelp(false)}>
          Explore the sample incident <ArrowUpRight size={16} />
        </Link>
      </Dialog>
    </div>
  );
}
