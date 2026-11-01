import { useEffect, useState } from 'react'
import api from '@/services/api'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'
import LecturerManagementPanel from '@/components/LecturerManagementPanel'
import ComplianceAnalysisPanel from '@/components/ComplianceAnalysisPanel'
import LecturerRegistrationRequestsPanel from '@/components/LecturerRegistrationRequestsPanel'

export default function RegistrarDashboard() {
  const [students, setStudents] = useState<any[]>([])
  useEffect(() => { api.get('/students').then((r) => setStudents(r.data)).catch(() => {}) }, [])
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-navy-900">Registrar Dashboard</h1>
      <div className="bg-white p-4 rounded-xl shadow"><p className="text-gray-500 text-sm">Total Students</p><p className="text-3xl font-bold">{students.length}</p></div>
      <ComplianceAnalysisPanel />
      <div className="bg-white p-4 rounded-xl shadow">
        <h2 className="font-semibold mb-2">Student Records</h2>
        {students.slice(0, 20).map((s: any) => <div key={s.id} className="border-b py-2">{s.student_number} - {s.full_name} ({s.status})</div>)}
      </div>
      <AcademicDocumentsPanel mode="reviewer" />
      <LecturerRegistrationRequestsPanel />
      <LecturerManagementPanel />
    </div>
  )
}
