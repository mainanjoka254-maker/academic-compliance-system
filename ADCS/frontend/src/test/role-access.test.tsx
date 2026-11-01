import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'

const { auth } = vi.hoisted(() => ({
  auth: { user: null as { roles: string[]; full_name: string } | null, loading: false },
}))

vi.mock('@/contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => ({ ...auth, logout: vi.fn(), login: vi.fn() }),
}))

vi.mock('@/dashboards/StudentDashboard', () => ({ default: () => <div>Student dashboard fixture</div> }))
vi.mock('@/dashboards/AdminDashboard', () => ({ default: () => <div>Admin dashboard fixture</div> }))
vi.mock('@/dashboards/LecturerDashboard', () => ({ default: () => <div>Lecturer dashboard fixture</div> }))
vi.mock('@/dashboards/RegistrarDashboard', () => ({ default: () => <div>Registrar dashboard fixture</div> }))
vi.mock('@/dashboards/ComplianceDashboard', () => ({ default: () => <div>Compliance dashboard fixture</div> }))
vi.mock('@/dashboards/SuperAdminDashboard', () => ({ default: () => <div>Super admin dashboard fixture</div> }))

describe('role-based dashboard routes', () => {
  beforeEach(() => {
    auth.user = null
    auth.loading = false
  })

  it('redirects a student away from the university administrator dashboard', async () => {
    auth.user = { roles: ['student'], full_name: 'Student fixture' }
    render(<MemoryRouter initialEntries={['/dashboard/admin']}><App /></MemoryRouter>)

    expect(await screen.findByText('Student dashboard fixture')).toBeInTheDocument()
    expect(screen.queryByText('Admin dashboard fixture')).not.toBeInTheDocument()
  })

  it('allows the university administrator role into its dashboard', async () => {
    auth.user = { roles: ['university_admin'], full_name: 'Admin fixture' }
    render(<MemoryRouter initialEntries={['/dashboard/admin']}><App /></MemoryRouter>)

    expect(await screen.findByText('Admin dashboard fixture')).toBeInTheDocument()
  })
})
