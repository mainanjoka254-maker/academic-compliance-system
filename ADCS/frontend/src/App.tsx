import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'

import Landing from '@/pages/Landing'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import AccountStatus from '@/pages/AccountStatus'
import VerifyOTP from '@/pages/VerifyOTP'
import ForgotPassword from '@/pages/ForgotPassword'
import ResetPassword from '@/pages/ResetPassword'
import GoogleCallback from '@/pages/GoogleCallback'
import About from '@/pages/About'
import Features from '@/pages/Features'
import InstitutionsPage from '@/pages/Institutions'
import Settings from '@/pages/Settings'

import DashboardLayout from '@/layouts/DashboardLayout'
import StudentDashboard from '@/dashboards/StudentDashboard'
import LecturerDashboard from '@/dashboards/LecturerDashboard'
import AdminDashboard from '@/dashboards/AdminDashboard'
import RegistrarDashboard from '@/dashboards/RegistrarDashboard'
import ComplianceDashboard from '@/dashboards/ComplianceDashboard'
import SuperAdminDashboard from '@/dashboards/SuperAdminDashboard'

const Protected: React.FC<{ children: React.ReactNode; roles?: string[] }> = ({ children, roles }) => {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-8">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.some((r) => user.roles.includes(r))) return <Navigate to="/" replace />
  return <>{children}</>
}

const HomeRedirect: React.FC = () => {
  const { user } = useAuth()
  if (!user) return <Landing />
  const r = user.roles[0]
  if (r === 'super_admin') return <Navigate to="/dashboard/superadmin" />
  if (r === 'university_admin') return <Navigate to="/dashboard/admin" />
  if (r === 'registrar') return <Navigate to="/dashboard/registrar" />
  if (r === 'lecturer') return <Navigate to="/dashboard/lecturer" />
  if (r === 'compliance_officer') return <Navigate to="/dashboard/compliance" />
  return <Navigate to="/dashboard/student" />
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/about" element={<About />} />
        <Route path="/features" element={<Features />} />
        <Route path="/institutions" element={<InstitutionsPage />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/account-status" element={<AccountStatus />} />
        <Route path="/verify-otp" element={<VerifyOTP />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/auth/callback" element={<GoogleCallback />} />

        <Route path="/dashboard" element={<Protected><DashboardLayout /></Protected>}>
          <Route path="student" element={<Protected roles={['student']}><StudentDashboard /></Protected>} />
          <Route path="lecturer" element={<Protected roles={['lecturer']}><LecturerDashboard /></Protected>} />
          <Route path="admin" element={<Protected roles={['university_admin']}><AdminDashboard /></Protected>} />
          <Route path="registrar" element={<Protected roles={['registrar']}><RegistrarDashboard /></Protected>} />
          <Route path="compliance" element={<Protected roles={['compliance_officer']}><ComplianceDashboard /></Protected>} />
          <Route path="superadmin" element={<Protected roles={['super_admin']}><SuperAdminDashboard /></Protected>} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
