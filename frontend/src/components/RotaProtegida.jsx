import { Navigate, Outlet } from 'react-router-dom'
import { temCredencial } from '../api/client'

export default function RotaProtegida() {
  return temCredencial() ? <Outlet /> : <Navigate to="/login" replace />
}
