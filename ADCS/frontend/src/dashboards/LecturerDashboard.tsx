import { useEffect, useState } from 'react'
import api from '@/services/api'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'
import { Link } from 'react-router-dom'

export default function LecturerDashboard() {
  const [profile, setProfile] = useState<any>(null)
  const [courses, setCourses] = useState<any[]>([])
  const [students, setStudents] = useState<any[]>([])
  const [compliance, setCompliance] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    (async () => {
      setLoading(true); setError('')
      try {
        const [p, c, s] = await Promise.all([
          api.get('/profile/me'),
          api.get('/courses').catch(()=>({data:[]})),
          api.get('/lecturers/me/students').catch(()=>({data:[]})),
        ])
        setProfile(p.data)
        setCourses(Array.isArray(c.data)?c.data:[])
        setStudents(Array.isArray(s.data)?s.data:[])
        try { const lp = await api.get('/lecturers/me'); setCompliance(lp.data?.compliance || null) } catch {}
      } catch (e:any) { setError(e?.response?.data?.detail || 'Failed to load lecturer data') }
      finally { setLoading(false) }
    })()
  }, [])

  if (loading) return <div className="p-6">Loading...</div>
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-navy-900 dark:text-white">Lecturer Dashboard</h1>
        <Link to="/dashboard/settings" className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Settings & Profile</Link>
      </div>
      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {profile && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:bg-slate-900 dark:border-slate-700">
          <h2 className="font-semibold mb-2 text-navy-900 dark:text-white">Profile</h2>
          <div className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <div><b>Name:</b> {profile.full_name}</div>
            <div><b>Staff ID:</b> {profile.lecturer?.staff_number || 'N/A'}</div>
            <div><b>Department:</b> {profile.lecturer?.department?.name || profile.department?.name || 'N/A'}</div>
            <div><b>Faculty:</b> {profile.lecturer?.faculty?.name || 'N/A'}</div>
            <div><b>Institution:</b> {profile.institution?.name || 'N/A'}</div>
            <div><b>Email:</b> {profile.email}</div>
          </div>
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Assigned Courses</p><p className="text-3xl font-bold">{courses.length}</p></div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Students (assigned)</p><p className="text-3xl font-bold">{students.length}</p></div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Pending verifications</p><p className="text-3xl font-bold">{compliance?.pending_verification ?? 'N/A'}</p></div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Compliance</p><p className="text-lg font-semibold capitalize">{compliance?.compliance_status || 'N/A'}</p></div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Assigned courses & classes</h2>
          {courses.length===0 ? <p className="text-gray-500 text-sm">No courses assigned (or none visible).</p> : courses.map((c:any)=>(<div key={c.id} className="border-b py-2 text-sm dark:border-slate-700"><b>{c.code}</b> — {c.name} {c.credits ? `(${c.credits} cr)` : ''}</div>))}
        </div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Student list (assigned courses)</h2>
          {students.length===0 ? <p className="text-gray-500 text-sm">No students found for assigned courses.</p> : <div className="max-h-80 overflow-auto">{students.map((s:any)=>(<div key={s.id} className="border-b py-2 text-sm dark:border-slate-700"><div className="font-medium">{s.full_name} <span className="text-slate-500">({s.student_number})</span></div><div className="text-slate-600 dark:text-slate-300">{s.program || '—'} · Yr {s.year_of_study ?? '—'} · GPA {s.gpa ?? 'N/A'} · Att {s.attendance_percentage ?? 'N/A'}%</div><div className="text-xs text-slate-500">{(s.courses||[]).map((c:any)=>c.code).join(', ')}</div></div>))}</div>}
        </div>
      </div>
      {compliance?.courses_without_submission?.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <b>Courses without recorded submission:</b> {compliance.courses_without_submission.map((c:any)=>c.code).join(', ')}
        </div>
      )}
      <AcademicDocumentsPanel mode="lecturer" courses={courses} />
    </div>
  )
}
