import { useEffect, useState } from 'react'
import api from '@/services/api'
import InstitutionManagementPanel from '@/components/InstitutionManagementPanel'
import AccountRequestsPanel from '@/components/AccountRequestsPanel'
import { Link } from 'react-router-dom'

export default function SuperAdminDashboard() {
  const [profile, setProfile] = useState<any>(null)
  const [summary, setSummary] = useState<any>(null)
  const [instSummary, setInstSummary] = useState<any>(null)
  const [audit, setAudit] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [summaryError, setSummaryError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    (async () => {
      try { const p = await api.get('/profile/me'); setProfile(p.data) } catch {}
      try { const r = await api.get('/reports/platform-summary'); setSummary(r.data) } catch { setSummaryError('Platform summary could not be loaded.') }
      try { const r = await api.get('/reports/institution-summary'); setInstSummary(r.data) } catch {}
      try { const a = await api.get('/admin/audit-logs'); setAudit(Array.isArray(a.data)?a.data:[]) } catch {}
      try { const u = await api.get('/users'); setUsers(Array.isArray(u.data)?u.data:[]) } catch {}
    })()
  }, [])

  const toggleUser = async (id: number, active: boolean) => {
    try { await api.patch(`/users/${id}`, { is_active: !active }); setUsers(us=>us.map(u=>u.id===id?{...u,is_active:!active}:u)); setNotice('User status updated (audited).'); setTimeout(()=>setNotice(''),3000) } catch {}
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-navy-900 dark:text-white">Super Administrator Dashboard</h1>
        <Link to="/dashboard/settings" className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Platform Settings & Profile</Link>
      </div>
      {profile && <div className="rounded-xl border bg-white p-4 text-sm shadow-sm dark:bg-slate-900 dark:border-slate-700"><b>{profile.full_name}</b> · Platform Super Administrator · Global scope</div>}
      {summaryError && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{summaryError}</p>}
      {notice && <p className="rounded bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p>}

      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-4">
        {summary && Object.entries(summary).map(([k, v]) => (
          <div key={k} className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">{k.replace(/_/g, ' ')}</p><p className="text-3xl font-bold">{String(v)}</p></div>
        ))}
        {instSummary && Object.entries(instSummary).slice(0,4).map(([k,v]) => (
          <div key={k} className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Global {k.replace(/_/g,' ')}</p><p className="text-2xl font-bold">{String(v)}</p></div>
        ))}
      </div>

      <InstitutionManagementPanel />

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl bg-white p-4 shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Global user management</h2>
          <div className="max-h-80 overflow-auto text-sm">
            {users.length===0 ? <p className="text-slate-500">No users.</p> : users.slice(0,50).map(u => (
              <div key={u.id} className="flex items-center justify-between border-b py-2 dark:border-slate-700">
                <div><div className="font-medium">{u.full_name || u.email}</div><div className="text-slate-500">{u.email} · inst {u.institution_id ?? '—'} · {(u.roles||[]).join(', ')}</div></div>
                <button onClick={()=>toggleUser(u.id, u.is_active)} className="rounded border px-2 py-1 text-xs dark:border-slate-600">{u.is_active?'Deactivate':'Activate'}</button>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">Role/permission and sensitive actions are enforced by backend RBAC and recorded in audit logs.</p>
        </div>
        <div className="rounded-xl bg-white p-4 shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">System configuration & maintenance (status)</h2>
          <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
            <li><b>Global configuration:</b> managed via environment/config, role and institution controls; security policies enforced server-side.</li>
            <li><b>Notification templates & policies:</b> category/priority preferences and event-driven notifications active; template management via configuration.</li>
            <li><b>AI configuration:</b> risk/compliance analysis uses deterministic, explainable assessments with evidence; authorized review required (no autonomous disciplinary actions).</li>
            <li><b>Compliance rules:</b> managed through policies/incidents/cases modules and analysis service.</li>
            <li><b>Database:</b> MySQL primary, Alembic migrations (head current). Health/connectivity monitored by application startup checks.</li>
            <li><b>Backups/maintenance:</b> perform regular MySQL backups and off-host retention per operational policy (external to app runtime).</li>
          </ul>
        </div>
      </div>

      <div className="rounded-xl bg-white p-4 shadow dark:bg-slate-900 dark:border dark:border-slate-700">
        <h2 className="font-semibold mb-2">System activity & audit logs</h2>
        <div className="max-h-80 overflow-auto text-sm">
          {audit.length===0 ? <p className="text-slate-500">No audit logs.</p> : audit.slice(0,80).map((l:any)=>(<div key={l.id} className="border-b py-1 dark:border-slate-700"><b>{l.action}</b> · inst {l.institution_id ?? 'global'} · user {l.user_id ?? '—'} · {l.resource_type||''} {l.resource_id||''} · {l.created_at?new Date(l.created_at).toLocaleString():''}</div>))}
        </div>
      </div>

      <AccountRequestsPanel />
    </div>
  )
}
