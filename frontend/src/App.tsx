import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { ToastProvider } from './components/ui'
import { AppShell } from './components/AppShell'
import Dashboard from './pages/Dashboard'
import Disputes from './pages/Disputes'
import DisputeDetail from './pages/DisputeDetail'
import Investigations from './pages/Investigations'
import EvidencePage from './pages/EvidencePage'
import Analytics from './pages/Analytics'
import Policies from './pages/Policies'
import Settings from './pages/Settings'

function NotFound() {
  return (
    <AppShell title="Page not found" subtitle="That view does not exist in this workspace.">
      <p className="text-sm text-ink-2">
        Return to the{' '}
        <Link to="/" className="text-accent underline-offset-4 hover:underline">
          dashboard
        </Link>
        .
      </p>
    </AppShell>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/disputes" element={<Disputes />} />
          <Route path="/disputes/:id" element={<DisputeDetail />} />
          <Route path="/investigations" element={<Investigations />} />
          <Route path="/evidence" element={<EvidencePage />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
