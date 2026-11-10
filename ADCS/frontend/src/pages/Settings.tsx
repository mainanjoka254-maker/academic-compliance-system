import { useEffect, useState } from 'react'
import api from '@/services/api'
import { User, Shield, Bell, Palette, HelpCircle, Save, Upload, Trash2, LogOut, RefreshCw } from 'lucide-react'

type Tab = 'profile' | 'account' | 'notifications' | 'security' | 'appearance' | 'help'

const tabs: { id: Tab; label: string; icon: any }[] = [
  { id: 'profile', label: 'My Profile', icon: User },
  { id: 'account', label: 'Account Settings', icon: Shield },
  { id: 'notifications', label: 'Notification Settings', icon: Bell },
  { id: 'security', label: 'Security & Privacy', icon: Shield },
  { id: 'appearance', label: 'Appearance & Accessibility', icon: Palette },
  { id: 'help', label: 'Help & Support', icon: HelpCircle },
]

export default function Settings() {
  const [tab, setTab] = useState<Tab>('profile')
  const [profile, setProfile] = useState<any>(null)
  const [settings, setSettings] = useState<any>(null)
  const [sessions, setSessions] = useState<any[]>([])
  const [loginHistory, setLoginHistory] = useState<any[]>([])
  const [tickets, setTickets] = useState<any[]>([])
  const [notifs, setNotifs] = useState<any[]>([])
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm: '' })
  const [ticketForm, setTicketForm] = useState({ subject: '', description: '', category: 'technical' })
  const [correction, setCorrection] = useState({ subject: '', details: '' })
  const [deactReason, setDeactReason] = useState('')
  const [avatarSrc, setAvatarSrc] = useState<string | null>(null)
  const [newEmail, setNewEmail] = useState('')
  const [pendingEmail, setPendingEmail] = useState('')

  const flash = (m: string, e = false) => { setMsg(e ? '' : m); setErr(e ? m : ''); setTimeout(() => { setMsg(''); setErr('') }, 4000) }

  const loadAvatar = async (hasAvatar: boolean) => {
    if (!hasAvatar) { setAvatarSrc(null); return }
    try {
      const r = await api.get('/profile/me/avatar/file', { responseType: 'blob' })
      setAvatarSrc((prev) => { if (prev) URL.revokeObjectURL(prev); return URL.createObjectURL(r.data) })
    } catch { setAvatarSrc(null) }
  }

  const load = async () => {
    setLoading(true)
    try {
      const [p, s] = await Promise.all([api.get('/profile/me'), api.get('/settings/me')])
      setProfile(p.data); setSettings(s.data)
      await loadAvatar(!!p.data?.profile_picture_path || !!p.data?.avatar_url)
      const [sess, hist, t, n] = await Promise.all([
        api.get('/profile/me/security/sessions').catch(() => ({ data: [] })),
        api.get('/profile/me/security/login-history').catch(() => ({ data: [] })),
        api.get('/support/tickets').catch(() => ({ data: [] })),
        api.get('/notifications', { params: { format: 'center', limit: 100 } }).catch(() => ({ data: { items: [], unread_count: 0 } })),
      ])
      setSessions(sess.data || [])
      setLoginHistory(hist.data || [])
      setTickets(Array.isArray(t.data) ? t.data : [])
      const nd = n.data; setNotifs(Array.isArray(nd) ? nd : (nd.items || [])); setUnread(Array.isArray(nd) ? nd.filter((x:any)=>!x.is_read).length : (nd.unread_count || 0))
    } catch (e: any) { flash(e?.response?.data?.detail || 'Failed to load settings', true) }
    finally { setLoading(false) }
  }
  useEffect(() => { load(); return () => { if (avatarSrc) URL.revokeObjectURL(avatarSrc) } }, [])

  const saveProfile = async () => {
    setSaving(true)
    try {
      const payload: any = { full_name: profile.full_name, phone: profile.phone, gender: profile.gender, date_of_birth: profile.date_of_birth || null, address: profile.address, biography: profile.biography }
      if (profile.student) payload.student_profile = profile.student.profile || {}
      if (profile.lecturer) payload.lecturer_profile = profile.lecturer.profile || {}
      if (profile.staff) payload.staff_profile = profile.staff || {}
      const r = await api.patch('/profile/me', payload); setProfile(r.data); flash('Profile saved')
    } catch (e: any) { flash(e?.response?.data?.detail || 'Save failed', true) } finally { setSaving(false) }
  }
  const saveSettings = async (patch?: any) => {
    setSaving(true)
    try { const body = patch ? { ...settings, ...patch } : settings; const r = await api.patch('/settings/me', body); setSettings(r.data); flash('Settings saved') } catch (e: any) { flash(e?.response?.data?.detail || 'Save failed', true) } finally { setSaving(false) }
  }
  const uploadAvatar = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (!f) return
    const fd = new FormData(); fd.append('file', f)
    try { await api.post('/profile/me/avatar', fd); await load(); flash('Profile picture updated') } catch (ex: any) { flash(ex?.response?.data?.detail || 'Upload failed', true) }
  }
  const removeAvatar = async () => { try { await api.delete('/profile/me/avatar'); await load(); flash('Profile picture removed') } catch (ex: any) { flash(ex?.response?.data?.detail || 'Remove failed', true) } }
  const changePassword = async () => { if (pw.new_password !== pw.confirm) return flash('New passwords do not match', true); try { await api.post('/profile/me/change-password', { current_password: pw.current_password, new_password: pw.new_password }); setPw({ current_password: '', new_password: '', confirm: '' }); flash('Password changed') } catch (e: any) { flash(e?.response?.data?.detail || 'Password change failed', true) } }
  const revokeOthers = async () => { if (!confirm('Log out from all other sessions?')) return; try { await api.post('/profile/me/security/sessions/revoke-others'); await load(); flash('Other sessions revoked') } catch (e: any) { flash(e?.response?.data?.detail || 'Failed', true) } }
  const submitTicket = async () => { if (!ticketForm.subject.trim() || !ticketForm.description.trim()) return flash('Subject and description required', true); try { await api.post('/support/tickets', ticketForm); setTicketForm({ subject: '', description: '', category: 'technical' }); const t = await api.get('/support/tickets'); setTickets(t.data || []); flash('Support ticket submitted') } catch (e: any) { flash(e?.response?.data?.detail || 'Failed', true) } }
  const submitCorrection = async () => { if (!correction.details.trim()) return flash('Details required', true); try { await api.post('/profile/me/correction-request', correction); setCorrection({ subject: '', details: '' }); flash('Correction request submitted to authorized administrators') } catch (e: any) { flash(e?.response?.data?.detail || 'Failed', true) } }
  const submitDeactivation = async () => { if (!deactReason.trim()) return flash('Reason required', true); if (!confirm('Submit account deactivation request for review?')) return; try { await api.post('/profile/me/deactivation-request', { reason: deactReason }); setDeactReason(''); flash('Deactivation request submitted for authorized review') } catch (e: any) { flash(e?.response?.data?.detail || 'Failed', true) } }
  const requestEmailChange = async () => {
    if (!newEmail.trim()) return flash('Enter a new email address', true)
    try { const r = await api.post('/profile/me/change-email/request', { new_email: newEmail }); setPendingEmail(r.data?.pending_email || newEmail); flash(r.data?.message || 'Verification sent'); setNewEmail('') } catch (e:any) { flash(e?.response?.data?.detail || 'Request failed', true) }
  }
  const markRead = async (id: number) => { try { await api.patch(`/notifications/${id}/read`); setNotifs(ns => ns.map(n => n.id===id?{...n,is_read:true}:n)); setUnread(u=>Math.max(0,u-1)) } catch {} }
  const markAll = async () => { try { await api.post('/notifications/read-all'); setNotifs(ns => ns.map(n => ({...n,is_read:true}))); setUnread(0) } catch {} }
  const archive = async (id: number) => { try { await api.post(`/notifications/${id}/archive`); setNotifs(ns => ns.filter(n => n.id!==id)) } catch {} }


  useEffect(() => { const root = document.documentElement; const theme = settings?.theme || 'system'; const dark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches); root.classList.toggle('dark', dark); root.style.fontSize = settings?.font_size === 'large' ? '18px' : settings?.font_size === 'small' ? '14px' : '16px' }, [settings?.theme, settings?.font_size])

  if (loading || !profile || !settings) return <div className="p-8 text-slate-600">Loading settings...</div>
  const Card = ({title, children}: any) => <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:bg-slate-900 dark:border-slate-700"><h3 className="mb-3 text-base font-semibold text-navy-900 dark:text-white">{title}</h3>{children}</div>
  const Label = ({children}: any) => <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">{children}</label>
  const Input = (p: any) => <input {...p} className={`w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:bg-slate-800 dark:border-slate-600 dark:text-slate-100 ${p.className||''}`} />

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold text-navy-900 dark:text-white">Settings</h1><p className="text-sm text-slate-600 dark:text-slate-300">Profile, preferences, security, notifications and support.</p></div><button onClick={load} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-600"><RefreshCw size={16}/>Refresh</button></div>
      {msg && <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{msg}</div>}
      {err && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{err}</div>}
      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        <aside className="h-fit rounded-xl border border-slate-200 bg-white p-2 shadow-sm dark:bg-slate-900 dark:border-slate-700">
          {tabs.map(t => { const Icon = t.icon; const active = tab===t.id; return (<button key={t.id} onClick={()=>setTab(t.id)} className={`mb-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium ${active ? 'bg-primary-600 text-white' : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'}`}><Icon size={16}/>{t.label}</button>) })}
        </aside>
        <section className="space-y-4">
          {tab==='profile' && <div className="space-y-4">
            <Card title="My Profile">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-full bg-slate-200 text-xl font-bold text-slate-600">{avatarSrc ? <img src={avatarSrc} alt="Profile" className="h-full w-full object-cover" /> : (profile.full_name||'?').slice(0,1)}</div>
                <div className="flex flex-wrap gap-2"><label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-600"><Upload size={16}/>Upload<input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={uploadAvatar} /></label><button onClick={removeAvatar} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-600"><Trash2 size={16}/>Remove</button></div>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div><Label>Full name</Label><Input value={profile.full_name||''} onChange={(e:any)=>setProfile({...profile,full_name:e.target.value})} /></div>
                <div><Label>Email address</Label><Input value={profile.email||''} disabled className="bg-slate-100 dark:bg-slate-800" /><p className="mt-1 text-xs text-slate-500">Email changes requiring new-address verification are handled via authorized support in this build.</p></div>
                <div><Label>Phone number</Label><Input value={profile.phone||''} onChange={(e:any)=>setProfile({...profile,phone:e.target.value})} /></div>
                <div><Label>Gender</Label><Input value={profile.gender||''} onChange={(e:any)=>setProfile({...profile,gender:e.target.value})} /></div>
                <div><Label>Date of birth</Label><Input type="date" value={(profile.date_of_birth||'').toString().slice(0,10)} onChange={(e:any)=>setProfile({...profile,date_of_birth:e.target.value})} /></div>
                <div><Label>Address</Label><Input value={profile.address||''} onChange={(e:any)=>setProfile({...profile,address:e.target.value})} /></div>
                <div className="sm:col-span-2"><Label>Biography</Label><textarea value={profile.biography||''} onChange={(e)=>setProfile({...profile,biography:e.target.value})} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600" rows={3} /></div>
              </div>
              <div className="mt-4 grid gap-2 text-sm text-slate-700 dark:text-slate-300 sm:grid-cols-2"><div><b>Account created:</b> {profile.account_created_at?new Date(profile.account_created_at).toLocaleString():'N/A'}</div><div><b>Account status:</b> {profile.account_status} {profile.is_verified?'(verified)':'(unverified)'}</div><div><b>Role:</b> {(profile.roles||[]).join(', ')||'N/A'}</div><div><b>Institution:</b> {profile.institution?.name||'N/A'} {profile.institution?.code?`(${profile.institution.code})`:''}</div></div>
              {profile.student && <div className="mt-4 rounded-lg border p-3 dark:border-slate-700"><h4 className="font-semibold">Student (official fields read-only)</h4><div className="mt-2 grid gap-2 text-sm sm:grid-cols-2"><div>Registration #: <b>{profile.student.student_number||'N/A'}</b></div><div>Programme: <b>{profile.student.program||'N/A'}</b></div><div>Year: <b>{profile.student.year_of_study ?? 'N/A'}</b></div><div>Status: <b>{profile.student.status||'N/A'}</b></div><div>GPA: <b>{profile.student.gpa ?? 'N/A'}</b></div><div>Attendance: <b>{profile.student.attendance_percentage ?? 'N/A'}%</b></div></div><div className="mt-3 grid gap-3 sm:grid-cols-3"><div><Label>Emergency contact name</Label><Input value={profile.student.profile?.emergency_contact_name||''} onChange={(e:any)=>setProfile({...profile,student:{...profile.student,profile:{...(profile.student.profile||{}),emergency_contact_name:e.target.value}}})} /></div><div><Label>Emergency contact phone</Label><Input value={profile.student.profile?.emergency_contact_phone||''} onChange={(e:any)=>setProfile({...profile,student:{...profile.student,profile:{...(profile.student.profile||{}),emergency_contact_phone:e.target.value}}})} /></div><div><Label>Relation</Label><Input value={profile.student.profile?.emergency_contact_relation||''} onChange={(e:any)=>setProfile({...profile,student:{...profile.student,profile:{...(profile.student.profile||{}),emergency_contact_relation:e.target.value}}})} /></div></div><p className="mt-2 text-xs text-slate-500">Students cannot modify official registration numbers, grades, attendance records, academic standing or compliance decisions.</p></div>}
              {profile.lecturer && <div className="mt-4 rounded-lg border p-3 dark:border-slate-700"><h4 className="font-semibold">Lecturer</h4><div className="mt-2 grid gap-2 text-sm sm:grid-cols-2"><div>Staff ID: <b>{profile.lecturer.staff_number||'N/A'}</b></div><div>Department: <b>{profile.lecturer.department?.name||'N/A'}</b></div></div><div className="mt-3 grid gap-3 sm:grid-cols-2"><div><Label>Professional title</Label><Input value={profile.lecturer.profile?.professional_title||''} onChange={(e:any)=>setProfile({...profile,lecturer:{...profile.lecturer,profile:{...(profile.lecturer.profile||{}),professional_title:e.target.value}}})} /></div><div><Label>Office</Label><Input value={profile.lecturer.profile?.office_location||''} onChange={(e:any)=>setProfile({...profile,lecturer:{...profile.lecturer,profile:{...(profile.lecturer.profile||{}),office_location:e.target.value}}})} /></div></div></div>}
              <div className="mt-4"><button onClick={saveProfile} disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"><Save size={16}/>{saving?'Saving...':'Save profile'}</button></div>
            </Card>
            {profile.roles?.includes('student') && <Card title="Request correction (official records)"><div className="grid gap-3"><div><Label>Subject</Label><Input value={correction.subject} onChange={(e:any)=>setCorrection({...correction,subject:e.target.value})} /></div><div><Label>Details</Label><textarea value={correction.details} onChange={(e)=>setCorrection({...correction,details:e.target.value})} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600" rows={3} /></div><div><button onClick={submitCorrection} className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white">Submit correction request</button></div></div></Card>}
          </div>}

          {tab==='account' && <Card title="Account Settings"><div className="grid gap-3 sm:grid-cols-2"><div><Label>Preferred language</Label><Input value={settings.language||'en'} onChange={(e:any)=>setSettings({...settings,language:e.target.value})} /></div><div><Label>Timezone</Label><Input value={settings.timezone||'Africa/Nairobi'} onChange={(e:any)=>setSettings({...settings,timezone:e.target.value})} /></div><div><Label>Date format</Label><Input value={settings.date_format||'YYYY-MM-DD'} onChange={(e:any)=>setSettings({...settings,date_format:e.target.value})} /></div><div><Label>Dashboard density</Label><select className="w-full rounded-lg border px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600" value={settings.dashboard_preferences?.density||'comfortable'} onChange={(e)=>setSettings({...settings,dashboard_preferences:{...(settings.dashboard_preferences||{}),density:e.target.value}})}><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></div></div><div className="mt-4"><button onClick={()=>saveSettings()} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Save account preferences</button></div><div className="mt-6 border-t pt-4 dark:border-slate-700"><h4 className="mb-2 font-semibold text-slate-800 dark:text-slate-100">Change email (verification required)</h4><div className="grid gap-2 sm:grid-cols-[1fr_auto]"><Input type="email" value={newEmail} onChange={(e:any)=>setNewEmail(e.target.value)} placeholder="New email address" /><button onClick={requestEmailChange} className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-slate-50 dark:border-slate-600">Send verification</button></div>{pendingEmail && <p className="mt-2 text-sm text-amber-700">Pending verification: <b>{pendingEmail}</b>. Confirm via the link sent to the new address.</p>}<p className="mt-2 text-xs text-slate-500">Current: {profile.email}. Your email changes only after you confirm the verification link sent to the new address.</p></div></Card>}

          {tab==='notifications' && <div className="space-y-4"><Card title="Notification Preferences">{(() => { const np=settings.notification_preferences||{}; const upd=(k:string,v:boolean)=>setSettings({...settings,notification_preferences:{...np,[k]:v}}); const row=(k:string,l:string)=>(<label key={k} className="flex items-center justify-between rounded-lg border px-3 py-2 dark:border-slate-700"><span className="text-sm">{l}</span><input type="checkbox" checked={!!np[k]} onChange={(e)=>upd(k,e.target.checked)} /></label>); return <div className="grid gap-2 sm:grid-cols-2">{row('email_enabled','Enable non-critical email notifications')}{row('in_app_enabled','Enable non-critical in-app notifications')}{row('academic_announcements','Academic announcements')}{row('course_notifications','Course notifications')}{row('registration_notifications','Registration notifications')}{row('attendance_alerts','Attendance alerts')}{row('compliance_alerts','Compliance alerts')}{row('assessment_notifications','Assessment notifications')}{row('security_notifications','Security notifications')}<div className="sm:col-span-2"><Label>Frequency</Label><select className="w-full rounded-lg border px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-700" value={np.frequency||'immediate'} onChange={(e)=>setSettings({...settings,notification_preferences:{...np,frequency:e.target.value}})}><option value="immediate">Immediate</option><option value="daily">Daily</option><option value="weekly">Weekly</option></select></div></div> })()}<div className="mt-4"><button onClick={()=>saveSettings()} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Save notification settings</button></div></Card>
            <Card title={`Notification Centre (${unread} unread)`}><div className="mb-3 flex flex-wrap gap-2"><button onClick={markAll} className="rounded-lg border px-3 py-1.5 text-sm">Mark all read</button></div><div className="max-h-[420px] space-y-2 overflow-auto">{notifs.length===0?<div className="rounded-lg border border-dashed p-6 text-center text-sm text-slate-500">No notifications.</div>:notifs.map(n=>(<div key={n.id} className={`rounded-lg border p-3 dark:border-slate-700 ${n.is_read?'':'bg-blue-50/50 dark:bg-slate-800'}`}><div className="flex items-start justify-between gap-2"><div><div className="text-sm font-semibold">{n.title} <span className="ml-2 rounded bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-700">{n.category||n.type}</span></div><div className="text-sm text-slate-600 dark:text-slate-300">{n.message}</div><div className="mt-1 text-xs text-slate-500">{n.created_at?new Date(n.created_at).toLocaleString():''} · {n.delivery_status||'in_app'}</div></div><div className="flex flex-col gap-1">{!n.is_read && <button onClick={()=>markRead(n.id)} className="text-xs text-primary-700">Read</button>} {!n.is_archived && <button onClick={()=>archive(n.id)} className="text-xs text-slate-600">Archive</button>}</div></div></div>))}</div></Card></div>}

          {tab==='security' && <div className="space-y-4"><Card title="Change password"><div className="grid gap-3 sm:grid-cols-3"><div><Label>Current password</Label><Input type="password" value={pw.current_password} onChange={(e:any)=>setPw({...pw,current_password:e.target.value})} /></div><div><Label>New password</Label><Input type="password" value={pw.new_password} onChange={(e:any)=>setPw({...pw,new_password:e.target.value})} /></div><div><Label>Confirm new password</Label><Input type="password" value={pw.confirm} onChange={(e:any)=>setPw({...pw,confirm:e.target.value})} /></div></div><div className="mt-3"><button onClick={changePassword} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Change password</button></div></Card>
            <Card title="Active sessions & devices"><div className="mb-3"><button onClick={revokeOthers} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm dark:border-slate-700"><LogOut size={16}/>Logout other sessions</button></div><div className="max-h-64 space-y-2 overflow-auto">{sessions.length===0?<p className="text-sm text-slate-500">No session records yet.</p>:sessions.map(s=>(<div key={s.id} className="rounded-lg border p-3 text-sm dark:border-slate-700"><div className="font-medium">{s.device_info||'Session'} {s.is_active?<span className="ml-2 text-emerald-600">Active</span>:<span className="ml-2 text-slate-500">Revoked</span>}</div><div className="text-slate-600 dark:text-slate-300">IP: {s.ip_address||'N/A'} · {s.last_active_at?new Date(s.last_active_at).toLocaleString():'N/A'}</div></div>))}</div></Card>
            <Card title="Login history"><div className="max-h-64 space-y-2 overflow-auto text-sm">{loginHistory.length===0?<p className="text-slate-500">No login history yet.</p>:loginHistory.map(h=>(<div key={h.id} className="flex items-center justify-between rounded-lg border p-2 dark:border-slate-700"><div><span className={h.success?'text-emerald-700':'text-red-700'}>{h.success?'Success':'Failed'}</span> · {h.method} · {h.ip_address||'N/A'}</div><div className="text-slate-500">{h.created_at?new Date(h.created_at).toLocaleString():''}</div></div>))}</div></Card>
            <Card title="Privacy preferences">{(() => { const pr=settings.privacy||{}; const upd=(k:string,v:boolean)=>setSettings({...settings,privacy:{...pr,[k]:v}}); return <div className="grid gap-2 sm:grid-cols-2"><label className="flex items-center justify-between rounded-lg border px-3 py-2 dark:border-slate-700"><span className="text-sm">Show profile picture</span><input type="checkbox" checked={!!pr.show_profile_picture} onChange={e=>upd('show_profile_picture',e.target.checked)} /></label><label className="flex items-center justify-between rounded-lg border px-3 py-2 dark:border-slate-700"><span className="text-sm">Show email</span><input type="checkbox" checked={!!pr.show_email} onChange={e=>upd('show_email',e.target.checked)} /></label><label className="flex items-center justify-between rounded-lg border px-3 py-2 dark:border-slate-700"><span className="text-sm">Show phone</span><input type="checkbox" checked={!!pr.show_phone} onChange={e=>upd('show_phone',e.target.checked)} /></label><label className="flex items-center justify-between rounded-lg border px-3 py-2 dark:border-slate-700"><span className="text-sm">Allow contact</span><input type="checkbox" checked={!!pr.allow_contact} onChange={e=>upd('allow_contact',e.target.checked)} /></label></div> })()}<div className="mt-3"><button onClick={()=>saveSettings()} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Save privacy preferences</button></div><div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Account deactivation/deletion requests (where permitted) are submitted for authorized review and recorded securely.</div><div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto]"><textarea value={deactReason} onChange={(e)=>setDeactReason(e.target.value)} placeholder="Reason for account deactivation request" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600" rows={2} /><button onClick={submitDeactivation} className="h-fit rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100">Submit deactivation request</button></div></Card></div>}

          {tab==='appearance' && <Card title="Appearance & Accessibility"><div className="grid gap-3 sm:grid-cols-2"><div><Label>Theme</Label><select className="w-full rounded-lg border px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-700" value={settings.theme||'system'} onChange={(e)=>setSettings({...settings,theme:e.target.value})}><option value="system">System default</option><option value="light">Light mode</option><option value="dark">Dark mode</option></select></div><div><Label>Font size</Label><select className="w-full rounded-lg border px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-700" value={settings.font_size||'medium'} onChange={(e)=>setSettings({...settings,font_size:e.target.value})}><option value="small">Small</option><option value="medium">Medium</option><option value="large">Large</option></select></div><div><Label>Language</Label><Input value={settings.language||'en'} onChange={(e:any)=>setSettings({...settings,language:e.target.value})} /></div><div><Label>Date display</Label><Input value={settings.date_format||'YYYY-MM-DD'} onChange={(e:any)=>setSettings({...settings,date_format:e.target.value})} /></div></div><div className="mt-4"><button onClick={()=>saveSettings()} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Save appearance preferences</button></div></Card>}

          {tab==='help' && <div className="space-y-4"><Card title="Frequently asked questions"><ul className="list-disc space-y-2 pl-5 text-sm text-slate-700 dark:text-slate-300"><li><b>How do I verify my email?</b> Use the verification code sent during registration or resend from the verification screen.</li><li><b>Why can’t I sign in?</b> Ensure email is verified, account is approved (staff roles), and active.</li><li><b>How do I correct official records?</b> Submit a correction request; authorized staff update official data.</li><li><b>Need help?</b> Submit a support ticket below.</li></ul></Card>
            <Card title="Submit a support ticket"><div className="grid gap-3"><div><Label>Subject</Label><Input value={ticketForm.subject} onChange={(e:any)=>setTicketForm({...ticketForm,subject:e.target.value})} /></div><div><Label>Category</Label><select className="w-full rounded-lg border px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-700" value={ticketForm.category} onChange={(e)=>setTicketForm({...ticketForm,category:e.target.value})}><option value="technical">Technical</option><option value="account">Account</option><option value="academic">Academic</option><option value="compliance">Compliance</option></select></div><div><Label>Description</Label><textarea value={ticketForm.description} onChange={(e)=>setTicketForm({...ticketForm,description:e.target.value})} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-700" rows={4} /></div><div><button onClick={submitTicket} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">Submit ticket</button></div></div></Card>
            <Card title="My support tickets"><div className="space-y-2">{tickets.length===0?<p className="text-sm text-slate-500">No tickets submitted yet.</p>:tickets.map(t=>(<div key={t.id} className="rounded-lg border p-3 text-sm dark:border-slate-700"><div className="flex flex-wrap items-center justify-between gap-2"><div className="font-medium">{t.subject}</div><div className="rounded bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-700">{t.status} · {t.priority}</div></div><div className="text-slate-600 dark:text-slate-300">{t.description}</div><div className="mt-1 text-xs text-slate-500">#{t.id} · {t.category||'general'} · {t.created_at?new Date(t.created_at).toLocaleString():''}</div></div>))}</div></Card></div>}
        </section>
      </div>
    </div>
  )
}

