import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  ArrowUpRight,
  Bell,
  BookOpen,
  Check,
  ClipboardCheck,
  Eye,
  EyeOff,
  FileDown,
  GraduationCap,
  LogOut,
  MessageCircle,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Settings,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:4000/api";

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || "Request failed");
  return payload;
}

function Login({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [role, setRole] = useState("ACADEMIC_OFFICER");
  const [showPassword, setShowPassword] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", firstName: "", lastName: "", regNo: "", programId: "" });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  function suggestPassword() {
    const password = `Ac${Math.random().toString(36).slice(2, 8)}!${Math.floor(1000 + Math.random() * 9000)}Q`;
    setForm({ ...form, password });
    setShowPassword(true);
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") {
        const data = await api("/auth/login", { method: "POST", body: JSON.stringify({ email: form.email, password: form.password }) });
        if (data.user.role !== role) throw new Error(`This account is registered as ${data.user.role.replaceAll("_", " ")}. Select the matching sign-in role.`);
        onLogin(data.user);
      } else {
        await api("/auth/register", { method: "POST", body: JSON.stringify({ ...form, role: "STUDENT" }) });
        setMode("login");
        setNotice("Account created. Verify your email OTP, then sign in.");
      }
    } catch (err) {
    setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  return (
    <main className="login-shell">
      <section className="login-art">
        <div className="brand-mark"><GraduationCap size={22} /></div>
        <p className="eyebrow">Academic operations</p>
        <h1>Keep every learner on track.</h1>
        <p className="login-intro">A clear view of academic health, emerging risk, and the action required next.</p>
        <div className="art-note"><ShieldCheck size={18} /><span>Evidence-led compliance monitoring</span></div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <p className="eyebrow">Academic workspace</p>
          <h2>{mode === "login" ? "Sign in" : "Create account"}</h2>
          <p className="muted">{mode === "login" ? "Choose your institutional role and open the right workspace." : "Student accounts can be created here. Staff accounts are managed by an administrator."}</p>
          <form onSubmit={submit}>
            {mode === "login" && <label>Sign in as<select value={role} onChange={(e) => setRole(e.target.value)}><option value="STUDENT">Student</option><option value="LECTURER">Lecturer</option><option value="ACADEMIC_OFFICER">Academic officer</option><option value="ADMIN">University administrator</option></select></label>}
            {mode === "register" && <div className="two-fields"><label>First name<input required value={form.firstName} onChange={update("firstName")} placeholder="Amina" /></label><label>Last name<input required value={form.lastName} onChange={update("lastName")} placeholder="Otieno" /></label></div>}
            <label>Email<input type="email" required value={form.email} onChange={update("email")} placeholder={mode === "login" ? "you@university.edu" : "student@university.edu"} /></label>
            {mode === "register" && <><label>Registration number<input required value={form.regNo} onChange={update("regNo")} placeholder="STU-2026-001" /></label><label>Programme ID<input required value={form.programId} onChange={update("programId")} placeholder="Paste the programme ID provided by your institution" /></label></>}
            <label>Password<div className="password-field"><input type={showPassword ? "text" : "password"} required minLength="8" value={form.password} onChange={update("password")} placeholder="At least 8 characters" /><button type="button" className="field-icon" title={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>
            {mode === "register" && <div className="password-tools"><p className="password-hint"><ShieldCheck size={14} /> Use 12+ characters with uppercase, lowercase, a number, and a symbol.</p><button type="button" className="suggest-password" onClick={suggestPassword}><Sparkles size={13} />Suggest strong password</button></div>}
            {notice && <div className="form-notice"><Check size={16} />{notice}</div>}
            {error && <div className="form-error"><AlertTriangle size={16} />{error}</div>}
            <button className="primary-button" disabled={busy}>{busy ? "Please wait..." : mode === "login" ? "Open workspace" : "Create student account"}{mode === "login" ? <ArrowUpRight size={17} /> : <UserPlus size={17} />}</button>
          </form>
          <button className="switch-auth" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); setNotice(""); }}>{mode === "login" ? "Need a student account? Create one" : "Already have an account? Sign in"}</button>
        </div>
      </section>
    </main>
  );
}

function Stat({ label, value, tone, note }) {
  return <article className={`stat-card ${tone}`}><div className="stat-label">{label}</div><strong>{value}</strong><span>{note}</span></article>;
}

