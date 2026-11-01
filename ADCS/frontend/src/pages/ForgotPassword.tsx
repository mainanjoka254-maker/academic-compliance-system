import React, { useState } from 'react'
import { isAxiosError } from 'axios'
import { Link } from 'react-router-dom'

import api from '@/services/api'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setMessage('')
    setError('')
    setSubmitting(true)
    try {
      await api.post('/auth/forgot-password', { email })
      setMessage('If the email exists, a reset link has been sent.')
    } catch (requestError: unknown) {
      const detail = isAxiosError<{ detail?: string }>(requestError)
        ? requestError.response?.data?.detail
        : undefined
      setError(detail || 'The reset request could not be completed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-2 text-2xl font-bold">Forgot password?</h1>
        <p className="mb-6 text-sm text-gray-600">We'll send a time-limited password reset link if the account exists.</p>
        {message && <div role="status" className="mb-4 rounded bg-green-50 p-3 text-sm text-green-700">{message}</div>}
        {error && <div role="alert" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <label className="mb-1 block text-sm font-medium" htmlFor="reset-email">Email address</label>
        <input id="reset-email" className="mb-4 w-full rounded border px-3 py-2" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        <button disabled={submitting} className="w-full rounded bg-primary-600 py-2.5 text-white disabled:opacity-60">
          {submitting ? 'Sending…' : 'Send reset link'}
        </button>
        <p className="mt-5 text-center text-sm"><Link to="/login" className="text-primary-600 hover:underline">Back to sign in</Link></p>
      </form>
    </main>
  )
}
