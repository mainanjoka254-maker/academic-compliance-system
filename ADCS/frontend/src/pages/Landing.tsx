import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ShieldCheck, BarChart3, Building2, GraduationCap, Users, FileCheck2,
  Bell, Bot, Menu, X, ChevronRight, CheckCircle2, ArrowRight, Sparkles,
} from 'lucide-react'
import api from '@/services/api'

type HomepageStats = {
  total_students?: number
  total_lecturers?: number
  total_institutions?: number
  compliance_rate?: number | null
}

export default function Landing() {
  const [stats, setStats] = useState<HomepageStats | null>(null)
  const [announcements, setAnnouncements] = useState<any[]>([])
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    api.get('/stats/homepage').then((r: any) => setStats(r.data)).catch(() => setStats(null))
    api.get('/announcements').then((r: any) => setAnnouncements(Array.isArray(r.data) ? r.data : [])).catch(() => setAnnouncements([]))
  }, [])

  const fmt = (v: number | null | undefined, suffix = '') =>
    v === null || v === undefined ? '—' : `${v}${suffix}`

  const roles = [
    { icon: ShieldCheck, name: 'Super Administrator', desc: 'Platform governance, institutional onboarding, and system-wide oversight.', tone: 'bg-slate-900 text-white' },
    { icon: Building2, name: 'University Administrator', desc: 'Institution operations, faculties, departments, and staff management.', tone: 'bg-blue-700 text-white' },
    { icon: FileCheck2, name: 'Registrar', desc: 'Student registration, academic records, and progression tracking.', tone: 'bg-indigo-600 text-white' },
    { icon: BarChart3, name: 'Compliance Officer', desc: 'Compliance monitoring, evidence verification, and accreditation reporting.', tone: 'bg-emerald-600 text-white' },
    { icon: Users, name: 'Lecturer', desc: 'Teaching, attendance, assessments, and academic submissions.', tone: 'bg-amber-500 text-white' },
    { icon: GraduationCap, name: 'Student', desc: 'Profile, course records, results, documents, and requirements.', tone: 'bg-sky-600 text-white' },
  ]

  const features = [
    { icon: Building2, title: 'Multi-Institution Management', text: 'Onboard and govern institutions with strict data isolation.' },
    { icon: FileCheck2, title: 'Academic Records', text: 'Manage students, programmes, courses, and verified records.' },
    { icon: ShieldCheck, title: 'Compliance Monitoring', text: 'Detect gaps, track cases, and manage corrective actions.' },
    { icon: BarChart3, title: 'Analytics & Reporting', text: 'Role-aware dashboards powered by real institutional data.' },
    { icon: Bot, title: 'AI Academic Assistant', text: 'Permission-aware guidance for compliance and workflows.' },
    { icon: Bell, title: 'Notifications & Approvals', text: 'Verification, approvals, alerts, and audit-ready activity.' },
  ]

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-navy-950/90 text-white backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <Link to="/" className="flex items-center gap-2 font-extrabold tracking-tight">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-primary-600"><GraduationCap size={18} /></span>
            <span className="text-lg">ADCS</span>
            <span className="hidden rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-300 sm:inline">v2</span>
          </Link>
          <nav className="hidden items-center gap-6 text-sm text-slate-200 md:flex">
            <a href="#features" className="hover:text-white">Features</a>
            <a href="#roles" className="hover:text-white">Roles</a>
            <a href="#how" className="hover:text-white">How it works</a>
            <a href="#announcements" className="hover:text-white">Announcements</a>
            <Link to="/login" className="adcs-btn-primary px-4 py-2 text-sm">Sign in</Link>
          </nav>
          <button className="rounded-lg p-2 text-slate-200 hover:bg-white/10 md:hidden" aria-label="Toggle menu" onClick={() => setMenuOpen((v) => !v)}>
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
        {menuOpen && (
          <div className="border-t border-white/10 px-4 py-3 md:hidden">
            <div className="flex flex-col gap-2 text-sm text-slate-200">
              <a href="#features" onClick={() => setMenuOpen(false)} className="rounded-lg px-2 py-2 hover:bg-white/10">Features</a>
              <a href="#roles" onClick={() => setMenuOpen(false)} className="rounded-lg px-2 py-2 hover:bg-white/10">Roles</a>
              <a href="#how" onClick={() => setMenuOpen(false)} className="rounded-lg px-2 py-2 hover:bg-white/10">How it works</a>
              <Link to="/login" onClick={() => setMenuOpen(false)} className="adcs-btn-primary mt-1 text-sm">Sign in</Link>
              <Link to="/register" onClick={() => setMenuOpen(false)} className="adcs-btn-secondary text-sm">Create account</Link>
            </div>
          </div>
        )}
      </header>

      <section className="relative overflow-hidden bg-navy-950 bg-hero-mesh text-white">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:py-24">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-slate-200">
              <Sparkles size={14} className="text-amber-300" /> Secure, role-based, multi-institution platform
            </div>
            <h1 className="text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              Academic compliance, <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-amber-300">built for trust.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base text-slate-300 sm:text-lg">
              ADCS helps institutions manage academic records, monitor compliance, verify evidence, and guide every role — with secure access, real-time visibility, and auditable workflows.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Link to="/login" className="adcs-btn-primary">Sign in to ADCS <ArrowRight size={16} className="ml-2" /></Link>
              <Link to="/register" className="adcs-btn-secondary border-white/20 bg-white/10 text-white hover:bg-white/15">Create account</Link>
              <a href="#features" className="inline-flex items-center justify-center px-2 py-2 text-sm font-medium text-slate-300 hover:text-white">Explore features <ChevronRight size={16} /></a>
            </div>
            <p className="mt-4 text-xs text-slate-400">Works on laptop and mobile. Access on your network: use your laptop’s IP with port 4173.</p>
          </div>

          <div className="adcs-card border-white/10 bg-white/5 p-5 text-slate-100 backdrop-blur">
            <div className="mb-4 flex items-center justify-between">
              <div className="text-sm font-semibold">Live platform overview</div>
              <div className="text-xs text-slate-400">from your database</div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Institutions', value: fmt(stats?.total_institutions) },
                { label: 'Students', value: fmt(stats?.total_students) },
                { label: 'Lecturers', value: fmt(stats?.total_lecturers) },
                { label: 'Compliance rate', value: fmt(stats?.compliance_rate, '%') },
              ].map((m) => (
                <div key={m.label} className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <div className="text-2xl font-bold">{m.value}</div>
                  <div className="text-xs text-slate-300">{m.label}</div>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-3 text-xs text-emerald-100">
              <CheckCircle2 size={14} className="mr-1 inline" /> Role-based access, email verification, and institutional approval workflows are active.
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <div className="mx-auto mb-10 max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-navy-900">Everything institutions need to stay compliant</h2>
          <p className="mt-3 text-slate-600">Modular capabilities that connect governance, academics, evidence, and reporting — without exposing unauthorized data.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="adcs-card p-5 transition hover:-translate-y-0.5">
              <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary-50 text-primary-700"><f.icon size={20} /></div>
              <h3 className="font-semibold text-navy-900">{f.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="roles" className="bg-white px-4 py-16 sm:px-6">
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto mb-10 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-navy-900">Access by role</h2>
            <p className="mt-3 text-slate-600">Each role sees only what it’s authorized to access. Dashboards require sign-in and backend permission checks.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {roles.map((r) => (
              <div key={r.name} className="adcs-card flex h-full flex-col p-5">
                <div className={`mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl ${r.tone}`}><r.icon size={20} /></div>
                <h3 className="font-semibold text-navy-900">{r.name}</h3>
                <p className="mt-1 flex-1 text-sm text-slate-600">{r.desc}</p>
                <Link to="/login" className="mt-4 inline-flex items-center text-sm font-semibold text-primary-700 hover:text-primary-800">Access dashboard <ChevronRight size={16} /></Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="how" className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <div className="mx-auto mb-10 max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-navy-900">How it works</h2>
          <p className="mt-3 text-slate-600">A secure onboarding flow that protects institutions while keeping access simple.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[
            { n: '01', t: 'Register / request access', d: 'Students register directly; staff roles submit verified requests with institutional approval.' },
            { n: '02', t: 'Verify & approve', d: 'Email verification and role-appropriate approvals activate secure access.' },
            { n: '03', t: 'Manage academics', d: 'Maintain records, documents, attendance, assessments, and compliance evidence.' },
            { n: '04', t: 'Monitor & report', d: 'Track compliance status, generate reports, and resolve corrective actions.' },
          ].map((s) => (
            <div key={s.n} className="adcs-card p-5">
              <div className="text-xs font-bold tracking-widest text-primary-600">{s.n}</div>
              <h3 className="mt-2 font-semibold text-navy-900">{s.t}</h3>
              <p className="mt-1 text-sm text-slate-600">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="announcements" className="bg-white px-4 py-16 sm:px-6">
        <div className="mx-auto max-w-7xl">
          <h2 className="text-3xl font-bold tracking-tight text-navy-900">Latest announcements</h2>
          <p className="mt-2 text-slate-600">Public announcements from the platform (when available).</p>
          {announcements.length === 0 ? (
            <div className="adcs-card mt-6 p-6 text-sm text-slate-500">No public announcements available right now.</div>
          ) : (
            <ul className="mt-6 grid gap-4 md:grid-cols-2">
              {announcements.slice(0, 6).map((a: any) => (
                <li key={a.id} className="adcs-card p-5">
                  <div className="font-semibold text-navy-900">{a.title}</div>
                  <div className="mt-1 text-sm text-slate-600">{a.body}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-slate-50 px-4 py-10 sm:px-6">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-sm text-slate-600 md:flex-row">
          <div className="flex items-center gap-2 font-semibold text-navy-900"><GraduationCap size={18} className="text-primary-700" /> ADCS <span className="font-normal text-slate-500">Academic-Driven Compliance System</span></div>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link to="/login" className="hover:text-navy-900">Sign in</Link>
            <Link to="/register" className="hover:text-navy-900">Register</Link>
            <Link to="/account-status" className="hover:text-navy-900">Check status</Link>
          </div>
          <div className="text-slate-500">© {new Date().getFullYear()} ADCS</div>
        </div>
      </footer>
    </div>
  )
}