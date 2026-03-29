import { Navigate, Route, Routes } from 'react-router-dom'
import { LandingPage } from '@/pages/LandingPage'
import { AppDashboard } from '@/AppDashboard'
import { LoginPage } from '@/pages/LoginPage'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { RoleRoute } from '@/components/RoleRoute'
import { AdminDashboard } from '@/pages/AdminDashboard'
import { useAuth } from '@/contexts/AuthContext'

function LoginRoute() {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return null
  if (isAuthenticated) {
    return <Navigate to="/app" replace />
  }
  return <LoginPage />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginRoute />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/app" element={<AppDashboard />} />
        <Route path="/dashboard" element={<Navigate to="/app" replace />} />
        <Route element={<RoleRoute allowedRoles={['admin']} />}>
          <Route path="/admin-site" element={<AdminDashboard />} />
          <Route path="/admin" element={<Navigate to="/admin-site" replace />} />
          <Route path="/admin/analytics" element={<Navigate to="/admin-site" replace />} />
          <Route path="/admin/controls" element={<Navigate to="/admin-site" replace />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
