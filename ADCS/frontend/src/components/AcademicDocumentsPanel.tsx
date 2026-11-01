import { FormEvent, useEffect, useState } from 'react'
import api from '@/services/api'

type DocumentRecord = {
  id: number
  course_id: number | null
  purpose: 'student_document' | 'lecturer_submission'
  original_filename: string
  size_bytes: number
  status: 'pending' | 'approved' | 'rejected'
  review_note: string | null
  created_at: string
}

type ReviewRecord = {
  id: number
  status: string
  note: string | null
  created_at: string
}

type CourseOption = { id: number; code: string; name: string }
type PanelMode = 'student' | 'lecturer' | 'reviewer'

type Props = {
  mode: PanelMode
  courses?: CourseOption[]
}

function errorMessage(error: unknown, fallback: string) {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof error.response === 'object' &&
    error.response !== null &&
    'data' in error.response &&
    typeof error.response.data === 'object' &&
    error.response.data !== null &&
    'detail' in error.response.data &&
    typeof error.response.data.detail === 'string'
  ) {
    return error.response.data.detail
  }
  return fallback
}

export default function AcademicDocumentsPanel({ mode, courses = [] }: Props) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [courseId, setCourseId] = useState('')
  const [rejectionNotes, setRejectionNotes] = useState<Record<number, string>>({})
  const [history, setHistory] = useState<Record<number, ReviewRecord[]>>({})
  const [expandedHistory, setExpandedHistory] = useState<Record<number, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadDocuments() {
    setLoading(true)
    setError('')
    try {
      const response = await api.get<DocumentRecord[]>('/documents')
      setDocuments(response.data)
    } catch (requestError) {
      setError(errorMessage(requestError, 'Documents could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDocuments()
  }, [mode])

  async function uploadDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    if (!selectedFile) {
      setError('Choose a PDF, PNG, or JPEG file to upload.')
      return
    }
    if (mode === 'lecturer' && !courseId) {
      setError('Choose the course for this submission.')
      return
    }

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('purpose', mode === 'lecturer' ? 'lecturer_submission' : 'student_document')
    if (mode === 'lecturer') formData.append('course_id', courseId)

    setError('')
    setNotice('')
    setBusyId(-1)
    try {
      await api.post('/documents', formData)
      setSelectedFile(null)
      form.reset()
      setNotice('Document uploaded. It is awaiting verification.')
      await loadDocuments()
    } catch (requestError) {
      setError(errorMessage(requestError, 'Document could not be uploaded.'))
    } finally {
      setBusyId(null)
    }
  }

  async function downloadDocument(document: DocumentRecord) {
    setBusyId(document.id)
    setError('')
    try {
      const response = await api.get(`/documents/${document.id}/download`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(response.data)
      const link = window.document.createElement('a')
      link.href = url
      link.download = document.original_filename
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (requestError) {
      setError(errorMessage(requestError, 'Document could not be downloaded.'))
    } finally {
      setBusyId(null)
    }
  }

  async function toggleHistory(documentId: number) {
    const willExpand = !expandedHistory[documentId]
    setExpandedHistory((current) => ({ ...current, [documentId]: willExpand }))
    if (!willExpand || history[documentId]) return
    setBusyId(documentId)
    setError('')
    try {
      const response = await api.get<ReviewRecord[]>(`/documents/${documentId}/history`)
      setHistory((current) => ({ ...current, [documentId]: response.data }))
    } catch (requestError) {
      setError(errorMessage(requestError, 'Verification history could not be loaded.'))
      setExpandedHistory((current) => ({ ...current, [documentId]: false }))
    } finally {
      setBusyId(null)
    }
  }

  async function reviewDocument(documentId: number, status: 'approved' | 'rejected') {
    const note = rejectionNotes[documentId]?.trim()
    if (status === 'rejected' && !note) {
      setError('Enter a reason before rejecting a document.')
      return
    }
    setBusyId(documentId)
    setError('')
    setNotice('')
    try {
      await api.post(`/documents/${documentId}/review`, {
        status,
        note: note || undefined,
      })
      setNotice(`Document ${status}.`)
      await loadDocuments()
    } catch (requestError) {
      setError(errorMessage(requestError, 'Document review could not be saved.'))
    } finally {
      setBusyId(null)
    }
  }

  const title =
    mode === 'student'
      ? 'My Academic Documents'
      : mode === 'lecturer'
        ? 'Course Submissions'
        : 'Document Verification'

  return (
    <section className="space-y-4 rounded-xl bg-white p-5 shadow">
      <div>
        <h2 className="text-lg font-semibold text-navy-900">{title}</h2>
        <p className="text-sm text-gray-500">
          PDF, PNG, and JPEG files up to 10 MB. Uploaded files remain private to authorized users.
        </p>
      </div>

      {mode !== 'reviewer' && (
        <form className="flex flex-col gap-3 md:flex-row md:items-end" onSubmit={uploadDocument}>
          {mode === 'lecturer' && (
            <label className="flex flex-col gap-1 text-sm">
              Course
              <select
                className="rounded border px-3 py-2"
                value={courseId}
                onChange={(event) => setCourseId(event.target.value)}
                required
              >
                <option value="">Select a course</option>
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} - {course.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="flex flex-col gap-1 text-sm">
            Document
            <input
              className="rounded border px-3 py-2"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              required
            />
          </label>
          <button
            className="rounded bg-blue-700 px-4 py-2 text-white disabled:opacity-50"
            type="submit"
            disabled={busyId === -1 || (mode === 'lecturer' && courses.length === 0)}
          >
            {busyId === -1 ? 'Uploading...' : 'Upload'}
          </button>
        </form>
      )}

      {error && <p className="text-sm text-red-700" role="alert">{error}</p>}
      {notice && <p className="text-sm text-green-700" role="status">{notice}</p>}
      {loading ? (
        <p className="text-sm text-gray-500">Loading documents...</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-gray-500">No documents found.</p>
      ) : (
        <ul className="divide-y">
          {documents.map((document) => (
            <li className="space-y-2 py-3" key={document.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium">{document.original_filename}</p>
                  <p className="text-xs text-gray-500">
                    {document.purpose.replace('_', ' ')} | {(document.size_bytes / 1024).toFixed(0)} KB |{' '}
                    {new Date(document.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="rounded bg-gray-100 px-2 py-1 text-xs capitalize">{document.status}</span>
              </div>
              {document.review_note && (
                <p className="text-sm text-gray-600">Review note: {document.review_note}</p>
              )}
              <div className="flex flex-wrap gap-3 text-sm">
                <button
                  className="text-blue-700 underline disabled:opacity-50"
                  type="button"
                  disabled={busyId === document.id}
                  onClick={() => void downloadDocument(document)}
                >
                  Download
                </button>
                <button
                  className="text-blue-700 underline disabled:opacity-50"
                  type="button"
                  disabled={busyId === document.id}
                  onClick={() => void toggleHistory(document.id)}
                >
                  {expandedHistory[document.id] ? 'Hide history' : 'Verification history'}
                </button>
              </div>
              {expandedHistory[document.id] && (
                <ul className="space-y-1 border-l-2 border-gray-200 pl-3 text-sm">
                  {(history[document.id] ?? []).length === 0 ? (
                    <li className="text-gray-500">No verification actions yet.</li>
                  ) : (
                    history[document.id].map((review) => (
                      <li key={review.id}>
                        {review.status} | {new Date(review.created_at).toLocaleString()}
                        {review.note && <span className="text-gray-600"> - {review.note}</span>}
                      </li>
                    ))
                  )}
                </ul>
              )}
              {mode === 'reviewer' && document.status === 'pending' && (
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    className="rounded border px-3 py-2 text-sm"
                    aria-label={`Rejection reason for ${document.original_filename}`}
                    placeholder="Reason required to reject"
                    value={rejectionNotes[document.id] ?? ''}
                    onChange={(event) =>
                      setRejectionNotes((current) => ({
                        ...current,
                        [document.id]: event.target.value,
                      }))
                    }
                  />
                  <button
                    className="rounded bg-green-700 px-3 py-2 text-sm text-white disabled:opacity-50"
                    type="button"
                    disabled={busyId === document.id}
                    onClick={() => void reviewDocument(document.id, 'approved')}
                  >
                    Approve
                  </button>
                  <button
                    className="rounded bg-red-700 px-3 py-2 text-sm text-white disabled:opacity-50"
                    type="button"
                    disabled={busyId === document.id}
                    onClick={() => void reviewDocument(document.id, 'rejected')}
                  >
                    Reject
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
