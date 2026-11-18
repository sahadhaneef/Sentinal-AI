import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './app/App';
import { ErrorBoundary } from './app/ErrorBoundary';
import './styles/globals.css';
import './styles/polish.css';
import './styles/product.css';
import './styles/landing-premium.css';
import './styles/agent-team.css';
import './styles/product-tour-video.css';
import './styles/workspace-explorer.css';
import './styles/landing-atmosphere.css';
import './styles/workflow-handoff.css';
import './styles/benefit-signals.css';
import './styles/public-header.css';
import './styles/hero-scene.css';
import './styles/cinematic-field.css';
import './styles/scroll-story.css';
import './styles/planet-backdrop.css';
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
