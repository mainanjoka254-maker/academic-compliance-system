import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { ArrowLeft } from 'lucide-react'
import api from '@/services/api'

function statusText(s: string) {
  if (s === 'email_verification_required') return 'Email verification required. Check your inbox for the OTP.'
  if (s === 'pending_approval') return 'Awaiting institutional approval. You can sign in after approval.'
  if (s === 'not_approved') return 'This request was not approved. Contact your institution.'
  if (s === 'inactive') return 'Account is inactive. Contact your institution administrator.'
  if (s === 'active') return 'Account is active. You can sign in.'
  return s
}

export default function AccountStatus() {
  const [email, setEmail] = useState('')
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const check = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setResult(null); setLoading(true)
    try {
      const r = await api.get('/auth/account-status', { params: { email } })
      setResult(r.data)
    } catch (err: unknown) {
      const detail = isAxiosError<{ detail?: string }>(err) ? err.response?.data?.detail : undefined
      setError(detail || 'Status could not be checked. Try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-navy-950 bg-hero-mesh px-4 py-10">
      <div className="mx-auto max-w-md pt-6">
        <Link to="/" className="mb-4 inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white"><ArrowLeft size={16} /> Home</Link>
        <form onSubmit={check} className="adcs-card p-6 sm:p-8">
          <h1 className="text-2xl font-bold text-navy-900">Check account status</h1>
          <p className="mt-1 text-sm text-slate-600">Enter the email you registered with to see verification and approval status.</p>
          {error && <div role="alert" className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          <label className="adcs-label mt-5" htmlFor="status-email">Email address</label>
          <input id="status-email" className="adcs-input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <button disabled={loading} className="adcs-btn-primary mt-4 w-full">{loading ? 'Checking…' : 'Check status'}</button>
          {result && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm">
              {result.found ? (
                <>
                  <p className="font-medium text-navy-900">{statusText(result.status)}</p>
                  {result.requested_role && <p className="text-slate-600">Role: {String(result.requested_role).replace(/_/g, ' ')}</p>}
                  {result.status === 'email_verification_required' && <Link to="/verify-otp" className="mt-2 inline-block font-medium text-primary-700 hover:text-primary-800">Go to email verification</Link>}
                  {result.status === 'active' && <Link to="/login" className="mt-2 inline-block font-medium text-primary-700 hover:text-primary-800">Sign in</Link>}
                </>
              ) : (
                <p className="text-slate-700">{result.message}</p>
              )}
            </div>
          )}
          <div className="mt-5 flex justify-between text-sm">
            <Link to="/register" className="font-medium text-primary-700 hover:text-primary-800">Create account</Link>
            <Link to="/login" className="font-medium text-primary-700 hover:text-primary-800">Sign in</Link>
          </div>
        </form>
      </div>
    </main>
  )
}