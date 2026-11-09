import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'

import api from '@/services/api'

type AccountRequest = {
  user_id: number
  email: string
  full_name: string
  phone: string | null
  requested_role: string
  staff_number: string | null
  institution_id: number
  is_verified: boolean
}

function messageFromError(error: unknown) {
  if (isAxiosError<{ detail?: string }>(error)) {
    return error.response?.data?.detail ?? 'Account requests could not be processed.'
  }
  return 'Account requests could not be processed.'
}

function roleLabel(role: string) {
  return role.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function AccountRequestsPanel() {
  const [requests, setRequests] = useState<AccountRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [reasons, setReasons] = useState<Record<number, string>>({})
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadRequests() {
    setLoading(true)
    setError('')
    try {
      const response = await api.get<AccountRequest[]>('/admin/account-requests')
      setRequests(response.data)
    } catch (requestError) {
      setError(messageFromError(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadRequests()
  }, [])

  async function decide(userId: number, decision: 'approve' | 'reject') {
    setSavingId(userId)
    setError('')
    setNotice('')
    try {
      const reason = (reasons[userId] || '').trim() || undefined
      await api.post(`/admin/account-requests/${userId}/${decision}`, reason ? { reason } : {})
      setNotice(decision === 'approve' ? 'Account request approved.' : 'Account request rejected.')
      await loadRequests()
    } catch (requestError) {
      setError(messageFromError(requestError))
    } finally {
      setSavingId(null)
    }
  }

  return (
    <section className="space-y-3 rounded-xl bg-white p-5 shadow" aria-label="Account requests">
      <div>
        <h2 className="text-lg font-semibold">Institutional account requests</h2>
        <p className="text-sm text-gray-600">Approve or reject pending staff, registrar, compliance, and administrator requests for your institution. Applicants must be email-verified before approval.</p>
      </div>
      {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {notice && <p role="status" className="rounded bg-green-50 p-3 text-sm text-green-700">{notice}</p>}
      {loading ? <p role="status">Loading account requests…</p> : requests.length === 0 ? (
        <p className="text-sm text-gray-600">There are no pending account requests.</p>
      ) : (
        <ul className="divide-y rounded border">
          {requests.map((r) => (
            <li key={r.user_id} className="flex flex-wrap items-start justify-between gap-3 p-3">
              <div className="min-w-[240px] flex-1">
                <p className="font-medium">{r.full_name} · <span className="text-primary-700">{roleLabel(r.requested_role)}</span></p>
                <p className="text-sm text-gray-600">{r.email}{r.phone ? ` · ${r.phone}` : ''}{r.staff_number ? ` · Staff ${r.staff_number}` : ''}</p>
                {!r.is_verified && <p className="text-sm text-amber-800">Email verification is still required.</p>}
                <label className="mt-2 block text-xs text-gray-600" htmlFor={`reason-${r.user_id}`}>Note to applicant (optional)</label>
                <input id={`reason-${r.user_id}`} className="mt-1 w-full rounded border px-2 py-1 text-sm" maxLength={500} value={reasons[r.user_id] || ''} onChange={(e) => setReasons((p) => ({ ...p, [r.user_id]: e.target.value }))} placeholder="Reason or instructions" />
              </div>
              <div className="flex gap-2">
                <button type="button" disabled={savingId !== null || !r.is_verified} className="rounded bg-primary-600 px-3 py-1 text-sm text-white disabled:opacity-50" onClick={() => void decide(r.user_id, 'approve')}>Approve</button>
                <button type="button" disabled={savingId !== null} className="rounded border px-3 py-1 text-sm disabled:opacity-50" onClick={() => void decide(r.user_id, 'reject')}>Reject</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}