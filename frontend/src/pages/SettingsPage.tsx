import { useState } from 'react';
import { Monitor, RotateCcw, Settings2, ShieldCheck } from 'lucide-react';
import { isDemo } from '../api/client';
import { usePreferences } from '../app/preferences';
import { useBackendSettings, useResetDemo } from '../hooks/queries';
import { Busy, Dialog, Heading, Panel, QueryState } from '../components/ui';
import { useNotify } from '../components/feedback';
export function SettingsPage() {
  const { preferences, setPreference } = usePreferences(),
    [reset, setReset] = useState(false),
    mutation = useResetDemo(),
    notify = useNotify(),
    settings = useBackendSettings();
  return (
    <>
      <Heading
        title="Settings"
        description="Make the workspace feel right for you. Interface preferences stay in this browser."
      />
      <div className="settings-grid">
        <Panel title="Workspace preferences" action={<Monitor size={20} />}>
          <div className="setting-row">
            <div>
              <h3>Appearance</h3>
              <p>Choose a light, dark, or system theme.</p>
            </div>
            <select
              aria-label="Theme"
              value={preferences.theme}
              onChange={(e) => setPreference('theme', e.target.value)}
            >
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>
          <div className="setting-row">
            <div>
              <h3>Motion</h3>
              <p>Follow your device or reduce animation.</p>
            </div>
            <select
              aria-label="Motion preference"
              value={preferences.motion}
              onChange={(e) => setPreference('motion', e.target.value)}
            >
              <option value="system">Follow device</option>
              <option value="reduce">Reduced motion</option>
            </select>
          </div>
          <div className="setting-row">
            <div>
              <h3>Refresh interval</h3>
              <p>Active incident polling pauses in hidden tabs.</p>
            </div>
            <select
              aria-label="Polling interval"
              value={preferences.polling}
              onChange={(e) => {
                setPreference('polling', e.target.value);
                notify('Refresh preference updated.');
              }}
            >
              <option value="3000">3 seconds</option>
              <option value="4000">4 seconds</option>
              <option value="5000">5 seconds</option>
            </select>
          </div>
        </Panel>
        <Panel title="Data & safety" action={<ShieldCheck size={20} />}>
          <div className="setting-row">
            <div>
              <h3>{isDemo ? 'Demo mode — simulated data' : 'API mode'}</h3>
              <p>
                {isDemo
                  ? 'A local developer demonstration identity. No real authentication, code execution or repository changes.'
                  : 'Read-only database API. Workflow controls and browser authentication are deferred. No automatic fallback to demo data.'}
              </p>
            </div>
          </div>
          <p className="notice">
            Human approval is tied to the exact candidate, hash and base revision. Application
            requires a separate action.
          </p>
          <button
            className="button"
            disabled={!isDemo || mutation.isPending}
            onClick={() => setReset(true)}
          >
            <RotateCcw size={16} /> Reset demo data
          </button>
          <p className="muted-caption spaced">
            {isDemo ? 'RESTORES ALL SEEDED SCENARIOS' : 'RESET IS AVAILABLE IN DEMO MODE ONLY'}
          </p>
        </Panel>
        <Panel title="Backend-owned preferences" action={<Settings2 size={20} />}>
          <p>
            Read-only in this interface. These safe values come from the same typed contract in both
            data modes.
          </p>
          <QueryState query={settings}>
            <dl className="key-values">
              <div>
                <dt>Monitoring interval</dt>
                <dd>{settings.data?.data.monitoring_interval_seconds} seconds</dd>
              </div>
              <div>
                <dt>Candidate revision limit</dt>
                <dd>{settings.data?.data.max_candidate_revisions}</dd>
              </div>
            </dl>
          </QueryState>
          <p className="notice">
            Provider credentials and server workspace paths are never stored in frontend settings.
          </p>
        </Panel>
      </div>
      <Dialog open={reset} title="Reset the simulated workspace?" onClose={() => setReset(false)}>
        <p>
          This discards demo decisions, monitoring changes and simulated outcomes, and restores the
          original demo incidents. Your interface preferences remain saved.
        </p>
        <div className="dialog-actions">
          <button className="button" onClick={() => setReset(false)}>
            Cancel
          </button>
          <button
            className="button primary"
            disabled={mutation.isPending}
            onClick={() =>
              mutation.mutate(undefined, {
                onSuccess: () => {
                  setReset(false);
                  notify('Demo data reset. All scenarios are ready.');
                },
                onError: (e) => notify(e.message),
              })
            }
          >
            {mutation.isPending ? <Busy /> : 'Confirm reset'}
          </button>
        </div>
      </Dialog>
    </>
  );
}
