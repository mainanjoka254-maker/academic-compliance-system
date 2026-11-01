import { useEffect, useState } from 'react'
import api from '@/services/api'
import InstitutionManagementPanel from '@/components/InstitutionManagementPanel'
import LecturerRegistrationRequestsPanel from '@/components/LecturerRegistrationRequestsPanel'

export default function SuperAdminDashboard() {
  const [summary, setSummary] = useState<any>(null)
  const [summaryError, setSummaryError] = useState('')
  useEffect(() => {
    api.get('/reports/platform-summary')
      .then((response) => setSummary(response.data))
      .catch(() => setSummaryError('Platform summary could not be loaded.'))
  }, [])
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-navy-900">Super Administrator Dashboard</h1>
      {summaryError && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{summaryError}</p>}
      {summary && (
        <div className="grid md:grid-cols-3 gap-4">
          {Object.entries(summary).map(([k, v]) => (
            <div key={k} className="bg-white p-4 rounded-xl shadow"><p className="text-gray-500 text-sm">{k.replace(/_/g, ' ')}</p><p className="text-3xl font-bold">{String(v)}</p></div>
          ))}
        </div>
      )}
      <InstitutionManagementPanel />
      <LecturerRegistrationRequestsPanel />
    </div>
  )
}
