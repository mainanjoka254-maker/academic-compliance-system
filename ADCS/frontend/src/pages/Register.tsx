import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { Eye, EyeOff } from 'lucide-react'

import api from '@/services/api'
import GoogleSignInButton from '@/components/GoogleSignInButton'

interface InstitutionOption {
  id: number
  name: string
}

type RequestedRole = 'student' | 'lecturer'

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
        staff_number: requestedRole === 'lecturer' ? staffNumber : undefined,
      })
      setMessage(
        requestedRole === 'lecturer'
          ? 'Lecturer request saved. Verify your email; your institution must approve the request before you can sign in.'
          : 'Registration saved. Check your email for the verification code.',
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
    if (requestedRole !== 'student') {
      setError('Google registration is currently available for student accounts only.')
      return
    }
    window.location.assign(`/api/v1/auth/google?institution_id=${institutionId}`)
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-50 to-white px-4 py-10">
      <form onSubmit={submit} className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-2 text-2xl font-bold text-navy-900">Create your ADCS account</h1>
        <p className="mb-6 text-sm text-gray-600">Student accounts are verified by email before sign-in.</p>
        {message && <div role="status" className="mb-4 rounded bg-green-50 p-3 text-sm text-green-700">{message}</div>}
        {error && <div role="alert" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        {institutionError && <p role="alert" className="mb-3 text-sm text-red-700">{institutionError}</p>}
        <label className="mb-1 block text-sm font-medium" htmlFor="register-name">Full name</label>
        <input id="register-name" className="mb-3 w-full rounded border px-3 py-2" autoComplete="name" minLength={2} required value={fullName} onChange={(event) => setFullName(event.target.value)} />
        <label className="mb-1 block text-sm font-medium" htmlFor="register-email">Email address</label>
        <input id="register-email" className="mb-3 w-full rounded border px-3 py-2" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        <label className="mb-1 block text-sm font-medium" htmlFor="register-role">Account type</label>
        <select id="register-role" className="mb-3 w-full rounded border px-3 py-2" value={requestedRole} onChange={(event) => setRequestedRole(event.target.value as RequestedRole)}>
          <option value="student">Student</option>
          <option value="lecturer">Lecturer (requires institutional approval)</option>
        </select>
        {requestedRole === 'lecturer' && (
          <>
            <label className="mb-1 block text-sm font-medium" htmlFor="register-staff-number">Staff number</label>
            <input id="register-staff-number" className="mb-3 w-full rounded border px-3 py-2" required minLength={1} maxLength={50} value={staffNumber} onChange={(event) => setStaffNumber(event.target.value)} />
          </>
        )}
        <label className="mb-1 block text-sm font-medium" htmlFor="register-phone">Phone number <span className="font-normal text-gray-500">(optional)</span></label>
        <input id="register-phone" className="mb-3 w-full rounded border px-3 py-2" type="tel" autoComplete="tel" value={phone} onChange={(event) => setPhone(event.target.value)} />
        <label className="mb-1 block text-sm font-medium" htmlFor="register-password">Password</label>
        <div className="mb-3 flex rounded border focus-within:ring-2 focus-within:ring-primary-500">
          <input id="register-password" className="min-w-0 flex-1 rounded-l px-3 py-2 outline-none" type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} />
          <button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((visible) => !visible)} className="px-3 text-gray-600">
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        <label className="mb-1 block text-sm font-medium" htmlFor="register-confirm">Confirm password</label>
        <input id="register-confirm" className="mb-3 w-full rounded border px-3 py-2" type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
        <label className="mb-1 block text-sm font-medium" htmlFor="register-institution">Institution</label>
        <select id="register-institution" className="mb-4 w-full rounded border px-3 py-2" required value={institutionId} onChange={(event) => setInstitutionId(event.target.value ? Number(event.target.value) : '')}>
          <option value="">Select institution</option>
          {institutions.map((institution) => <option key={institution.id} value={institution.id}>{institution.name}</option>)}
        </select>
        {institutionsLoaded && institutions.length === 0 && !institutionError && (
          <p role="status" className="mb-3 text-sm text-amber-800">
            No active institutions are available yet. Contact a system administrator before registering.
          </p>
        )}
        <button disabled={submitting || institutions.length === 0} className="w-full rounded bg-primary-600 py-2.5 text-white hover:bg-primary-700 disabled:opacity-60">
          {submitting ? 'Creating account…' : requestedRole === 'lecturer' ? 'Request lecturer account' : 'Create student account'}
        </button>
        {verificationPending && (
          <Link to="/verify-otp" className="mt-3 block text-center text-sm text-primary-600 hover:underline">
            Continue to email verification
          </Link>
        )}
        <div className="my-5 flex items-center gap-3 text-xs text-gray-400">
          <span className="h-px flex-1 bg-gray-200" />
          OR
          <span className="h-px flex-1 bg-gray-200" />
        </div>
        <GoogleSignInButton
          label="Continue with Google"
          disabled={!googleEnabled || requestedRole !== 'student'}
          onClick={startGoogleRegistration}
        />
        {!googleEnabled && <p className="mt-2 text-center text-xs text-gray-500">Google Sign-In is not configured.</p>}
        <p className="mt-3 text-xs text-gray-500">Staff roles are assigned by authorized institutional administrators.</p>
        <div className="mt-5 text-center text-sm">
          <Link to="/login" className="text-primary-600 hover:underline">Already registered? Sign in</Link>
        </div>
      </form>
    </main>
  )
}