function RiskPill({ value }) {
  return <span className={`risk-pill ${String(value).toLowerCase()}`}>{value?.replace("_", " ") || "Unknown"}</span>;
}

function AcademicAgent() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([{ role: "agent", text: "Ask me about attendance, GPA, risk levels, assessments, registration, or compliance rules." }]);

  async function ask(event) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy) return;
    setQuestion("");
    setMessages((items) => [...items, { role: "user", text }]);
    setBusy(true);
    try {
      const result = await api("/ai/ask", { method: "POST", body: JSON.stringify({ question: text }) });
      setMessages((items) => [...items, { role: "agent", text: result.answer }]);
    } catch (err) {
      setMessages((items) => [...items, { role: "agent", text: err.message }]);
    } finally { setBusy(false); }
  }

  return <div className={`agent ${open ? "open" : ""}`}>
    {open && <section className="agent-panel"><header><div><b>Academic agent</b><span>Compliance guidance</span></div><button className="field-icon" onClick={() => setOpen(false)} title="Close assistant"><X size={17} /></button></header><div className="agent-messages">{messages.map((message, index) => <div className={`agent-message ${message.role}`} key={`${message.role}-${index}`}>{message.text}</div>)}{busy && <div className="agent-message">Thinking...</div>}</div><form onSubmit={ask} className="agent-form"><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a compliance question" /><button type="submit" title="Send question" disabled={busy}><Send size={16} /></button></form></section>}
    <button className="agent-trigger" onClick={() => setOpen(!open)} title="Open academic agent"><MessageCircle size={20} />{!open && <span>Ask academic agent</span>}</button>
  </div>;
}

function AccountCenter({ user, onClose }) {
  const [tab, setTab] = useState("profile");
  const [profile, setProfile] = useState({ firstName: user.firstName || "", lastName: user.lastName || "", email: user.email || "" });
  const [settings, setSettings] = useState({ emailNotifications: true, inAppNotifications: true, digestFrequency: "DAILY", language: "en", timezone: "UTC" });
  const [notifications, setNotifications] = useState([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api("/account/settings"), api("/account/notifications")]).then(([settingData, notificationData]) => {
      setSettings(settingData.settings);
      setNotifications(notificationData.notifications || []);
    }).catch((err) => setMessage(err.message));
  }, []);

  async function saveProfile(event) {
    event.preventDefault(); setBusy(true); setMessage("");
    try { await api("/account/profile", { method: "PATCH", body: JSON.stringify(profile) }); setMessage("Profile saved."); }
    catch (err) { setMessage(err.message); } finally { setBusy(false); }
  }

  async function saveSettings(event) {
    event.preventDefault(); setBusy(true); setMessage("");
    try { await api("/account/settings", { method: "PATCH", body: JSON.stringify(settings) }); setMessage("Settings saved."); }
    catch (err) { setMessage(err.message); } finally { setBusy(false); }
  }

  async function readAll() {
    await api("/account/notifications/read-all", { method: "POST" });
    setNotifications((items) => items.map((item) => ({ ...item, isRead: true })));
  }

  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="account-modal"><header className="account-header"><div><p className="eyebrow">Account center</p><h2>{tab === "profile" ? "Your profile" : tab === "notifications" ? "Notifications" : "Settings"}</h2></div><button className="icon-button" onClick={onClose} title="Close account center"><X size={18} /></button></header><nav className="account-tabs"><button className={tab === "profile" ? "selected" : ""} onClick={() => setTab("profile")}><Users size={15} />Profile</button><button className={tab === "notifications" ? "selected" : ""} onClick={() => setTab("notifications")}><Bell size={15} />Notifications</button><button className={tab === "settings" ? "selected" : ""} onClick={() => setTab("settings")}><Settings size={15} />Settings</button></nav>{message && <div className="modal-message">{message}</div>}{tab === "profile" && <form className="account-form" onSubmit={saveProfile}><label>First name<input value={profile.firstName} onChange={(event) => setProfile({ ...profile, firstName: event.target.value })} /></label><label>Last name<input value={profile.lastName} onChange={(event) => setProfile({ ...profile, lastName: event.target.value })} /></label><label>Email<input type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} /></label><div className="account-meta"><span>Role</span><b>{user.role?.replaceAll("_", " ")}</b></div><button className="primary-button" disabled={busy}>Save profile</button></form>}{tab === "notifications" && <div className="notification-view"><button className="text-button" onClick={readAll}>Mark all as read</button>{notifications.length === 0 ? <div className="empty-state small"><Bell size={25} /><b>No notifications</b><span>Important academic updates will appear here.</span></div> : <div className="notification-list">{notifications.map((item) => <article className={item.isRead ? "notification read" : "notification"} key={item.id}><div><b>{item.title}</b><p>{item.body}</p><span>{new Date(item.createdAt).toLocaleString()}</span></div>{!item.isRead && <i />}</article>)}</div>}</div>}{tab === "settings" && <form className="account-form" onSubmit={saveSettings}><label className="toggle-row"><span><b>Email notifications</b><small>Receive important compliance updates by email.</small></span><input type="checkbox" checked={settings.emailNotifications} onChange={(event) => setSettings({ ...settings, emailNotifications: event.target.checked })} /></label><label className="toggle-row"><span><b>In-app notifications</b><small>Show alerts and updates in the notification inbox.</small></span><input type="checkbox" checked={settings.inAppNotifications} onChange={(event) => setSettings({ ...settings, inAppNotifications: event.target.checked })} /></label><label>Digest frequency<select value={settings.digestFrequency} onChange={(event) => setSettings({ ...settings, digestFrequency: event.target.value })}><option>IMMEDIATE</option><option>DAILY</option><option>WEEKLY</option><option>NEVER</option></select></label><label>Timezone<input value={settings.timezone} onChange={(event) => setSettings({ ...settings, timezone: event.target.value })} /></label><button className="primary-button" disabled={busy}>Save settings</button></form>}</section></div>;
}

