import { useEffect, useState } from 'react'
import api from '@/services/api'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'
import ComplianceAnalysisPanel from '@/components/ComplianceAnalysisPanel'
import { Link } from 'react-router-dom'

export default function ComplianceDashboard() {
  const [profile, setProfile] = useState<any>(null)
  const [cases, setCases] = useState<any[]>([])
  const [incidents, setIncidents] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any[]>([])
  const [analysis, setAnalysis] = useState<any>(null)

  useEffect(() => {
    (async () => {
      try { const p = await api.get('/profile/me'); setProfile(p.data) } catch {}
      try { const c = await api.get('/compliance/cases'); setCases(Array.isArray(c.data)?c.data:[]) } catch {}
      try { const i = await api.get('/compliance/incidents'); setIncidents(Array.isArray(i.data)?i.data:[]) } catch {}
      try { const a = await api.get('/risk/alerts'); setAlerts(Array.isArray(a.data)?a.data:[]) } catch {}
      try { const an = await api.get('/compliance/analysis'); setAnalysis(an.data) } catch {}
    })()
  }, [])

  const openCases = cases.filter((c:any)=>!['resolved','closed'].includes(c.status))
  const elevated = analysis?.findings?.elevated_risk_students || []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-navy-900 dark:text-white">Compliance Officer Dashboard</h1>
        <Link to="/dashboard/settings" className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Settings & Profile</Link>
      </div>
      {profile && <div className="rounded-xl border bg-white p-4 text-sm shadow-sm dark:bg-slate-900 dark:border-slate-700"><b>{profile.full_name}</b> · {profile.staff?.staff_number || profile.lecturer?.staff_number || 'Staff'} · {profile.institution?.name || 'Institution'} · <span className="capitalize">{(profile.roles||[]).join(', ')}</span></div>}

      <div className="grid gap-4 md:grid-cols-4">
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Open Cases</p><p className="text-3xl font-bold">{openCases.length}</p></div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Incidents</p><p className="text-3xl font-bold">{incidents.length}</p></div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Unread Alerts</p><p className="text-3xl font-bold">{alerts.filter((a:any)=>!a.is_read).length}</p></div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Elevated-risk students</p><p className="text-3xl font-bold">{elevated.length}</p></div>
      </div>

      <ComplianceAnalysisPanel />

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Case management & escalation</h2>
          {cases.length===0 ? <p className="text-gray-500 text-sm">No cases.</p> : <div className="max-h-80 overflow-auto">{cases.map((c:any)=>(<div key={c.id} className="border-b py-2 text-sm dark:border-slate-700"><div className="font-medium">{c.case_number} — {c.title || c.status}</div><div className="text-slate-600 dark:text-slate-300">Status: {c.status} · Priority: {c.priority} · Stage: {c.current_stage || 'N/A'}</div></div>))}</div>}
        </div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Incident management</h2>
          {incidents.length===0 ? <p className="text-gray-500 text-sm">No incidents recorded.</p> : <div className="max-h-80 overflow-auto">{incidents.map((i:any)=>(<div key={i.id} className="border-b py-2 text-sm dark:border-slate-700"><div className="font-medium">{i.title}</div><div className="text-slate-600 dark:text-slate-300">{i.incident_type} · {i.status} · {i.priority}</div></div>))}</div>}
        </div>
      </div>

      <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
        <h2 className="font-semibold mb-2">Student risk assessments (AI-assisted, requires authorized review)</h2>
        <p className="mb-3 text-xs text-slate-500">Assessments are based on deterministic rules and recorded evidence/factors. AI outputs are advisory and must be reviewed by authorized staff; the system does not independently impose disciplinary actions.</p>
        {elevated.length===0 ? <p className="text-sm text-slate-500">No elevated-risk students in current analysis.</p> : <div className="space-y-3">{elevated.slice(0,20).map((r:any)=>(<div key={r.student_id} className="rounded-lg border p-3 dark:border-slate-700"><div className="flex flex-wrap items-center justify-between gap-2"><div className="font-medium">Student {r.student_number} (ID {r.student_id})</div><div className="text-sm"><b className="capitalize">{r.risk_level}</b> · score {r.risk_score}</div></div><div className="mt-2 text-sm"><b>Evidence/factors:</b><ul className="list-disc pl-5">{(r.factors||[]).map((f:any,idx:number)=>(<li key={idx}>{f.factor || f.explanation}: {f.explanation || JSON.stringify(f)}</li>))}</ul></div><div className="mt-2 text-sm"><b>Recommendations (advisory):</b><ul className="list-disc pl-5">{(r.recommendations||[]).map((rec:string,idx:number)=>(<li key={idx}>{rec}</li>))}</ul></div></div>))}</div>}
      </div>

      <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
        <h2 className="font-semibold mb-2">Risk alerts & corrective action tracking</h2>
        {alerts.length===0 ? <p className="text-sm text-slate-500">No alerts.</p> : <div className="max-h-72 overflow-auto">{alerts.map((a:any)=>(<div key={a.id} className="border-b py-2 text-sm dark:border-slate-700"><b className="capitalize">{a.level}</b> — {a.message} <span className="text-slate-500">({a.is_read?'read':'unread'})</span></div>))}</div>}
      </div>

      <AcademicDocumentsPanel mode="reviewer" />
    </div>
  )
}
