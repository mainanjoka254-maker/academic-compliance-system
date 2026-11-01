import { useEffect, useState } from 'react'
import api from '@/services/api'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'
import ComplianceAnalysisPanel from '@/components/ComplianceAnalysisPanel'

export default function ComplianceDashboard() {
  const [cases, setCases] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any[]>([])
  useEffect(() => {
    (async () => {
      try { const c = await api.get('/compliance/cases'); setCases(c.data) } catch {}
      try { const a = await api.get('/risk/alerts'); setAlerts(a.data) } catch {}
    })()
  }, [])
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-navy-900">Compliance Officer Dashboard</h1>
      <ComplianceAnalysisPanel />
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white p-4 rounded-xl shadow"><p className="text-gray-500 text-sm">Open Cases</p><p className="text-3xl font-bold">{cases.filter((c:any)=>!['resolved','closed'].includes(c.status)).length}</p></div>
        <div className="bg-white p-4 rounded-xl shadow"><p className="text-gray-500 text-sm">Unread Alerts</p><p className="text-3xl font-bold">{alerts.filter((a:any)=>!a.is_read).length}</p></div>
      </div>
      <div className="bg-white p-4 rounded-xl shadow">
        <h2 className="font-semibold mb-2">Cases</h2>
        {cases.map((c:any)=><div key={c.id} className="border-b py-2">{c.case_number} - {c.status} ({c.priority})</div>)}
      </div>
      <AcademicDocumentsPanel mode="reviewer" />
    </div>
  )
}
