import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '@/services/api'

export default function Landing() {
  const [stats, setStats] = useState<any>(null)
  const [announcements, setAnnouncements] = useState<any[]>([])

  useEffect(() => {
    api.get('/stats/homepage').then((r: any) => setStats(r.data)).catch(() => setStats(null))
    api.get('/announcements').then((r: any) => setAnnouncements(r.data || [])).catch(() => setAnnouncements([]))
  }, [])

  const roles = [
    { name: 'Super Administrator', desc: 'Platform governance, institutional onboarding and system-wide monitoring.' },
    { name: 'University Administrator', desc: 'Institutional operations, departments, faculties and staff management.' },
    { name: 'Registrar', desc: 'Student registration, academic records and academic progression.' },
    { name: 'Compliance Officer', desc: 'Compliance monitoring, document verification and accreditation reporting.' },
    { name: 'Lecturer', desc: 'Teaching management, attendance, assessments and academic submissions.' },
    { name: 'Student', desc: 'Academic profile, course registration, results and document tracking.' },
  ]

  const features = [
    'Multi-Institution Management',
    'Academic Records Management',
    'Automated Compliance Monitoring',
    'Accreditation Management',
    'AI Academic Assistant',
    'Document Verification',
    'Attendance and Assessment Tracking',
    'Advanced Analytics and Reporting',
    'Notifications and Reminders',
    'Secure Role-Based Access',
  ]

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="sticky top-0 z-50 bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-xl"><span>🎓</span> ADCS</div>
        <nav className="hidden md:flex gap-6 items-center">
          <a href="#home">Home</a>
          <a href="#about">About</a>
          <a href="#features">Features</a>
          <a href="#how">How It Works</a>
          <a href="#institutions">Institutions</a>
          <a href="#contact">Contact</a>
          <Link to="/login" className="bg-blue-600 px-4 py-2 rounded-lg">Login</Link>
        </nav>
      </header>

      <section id="home" className="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 text-white px-6 py-24">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-10 items-center">
          <div>
            <h1 className="text-5xl font-bold mb-3">Academic Compliance. Simplified. Intelligent. Transparent.</h1>
            <h2 className="text-2xl text-amber-300 mb-4">Academic Compliance System (ADCS)</h2>
            <p className="text-slate-200 mb-8">A secure, intelligent, multi-institution platform designed to strengthen academic governance, monitor compliance, manage academic records and promote institutional excellence.</p>
            <div className="flex gap-4 flex-wrap">
              <a href="#features" className="bg-blue-600 px-6 py-3 rounded-lg font-semibold">Explore ADCS</a>
              <Link to="/login" className="bg-white text-slate-900 px-6 py-3 rounded-lg font-semibold">Sign In to ADCS</Link>
              <Link to="/register" className="underline self-center">Create Account</Link>
            </div>
          </div>
          <div className="bg-white/10 rounded-2xl p-6 backdrop-blur">
            <div className="text-sm text-slate-200">Compliance analytics preview</div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div className="bg-white/20 rounded-lg p-4">Institutions: {stats?.total_institutions ?? '—'}</div>
              <div className="bg-white/20 rounded-lg p-4">Students: {stats?.total_students ?? '—'}</div>
              <div className="bg-white/20 rounded-lg p-4">Lecturers: {stats?.total_lecturers ?? '—'}</div>
              <div className="bg-white/20 rounded-lg p-4">Compliance: {stats?.compliance_rate ?? '—'}%</div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-12 bg-white">
        <div className="max-w-6xl mx-auto grid md:grid-cols-4 gap-6 text-center">
          <div><div className="text-3xl font-bold text-blue-700">{stats?.total_institutions ?? '—'}</div><div>Institutions registered</div></div>
          <div><div className="text-3xl font-bold text-blue-700">{stats?.total_students ?? '—'}</div><div>Academic records managed</div></div>
          <div><div className="text-3xl font-bold text-blue-700">{stats?.total_lecturers ?? '—'}</div><div>Lecturers</div></div>
          <div><div className="text-3xl font-bold text-blue-700">{stats?.compliance_rate ?? '—'}%</div><div>Compliance rate</div></div>
        </div>
      </section>

      <section className="px-6 py-16 max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-10">Role Access</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {roles.map((r) => (
            <div key={r.name} className="bg-white rounded-xl shadow p-6 border">
              <h3 className="text-xl font-semibold text-blue-900 mb-2">{r.name}</h3>
              <p className="text-slate-600 mb-4">{r.desc}</p>
              <Link to="/login" className="text-blue-600 font-medium">Access Dashboard →</Link>
            </div>
          ))}
        </div>
      </section>

      <section id="features" className="bg-slate-50 px-6 py-16">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-10">Platform Features</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
            {features.map((f) => (
              <div key={f} className="bg-white p-4 rounded-lg shadow text-center">{f}</div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-16 max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold mb-4">Meet Your Intelligent Academic Assistant</h2>
        <p className="text-slate-600 mb-6">Get instant assistance with academic records, compliance requirements, accreditation standards and institutional reporting.</p>
        <div className="bg-white rounded-xl shadow p-6">
          <ul className="list-disc pl-6 text-slate-700">
            <li>What compliance requirements are outstanding?</li>
            <li>Which documents need verification?</li>
            <li>Summarize our department's compliance performance.</li>
            <li>What corrective actions are overdue?</li>
          </ul>
          <Link to="/login" className="inline-block mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg">Open AI Assistant</Link>
        </div>
      </section>

      <section id="how" className="bg-slate-50 px-6 py-16">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-10">How It Works</h2>
          <div className="grid md:grid-cols-4 gap-6">
            {['Register your institution','Set up academic departments and users','Monitor academic activities and compliance','Generate reports and improve academic performance'].map((s,i) => (
              <div key={s} className="bg-white p-6 rounded-xl shadow text-center">
                <div className="text-2xl font-bold text-blue-700 mb-2">{i+1}</div>
                <div>{s}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-16 max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold mb-6">Latest Announcements</h2>
        {announcements.length === 0 ? (
          <p className="text-slate-500">No announcements available.</p>
        ) : (
          <ul className="space-y-4">
            {announcements.slice(0,5).map((a:any) => (
              <li key={a.id} className="bg-white p-4 rounded-lg shadow">
                <div className="font-semibold">{a.title}</div>
                <div className="text-slate-600 text-sm">{a.body}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer id="contact" className="bg-slate-900 text-white px-6 py-10 text-center">
        <div className="mb-2 font-bold text-lg">ADCS</div>
        <div className="text-slate-300 mb-4">Secure, Reliable and Compliant</div>
        <div className="text-sm text-slate-400">© ADCS Academic Compliance System</div>
      </footer>
    </div>
  )
}