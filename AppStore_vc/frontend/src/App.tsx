import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Dashboard } from "./pages/Dashboard";
import { Analyze } from "./pages/Analyze";
import { Import } from "./pages/Import";
import { RunList } from "./pages/RunList";
import { RunDetail } from "./pages/RunDetail";
import { Traceability } from "./pages/Traceability";

export default function App() {
  return (
    <Router>
      <ErrorBoundary>
        <Sidebar />
        <main className="lg:ml-64">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/import" element={<Import />} />
            <Route path="/runs" element={<RunList />} />
            <Route path="/runs/:id" element={<RunDetail />} />
            <Route path="/traceability" element={<Traceability />} />
          </Routes>
        </main>
      </ErrorBoundary>
    </Router>
  );
}
