import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { AssetDetailPage } from "./pages/AssetDetailPage";
import { AssetsPage } from "./pages/AssetsPage";
import { DetectionDetailPage } from "./pages/DetectionDetailPage";
import { DetectionsPage } from "./pages/DetectionsPage";
import { IncidentDetailPage } from "./pages/IncidentDetailPage";
import { IncidentsPage } from "./pages/IncidentsPage";
import { AgentAuditPage } from "./pages/AgentAuditPage";
import { AgentAuditRunPage } from "./pages/AgentAuditRunPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { NetworkHealthPage } from "./pages/NetworkHealthPage";
import { PipelineLabPage } from "./pages/PipelineLabPage";
import {
  IntegrationFindingPage,
  IntegrationRecommendationPage,
  IntegrationRunPage,
} from "./pages/IntegrationDetailPages";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { MaintenancePage } from "./pages/MaintenancePage";
import { OperationsPage } from "./pages/OperationsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { WorkOrderDetailPage } from "./pages/WorkOrderDetailPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { Skeleton } from "./components/ui/Skeleton";

const LiveMapPage = lazy(() => import("./pages/LiveMapPage"));

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<OverviewPage />} />
        <Route
          path="/map"
          element={
            <Suspense fallback={<Skeleton className="h-full min-h-[24rem] w-full rounded-none" />}>
              <LiveMapPage />
            </Suspense>
          }
        />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
        <Route path="/operations" element={<OperationsPage />} />
        <Route path="/detections" element={<DetectionsPage />} />
        <Route path="/detections/findings/:findingId" element={<IntegrationFindingPage />} />
        <Route path="/detections/:detectionId" element={<DetectionDetailPage />} />
        <Route path="/assets" element={<AssetsPage />} />
        <Route path="/assets/:assetId" element={<AssetDetailPage />} />
        <Route path="/maintenance" element={<MaintenancePage />} />
        <Route path="/maintenance/work-orders/:workOrderId" element={<WorkOrderDetailPage />} />
        <Route
          path="/agents"
          element={
            <PlaceholderPage
              title="AI Agents"
              description="Detection, investigation, and briefing agents are not wired yet."
            />
          }
        />
        <Route path="/integrations" element={<IntegrationsPage />} />
        <Route path="/integrations/runs/:runId" element={<IntegrationRunPage />} />
        <Route path="/integrations/findings/:findingId" element={<IntegrationFindingPage />} />
        <Route
          path="/integrations/recommendations/:recommendationId"
          element={<IntegrationRecommendationPage />}
        />
        <Route path="/network" element={<NetworkHealthPage />} />
        <Route path="/network-health" element={<NetworkHealthPage />} />
        <Route path="/pipeline-lab" element={<PipelineLabPage />} />
        <Route path="/testbed" element={<PipelineLabPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/agent-audit" element={<AgentAuditPage />} />
        <Route path="/agent-audit/runs/:runId" element={<AgentAuditRunPage />} />
        <Route
          path="/audit"
          element={
            <PlaceholderPage
              title="Operator Audit Trail"
              description="Operator workflow history is separate from the Agent Audit Trail and is not implemented in this step."
            />
          }
        />
        <Route
          path="/settings"
          element={
            <PlaceholderPage
              title="Settings"
              description="Workspace preferences and operator configuration are not in this step."
            />
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
