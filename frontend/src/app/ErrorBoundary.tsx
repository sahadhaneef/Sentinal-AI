import { Component, type ReactNode } from 'react';
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main className="error-state" role="alert">
        <h1>The workspace could not be displayed</h1>
        <p>Reload to restore the interface. Demo decisions reset on a full reload.</p>
        <button className="button primary" onClick={() => window.location.reload()}>
          Reload workspace
        </button>
      </main>
    ) : (
      this.props.children
    );
  }
}
