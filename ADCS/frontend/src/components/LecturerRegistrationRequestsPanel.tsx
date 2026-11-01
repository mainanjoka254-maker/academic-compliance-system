import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'

import api from '@/services/api'

type LecturerRequest = {
  user_id: number
  email: string
  full_name: string
  phone: string | null
  staff_number: string | null
  is_verified: boolean
}

function messageFromError(error: unknown) {
  if (isAxiosError<{ detail?: string }>(error)) {
    return error.response?.data?.detail ?? 'Lecturer requests could not be processed.'
  }
  return 'Lecturer requests could not be processed.'
}

export default function LecturerRegistrationRequestsPanel() {
  const [requests, setRequests] = useState<LecturerRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadRequests() {
    setLoading(true)
    setError('')
    try {
      const response = await api.get<LecturerRequest[]>('/lecturers/registration-requests')
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
      await api.post(`/lecturers/${userId}/registration-request/${decision}`)
      setNotice(decision === 'approve' ? 'Lecturer registration approved.' : 'Lecturer registration rejected.')
      await loadRequests()
    } catch (requestError) {
      setError(messageFromError(requestError))
    } finally {
      setSavingId(null)
    }
  }

  return (
    <section className="space-y-3 rounded-xl bg-white p-5 shadow" aria-label="Lecturer registration requests">
      <div>
        <h2 className="text-lg font-semibold">Lecturer registration requests</h2>
        <p className="text-sm text-gray-600">Email-verified applicants remain inactive until an authorized administrator approves them.</p>
      </div>
      {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {notice && <p role="status" className="rounded bg-green-50 p-3 text-sm text-green-700">{notice}</p>}
      {loading ? <p role="status">Loading lecturer requests…</p> : requests.length === 0 ? (
        <p className="text-sm text-gray-600">There are no pending lecturer requests.</p>
      ) : (
        <ul className="divide-y rounded border">
          {requests.map((request) => (
            <li key={request.user_id} className="flex flex-wrap items-center justify-between gap-3 p-3">
              <div>
                <p className="font-medium">{request.full_name} · {request.staff_number}</p>
                <p className="text-sm text-gray-600">{request.email}{request.phone ? ` · ${request.phone}` : ''}</p>
                {!request.is_verified && <p className="text-sm text-amber-800">Email verification is still required.</p>}
              </div>
              <div className="flex gap-2">
                <button type="button" disabled={savingId !== null || !request.is_verified} className="rounded bg-primary-600 px-3 py-1 text-sm text-white disabled:opacity-50" onClick={() => void decide(request.user_id, 'approve')}>Approve</button>
                <button type="button" disabled={savingId !== null} className="rounded border px-3 py-1 text-sm disabled:opacity-50" onClick={() => void decide(request.user_id, 'reject')}>Reject</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
