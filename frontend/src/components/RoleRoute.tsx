import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

type RoleRouteProps = {
  allowedRoles: Array<'admin' | 'researcher' | 'viewer'>
}

export function RoleRoute({ allowedRoles }: RoleRouteProps) {
  const { user, loading } = useAuth()
  const location = useLocation()
  const normalizedRole = (user?.role ?? '').toLowerCase() as 'admin' | 'researcher' | 'viewer' | ''

  if (loading) {
    return null
  }

  if (!normalizedRole || !allowedRoles.includes(normalizedRole)) {
    return <Navigate to="/app" replace state={{ from: location }} />
  }

  return <Outlet />
}
