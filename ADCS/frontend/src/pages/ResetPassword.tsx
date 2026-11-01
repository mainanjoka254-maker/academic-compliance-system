import React, { useState } from 'react'
import { isAxiosError } from 'axios'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'

import api from '@/services/api'

export default function ResetPassword() {
  const [params] = useSearchParams()
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()
  const token = params.get('token')

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')
    if (!token) {
      setError('This password reset link is invalid or incomplete.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await api.post('/auth/reset-password', { token, new_password: newPassword })
      setMessage('Password reset successfully. Redirecting to sign in…')
      window.setTimeout(() => navigate('/login'), 1200)
    } catch (requestError: unknown) {
      const detail = isAxiosError<{ detail?: string }>(requestError)
        ? requestError.response?.data?.detail
        : undefined
      setError(detail || 'The password could not be reset. Request a new link and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-2 text-2xl font-bold">Reset password</h1>
        <p className="mb-6 text-sm text-gray-600">Choose a new password with at least eight characters.</p>
        {message && <div role="status" className="mb-4 rounded bg-green-50 p-3 text-sm text-green-700">{message}</div>}
        {error && <div role="alert" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <label className="mb-1 block text-sm font-medium" htmlFor="new-password">New password</label>
        <div className="mb-3 flex rounded border focus-within:ring-2 focus-within:ring-primary-500">
          <input id="new-password" className="min-w-0 flex-1 rounded-l px-3 py-2 outline-none" type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          <button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((visible) => !visible)} className="px-3 text-gray-600">
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        <label className="mb-1 block text-sm font-medium" htmlFor="confirm-new-password">Confirm new password</label>
        <input id="confirm-new-password" className="mb-4 w-full rounded border px-3 py-2" type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={8} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
        <button disabled={submitting || !token} className="w-full rounded bg-primary-600 py-2.5 text-white disabled:opacity-60">
          {submitting ? 'Resetting…' : 'Reset password'}
        </button>
      </form>
    </main>
  )
}