function ViewHeader({ eyebrow, title, action, onAction }) {
  return <div className="view-header"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>{action && <button className="primary-button compact" onClick={onAction}><Plus size={16} />{action}</button>}</div>;
}

function StudentsView() {
  const [students, setStudents] = useState([]); const [query, setQuery] = useState(""); const [message, setMessage] = useState("");
  useEffect(() => { api("/students").then((data) => setStudents(data.students || [])).catch((err) => setMessage(err.message)); }, []);
  const filtered = students.filter((student) => `${student.regNo} ${student.user?.firstName} ${student.user?.lastName} ${student.program?.name}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="content-view panel"><ViewHeader eyebrow="Academic records" title="Students" /><div className="view-toolbar"><div className="search-box"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search students" /></div><span className="record-count">{filtered.length} students</span></div>{message && <div className="notice">{message}</div>}<div className="table-wrap"><table><thead><tr><th>Student</th><th>Registration</th><th>Programme</th><th>Year</th><th>Status</th><th>Risk</th></tr></thead><tbody>{filtered.map((student) => { const record = student.compliance?.[0]; return <tr key={student.id}><td><b>{student.user?.firstName} {student.user?.lastName}</b><span>{student.user?.email}</span></td><td>{student.regNo}</td><td>{student.program?.code || "-"}</td><td>{student.yearOfStudy}</td><td><span className={`status ${String(record?.status || "PENDING").toLowerCase()}`}>{record?.status?.replaceAll("_", " ") || "PENDING"}</span></td><td><RiskPill value={record?.riskLevel || "LOW"} /></td></tr>; })}</tbody></table>{!filtered.length && <div className="empty-state"><Users size={28} /><b>No students found</b><span>Registered students will appear here.</span></div>}</div></section>;
}

function RulesView() {
  const [rules, setRules] = useState([]); const [message, setMessage] = useState("");
  useEffect(() => { api("/compliance/rules").then((data) => setRules(data.rules || [])).catch((err) => setMessage(err.message)); }, []);
  async function save(rule) { try { const data = await api(`/compliance/rules/${rule.id}`, { method: "PATCH", body: JSON.stringify({ enabled: rule.enabled, threshold: rule.threshold }) }); setRules((items) => items.map((item) => item.id === rule.id ? data.rule : item)); setMessage("Rule saved."); } catch (err) { setMessage(err.message); } }
  return <section className="content-view panel"><ViewHeader eyebrow="Governance" title="Rules & thresholds" /><p className="muted view-description">These rules drive compliance evaluation. Changes are audited.</p>{message && <div className="notice">{message}</div>}<div className="rule-list">{rules.map((rule) => <article className="rule-row" key={rule.id}><div><b>{rule.name}</b><p>{rule.description}</p><code>{rule.key}</code></div><div className="rule-controls"><label className="inline-toggle"><input type="checkbox" checked={rule.enabled} onChange={(event) => setRules((items) => items.map((item) => item.id === rule.id ? { ...item, enabled: event.target.checked } : item))} />Enabled</label>{rule.threshold !== null && <input className="threshold-input" type="number" value={rule.threshold} onChange={(event) => setRules((items) => items.map((item) => item.id === rule.id ? { ...item, threshold: Number(event.target.value) } : item))} />}{<button className="small-button" onClick={() => save(rule)}>Save</button>}</div></article>)}</div></section>;
}

function UsersView() {
  const [users, setUsers] = useState([]); const [showForm, setShowForm] = useState(false); const [message, setMessage] = useState(""); const [form, setForm] = useState({ firstName: "", lastName: "", email: "", password: "", role: "ACADEMIC_OFFICER", departmentId: "" });
  function update(key) { return (event) => setForm({ ...form, [key]: event.target.value }); }
  async function load() { try { const data = await api("/users"); setUsers(data.users || []); } catch (err) { setMessage(err.message); } }
  useEffect(() => { load(); }, []);
  async function create(event) { event.preventDefault(); try { await api("/users", { method: "POST", body: JSON.stringify(form) }); setShowForm(false); setMessage("User created."); await load(); } catch (err) { setMessage(err.message); } }
  return <section className="content-view panel"><ViewHeader eyebrow="Access control" title="Users & staff" action="Add user" onAction={() => setShowForm(!showForm)} />{message && <div className="notice">{message}</div>}{showForm && <form className="inline-form" onSubmit={create}><input required placeholder="First name" value={form.firstName} onChange={update("firstName")} /><input required placeholder="Last name" value={form.lastName} onChange={update("lastName")} /><input required type="email" placeholder="Email" value={form.email} onChange={update("email")} /><input required minLength="8" placeholder="Temporary password" value={form.password} onChange={update("password")} /><select value={form.role} onChange={update("role")}><option value="ACADEMIC_OFFICER">Academic officer</option><option value="LECTURER">Lecturer</option><option value="ADMIN">Administrator</option><option value="STUDENT">Student</option></select><button className="primary-button compact">Create</button></form>}<div className="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead><tbody>{users.map((item) => <tr key={item.id}><td><b>{item.firstName} {item.lastName}</b></td><td>{item.email}</td><td>{item.role?.replaceAll("_", " ")}</td><td><span className={`status ${item.isActive ? "compliant" : "non_compliant"}`}>{item.isActive ? "Active" : "Inactive"}</span></td></tr>)}</tbody></table></div></section>;
}

function AcademicView() {
  const [courses, setCourses] = useState([]); const [offerings, setOfferings] = useState([]); const [message, setMessage] = useState(""); const [showForm, setShowForm] = useState(false); const [form, setForm] = useState({ code: "", title: "", credits: 3, departmentId: "dept-demo", programId: "program-demo", isCore: true });
  useEffect(() => { Promise.all([api("/org/courses"), api("/org/offerings")]).then(([courseData, offeringData]) => { setCourses(courseData.courses || []); setOfferings(offeringData.offerings || []); }).catch((err) => setMessage(err.message)); }, []);
  async function create(event) { event.preventDefault(); try { const data = await api("/org/courses", { method: "POST", body: JSON.stringify({ ...form, credits: Number(form.credits) }) }); setCourses((items) => [...items, data.course]); setShowForm(false); setMessage("Course created."); } catch (err) { setMessage(err.message); } }
  return <section className="content-view panel"><ViewHeader eyebrow="Academic operations" title="Courses & offerings" action="Add course" onAction={() => setShowForm(!showForm)} /><p className="muted view-description">Monitor the catalogue and delivery instances used for attendance, assessments, and grades.</p>{message && <div className="notice">{message}</div>}{showForm && <form className="inline-form course-form" onSubmit={create}><input required placeholder="Course code" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} /><input required placeholder="Course title" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /><input required type="number" min="1" max="12" placeholder="Credits" value={form.credits} onChange={(event) => setForm({ ...form, credits: event.target.value })} /><input required placeholder="Department ID" value={form.departmentId} onChange={(event) => setForm({ ...form, departmentId: event.target.value })} /><button className="primary-button compact">Create</button></form>}<div className="academic-summary"><article><BookOpen size={18} /><b>{courses.length}</b><span>Courses in catalogue</span></article><article><ClipboardCheck size={18} /><b>{offerings.length}</b><span>Active offerings</span></article></div><div className="table-wrap"><table><thead><tr><th>Course</th><th>Title</th><th>Credits</th><th>Type</th></tr></thead><tbody>{courses.map((course) => <tr key={course.id}><td><b>{course.code}</b></td><td>{course.title}</td><td>{course.credits}</td><td>{course.isCore ? "Core" : "Elective"}</td></tr>)}</tbody></table>{!courses.length && <div className="empty-state"><BookOpen size={28} /><b>No courses yet</b><span>Add courses from the organisation management API.</span></div>}</div></section>;
}

function AuditView() {
  const [logs, setLogs] = useState([]); const [message, setMessage] = useState("");
  useEffect(() => { api("/account/audit").then((data) => setLogs(data.logs || [])).catch((err) => setMessage(err.message)); }, []);
  return <section className="content-view panel"><ViewHeader eyebrow="Governance" title="Audit log" /><p className="muted view-description">A chronological record of authentication, academic, compliance, and account changes.</p>{message && <div className="notice">{message}</div>}<div className="table-wrap"><table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Entity</th><th>IP</th></tr></thead><tbody>{logs.map((log) => <tr key={log.id}><td>{new Date(log.createdAt).toLocaleString()}</td><td>{log.user ? `${log.user.firstName} ${log.user.lastName}` : "System"}</td><td><b>{log.action}</b></td><td>{log.entity || "-"}</td><td>{log.ip || "-"}</td></tr>)}</tbody></table></div></section>;
}

function ReportsView({ records }) {
  function download() { const rows = records.map((record) => ({ student: `${record.student?.user?.firstName || ""} ${record.student?.user?.lastName || ""}`, registration: record.student?.regNo, programme: record.student?.program?.code, status: record.status, risk: record.riskLevel, compliance: record.compliancePct })); const csv = [Object.keys(rows[0] || { student: "", registration: "", programme: "", status: "", risk: "", compliance: "" }).join(","), ...rows.map((row) => Object.values(row).map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`).join(","))].join("\n"); const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); const link = document.createElement("a"); link.href = url; link.download = "compliance-report.csv"; link.click(); URL.revokeObjectURL(url); }
  return <section className="content-view panel"><ViewHeader eyebrow="Evidence & reporting" title="Reports" action="Export CSV" onAction={download} /><p className="muted view-description">Download the current compliance register for review, meetings, and follow-up.</p><div className="report-card"><FileDown size={24} /><div><b>Current compliance register</b><span>{records.length} student records available</span></div><button className="small-button" onClick={download}>Download</button></div></section>;
}

