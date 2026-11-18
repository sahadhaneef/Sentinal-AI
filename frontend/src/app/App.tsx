import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { lazy } from 'react';
import { PublicShell } from '../layouts/PublicShell';
import { MotionConfig } from 'motion/react';
import { PreferencesProvider, usePreferences } from './preferences';
import { FeedbackProvider } from '../components/feedback';
import { AppShell } from '../layouts/AppShell';
import { queryPolicy } from '../hooks/queries';
import { Heading } from '../components/ui';
const DashboardPage = lazy(() =>
  import('../pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
);
const ApplicationsPage = lazy(() =>
  import('../pages/ApplicationsPage').then((m) => ({ default: m.ApplicationsPage })),
);
const ApplicationDetailPage = lazy(() =>
  import('../pages/ApplicationsPage').then((m) => ({ default: m.ApplicationDetailPage })),
);
const IncidentsPage = lazy(() =>
  import('../pages/IncidentsPage').then((m) => ({ default: m.IncidentsPage })),
);
const AgentsPage = lazy(() =>
  import('../pages/AgentsPage').then((m) => ({ default: m.AgentsPage })),
);
const AgentDetailPage = lazy(() =>
  import('../pages/AgentsPage').then((m) => ({ default: m.AgentDetailPage })),
);
const IncidentDetailPage = lazy(() =>
  import('../pages/IncidentDetailPage').then((m) => ({ default: m.IncidentDetailPage })),
);
const WorkflowQueuePage = lazy(() =>
  import('../pages/WorkflowQueuePage').then((m) => ({ default: m.WorkflowQueuePage })),
);
const SettingsPage = lazy(() =>
  import('../pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
);
const LandingPage = lazy(() =>
  import('../pages/LandingPage').then((m) => ({ default: m.LandingPage })),
);
const DemoPage = lazy(() => import('../pages/DemoPage').then((m) => ({ default: m.DemoPage })));
const OnboardingPage = lazy(() =>
  import('../pages/OnboardingPage').then((m) => ({ default: m.OnboardingPage })),
);
const DocumentationPage = lazy(() =>
  import('../pages/DocumentationPage').then((m) => ({ default: m.DocumentationPage })),
);
const client = new QueryClient({
  defaultOptions: { queries: { ...queryPolicy, staleTime: 1000 } },
});
function Content() {
  const { preferences } = usePreferences();
  return (
    <MotionConfig reducedMotion={preferences.motion === 'reduce' ? 'always' : 'user'}>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicShell />}>
            <Route index element={<LandingPage />} />
            <Route path="demo" element={<DemoPage />} />
            <Route path="onboarding" element={<OnboardingPage />} />
            <Route path="docs" element={<DocumentationPage />} />
          </Route>
          <Route element={<AppShell />}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="applications" element={<ApplicationsPage />} />
            <Route path="applications/:id" element={<ApplicationDetailPage />} />
            <Route path="incidents" element={<IncidentsPage />} />
            <Route path="agents" element={<AgentsPage />} />
            <Route path="agents/:type" element={<AgentDetailPage />} />
            <Route path="history" element={<IncidentsPage history />} />
            <Route path="incidents/:id" element={<IncidentDetailPage />} />
            <Route path="repair-testing" element={<WorkflowQueuePage />} />
            <Route path="approval-recovery" element={<WorkflowQueuePage approval />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route
              path="*"
              element={
                <>
                  <Heading
                    title="Page not found"
                    description="This page isn’t part of the workspace."
                  />
                  <a href="/dashboard">Return to Dashboard</a>
                </>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </MotionConfig>
  );
}
export function App() {
  return (
    <QueryClientProvider client={client}>
      <PreferencesProvider>
        <FeedbackProvider>
          <Content />
        </FeedbackProvider>
      </PreferencesProvider>
    </QueryClientProvider>
  );
}
