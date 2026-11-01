import { useCallback, useEffect, useState } from 'react'
import api from '@/services/api'

type ComplianceReport = {
  as_of: string
  analysis_method: string
  summary: Record<string, number>
  findings: Record<string, Array<Record<string, unknown>>>
  recommendations: string[]
  limitations: string[]
}

const labels: Record<string, string> = {
  active_students: 'Active students',
  students_without_documents: 'Students without document uploads',
  incomplete_assessments: 'Incomplete assessments',
  overdue_assessments: 'Overdue assessments',
  upcoming_assessments: 'Upcoming assessments',
  courses_without_lecturer_submissions: 'Courses without lecturer submissions',
  students_at_elevated_risk: 'Students at elevated risk',
}

export default function ComplianceAnalysisPanel() {
  const [report, setReport] = useState<ComplianceReport | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState(false)

  const loadReport = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await api.get('/compliance/analysis')
      setReport(response.data)
    } catch (requestError: any) {
      setError(requestError.response?.data?.detail || 'Unable to load compliance analysis.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadReport() }, [loadReport])

  const downloadReport = async () => {
    setDownloading(true)
    setError('')
    try {
      const response = await api.get('/compliance/analysis.csv', { responseType: 'blob' })
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = 'adcs-compliance-report.csv'
      link.click()
      URL.revokeObjectURL(url)
    } catch (requestError: any) {
      setError(requestError.response?.data?.detail || 'Unable to download the compliance report.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <section className="space-y-4 rounded-xl bg-white p-5 shadow" aria-labelledby="compliance-analysis-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="compliance-analysis-title" className="text-lg font-semibold">Institution compliance analysis</h2>
          {report && <p className="text-sm text-gray-500">As of {report.as_of} · deterministic rules</p>}
        </div>
        <button type="button" onClick={() => void downloadReport()} disabled={!report || downloading}
          className="rounded bg-navy-900 px-4 py-2 text-white disabled:opacity-50">
          {downloading ? 'Preparing report…' : 'Download CSV'}
        </button>
      </div>
      {loading && <p role="status">Loading analysis…</p>}
      {error && <p role="alert" className="text-red-700">{error}</p>}
      {report && (
        <>
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(report.summary).map(([key, value]) => (
              <div key={key} className="rounded border p-3">
                <dt className="text-sm text-gray-600">{labels[key] || key.replace(/_/g, ' ')}</dt>
                <dd className="text-2xl font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
          <div>
            <h3 className="font-semibold">Recommended actions</h3>
            {report.recommendations.length
              ? <ul className="list-disc space-y-1 pl-5">{report.recommendations.map((item) => <li key={item}>{item}</li>)}</ul>
              : <p>No corrective actions were indicated by the available records.</p>}
          </div>
          <ul className="space-y-1 text-xs text-gray-500">
            {report.limitations.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </>
      )}
    </section>
  )
}
