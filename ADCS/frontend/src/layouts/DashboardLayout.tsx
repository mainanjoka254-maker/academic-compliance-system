import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { LogOut, GraduationCap, Menu, X, LayoutDashboard, Settings, UserCircle2, Bell } from 'lucide-react'
import { useEffect, useState } from 'react'
import api from '@/services/api'

export default function DashboardLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [unread, setUnread] = useState(0)
  const [notifOpen, setNotifOpen] = useState(false)
  const [notifs, setNotifs] = useState<any[]>([])
  const handleLogout = () => { logout(); navigate('/login') }

  const links = [
    { to: '/dashboard/student', label: 'Student', roles: ['student'] },
    { to: '/dashboard/lecturer', label: 'Lecturer', roles: ['lecturer'] },
    { to: '/dashboard/admin', label: 'Admin', roles: ['university_admin'] },
    { to: '/dashboard/registrar', label: 'Registrar', roles: ['registrar'] },
    { to: '/dashboard/compliance', label: 'Compliance', roles: ['compliance_officer'] },
    { to: '/dashboard/superadmin', label: 'Super Admin', roles: ['super_admin'] },
  ].filter((l) => l.roles.some((r) => user?.roles.includes(r)))

  const roleLabel = (user?.roles?.[0] || 'user').replace(/_/g, ' ')

  const loadNotifs = async () => {
    try {
      const r = await api.get('/notifications', { params: { format: 'center', limit: 8 } })
      const data = r.data
      if (Array.isArray(data)) { setNotifs(data); setUnread(data.filter((n: any) => !n.is_read).length) }
      else { setNotifs(data.items || []); setUnread(data.unread_count || 0) }
    } catch { /* ignore */ }
  }

  useEffect(() => { loadNotifs(); const t = setInterval(loadNotifs, 30000); return () => clearInterval(t) }, [])

  const markRead = async (id: number) => {
    try { await api.patch(`/notifications/${id}/read`); setNotifs((ns) => ns.map((n) => n.id === id ? { ...n, is_read: true } : n)); setUnread((u) => Math.max(0, u - 1)) } catch {}
  }
  const markAll = async () => { try { await api.post('/notifications/read-all'); setNotifs((ns) => ns.map((n) => ({ ...n, is_read: true }))); setUnread(0) } catch {} }

  const Sidebar = ({ mobile }: { mobile?: boolean }) => (
    <div className="flex h-full flex-col bg-navy-950 text-slate-100">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-4">
        <Link to="/" className="flex items-center gap-2 font-extrabold tracking-tight text-white">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-primary-600"><GraduationCap size={18} /></span>
          <span>ADCS</span>
        </Link>
        {mobile && <button className="rounded-lg p-2 text-slate-300 hover:bg-white/10" aria-label="Close menu" onClick={() => setOpen(false)}><X size={18} /></button>}
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {links.map((l) => {
          const active = location.pathname.startsWith(l.to)
          return (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)}
              className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium transition ${active ? 'bg-primary-600 text-white shadow-glow' : 'text-slate-200 hover:bg-white/10'}`}>
              <LayoutDashboard size={16} /> {l.label} Dashboard
            </Link>
          )
        })}
        <Link to="/dashboard/settings" onClick={() => setOpen(false)}
          className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium transition ${location.pathname.includes('/settings') ? 'bg-primary-600 text-white shadow-glow' : 'text-slate-200 hover:bg-white/10'}`}>
          <Settings size={16} /> Settings
        </Link>
      </nav>
      <div className="border-t border-white/10 p-4">
        <div className="mb-3 flex items-center gap-3 rounded-xl bg-white/5 p-3">
          <UserCircle2 size={20} className="text-slate-300" />
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-white">{user?.full_name}</div>
            <div className="text-xs capitalize text-slate-400">{roleLabel}</div>
          </div>
        </div>
        <button onClick={handleLogout} className="inline-flex w-full items-center justify-center gap-1 rounded-xl border border-red-400/20 bg-red-500/10 px-2 py-2 text-xs text-red-200 hover:bg-red-500/20">
          <LogOut size={14} /> Logout
        </button>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen bg-slate-100">
      <aside className="hidden w-72 shrink-0 lg:block"><Sidebar /></aside>
      {open && <div className="fixed inset-0 z-50 lg:hidden">
        <div className="absolute inset-0 bg-slate-900/50" onClick={() => setOpen(false)} />
        <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] shadow-2xl"><Sidebar mobile /></div>
      </div>}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:px-6">
          <div className="flex items-center gap-3">
            <button className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" aria-label="Open menu" onClick={() => setOpen(true)}><Menu size={20} /></button>
            <div>
              <div className="text-sm font-semibold text-navy-900">ADCS Workspace</div>
              <div className="text-xs capitalize text-slate-500">{roleLabel} dashboard</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <button className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100" aria-label="Notifications" onClick={() => { setNotifOpen((v) => !v); if (!notifOpen) loadNotifs() }}>
                <Bell size={18} />
                {unread > 0 && <span className="absolute -right-0.5 -top-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">{unread > 99 ? '99+' : unread}</span>}
              </button>
              {notifOpen && (
                <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-slate-200 bg-white shadow-xl">
                  <div className="flex items-center justify-between border-b px-3 py-2">
                    <span className="text-sm font-semibold text-navy-900">Notifications</span>
                    <button onClick={markAll} className="text-xs text-primary-700 hover:underline">Mark all read</button>
                  </div>
                  <div className="max-h-80 overflow-auto">
                    {notifs.length === 0 ? <div className="p-4 text-sm text-slate-500">No notifications.</div> : notifs.map((n) => (
                      <button key={n.id} onClick={() => markRead(n.id)} className={`block w-full border-b px-3 py-2 text-left hover:bg-slate-50 ${n.is_read ? 'opacity-70' : 'bg-blue-50/40'}`}>
                        <div className="text-sm font-medium text-slate-800">{n.title}</div>
                        <div className="line-clamp-2 text-xs text-slate-600">{n.message}</div>
                      </button>
                    ))}
                  </div>
                  <div className="px-3 py-2 text-center"><Link to="/dashboard/settings" onClick={() => setNotifOpen(false)} className="text-xs font-medium text-primary-700 hover:underline">Open settings &amp; notification centre</Link></div>
                </div>
              )}
            </div>
            <Link to="/" className="text-xs font-medium text-primary-700 hover:text-primary-800">Home</Link>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
