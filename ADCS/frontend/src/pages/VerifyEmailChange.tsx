import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '@/services/api'

export default function VerifyEmailChange() {
  const [sp] = useSearchParams()
  const token = sp.get('token') || ''
  const [status, setStatus] = useState<'idle'|'loading'|'ok'|'error'>('idle')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (!token) { setStatus('error'); setMsg('Missing verification token.'); return }
    (async () => {
      setStatus('loading')
      try {
        const r = await api.post('/profile/me/change-email/confirm', { token })
        setStatus('ok'); setMsg(r.data?.message || 'Email address updated.')
      } catch (e: any) { setStatus('error'); setMsg(e?.response?.data?.detail || 'Verification failed.') }
    })()
  }, [token])

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="text-xl font-bold text-navy-900">Confirm email change</h1>
        {status==='loading' && <p className="mt-3 text-slate-600">Verifying…</p>}
        {status==='ok' && <p className="mt-3 rounded bg-emerald-50 p-3 text-emerald-800">{msg}</p>}
        {status==='error' && <p className="mt-3 rounded bg-red-50 p-3 text-red-700">{msg}</p>}
        <div className="mt-4"><Link to="/dashboard/settings" className="text-primary-700 hover:underline">Back to Settings</Link></div>
      </div>
    </div>
  )
}
