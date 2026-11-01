import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ComplianceAnalysisPanel from '@/components/ComplianceAnalysisPanel'
import LecturerManagementPanel from '@/components/LecturerManagementPanel'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}))

const lecturerFixture = {
  id: 12,
  user_id: 41,
  staff_number: 'STAFF-12',
  full_name: 'Ada Lecturer',
  email: 'ada@example.test',
  phone: null,
  title: null,
  specialization: null,
  department_id: null,
  is_active: true,
  courses: [],
  programs: [],
}
const courseFixture = { id: 3, code: 'CS101', name: 'Foundations of Computing' }
const programFixture = {
  id: 6,
  code: 'BSC-COMP',
  name: 'BSc Computing',
  faculty_id: 2,
  department_id: 4,
  award_level: 'Bachelor',
}

describe('lecturer management and compliance workflows', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.put).mockReset()
    vi.mocked(api.patch).mockReset()
  })

  it('persists a teaching allocation and reports API failures', async () => {
    vi.mocked(api.get).mockImplementation((url) => Promise.resolve({
      data: url === '/lecturers'
        ? [lecturerFixture]
        : url === '/courses'
          ? [courseFixture]
          : url === '/academic-structure/programmes'
            ? [programFixture]
            : [],
    } as never))
    vi.mocked(api.put).mockResolvedValue({ data: lecturerFixture } as never)
    render(<LecturerManagementPanel />)

    const allocationCheckbox = await screen.findByLabelText(/CS101 - Foundations of Computing/)
    await act(async () => { await new Promise((resolve) => window.setTimeout(resolve, 0)) })
    fireEvent.click(allocationCheckbox)
    await waitFor(() => expect(allocationCheckbox).toBeChecked())
    fireEvent.click(screen.getByRole('button', { name: 'Save teaching allocation' }))
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/lecturers/12/courses', { course_ids: [3] }))

    fireEvent.click(await screen.findByLabelText(/BSC-COMP - BSc Computing/))
    fireEvent.click(screen.getByRole('button', { name: 'Save programme assignments' }))
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/lecturers/12/programs', { program_ids: [6] }))

    vi.mocked(api.get).mockRejectedValue({ response: { data: { detail: 'Lecturer API unavailable' } } })
    render(<LecturerManagementPanel />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Lecturer API unavailable')
  })

  it('renders database-backed compliance totals and explanatory limits', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        as_of: '2026-03-10',
        analysis_method: 'deterministic_rules',
        summary: {
          active_students: 4,
          students_without_documents: 1,
          incomplete_assessments: 2,
          overdue_assessments: 1,
          upcoming_assessments: 1,
          courses_without_lecturer_submissions: 1,
          students_at_elevated_risk: 1,
        },
        findings: {},
        recommendations: ['Contact the students with incomplete work.'],
        limitations: ['Mandatory document types are not configured.'],
      },
    } as never)
    render(<ComplianceAnalysisPanel />)

    expect(await screen.findByText('Students without document uploads')).toBeInTheDocument()
    expect(screen.getByText('Contact the students with incomplete work.')).toBeInTheDocument()
    expect(screen.getByText('Mandatory document types are not configured.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download CSV' })).toBeEnabled()
  })

  it('surfaces unauthorized compliance-analysis responses', async () => {
    vi.mocked(api.get).mockRejectedValue({ response: { data: { detail: 'Insufficient permissions' } } })
    render(<ComplianceAnalysisPanel />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Insufficient permissions')
  })
})