function StudentHome({ user, onLogout }) {
  const [student, setStudent] = useState(null); const [message, setMessage] = useState("");
  useEffect(() => { api(`/students/${user.student?.id}`).then((data) => setStudent(data.student)).catch((err) => setMessage(err.message)); }, [user.student?.id]);
  const record = student?.compliance?.[0];
  return <div className="app-shell"><aside className="sidebar"><div className="sidebar-brand"><div className="brand-mark"><GraduationCap size={20} /></div><span>Academic<br /><b>Compliance</b></span></div><nav><button className="nav-item active"><ClipboardCheck size={18} />My academic record</button><button className="nav-item"><Bell size={18} />My alerts</button></nav><div className="sidebar-bottom"><div className="profile"><div className="avatar">{user.firstName?.[0]}{user.lastName?.[0]}</div><div><b>{user.firstName} {user.lastName}</b><span>Student</span></div></div><button className="logout" onClick={onLogout}><LogOut size={16} />Sign out</button></div></aside><main className="main-content"><header className="topbar"><div><p className="eyebrow">Student workspace</p><h1>My academic record</h1></div><div className="top-actions"><span className="live-dot">Private record</span></div></header>{message && <div className="notice">{message}</div>}{!student ? <div className="empty-state">Loading your academic record...</div> : <><section className="welcome-row"><div><h2>Welcome, {student.user?.firstName}.</h2><p className="muted">{student.regNo} · {student.program?.name}</p></div></section><section className="stats-grid"><Stat label="Compliance" value={`${Math.round(record?.compliancePct || 0)}%`} tone="green" note={record?.status?.replaceAll("_", " ") || "Awaiting evaluation"} /><Stat label="Attendance" value={`${Math.round(record?.attendancePct || 0)}%`} tone="amber" note="Recorded attendance" /><Stat label="Semester GPA" value={record?.gpa?.toFixed(2) || "-"} tone="ink" note="Current academic period" /><Stat label="Risk level" value={record?.riskLevel || "LOW"} tone={record?.riskLevel === "HIGH" ? "red" : "green"} note="Advisory classification" /></section><section className="workspace-grid"><div className="records-panel panel"><div className="panel-heading"><div><p className="eyebrow">Enrolled courses</p><h2>Academic progress</h2></div></div><div className="table-wrap"><table><thead><tr><th>Course</th><th>Semester</th><th>Grade</th><th>Attendance sessions</th></tr></thead><tbody>{student.enrollments?.map((enrollment) => <tr key={enrollment.id}><td><b>{enrollment.offering?.course?.code}</b><span>{enrollment.offering?.course?.title}</span></td><td>{enrollment.offering?.semester?.name}</td><td>{enrollment.grade?.letter || "Pending"}</td><td>{enrollment.attendance?.length || 0}</td></tr>)}</tbody></table></div></div><aside className="alerts-panel panel"><div className="panel-heading"><div><p className="eyebrow">Academic alerts</p><h2>What needs attention</h2></div><span className="alert-count">{student.alerts?.length || 0}</span></div>{student.alerts?.length ? <div className="alert-list">{student.alerts.map((alert) => <article className="alert-item" key={alert.id}><div className="alert-icon"><AlertTriangle size={16} /></div><div><b>{alert.type.replaceAll("_", " ")}</b><p>{alert.message}</p></div></article>)}</div> : <div className="empty-state small"><Check size={25} /><b>No open alerts</b><span>Keep meeting your academic requirements.</span></div>}</aside></section></>}</main></div>;
}

