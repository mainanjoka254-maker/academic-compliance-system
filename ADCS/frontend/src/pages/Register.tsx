import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { Eye, EyeOff, GraduationCap, ArrowLeft } from 'lucide-react'

import api from '@/services/api'
import GoogleSignInButton from '@/components/GoogleSignInButton'

interface InstitutionOption {
  id: number
  name: string
}

type RequestedRole = 'student' | 'lecturer' | 'registrar' | 'compliance_officer' | 'university_admin'

const ROLE_OPTIONS: { value: RequestedRole; label: string; staff: boolean; google: boolean }[] = [
  { value: 'student', label: 'Student', staff: false, google: true },
  { value: 'lecturer', label: 'Lecturer (requires institutional approval)', staff: true, google: false },
  { value: 'registrar', label: 'Registrar (requires institutional approval)', staff: true, google: false },
  { value: 'compliance_officer', label: 'Compliance Officer (requires institutional approval)', staff: true, google: false },
  { value: 'university_admin', label: 'University Administrator (requires institutional approval)', staff: true, google: false },
]

export default function Register() {
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [requestedRole, setRequestedRole] = useState<RequestedRole>('student')
  const [staffNumber, setStaffNumber] = useState('')
  const [institutionId, setInstitutionId] = useState<number | ''>('')
  const [institutions, setInstitutions] = useState<InstitutionOption[]>([])
  const [institutionsLoaded, setInstitutionsLoaded] = useState(false)
  const [institutionError, setInstitutionError] = useState('')
  const [googleEnabled, setGoogleEnabled] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [verificationPending, setVerificationPending] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api.get<InstitutionOption[]>('/institutions/registration-options')
      .then((response) => setInstitutions(response.data))
      .catch(() => setInstitutionError('Institutions could not be loaded. Please try again later.'))
      .finally(() => setInstitutionsLoaded(true))
    api.get<{ enabled: boolean }>('/auth/google/status')
      .then((response) => setGoogleEnabled(response.data.enabled))
      .catch(() => setGoogleEnabled(false))
  }, [])

  const selectedRole = ROLE_OPTIONS.find((r) => r.value === requestedRole) || ROLE_OPTIONS[0]

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    if (!institutionId) {
      setError('Select your institution to continue.')
      return
    }
    if (selectedRole.staff && !staffNumber.trim()) {
      setError('A staff/employee number is required for this account type.')
      return
    }
    setSubmitting(true)
    window.sessionStorage.setItem('adcs_verification_email', email)
    try {
      await api.post('/auth/register', {
        email,
        phone: phone || undefined,
        password,
        full_name: fullName,
        institution_id: institutionId,
        role_requested: requestedRole,
        staff_number: selectedRole.staff ? staffNumber : undefined,
      })
      setMessage(
        requestedRole === 'student'
          ? 'Registration saved. Check your email for the verification code.'
          : 'Account request saved. Verify your email; your institution must approve the request before you can sign in.',
      )
      window.setTimeout(() => navigate('/verify-otp'), 1000)
    } catch (requestError: unknown) {
      const detail = isAxiosError<{ detail?: string }>(requestError)
        ? requestError.response?.data?.detail
        : undefined
      if (isAxiosError(requestError) && requestError.response?.status === 503) {
        setVerificationPending(true)
      }
      setError(detail || 'Registration failed. Please review your details and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const startGoogleRegistration = () => {
    if (!institutionId) {
      setError('Select your institution before continuing with Google.')
      return
    }
    if (!selectedRole.google) {
      setError('Google registration is currently available for student accounts only.')
      return
    }
    window.location.assign(`/api/v1/auth/google?institution_id=${institutionId}`)
  }

  return (
    <main className="min-h-screen bg-navy-950 bg-hero-mesh px-4 py-8 sm:px-6">
      <div className="mx-auto flex max-w-6xl items-start justify-center gap-8 lg:py-6">
        <div className="hidden max-w-md pt-10 text-white lg:block">
          <Link to="/" className="mb-8 inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white"><ArrowLeft size={16} /> Back to home</Link>
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-600"><GraduationCap /></div>
          <h1 className="text-4xl font-extrabold tracking-tight">Create your ADCS account</h1>
          <p className="mt-4 text-slate-300">Register with your institution, verify your email, and access your role-based workspace. Staff roles require institutional approval.</p>
        </div>

        <form onSubmit={submit} className="adcs-card w-full max-w-xl p-6 sm:p-8">
          <Link to="/" className="mb-4 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 lg:hidden"><ArrowLeft size={16} /> Home</Link>
          <h1 className="text-2xl font-bold text-navy-900 lg:hidden">Create your ADCS account</h1>
          <p className="mt-1 mb-5 text-sm text-slate-600">Verify your email, then sign in. Staff accounts require institutional approval.</p>
          {message && <div role="status" className="mb-4 rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-800">{message}</div>}
          {error && <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          {institutionError && <p role="alert" className="mb-3 text-sm text-red-700">{institutionError}</p>}

          <div className="grid gap-x-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="adcs-label" htmlFor="register-name">Full name</label>
              <input id="register-name" className="adcs-input mb-3" autoComplete="name" minLength={2} required value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
            <div>
              <label className="adcs-label" htmlFor="register-email">Email address</label>
              <input id="register-email" className="adcs-input mb-3" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="adcs-label" htmlFor="register-phone">Phone number <span className="font-normal text-slate-400">(optional)</span></label>
              <input id="register-phone" className="adcs-input mb-3" type="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
            <div className="sm:col-span-2">
              <label className="adcs-label" htmlFor="register-role">Account type</label>
              <select id="register-role" className="adcs-input mb-3" value={requestedRole} onChange={(e) => setRequestedRole(e.target.value as RequestedRole)}>
                {ROLE_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
            {selectedRole.staff && (
              <div className="sm:col-span-2">
                <label className="adcs-label" htmlFor="register-staff-number">Staff / employee number</label>
                <input id="register-staff-number" className="adcs-input mb-1" required minLength={1} maxLength={50} value={staffNumber} onChange={(e) => setStaffNumber(e.target.value)} />
                <p className="mb-3 text-xs text-slate-500">Your institution will verify and approve this request before access is granted.</p>
              </div>
            )}
            <div className="sm:col-span-2">
              <label className="adcs-label" htmlFor="register-institution">Institution</label>
              <select id="register-institution" className="adcs-input mb-3" required value={institutionId} onChange={(e) => setInstitutionId(e.target.value ? Number(e.target.value) : '')}>
                <option value="">Select institution</option>
                {institutions.map((institution) => <option key={institution.id} value={institution.id}>{institution.name}</option>)}
              </select>
            </div>
            <div>
              <label className="adcs-label" htmlFor="register-password">Password</label>
              <div className="mb-3 flex rounded-xl border border-slate-300 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20">
                <input id="register-password" className="min-w-0 flex-1 rounded-l-xl px-3 py-2.5 outline-none" type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
                <button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((v) => !v)} className="px-3 text-slate-500">
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            <div>
              <label className="adcs-label" htmlFor="register-confirm">Confirm password</label>
              <input id="register-confirm" className="adcs-input mb-3" type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
            </div>
          </div>

          {institutionsLoaded && institutions.length === 0 && !institutionError && (
            <p role="status" className="mb-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              No active institutions are available yet. Contact a system administrator before registering.
            </p>
          )}
          <button disabled={submitting || institutions.length === 0} className="adcs-btn-primary mt-1 w-full">
            {submitting ? 'Creating account…' : requestedRole === 'student' ? 'Create student account' : 'Submit account request'}
          </button>
          {verificationPending && (
            <Link to="/verify-otp" className="mt-3 block text-center text-sm font-medium text-primary-700 hover:text-primary-800">
              Continue to email verification
            </Link>
          )}
          <div className="my-5 flex items-center gap-3 text-xs text-slate-400"><span className="h-px flex-1 bg-slate-200" />OR<span className="h-px flex-1 bg-slate-200" /></div>
          <GoogleSignInButton label="Continue with Google" disabled={!googleEnabled || !selectedRole.google} onClick={startGoogleRegistration} />
          {!googleEnabled && <p className="mt-2 text-center text-xs text-slate-500">Google Sign-In is not configured.</p>}
          {selectedRole.staff && <p className="mt-2 text-center text-xs text-slate-500">Google registration is available for student accounts only.</p>}
          <p className="mt-3 text-center text-xs text-slate-500">Super Administrator accounts are provisioned by platform setup and are not self-registered.</p>
          <div className="mt-5 text-center text-sm">
            <Link to="/login" className="font-medium text-primary-700 hover:text-primary-800">Already registered? Sign in</Link>
          </div>
        </form>
      </div>
    </main>
  )
}
