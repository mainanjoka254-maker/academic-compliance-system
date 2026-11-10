import { useEffect, useState } from 'react'
import api from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'
import { Link } from 'react-router-dom'

export default function StudentDashboard() {
  const { user } = useAuth()
  const [student, setStudent] = useState<any>(null)
  const [profile, setProfile] = useState<any>(null)
  const [assessments, setAssessments] = useState<any[]>([])
  const [cases, setCases] = useState<any[]>([])
  const [notifs, setNotifs] = useState<any[]>([])

  useEffect(() => {
    (async () => {
      try { const p = await api.get('/profile/me'); setProfile(p.data) } catch {}
      try {
        const students = await api.get('/students')
        const me = students.data.find((s: any) => s.user_id === user?.id)
        if (me) {
          setStudent(me)
          const a = await api.get(`/academic/assessments/${me.id}`).catch(()=>({data:[]}))
          setAssessments(a.data || [])
          const c = await api.get('/compliance/cases').catch(()=>({data:[]}))
          setCases(Array.isArray(c.data) ? c.data : (c.data?.items || []))
        }
      } catch {}
      try { const n = await api.get('/notifications', { params: { format: 'center', limit: 20 } }); const d=n.data; setNotifs(Array.isArray(d)?d:(d.items||[])) } catch {}
    })()
  }, [user])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-navy-900 dark:text-white">Student Dashboard</h1>
        <div className="flex gap-2">
          <Link to="/dashboard/student/profile" className="rounded-lg border border-primary-200 bg-white px-4 py-2 text-sm font-medium text-primary-700 hover:bg-primary-50">My Profile (9 tabs)</Link>
          <Link to="/dashboard/settings" className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Settings</Link>
        </div>
      </div>
      {profile && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:bg-slate-900 dark:border-slate-700">
          <h2 className="mb-2 font-semibold text-navy-900 dark:text-white">Overview</h2>
          <div className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <div><b>Name:</b> {profile.full_name}</div>
            <div><b>Email:</b> {profile.email}</div>
            <div><b>Student No:</b> {profile.student?.student_number || student?.student_number || 'N/A'}</div>
            <div><b>Programme:</b> {profile.student?.program || 'N/A'}</div>
            <div><b>Institution:</b> {profile.institution?.name || 'N/A'}</div>
            <div><b>Status:</b> {profile.account_status}</div>
          </div>
        </div>
      )}
      {student && (
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Attendance</p><p className="text-3xl font-bold">{student.attendance_percentage?.toFixed ? student.attendance_percentage.toFixed(1) : student.attendance_percentage}%</p></div>
          <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">GPA</p><p className="text-3xl font-bold">{student.gpa ?? 'N/A'}</p></div>
          <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Status</p><p className="text-3xl font-bold">{student.status}</p></div>
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Compliance & Cases</h2>
          {cases.length === 0 ? <p className="text-gray-500">No cases.</p> : cases.map((c:any)=><div key={c.id || c.case_number} className="border-b py-2 text-sm dark:border-slate-700">{c.case_number || c.id} - {c.status} {c.priority ? `(${c.priority})` : ''}</div>)}
        </div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Assessments & Academic Progress</h2>
          {assessments.length === 0 ? <p className="text-gray-500">No assessments recorded.</p> : assessments.slice(0, 8).map((assessment: any) => (
            <div key={assessment.id} className="border-b py-2 text-sm dark:border-slate-700">
              {assessment.title} - {assessment.submitted ? 'Submitted' : 'Not submitted'}
              {assessment.due_date && <span className="text-gray-500"> (Due {assessment.due_date})</span>}
            </div>
          ))}
        </div>
      </div>
      <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
        <h2 className="font-semibold mb-2">Notifications</h2>
        {notifs.length === 0 ? <p className="text-gray-500">No notifications.</p> : notifs.slice(0,8).map((n:any)=><div key={n.id} className="border-b py-2 text-sm dark:border-slate-700"><b>{n.title}</b> — {n.message}</div>)}
      </div>
      <AcademicDocumentsPanel mode="student" />
    </div>
  )
}