function LecturerHome({ user, onLogout }) {
  const [offerings, setOfferings] = useState([]); const [students, setStudents] = useState([]); const [message, setMessage] = useState("");
  useEffect(() => { Promise.all([api("/academic/offerings"), api("/students")]).then(([offeringData, studentData]) => { setOfferings(offeringData.offerings || []); setStudents(studentData.students || []); }).catch((err) => setMessage(err.message)); }, []);
  return <div className="app-shell"><aside className="sidebar"><div className="sidebar-brand"><div className="brand-mark"><GraduationCap size={20} /></div><span>Academic<br /><b>Compliance</b></span></div><nav><button className="nav-item active"><BookOpen size={18} />My course offerings</button><button className="nav-item"><Users size={18} />My students</button></nav><div className="sidebar-bottom"><div className="profile"><div className="avatar">{user.firstName?.[0]}{user.lastName?.[0]}</div><div><b>{user.firstName} {user.lastName}</b><span>Lecturer</span></div></div><button className="logout" onClick={onLogout}><LogOut size={16} />Sign out</button></div></aside><main className="main-content"><header className="topbar"><div><p className="eyebrow">Teaching workspace</p><h1>My course offerings</h1></div><div className="top-actions"><span className="live-dot">Teaching view</span></div></header>{message && <div className="notice">{message}</div>}<section className="stats-grid"><Stat label="Course offerings" value={offerings.length} tone="green" note="Assigned to you" /><Stat label="Students" value={students.length} tone="ink" note="Across your offerings" /><Stat label="Pending marks" value="-" tone="amber" note="Requires course review" /><Stat label="Alerts" value="-" tone="red" note="Student risk alerts" /></section><section className="content-view panel"><ViewHeader eyebrow="Teaching load" title="Assigned offerings" /><div className="table-wrap"><table><thead><tr><th>Course</th><th>Semester</th><th>Enrolled</th><th>Assessments</th></tr></thead><tbody>{offerings.map((offering) => <tr key={offering.id}><td><b>{offering.course?.code}</b><span>{offering.course?.title}</span></td><td>{offering.semester?.name}</td><td>{offering._count?.enrollments || 0}</td><td>{offering._count?.assessments || 0}</td></tr>)}</tbody></table>{!offerings.length && <div className="empty-state"><BookOpen size={28} /><b>No offerings assigned</b><span>Course offerings assigned to you will appear here.</span></div>}</div></section></main></div>;
}

