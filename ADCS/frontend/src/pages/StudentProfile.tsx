import { useEffect, useMemo, useState } from 'react'
import api from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'

type Tab = 'overview'|'personal'|'academic'|'courses'|'progress'|'attendance'|'compliance'|'documents'|'activity'

const tabs: {id:Tab,label:string}[] = [
  {id:'overview',label:'Overview'},
  {id:'personal',label:'Personal information'},
  {id:'academic',label:'Academic information'},
  {id:'courses',label:'Registered courses'},
  {id:'progress',label:'Academic progress'},
  {id:'attendance',label:'Attendance'},
  {id:'compliance',label:'Compliance'},
  {id:'documents',label:'Documents'},
  {id:'activity',label:'Activity history'},
]

export default function StudentProfile() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('overview')
  const [profile, setProfile] = useState<any>(null)
  const [student, setStudent] = useState<any>(null)
  const [courses, setCourses] = useState<any[]>([])
  const [assessments, setAssessments] = useState<any[]>([])
  const [attendance, setAttendance] = useState<any[]>([])
  const [cases, setCases] = useState<any[]>([])
  const [activity, setActivity] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')

  useEffect(() => {
    (async () => {
      setLoading(true); setErr('')
      try {
        const p = await api.get('/profile/me'); setProfile(p.data)
        const sres = await api.get('/students'); const me = (sres.data||[]).find((s:any)=>s.user_id===user?.id) || null; setStudent(me)
        const [c,a,att,cs,act] = await Promise.all([
          api.get('/courses').catch(()=>({data:[]})),
          me ? api.get(`/academic/assessments/${me.id}`).catch(()=>({data:[]})) : Promise.resolve({data:[]}),
          me ? api.get(`/academic/attendance/${me.id}`).catch(()=>({data:[]})) : Promise.resolve({data:[]}),
          api.get('/compliance/cases').catch(()=>({data:[]})),
          api.get('/profile/me/activity').catch(()=>({data:[]})),
        ])
        setCourses(Array.isArray(c.data)?c.data:[])
        setAssessments(Array.isArray(a.data)?a.data:[])
        setAttendance(Array.isArray(att.data)?att.data:[])
        setCases(Array.isArray(cs.data)?cs.data:(cs.data?.items||[]))
        setActivity(Array.isArray(act.data)?act.data:[])
      } catch (e:any) { setErr(e?.response?.data?.detail || 'Failed to load profile data') }
      finally { setLoading(false) }
    })()
  }, [user])

  const attendanceSummary = useMemo(() => {
    const total = attendance.length
    const present = attendance.filter(r => ['present','late','excused'].includes(r.status)).length
    const rate = total ? Math.round((present/total)*1000)/10 : (student?.attendance_percentage ?? null)
    return { total, present, rate }
  }, [attendance, student])

  if (loading) return <div className="p-6">Loading student profile...</div>
  if (err) return <div className="p-6 text-red-700">{err}</div>

  const sp = profile?.student || {}
  const Card = ({title,children}:{title:string,children:any}) => <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:bg-slate-900 dark:border-slate-700"><h3 className="mb-3 text-base font-semibold text-navy-900 dark:text-white">{title}</h3>{children}</div>
  const Row = ({k,v}:{k:string,v:any}) => <div className="flex justify-between gap-4 border-b py-2 text-sm dark:border-slate-700"><span className="text-slate-500">{k}</span><span className="font-medium text-slate-800 dark:text-slate-100 text-right">{v ?? 'N/A'}</span></div>

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-navy-900 dark:text-white">Student Profile</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">View your academic record and manage permitted personal information in Settings.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {tabs.map(t => <button key={t.id} onClick={()=>setTab(t.id)} className={`rounded-lg px-3 py-2 text-sm font-medium border ${tab===t.id?'bg-primary-600 text-white border-primary-600':'bg-white hover:bg-slate-50 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-200'}`}>{t.label}</button>)}
      </div>

      {tab==='overview' && <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Overview">
          <Row k="Full name" v={profile?.full_name} />
          <Row k="Student number" v={sp.student_number || student?.student_number} />
          <Row k="Institution" v={profile?.institution?.name} />
          <Row k="Programme" v={sp.program || student?.program} />
          <Row k="Year of study" v={sp.year_of_study ?? student?.year_of_study} />
          <Row k="Academic status" v={sp.status || student?.status} />
          <Row k="GPA" v={sp.gpa ?? student?.gpa} />
          <Row k="Attendance" v={`${attendanceSummary.rate ?? 'N/A'}%`} />
        </Card>
        <Card title="Quick summaries">
          <Row k="Registered courses" v={courses.length} />
          <Row k="Assessments" v={assessments.length} />
          <Row k="Attendance records" v={attendance.length} />
          <Row k="Compliance cases" v={cases.length} />
          <Row k="Account status" v={profile?.account_status} />
          <Row k="Email verified" v={profile?.is_verified ? 'Yes' : 'No'} />
        </Card>
      </div>}

      {tab==='personal' && <Card title="Personal information">
        <Row k="Full name" v={profile?.full_name} />
        <Row k="Email" v={profile?.email} />
        <Row k="Phone" v={profile?.phone} />
        <Row k="Gender" v={profile?.gender} />
        <Row k="Date of birth" v={profile?.date_of_birth} />
        <Row k="Address" v={profile?.address} />
        <Row k="Biography" v={profile?.biography} />
        <Row k="Emergency contact" v={sp.profile?.emergency_contact_name} />
        <Row k="Emergency phone" v={sp.profile?.emergency_contact_phone} />
        <Row k="Relation" v={sp.profile?.emergency_contact_relation} />
        <p className="mt-3 text-xs text-slate-500">Update permitted personal details and submit correction requests in Settings → My Profile.</p>
      </Card>}

      {tab==='academic' && <Card title="Academic information (official)">
        <Row k="Student registration number" v={sp.student_number || student?.student_number} />
        <Row k="Institution" v={profile?.institution?.name} />
        <Row k="Faculty" v={sp.faculty?.name || sp.department?.faculty_name} />
        <Row k="Department" v={sp.department?.name} />
        <Row k="Programme" v={sp.program || student?.program} />
        <Row k="Year of study" v={sp.year_of_study ?? student?.year_of_study} />
        <Row k="Enrollment/Admission" v={sp.enrollment_date || sp.profile?.admission_date} />
        <Row k="Academic status" v={sp.status || sp.profile?.academic_status} />
        <Row k="GPA" v={sp.gpa ?? student?.gpa} />
        <p className="mt-3 text-xs text-slate-500">Official academic records are managed by authorized staff and cannot be edited by students.</p>
      </Card>}

      {tab==='courses' && <Card title="Registered courses">
        {courses.length===0 ? <p className="text-sm text-slate-500">No registered courses found.</p> : <div className="space-y-2">{courses.map((c:any)=>(<div key={c.id} className="rounded-lg border p-3 dark:border-slate-700"><div className="font-medium">{c.code} — {c.name}</div><div className="text-sm text-slate-600 dark:text-slate-300">Credits: {c.credits ?? 'N/A'} · Active: {String(c.is_active ?? true)}</div></div>))}</div>}
      </Card>}

      {tab==='progress' && <Card title="Academic progress">
        <Row k="GPA" v={sp.gpa ?? student?.gpa} />
        <Row k="Attendance rate" v={`${attendanceSummary.rate ?? 'N/A'}%`} />
        <Row k="Assessments recorded" v={assessments.length} />
        <Row k="Submitted assessments" v={assessments.filter(a=>a.submitted).length} />
        <div className="mt-3 space-y-2">{assessments.slice(0,20).map((a:any)=>(<div key={a.id} className="flex justify-between border-b py-2 text-sm dark:border-slate-700"><span>{a.title} ({a.assessment_type})</span><span>{a.submitted ? `Submitted${a.score!=null?` · ${a.score}/${a.max_score}`:''}` : 'Not submitted'}</span></div>))}{assessments.length===0 && <p className="text-sm text-slate-500">No assessment records yet.</p>}</div>
      </Card>}

      {tab==='attendance' && <Card title="Attendance">
        <Row k="Summary rate" v={`${attendanceSummary.rate ?? 'N/A'}%`} />
        <Row k="Present/late/excused" v={`${attendanceSummary.present} / ${attendanceSummary.total}`} />
        <div className="mt-3 max-h-96 space-y-2 overflow-auto">{attendance.length===0 ? <p className="text-sm text-slate-500">No attendance records.</p> : attendance.map((r:any)=>(<div key={r.id} className="flex justify-between border-b py-2 text-sm dark:border-slate-700"><span>{r.date} · Course #{r.course_id}</span><span className="font-medium capitalize">{r.status}</span></div>))}</div>
      </Card>}

      {tab==='compliance' && <Card title="Compliance">
        <Row k="Compliance status" v={sp.profile?.compliance_status || 'N/A'} />
        {cases.length===0 ? <p className="mt-2 text-sm text-slate-500">No compliance cases.</p> : <div className="mt-3 space-y-2">{cases.map((c:any)=>(<div key={c.id||c.case_number} className="rounded-lg border p-3 dark:border-slate-700"><div className="font-medium">{c.case_number || `Case #${c.id}`} — {c.title || c.status}</div><div className="text-sm text-slate-600 dark:text-slate-300">Status: {c.status} · Priority: {c.priority || 'N/A'}</div></div>))}</div>}
      </Card>}

      {tab==='documents' && <Card title="Documents"><AcademicDocumentsPanel mode="student" /></Card>}

      {tab==='activity' && <Card title="Activity history">
        {activity.length===0 ? <p className="text-sm text-slate-500">No activity recorded yet.</p> : <div className="max-h-[480px] space-y-2 overflow-auto">{activity.map((a:any)=>(<div key={a.id} className="border-b py-2 text-sm dark:border-slate-700"><div className="font-medium">{a.activity_type}</div><div className="text-slate-600 dark:text-slate-300">{a.description}</div><div className="text-xs text-slate-500">{a.created_at ? new Date(a.created_at).toLocaleString():''}</div></div>))}</div>}
      </Card>}
    </div>
  )
}
