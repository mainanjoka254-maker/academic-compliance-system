import { FormEvent, useEffect, useState } from 'react'
import api from '@/services/api'

type Course = { id: number; code: string; name: string }
type Faculty = { id: number; code: string; name: string }
type Department = { id: number; code: string; name: string; faculty_id: number | null }
type AcademicProgram = {
  id: number
  code: string
  name: string
  faculty_id: number | null
  department_id: number | null
  award_level: string | null
}
type LecturerRecord = {
  id: number
  user_id: number
  staff_number: string
  full_name: string
  email: string
  phone: string | null
  title: string | null
  specialization: string | null
  department_id: number | null
  is_active: boolean
  courses: Course[]
  programs: AcademicProgram[]
}
type ComplianceReport = {
  compliance_status: string
  assigned_courses: number
  course_submissions: number
  pending_verification: number
  rejected_submissions: number
  courses_without_submission: Course[]
  explanation: string
}

function getErrorMessage(error: unknown, fallback: string) {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof error.response === 'object' &&
    error.response !== null &&
    'data' in error.response &&
    typeof error.response.data === 'object' &&
    error.response.data !== null &&
    'detail' in error.response.data &&
    typeof error.response.data.detail === 'string'
  ) {
    return error.response.data.detail
  }
  return fallback
}

