import { useEffect, useState } from 'react'
import api from '@/services/api'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'
import LecturerManagementPanel from '@/components/LecturerManagementPanel'
import ComplianceAnalysisPanel from '@/components/ComplianceAnalysisPanel'
import AccountRequestsPanel from '@/components/AccountRequestsPanel'

export default function AdminDashboard() {
  const [summary, setSummary] = useState<any>(null)
  useEffect(() => { api.get('/reports/institution-summary').then((r) => setSummary(r.data)).catch(() => {}) }, [])
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-navy-900">University Administrator Dashboard</h1>
      {summary && (
        <div className="grid md:grid-cols-3 gap-4">
          {Object.entries(summary).map(([k, v]) => (
            <div key={k} className="bg-white p-4 rounded-xl shadow">
              <p className="text-gray-500 text-sm">{k.replace(/_/g, ' ')}</p>
              <p className="text-3xl font-bold">{String(v)}</p>
            </div>
          ))}
        </div>
      )}
      <ComplianceAnalysisPanel />
      <AcademicDocumentsPanel mode="reviewer" />
      <AccountRequestsPanel />
      <LecturerManagementPanel />
    </div>
  )
}
