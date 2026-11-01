import React, { useState } from 'react'
import { isAxiosError } from 'axios'
import { Link, useNavigate } from 'react-router-dom'

import api from '@/services/api'

export default function VerifyOTP() {
  const [email, setEmail] = useState(() => window.sessionStorage.getItem('adcs_verification_email') || '')
  const [otp, setOtp] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [resending, setResending] = useState(false)
  const navigate = useNavigate()

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setSubmitting(true)
    try {
      await api.post('/auth/verify-otp', { email, otp })
      window.sessionStorage.removeItem('adcs_verification_email')
      setMessage('Email verified. Redirecting to sign in…')
      window.setTimeout(() => navigate('/login'), 1200)
    } catch (requestError: unknown) {
      const detail = isAxiosError<{ detail?: string }>(requestError)
        ? requestError.response?.data?.detail
        : undefined
      setError(detail || 'Verification failed. Check the email and code.')
    } finally {
      setSubmitting(false)
    }
  }

  const resend = async () => {
    setError('')
    setMessage('')
    setResending(true)
    try {
      await api.post('/auth/resend-otp', { email })
      setMessage('If this account needs verification, a new code has been sent.')
    } catch (requestError: unknown) {
      const detail = isAxiosError<{ detail?: string }>(requestError)
        ? requestError.response?.data?.detail
        : undefined
      setError(detail || 'A new verification code could not be sent.')
    } finally {
      setResending(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-2 text-2xl font-bold">Verify your email</h1>
        <p className="mb-6 text-sm text-gray-600">Enter the six-digit code sent to your email address.</p>
        {message && <div role="status" className="mb-4 rounded bg-green-50 p-3 text-sm text-green-700">{message}</div>}
        {error && <div role="alert" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <label className="mb-1 block text-sm font-medium" htmlFor="verification-email">Email address</label>
        <input id="verification-email" className="mb-3 w-full rounded border px-3 py-2" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        <label className="mb-1 block text-sm font-medium" htmlFor="verification-code">Verification code</label>
        <input id="verification-code" className="mb-4 w-full rounded border px-3 py-2" inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="[0-9]{6}" required value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))} />
        <button disabled={submitting} className="w-full rounded bg-primary-600 py-2.5 text-white disabled:opacity-60">
          {submitting ? 'Verifying…' : 'Verify email'}
        </button>
        <button type="button" disabled={resending || !email} onClick={resend} className="mt-3 w-full rounded border py-2.5 text-gray-700 disabled:opacity-60">
          {resending ? 'Sending…' : 'Resend code'}
        </button>
        <p className="mt-5 text-center text-sm"><Link to="/login" className="text-primary-600 hover:underline">Back to sign in</Link></p>
      </form>
    </main>
  )
}
