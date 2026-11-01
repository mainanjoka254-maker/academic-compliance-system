import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { Eye, EyeOff } from 'lucide-react'

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
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-50 to-white px-4 py-10">
      <form onSubmit={submit} className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-2 text-2xl font-bold text-navy-900">Sign in to ADCS</h1>
        <p className="mb-6 text-sm text-gray-600">Access your institution's academic compliance workspace.</p>
        {error && <div role="alert" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <label className="mb-1 block text-sm font-medium" htmlFor="login-email">Email address</label>
        <input
          id="login-email"
          className="mb-4 w-full rounded border px-3 py-2"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <label className="mb-1 block text-sm font-medium" htmlFor="login-password">Password</label>
        <div className="mb-4 flex rounded border focus-within:ring-2 focus-within:ring-primary-500">
          <input
            id="login-password"
            className="min-w-0 flex-1 rounded-l px-3 py-2 outline-none"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button
            type="button"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            onClick={() => setShowPassword((visible) => !visible)}
            className="px-3 text-gray-600"
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        <button
          disabled={submitting}
          className="w-full rounded bg-primary-600 py-2.5 text-white hover:bg-primary-700 disabled:opacity-60"
        >
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
        <div className="my-5 flex items-center gap-3 text-xs text-gray-400">
          <span className="h-px flex-1 bg-gray-200" />
          OR
          <span className="h-px flex-1 bg-gray-200" />
        </div>
        <GoogleSignInButton
          label="Sign in with Google"
          disabled={!googleEnabled}
          onClick={() => { window.location.assign('/api/v1/auth/google') }}
        />
        {!googleEnabled && <p className="mt-2 text-center text-xs text-gray-500">Google Sign-In is not configured.</p>}
        <div className="mt-5 flex justify-between text-sm">
          <Link to="/forgot-password" className="text-primary-600 hover:underline">Forgot password?</Link>
          <Link to="/register" className="text-primary-600 hover:underline">Create account</Link>
        </div>
      </form>
    </main>
  )
}