function Dashboard({ user, onLogout }) {
  const [records, setRecords] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("ALL");
  const [status, setStatus] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [view, setView] = useState("desk");

  async function load() {
    setLoading(true);
    try {
      const [recordData, alertData] = await Promise.all([api("/compliance/records"), api("/compliance/alerts")]);
      setRecords(recordData.records || []);
      setAlerts(alertData.alerts || []);
      setMessage("");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => records.filter((record) => {
    const name = `${record.student?.user?.firstName || ""} ${record.student?.user?.lastName || ""} ${record.student?.regNo || ""}`.toLowerCase();
    return name.includes(query.toLowerCase()) && (risk === "ALL" || record.riskLevel === risk) && (status === "ALL" || record.status === status);
  }), [records, query, risk, status]);

  const counts = useMemo(() => ({
    compliant: records.filter((r) => r.status === "COMPLIANT").length,
    risk: records.filter((r) => r.status === "AT_RISK" || r.riskLevel === "MEDIUM").length,
    nonCompliant: records.filter((r) => r.status === "NON_COMPLIANT" || r.riskLevel === "HIGH").length,
    total: records.length,
  }), [records]);

  async function recompute() {
    setBusy(true);
    try { await api("/compliance/recompute", { method: "POST", body: "{}" }); await load(); setMessage("Compliance records refreshed."); }
    catch (err) { setMessage(err.message); }
    finally { setBusy(false); }
  }

  async function resolveAlert(id) {
    try { await api(`/compliance/alerts/${id}/resolve`, { method: "POST" }); setAlerts((items) => items.filter((item) => item.id !== id)); }
    catch (err) { setMessage(err.message); }
  }

  async function review(record, reviewStatus) {
    try {
      await api(`/compliance/records/${record.id}/review`, { method: "PATCH", body: JSON.stringify({ reviewStatus }) });
      setRecords((items) => items.map((item) => item.id === record.id ? { ...item, reviewStatus } : item));
    } catch (err) { setMessage(err.message); }
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="sidebar-brand"><div className="brand-mark"><GraduationCap size={20} /></div><span>Academic<br /><b>Compliance</b></span></div>
      <nav><button className={`nav-item ${view === "desk" ? "active" : ""}`} onClick={() => setView("desk")}><ClipboardCheck size={18} />Compliance desk</button><button className={`nav-item ${view === "students" ? "active" : ""}`} onClick={() => setView("students")}><Users size={18} />Students</button><button className={`nav-item ${view === "academic" ? "active" : ""}`} onClick={() => setView("academic")}><BookOpen size={18} />Courses & offerings</button><button className={`nav-item ${view === "rules" ? "active" : ""}`} onClick={() => setView("rules")}><SlidersHorizontal size={18} />Rules & thresholds</button><button className={`nav-item ${view === "users" ? "active" : ""}`} onClick={() => setView("users")}><Settings size={18} />Users & staff</button><button className={`nav-item ${view === "reports" ? "active" : ""}`} onClick={() => setView("reports")}><FileDown size={18} />Reports</button><button className={`nav-item ${view === "audit" ? "active" : ""}`} onClick={() => setView("audit")}><ClipboardCheck size={18} />Audit log</button></nav>
      <div className="sidebar-bottom"><div className="profile"><div className="avatar">{user.firstName?.[0]}{user.lastName?.[0]}</div><div><b>{user.firstName} {user.lastName}</b><span>{user.role?.replace("_", " ")}</span></div></div><button className="logout" onClick={onLogout}><LogOut size={16} />Sign out</button></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div><p className="eyebrow">Institutional overview</p><h1>{{ desk: "Compliance desk", students: "Students", academic: "Courses & offerings", rules: "Rules & thresholds", users: "Users & staff", reports: "Reports", audit: "Audit log" }[view]}</h1></div><div className="top-actions"><span className="live-dot">Live monitoring</span><button className="icon-button" onClick={() => setAccountOpen(true)} title="Account center"><Settings size={18} /></button><button className="icon-button" onClick={load} title="Refresh data"><RefreshCw size={18} /></button></div></header>
      {view === "desk" ? <>
      <section className="welcome-row"><div><h2>Good morning, {user.firstName}.</h2><p className="muted">Review the students who need an informed decision today.</p></div><button className="primary-button compact" onClick={recompute} disabled={busy}><Sparkles size={16} />{busy ? "Refreshing..." : "Recompute compliance"}</button></section>
      {message && <div className="notice"><AlertTriangle size={17} />{message}</div>}
      <section className="stats-grid"><Stat label="Students monitored" value={counts.total} tone="ink" note="Across current records" /><Stat label="Compliant" value={counts.compliant} tone="green" note="Meeting current rules" /><Stat label="Needs attention" value={counts.risk} tone="amber" note="Medium or at risk" /><Stat label="Non-compliant" value={counts.nonCompliant} tone="red" note="Requires intervention" /></section>
      <section className="workspace-grid">
        <div className="records-panel panel"><div className="panel-heading"><div><p className="eyebrow">Student register</p><h2>Risk overview</h2></div><span className="record-count">{filtered.length} records</span></div><div className="filters"><div className="search-box"><Search size={17} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search name or registration number" /></div><select value={risk} onChange={(e) => setRisk(e.target.value)}><option value="ALL">All risk levels</option><option value="LOW">Low risk</option><option value="MEDIUM">Medium risk</option><option value="HIGH">High risk</option></select><select value={status} onChange={(e) => setStatus(e.target.value)}><option value="ALL">All statuses</option><option value="COMPLIANT">Compliant</option><option value="PARTIALLY_COMPLIANT">Partial</option><option value="AT_RISK">At risk</option><option value="NON_COMPLIANT">Non-compliant</option></select></div>{loading ? <div className="empty-state">Loading compliance records...</div> : filtered.length === 0 ? <div className="empty-state"><ClipboardCheck size={28} /><b>No records match this view</b><span>Run a recomputation after loading academic data.</span></div> : <div className="table-wrap"><table><thead><tr><th>Student</th><th>Programme</th><th>Status</th><th>Risk</th><th>Compliance</th><th>Review</th></tr></thead><tbody>{filtered.map((record) => <tr key={record.id}><td><b>{record.student?.user?.firstName} {record.student?.user?.lastName}</b><span>{record.student?.regNo}</span></td><td>{record.student?.program?.code || "-"}</td><td><span className={`status ${String(record.status).toLowerCase()}`}>{record.status?.replaceAll("_", " ")}</span></td><td><RiskPill value={record.riskLevel} /></td><td><div className="progress-cell"><b>{Math.round(record.compliancePct || 0)}%</b><div className="progress"><i style={{ width: `${record.compliancePct || 0}%` }} /></div></div></td><td>{record.reviewStatus === "APPROVED" ? <span className="reviewed"><Check size={14} />Approved</span> : <div className="review-actions"><button title="Approve" onClick={() => review(record, "APPROVED")}><Check size={14} /></button><button title="Flag" onClick={() => review(record, "FLAGGED")}><X size={14} /></button></div>}</td></tr>)}</tbody></table></div>}</div>
        <aside className="alerts-panel panel"><div className="panel-heading"><div><p className="eyebrow">Action queue</p><h2>Open alerts</h2></div><span className="alert-count">{alerts.length}</span></div>{alerts.length === 0 ? <div className="empty-state small"><Check size={25} /><b>Nothing urgent</b><span>Open alerts will appear here.</span></div> : <div className="alert-list">{alerts.slice(0, 7).map((alert) => <article className="alert-item" key={alert.id}><div className={`alert-icon ${alert.severity}`}><AlertTriangle size={16} /></div><div><b>{alert.student?.user ? `${alert.student.user.firstName} ${alert.student.user.lastName}` : "Student alert"}</b><p>{alert.message}</p><button onClick={() => resolveAlert(alert.id)}>Mark handled <ArrowUpRight size={13} /></button></div></article>)}</div>}</aside>
      </section></> : view === "students" ? <StudentsView /> : view === "academic" ? <AcademicView /> : view === "rules" ? <RulesView /> : view === "users" ? <UsersView /> : view === "audit" ? <AuditView /> : <ReportsView records={records} />}
      <AcademicAgent />
      {accountOpen && <AccountCenter user={user} onClose={() => setAccountOpen(false)} />}
    </main>
  </div>;
}

function App() {
  const [user, setUser] = useState(null);
  if (!user) return <Login onLogin={setUser} />;
  if (user.role === "STUDENT") return <StudentHome user={user} onLogout={() => { api("/auth/logout", { method: "POST" }).catch(() => {}); setUser(null); }} />;
  if (user.role === "LECTURER") return <LecturerHome user={user} onLogout={() => { api("/auth/logout", { method: "POST" }).catch(() => {}); setUser(null); }} />;
  return <Dashboard user={user} onLogout={() => { api("/auth/logout", { method: "POST" }).catch(() => {}); setUser(null); }} />;
}

export default App;

createRoot(document.getElementById("root")).render(<App />);
