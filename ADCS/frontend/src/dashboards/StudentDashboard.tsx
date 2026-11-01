import { useEffect, useState } from 'react'
import api from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'

export default function StudentDashboard() {
  const { user } = useAuth()
  const [student, setStudent] = useState<any>(null)
  const [assessments, setAssessments] = useState<any[]>([])
  const [cases, setCases] = useState<any[]>([])
  const [notifs, setNotifs] = useState<any[]>([])

  useEffect(() => {
    (async () => {
      try {
        const students = await api.get('/students')
        const me = students.data.find((s: any) => s.user_id === user?.id)
        if (me) {
          setStudent(me)
          const a = await api.get(`/academic/assessments/${me.id}`)
          setAssessments(a.data)
          const c = await api.get('/compliance/cases')
          setCases(c.data)
        }
        const n = await api.get('/notifications')
        setNotifs(n.data)
      } catch {}
    })()
  }, [user])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-navy-900">Student Dashboard</h1>
      {student && (
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-xl shadow"><p className="text-gray-500 text-sm">Attendance</p><p className="text-3xl font-bold">{student.attendance_percentage?.toFixed(1)}%</p></div>
          <div className="bg-white p-4 rounded-xl shadow"><p className="text-gray-500 text-sm">GPA</p><p className="text-3xl font-bold">{student.gpa ?? 'N/A'}</p></div>
          <div className="bg-white p-4 rounded-xl shadow"><p className="text-gray-500 text-sm">Status</p><p className="text-3xl font-bold">{student.status}</p></div>
        </div>
      )}
      <div className="bg-white p-4 rounded-xl shadow">
        <h2 className="font-semibold mb-2">Compliance Cases</h2>
        {cases.length === 0 ? <p className="text-gray-500">No cases.</p> : cases.map((c:any)=><div key={c.id} className="border-b py-2">{c.case_number} - {c.status}</div>)}
      </div>
      <div className="bg-white p-4 rounded-xl shadow">
        <h2 className="font-semibold mb-2">Assessments</h2>
        {assessments.length === 0 ? <p className="text-gray-500">No assessments recorded.</p> : assessments.slice(0, 5).map((assessment: any) => (
          <div key={assessment.id} className="border-b py-2">
            {assessment.title} - {assessment.submitted ? 'Submitted' : 'Not submitted'}
            {assessment.due_date && <span className="text-gray-500"> (Due {assessment.due_date})</span>}
          </div>
        ))}
      </div>
      <div className="bg-white p-4 rounded-xl shadow">
        <h2 className="font-semibold mb-2">Notifications</h2>
        {notifs.slice(0,5).map((n:any)=><div key={n.id} className="border-b py-2">{n.title}</div>)}
      </div>
      <AcademicDocumentsPanel mode="student" />
    </div>
  )
}
