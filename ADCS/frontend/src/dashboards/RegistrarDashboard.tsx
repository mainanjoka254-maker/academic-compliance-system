import { useEffect, useState } from 'react'
import api from '@/services/api'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'
import LecturerManagementPanel from '@/components/LecturerManagementPanel'
import ComplianceAnalysisPanel from '@/components/ComplianceAnalysisPanel'
import LecturerRegistrationRequestsPanel from '@/components/LecturerRegistrationRequestsPanel'
import { Link } from 'react-router-dom'

export default function RegistrarDashboard() {
  const [profile, setProfile] = useState<any>(null)
  const [students, setStudents] = useState<any[]>([])
  const [courses, setCourses] = useState<any[]>([])

  useEffect(() => {
    (async () => {
      try { const p = await api.get('/profile/me'); setProfile(p.data) } catch {}
      try { const s = await api.get('/students'); setStudents(Array.isArray(s.data)?s.data:[]) } catch {}
      try { const c = await api.get('/courses'); setCourses(Array.isArray(c.data)?c.data:[]) } catch {}
    })()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-navy-900 dark:text-white">Registrar Dashboard</h1>
        <Link to="/dashboard/settings" className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Settings & Profile</Link>
      </div>
      {profile && <div className="rounded-xl border bg-white p-4 text-sm shadow-sm dark:bg-slate-900 dark:border-slate-700"><b>{profile.full_name}</b> · {profile.staff?.staff_number || 'Staff'} · {profile.institution?.name || 'Institution'} · Registrar</div>}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Student Records</p><p className="text-3xl font-bold">{students.length}</p></div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Courses</p><p className="text-3xl font-bold">{courses.length}</p></div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700"><p className="text-gray-500 text-sm">Registration & approvals</p><p className="text-sm font-medium">Manage requests, enrolments & records</p></div>
      </div>
      <ComplianceAnalysisPanel />
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Student registration & academic records</h2>
          <div className="max-h-80 overflow-auto text-sm">
            {students.length===0 ? <p className="text-slate-500">No student records.</p> : students.slice(0,30).map((s:any)=>(<div key={s.id} className="border-b py-2 dark:border-slate-700"><div className="font-medium">{s.student_number} — {s.full_name}</div><div className="text-slate-600 dark:text-slate-300">{s.program || '—'} · Yr {s.year_of_study ?? '—'} · {s.status} · GPA {s.gpa ?? 'N/A'} · Att {s.attendance_percentage ?? 'N/A'}%</div></div>))}
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow dark:bg-slate-900 dark:border dark:border-slate-700">
          <h2 className="font-semibold mb-2">Course registration oversight</h2>
          <div className="max-h-80 overflow-auto text-sm">
            {courses.length===0 ? <p className="text-slate-500">No courses.</p> : courses.map((c:any)=>(<div key={c.id} className="border-b py-2 dark:border-slate-700"><b>{c.code}</b> — {c.name} {c.credits?`(${c.credits} cr)`:''}</div>))}
          </div>
          <p className="mt-2 text-xs text-slate-500">Academic request approvals, transcript/document verification and calendar management are available via authorized modules and records workflows.</p>
        </div>
      </div>
      <AcademicDocumentsPanel mode="reviewer" />
      <LecturerRegistrationRequestsPanel />
      <LecturerManagementPanel />
    </div>
  )
}
