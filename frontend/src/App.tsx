import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { DashboardPage } from "./pages/Dashboard";
import { LegacyScanPage } from "./pages/LegacyScan";
import { CaseDetailPage } from "./pages/cases/CaseDetail";
import { CaseEvidencePage } from "./pages/cases/CaseEvidence";
import { CaseGraphPage } from "./pages/cases/CaseGraph";
import { CaseInventoryPage } from "./pages/cases/CaseInventory";
import { CaseReportsPage } from "./pages/cases/CaseReports";
import { CaseSourcesPage } from "./pages/cases/CaseSources";
import { CaseListPage } from "./pages/cases/CaseList";
import { CaseNewPage } from "./pages/cases/CaseNew";
import { CaseDataPage } from "./pages/cases/CaseData";
import { CaseSearchPage } from "./pages/cases/CaseSearch";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="cases" element={<CaseListPage />} />
        <Route path="cases/new" element={<CaseNewPage />} />
        <Route path="cases/:caseId" element={<CaseDetailPage />}>
          <Route index element={<Navigate to="search" replace />} />
          <Route path="search" element={<CaseSearchPage />} />
          <Route path="data" element={<CaseDataPage />} />
          <Route path="inventory" element={<CaseInventoryPage />} />
          <Route path="sources" element={<CaseSourcesPage />} />
          <Route path="graph" element={<CaseGraphPage />} />
          <Route path="reports" element={<CaseReportsPage />} />
          <Route path="overview" element={<Navigate to="data" replace />} />
          <Route path="entities" element={<Navigate to="data" replace />} />
          <Route path="evidence" element={<CaseEvidencePage />} />
          <Route path="url-review" element={<Navigate to="data" replace />} />
        </Route>
        <Route path="scan" element={<LegacyScanPage />} />
      </Route>
    </Routes>
  );
}
