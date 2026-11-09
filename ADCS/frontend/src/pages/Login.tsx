import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { Eye, EyeOff, GraduationCap, ShieldCheck, ArrowLeft } from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import GoogleSignInButton from '@/components/GoogleSignInButton'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [googleEnabled, setGoogleEnabled] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    api.get<{ enabled: boolean }>('/auth/google/status')
      .then((response) => setGoogleEnabled(response.data.enabled))
      .catch(() => setGoogleEnabled(false))
  }, [])

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (requestError: unknown) {
      const detail = isAxiosError<{ detail?: string }>(requestError)
        ? requestError.response?.data?.detail
        : undefined
      setError(detail || 'Sign-in failed. Check your credentials and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen bg-navy-950 bg-hero-mesh px-4 py-8 sm:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-2">
        <div className="hidden text-white lg:block">
          <Link to="/" className="mb-8 inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white"><ArrowLeft size={16} /> Back to home</Link>
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-600"><GraduationCap /></div>
          <h1 className="text-4xl font-extrabold tracking-tight">Welcome back to ADCS</h1>
          <p className="mt-4 max-w-md text-slate-300">Sign in to access your role-based dashboard, academic records, compliance workflows, and institutional tools.</p>
          <div className="mt-8 space-y-3 text-sm text-slate-200">
            <div className="flex items-center gap-2"><ShieldCheck size={16} className="text-emerald-300" /> Secure, permission-enforced access</div>
            <div className="flex items-center gap-2"><ShieldCheck size={16} className="text-emerald-300" /> Works on laptop and mobile</div>
          </div>
        </div>

        <form onSubmit={submit} className="adcs-card mx-auto w-full max-w-md p-6 sm:p-8">
          <Link to="/" className="mb-4 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 lg:hidden"><ArrowLeft size={16} /> Home</Link>
          <h2 className="text-2xl font-bold text-navy-900">Sign in</h2>
          <p className="mt-1 text-sm text-slate-600">Use your verified ADCS account.</p>
          {error && <div role="alert" className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

          <label className="adcs-label mt-5" htmlFor="login-email">Email address</label>
          <input id="login-email" className="adcs-input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />

          <label className="adcs-label mt-4" htmlFor="login-password">Password</label>
          <div className="flex rounded-xl border border-slate-300 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20">
            <input id="login-password" className="min-w-0 flex-1 rounded-l-xl px-3 py-2.5 outline-none" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((v) => !v)} className="px-3 text-slate-500 hover:text-slate-700">
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <button disabled={submitting} className="adcs-btn-primary mt-5 w-full">{submitting ? 'Signing in…' : 'Sign in'}</button>

          <div className="my-5 flex items-center gap-3 text-xs text-slate-400"><span className="h-px flex-1 bg-slate-200" />OR<span className="h-px flex-1 bg-slate-200" /></div>
          <GoogleSignInButton label="Sign in with Google" disabled={!googleEnabled} onClick={() => { window.location.assign('/api/v1/auth/google') }} />
          {!googleEnabled && <p className="mt-2 text-center text-xs text-slate-500">Google Sign-In is not configured.</p>}

          <div className="mt-5 flex flex-col gap-2 text-center text-sm sm:flex-row sm:justify-between sm:text-left">
            <Link to="/forgot-password" className="font-medium text-primary-700 hover:text-primary-800">Forgot password?</Link>
            <Link to="/register" className="font-medium text-primary-700 hover:text-primary-800">Create account</Link>
          </div>
          <div className="mt-2 text-center text-sm">
            <Link to="/account-status" className="text-slate-500 hover:text-slate-700">Check registration/approval status</Link>
          </div>
        </form>
      </div>
    </main>
  )
}
