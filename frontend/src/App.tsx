import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Applications from './pages/Applications'
import Scans from './pages/Scans'
import ScanDetail from './pages/ScanDetail'
import Schedules from './pages/Schedules'
import Reports from './pages/Reports'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  // TODO: Restore auth check for production
  // const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isAuthenticated = true // Demo mode - bypass auth

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="applications" element={<Applications />} />
        <Route path="scans" element={<Scans />} />
        <Route path="scans/:scanId" element={<ScanDetail />} />
        <Route path="schedules" element={<Schedules />} />
        <Route path="reports" element={<Reports />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
