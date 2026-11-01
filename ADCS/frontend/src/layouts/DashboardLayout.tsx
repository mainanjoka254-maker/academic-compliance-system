import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { LogOut } from 'lucide-react'

export default function DashboardLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const handleLogout = () => { logout(); navigate('/login') }

  const links = [
    { to: '/dashboard/student', label: 'Student', roles: ['student'] },
    { to: '/dashboard/lecturer', label: 'Lecturer', roles: ['lecturer'] },
    { to: '/dashboard/admin', label: 'Admin', roles: ['university_admin'] },
    { to: '/dashboard/registrar', label: 'Registrar', roles: ['registrar'] },
    { to: '/dashboard/compliance', label: 'Compliance', roles: ['compliance_officer'] },
    { to: '/dashboard/superadmin', label: 'Super Admin', roles: ['super_admin'] },
  ].filter((l) => l.roles.some((r) => user?.roles.includes(r)))

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-64 bg-navy-900 text-white flex flex-col">
        <div className="p-4 text-xl font-bold border-b border-navy-700">ADCS</div>
        <nav className="flex-1 p-2 space-y-1">
          {links.map((l) => (
            <Link key={l.to} to={l.to} className="block px-3 py-2 rounded hover:bg-navy-700">{l.label} Dashboard</Link>
          ))}
        </nav>
        <div className="p-4 border-t border-navy-700">
          <div className="text-sm mb-2">{user?.full_name}</div>
          <button onClick={handleLogout} className="flex items-center gap-2 text-sm text-red-300 hover:text-red-200">
            <LogOut size={16} /> Logout
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