export default function LecturerManagementPanel() {
  const [lecturers, setLecturers] = useState<LecturerRecord[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [faculties, setFaculties] = useState<Faculty[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [programs, setPrograms] = useState<AcademicProgram[]>([])
  const [selectedId, setSelectedId] = useState<number | ''>('')
  const [selectedCourses, setSelectedCourses] = useState<number[]>([])
  const [selectedPrograms, setSelectedPrograms] = useState<number[]>([])
  const [report, setReport] = useState<ComplianceReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
    staff_number: '',
    title: '',
    specialization: '',
    department_id: '',
  })
  const [facultyForm, setFacultyForm] = useState({ name: '', code: '' })
  const [departmentForm, setDepartmentForm] = useState({ name: '', code: '', faculty_id: '' })
  const [programForm, setProgramForm] = useState({
    name: '',
    code: '',
    award_level: '',
    faculty_id: '',
    department_id: '',
  })

  async function loadData() {
    setLoading(true)
    setError('')
    try {
      const [lecturerResponse, courseResponse, facultyResponse, departmentResponse, programResponse] = await Promise.all([
        api.get<LecturerRecord[]>('/lecturers'),
        api.get<Course[]>('/courses'),
        api.get<Faculty[]>('/academic-structure/faculties'),
        api.get<Department[]>('/academic-structure/departments'),
        api.get<AcademicProgram[]>('/academic-structure/programmes'),
      ])
      setLecturers(lecturerResponse.data)
      setCourses(courseResponse.data)
      setFaculties(facultyResponse.data)
      setDepartments(departmentResponse.data)
      setPrograms(programResponse.data)
      setSelectedId((current) =>
        current && lecturerResponse.data.some((item) => item.id === current)
          ? current
          : lecturerResponse.data[0]?.id ?? '',
      )
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Lecturer data could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const selectedLecturer = lecturers.find((lecturer) => lecturer.id === selectedId)

  useEffect(() => {
    setSelectedCourses(selectedLecturer?.courses.map((course) => course.id) ?? [])
    setSelectedPrograms(selectedLecturer?.programs.map((program) => program.id) ?? [])
    setReport(null)
  }, [selectedId, lecturers])

  async function createLecturer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const response = await api.post<LecturerRecord>('/lecturers', {
        ...form,
        department_id: form.department_id ? Number(form.department_id) : undefined,
        title: form.title || undefined,
        specialization: form.specialization || undefined,
      })
      setForm({ email: '', password: '', full_name: '', staff_number: '', title: '', specialization: '', department_id: '' })
      setNotice('Lecturer account created.')
      await loadData()
      setSelectedId(response.data.id)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Lecturer account could not be created.'))
    } finally {
      setSaving(false)
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedLecturer) return
    const formData = new FormData(event.currentTarget)
    const departmentId = String(formData.get('department_id') ?? '')
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await api.patch(`/lecturers/${selectedLecturer.id}`, {
        full_name: String(formData.get('full_name') ?? ''),
        phone: String(formData.get('phone') ?? '') || null,
        title: String(formData.get('title') ?? '') || null,
        specialization: String(formData.get('specialization') ?? '') || null,
        department_id: departmentId ? Number(departmentId) : null,
        is_active: formData.get('is_active') === 'on',
      })
      setNotice('Lecturer profile updated.')
      await loadData()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Lecturer profile could not be updated.'))
    } finally {
      setSaving(false)
    }
  }

  async function saveCourses() {
    if (!selectedLecturer) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await api.put(`/lecturers/${selectedLecturer.id}/courses`, { course_ids: selectedCourses })
      setNotice('Teaching allocation saved.')
      await loadData()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Teaching allocation could not be saved.'))
    } finally {
      setSaving(false)
    }
  }

  async function savePrograms() {
    if (!selectedLecturer) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await api.put(`/lecturers/${selectedLecturer.id}/programs`, { program_ids: selectedPrograms })
      setNotice('Academic programme assignments saved.')
      await loadData()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Academic programme assignments could not be saved.'))
    } finally {
      setSaving(false)
    }
  }

  async function createFaculty(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await api.post('/academic-structure/faculties', facultyForm)
      setFacultyForm({ name: '', code: '' })
      setNotice('Faculty created.')
      await loadData()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Faculty could not be created.'))
    } finally {
      setSaving(false)
    }
  }

  async function createDepartment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await api.post('/academic-structure/departments', {
        ...departmentForm,
        faculty_id: departmentForm.faculty_id ? Number(departmentForm.faculty_id) : undefined,
      })
      setDepartmentForm({ name: '', code: '', faculty_id: '' })
      setNotice('Department created.')
      await loadData()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Department could not be created.'))
    } finally {
      setSaving(false)
    }
  }

  async function createProgram(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await api.post('/academic-structure/programmes', {
        ...programForm,
        award_level: programForm.award_level || undefined,
        faculty_id: programForm.faculty_id ? Number(programForm.faculty_id) : undefined,
        department_id: programForm.department_id ? Number(programForm.department_id) : undefined,
      })
      setProgramForm({ name: '', code: '', award_level: '', faculty_id: '', department_id: '' })
      setNotice('Academic programme created.')
      await loadData()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Academic programme could not be created.'))
    } finally {
      setSaving(false)
    }
  }

  async function loadComplianceReport() {
    if (!selectedLecturer) return
    setSaving(true)
    setError('')
    try {
      const response = await api.get<ComplianceReport>(`/lecturers/${selectedLecturer.id}/compliance`)
      setReport(response.data)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Lecturer compliance report could not be loaded.'))
    } finally {
      setSaving(false)
    }
  }

  async function downloadReport() {
    if (!selectedLecturer) return
    setSaving(true)
    setError('')
    try {
      const response = await api.get(`/lecturers/${selectedLecturer.id}/report.csv`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(response.data)
      const link = window.document.createElement('a')
      link.href = url
      link.download = `lecturer-${selectedLecturer.id}-compliance.csv`
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Lecturer report could not be downloaded.'))
    } finally {
      setSaving(false)
    }
  }

  function toggleCourse(courseId: number) {
    setSelectedCourses((current) =>
      current.includes(courseId)
        ? current.filter((id) => id !== courseId)
        : [...current, courseId],
    )
  }

  function toggleProgram(programId: number) {
    setSelectedPrograms((current) =>
      current.includes(programId)
        ? current.filter((id) => id !== programId)
        : [...current, programId],
    )
  }

  return (
    <section className="space-y-5 rounded-xl bg-white p-5 shadow">
      <div>
        <h2 className="text-lg font-semibold text-navy-900">Lecturer Management</h2>
        <p className="text-sm text-gray-500">Manage lecturer accounts, departments, teaching allocations, and submission compliance.</p>
      </div>
      {error && <p className="text-sm text-red-700" role="alert">{error}</p>}
      {notice && <p className="text-sm text-green-700" role="status">{notice}</p>}

      <details className="rounded border p-4">
        <summary className="cursor-pointer font-medium">Manage faculties, departments, and academic programmes</summary>
        <div className="mt-4 grid gap-5 lg:grid-cols-3">
          <form className="space-y-2" onSubmit={createFaculty}>
            <h3 className="font-medium">Create faculty</h3>
            <input aria-label="Faculty name" className="w-full rounded border px-3 py-2" placeholder="Faculty name" required value={facultyForm.name} onChange={(event) => setFacultyForm({ ...facultyForm, name: event.target.value })} />
            <input aria-label="Faculty code" className="w-full rounded border px-3 py-2" placeholder="Faculty code" required value={facultyForm.code} onChange={(event) => setFacultyForm({ ...facultyForm, code: event.target.value })} />
            <button className="rounded border px-3 py-2" disabled={saving}>Create faculty</button>
          </form>
          <form className="space-y-2" onSubmit={createDepartment}>
            <h3 className="font-medium">Create department</h3>
            <input aria-label="Department name" className="w-full rounded border px-3 py-2" placeholder="Department name" required value={departmentForm.name} onChange={(event) => setDepartmentForm({ ...departmentForm, name: event.target.value })} />
            <input aria-label="Department code" className="w-full rounded border px-3 py-2" placeholder="Department code" required value={departmentForm.code} onChange={(event) => setDepartmentForm({ ...departmentForm, code: event.target.value })} />
            <select aria-label="Department faculty" className="w-full rounded border px-3 py-2" value={departmentForm.faculty_id} onChange={(event) => setDepartmentForm({ ...departmentForm, faculty_id: event.target.value })}>
              <option value="">No faculty</option>
              {faculties.map((faculty) => <option key={faculty.id} value={faculty.id}>{faculty.code} - {faculty.name}</option>)}
            </select>
            <button className="rounded border px-3 py-2" disabled={saving}>Create department</button>
          </form>
          <form className="space-y-2" onSubmit={createProgram}>
            <h3 className="font-medium">Create academic programme</h3>
            <input aria-label="Programme name" className="w-full rounded border px-3 py-2" placeholder="Programme name" required value={programForm.name} onChange={(event) => setProgramForm({ ...programForm, name: event.target.value })} />
            <input aria-label="Programme code" className="w-full rounded border px-3 py-2" placeholder="Programme code" required value={programForm.code} onChange={(event) => setProgramForm({ ...programForm, code: event.target.value })} />
            <input aria-label="Award level" className="w-full rounded border px-3 py-2" placeholder="Award level (optional)" value={programForm.award_level} onChange={(event) => setProgramForm({ ...programForm, award_level: event.target.value })} />
            <select aria-label="Programme faculty" className="w-full rounded border px-3 py-2" value={programForm.faculty_id} onChange={(event) => setProgramForm({ ...programForm, faculty_id: event.target.value })}>
              <option value="">No faculty</option>
              {faculties.map((faculty) => <option key={faculty.id} value={faculty.id}>{faculty.code} - {faculty.name}</option>)}
            </select>
            <select aria-label="Programme department" className="w-full rounded border px-3 py-2" value={programForm.department_id} onChange={(event) => setProgramForm({ ...programForm, department_id: event.target.value })}>
              <option value="">No department</option>
              {departments.map((department) => <option key={department.id} value={department.id}>{department.code} - {department.name}</option>)}
            </select>
            <button className="rounded border px-3 py-2" disabled={saving}>Create academic programme</button>
          </form>
        </div>
      </details>

      <form className="grid gap-3 md:grid-cols-3" onSubmit={createLecturer}>
        <h3 className="font-medium md:col-span-3">Register lecturer</h3>
        <input className="rounded border px-3 py-2" placeholder="Full name" aria-label="New lecturer full name" minLength={2} required value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} />
        <input className="rounded border px-3 py-2" type="email" placeholder="Email" aria-label="New lecturer email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
        <input className="rounded border px-3 py-2" placeholder="Staff number" aria-label="New lecturer staff number" required value={form.staff_number} onChange={(event) => setForm({ ...form, staff_number: event.target.value })} />
        <input className="rounded border px-3 py-2" type="password" placeholder="Initial password" aria-label="New lecturer password" minLength={8} required value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
        <select aria-label="New lecturer department" className="rounded border px-3 py-2" value={form.department_id} onChange={(event) => setForm({ ...form, department_id: event.target.value })}>
          <option value="">No department</option>
          {departments.map((department) => <option key={department.id} value={department.id}>{department.code} - {department.name}</option>)}
        </select>
        <input className="rounded border px-3 py-2" placeholder="Title (optional)" aria-label="New lecturer title" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
        <input className="rounded border px-3 py-2" placeholder="Specialization (optional)" aria-label="New lecturer specialization" value={form.specialization} onChange={(event) => setForm({ ...form, specialization: event.target.value })} />
        <button className="rounded bg-blue-700 px-4 py-2 text-white disabled:opacity-50 md:col-span-3" disabled={saving}>
          {saving ? 'Saving...' : 'Create lecturer account'}
        </button>
      </form>

      <div className="border-t pt-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Lecturer record
          <select
            className="max-w-xl rounded border px-3 py-2"
            value={selectedId}
            onChange={(event) => setSelectedId(event.target.value ? Number(event.target.value) : '')}
          >
            {lecturers.length === 0 && <option value="">No lecturers registered</option>}
            {lecturers.map((lecturer) => (
              <option key={lecturer.id} value={lecturer.id}>
                {lecturer.staff_number} - {lecturer.full_name} ({lecturer.is_active ? 'active' : 'inactive'})
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading lecturer records...</p>
      ) : selectedLecturer ? (
        <>
          <form className="grid gap-3 md:grid-cols-2" onSubmit={saveProfile}>
            <h3 className="font-medium md:col-span-2">Edit lecturer profile</h3>
            <input className="rounded border px-3 py-2" name="full_name" aria-label="Lecturer full name" required defaultValue={selectedLecturer.full_name} />
            <input className="rounded border px-3 py-2" name="phone" aria-label="Lecturer phone" defaultValue={selectedLecturer.phone ?? ''} />
            <input className="rounded border px-3 py-2" name="title" aria-label="Lecturer title" defaultValue={selectedLecturer.title ?? ''} />
            <input className="rounded border px-3 py-2" name="specialization" aria-label="Lecturer specialization" defaultValue={selectedLecturer.specialization ?? ''} />
            <select className="rounded border px-3 py-2" name="department_id" aria-label="Lecturer department" defaultValue={selectedLecturer.department_id ?? ''}>
              <option value="">No department</option>
              {departments.map((department) => <option key={department.id} value={department.id}>{department.code} - {department.name}</option>)}
            </select>
            <label className="flex items-center gap-2 text-sm">
              <input name="is_active" type="checkbox" defaultChecked={selectedLecturer.is_active} />
              Account active
            </label>
            <button className="rounded border px-4 py-2 disabled:opacity-50 md:col-span-2" disabled={saving}>
              Save lecturer profile
            </button>
          </form>

          <div className="space-y-3 border-t pt-4">
            <h3 className="font-medium">Teaching allocation</h3>
            {courses.length === 0 ? (
              <p className="text-sm text-gray-500">No courses are available for this institution.</p>
            ) : (
              <div className="grid gap-2 md:grid-cols-2">
                {courses.map((course) => (
                  <label className="flex items-center gap-2 text-sm" key={course.id}>
                    <input
                      type="checkbox"
                      checked={selectedCourses.includes(course.id)}
                      onChange={() => toggleCourse(course.id)}
                    />
                    {course.code} - {course.name}
                  </label>
                ))}
              </div>
            )}
            <button className="rounded border px-4 py-2 disabled:opacity-50" type="button" disabled={saving} onClick={() => void saveCourses()}>
              Save teaching allocation
            </button>
          </div>

          <div className="space-y-3 border-t pt-4">
            <h3 className="font-medium">Academic programme assignments</h3>
            {programs.length === 0 ? (
              <p className="text-sm text-gray-500">Create an academic programme before assigning one to a lecturer.</p>
            ) : (
              <div className="grid gap-2 md:grid-cols-2">
                {programs.map((program) => (
                  <label className="flex items-center gap-2 text-sm" key={program.id}>
                    <input type="checkbox" checked={selectedPrograms.includes(program.id)} onChange={() => toggleProgram(program.id)} />
                    {program.code} - {program.name}
                  </label>
                ))}
              </div>
            )}
            <button className="rounded border px-4 py-2 disabled:opacity-50" type="button" disabled={saving} onClick={() => void savePrograms()}>
              Save programme assignments
            </button>
          </div>

          <div className="flex flex-wrap gap-3 border-t pt-4">
            <button className="rounded border px-4 py-2 disabled:opacity-50" type="button" disabled={saving} onClick={() => void loadComplianceReport()}>
              View compliance status
            </button>
            <button className="rounded border px-4 py-2 disabled:opacity-50" type="button" disabled={saving} onClick={() => void downloadReport()}>
              Download CSV report
            </button>
          </div>
          {report && (
            <div className="space-y-2 rounded bg-gray-50 p-4" aria-live="polite">
              <p className="font-medium">Compliance status: {report.compliance_status.replace('_', ' ')}</p>
              <p className="text-sm">
                {report.assigned_courses} courses; {report.course_submissions} submissions;{' '}
                {report.pending_verification} pending verification; {report.rejected_submissions} rejected.
              </p>
              <p className="text-sm text-gray-600">{report.explanation}</p>
              {report.courses_without_submission.length > 0 && (
                <p className="text-sm text-amber-800">
                  No lecturer submission recorded for:{' '}
                  {report.courses_without_submission.map((course) => course.code).join(', ')}.
                </p>
              )}
            </div>
          )}
        </>
      ) : (
        <p className="text-sm text-gray-500">No lecturer is selected.</p>
      )}
    </section>
  )
}
