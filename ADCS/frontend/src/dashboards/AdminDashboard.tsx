import { useEffect, useState } from 'react'
import api from '@/services/api'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'
import LecturerManagementPanel from '@/components/LecturerManagementPanel'
import ComplianceAnalysisPanel from '@/components/ComplianceAnalysisPanel'
import AccountRequestsPanel from '@/components/AccountRequestsPanel'
import { Link } from 'react-router-dom'

export default function AdminDashboard() {
  const [profile, setProfile] = useState<any>(null)
  const [summary, setSummary] = useState<any>(null)
  const [users, setUsers] = useState<any[]>([])
  const [audit, setAudit] = useState<any[]>([])
  const [ann, setAnn] = useState({ title: '', body: '', audience: 'all' })
  const [notice, setNotice] = useState('')

  useEffect(() => {
    (async () => {
      try { const p = await api.get('/profile/me'); setProfile(p.data) } catch {}
      try { const s = await api.get('/reports/institution-summary'); setSummary(s.data) } catch {}
      try { const u = await api.get('/users'); setUsers(Array.isArray(u.data)?u.data:[]) } catch {}
      try { const a = await api.get('/admin/audit-logs'); setAudit(Array.isArray(a.data)?a.data:[]) } catch {}
    })()
  }, [])

  const postAnnouncement = async () => {
    if (!ann.title.trim() || !ann.body.trim()) return
    try { await api.post('/announcements', ann); setAnn({ title: '', body: '', audience: 'all' }); setNotice('Announcement published and notifications sent.'); setTimeout(()=>setNotice(''),4000) } catch {}
  }

  const toggleUser = async (id: number, active: boolean) => {
    try { await api.patch(`/users/${id}`, { is_active: !active }); setUsers(us => us.map(u => u.id===id?{...u,is_active:!active}:u)) } catch {}
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-navy-900 dark:text-white">University Administrator Dashboard</h1>
        <Link to="/dashboard/settings" className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Settings & Institution Profile</Link>
      </div>
      {profile && <div className="rounded-xl border bg-white p-4 text-sm shadow-sm dark:bg-slate-900 dark:border-slate-700"><b>{profile.full_name}</b> · {profile.institution?.name || 'Institution'} · <span className="capitalize">{(profile.roles||[]).join(', ')}</span></div>}
      {summary && (
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-4">
          {Object.entries(summary).map(([k, v]) => (
            <div key={k} className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
              <p className="text-gray-500 text-sm">{k.replace(/_/g, ' ')}</p>
              <p className="text-3xl font-bold">{String(v)}</p>
            </div>
          ))}
        </div>
      )}
      <ComplianceAnalysisPanel />

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl bg-white p-4 shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Student & staff user management (institution-scoped)</h2>
          <div className="max-h-80 overflow-auto text-sm">
            {users.length===0 ? <p className="text-slate-500">No users found.</p> : users.map(u => (
              <div key={u.id} className="flex items-center justify-between border-b py-2 dark:border-slate-700">
                <div><div className="font-medium">{u.full_name || u.email}</div><div className="text-slate-500">{u.email} · {(u.roles||[]).join(', ')} · {u.is_active?'Active':'Inactive'}</div></div>
                <button onClick={()=>toggleUser(u.id, u.is_active)} className="rounded border px-2 py-1 text-xs hover:bg-slate-50 dark:border-slate-600">{u.is_active?'Deactivate':'Activate'}</button>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">Activation/deactivation and role-aware access are enforced server-side. Administrators can only manage their own institution.</p>
        </div>
        <div className="rounded-xl bg-white p-4 shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Institution announcements & notifications</h2>
          {notice && <div className="mb-2 rounded bg-emerald-50 p-2 text-sm text-emerald-700">{notice}</div>}
          <input className="mb-2 w-full rounded border px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600" placeholder="Title" value={ann.title} onChange={e=>setAnn({...ann,title:e.target.value})} />
          <textarea className="mb-2 w-full rounded border px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600" rows={3} placeholder="Message" value={ann.body} onChange={e=>setAnn({...ann,body:e.target.value})} />
          <div className="flex gap-2">
            <select className="rounded border px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600" value={ann.audience} onChange={e=>setAnn({...ann,audience:e.target.value})}>
              <option value="all">All users</option><option value="student">Students</option><option value="lecturer">Lecturers</option><option value="registrar">Registrars</option><option value="compliance_officer">Compliance officers</option>
            </select>
            <button onClick={postAnnouncement} className="rounded bg-primary-600 px-4 py-2 text-sm font-medium text-white">Publish (sends notifications)</button>
          </div>
        </div>
      </div>

      <div className="rounded-xl bg-white p-4 shadow dark:bg-slate-900 dark:border dark:border-slate-700">
        <h2 className="font-semibold mb-2">Audit logs & security (recent)</h2>
        <div className="max-h-72 overflow-auto text-sm">
          {audit.length===0 ? <p className="text-slate-500">No audit logs visible.</p> : audit.slice(0,50).map((l:any)=>(<div key={l.id} className="border-b py-1 dark:border-slate-700"><b>{l.action}</b> · {l.resource_type || ''} {l.resource_id||''} · user {l.user_id||'—'} · {l.created_at?new Date(l.created_at).toLocaleString():''} {l.success===false?'(failed)':''}</div>))}
        </div>
      </div>

      <AcademicDocumentsPanel mode="reviewer" />
      <AccountRequestsPanel />
      <LecturerManagementPanel />
    </div>
  )
}
