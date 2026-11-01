import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import InstitutionManagementPanel from '@/components/InstitutionManagementPanel'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

describe('Super Administrator institution management', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.patch).mockReset()
  })

  it('creates a real institution through the authenticated institutions API', async () => {
    vi.mocked(api.get).mockImplementation((url) => Promise.resolve({
      data: url === '/institutions' ? [] : [],
    } as never))
    vi.mocked(api.post).mockResolvedValue({
      data: {
        id: 21,
        name: 'North University',
        code: 'NORTH',
        type: 'university',
        email: null,
        phone: null,
        address: null,
        country: null,
        is_active: true,
      },
    } as never)
    render(<InstitutionManagementPanel />)

    expect(await screen.findByText(/No institutions exist yet/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Institution name'), { target: { value: 'North University' } })
    fireEvent.change(screen.getByLabelText('Institution code'), { target: { value: 'NORTH' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create active institution' }))

    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/institutions', expect.objectContaining({
      name: 'North University',
      code: 'NORTH',
      type: 'university',
    })))
    expect(await screen.findByRole('status')).toHaveTextContent('Institution created and activated.')
  })

  it('surfaces institution loading failures rather than hiding them', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('backend unavailable'))
    render(<InstitutionManagementPanel />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Institutions could not be loaded.')
  })

  it('creates an institution administrator only through the institution-scoped API', async () => {
    const institution = {
      id: 21,
      name: 'North University',
      code: 'NORTH',
      type: 'university',
      email: null,
      phone: null,
      address: null,
      country: null,
      is_active: true,
    }
    vi.mocked(api.get).mockImplementation((url) => Promise.resolve({
      data: url === '/institutions' ? [institution] : [],
    } as never))
    vi.mocked(api.post).mockResolvedValue({
      data: { id: 31, email: 'admin@north.test', full_name: 'North Admin' },
    } as never)
    render(<InstitutionManagementPanel />)

    await screen.findByRole('option', { name: 'North University' })
    fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'North Admin' } })
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'admin@north.test' } })
    fireEvent.change(screen.getByLabelText(/Temporary password/), { target: { value: 'LongTemporaryPassword123!' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create institution administrator' }))

    await waitFor(() => expect(api.post).toHaveBeenCalledWith(
      '/institutions/21/administrators',
      expect.objectContaining({
        email: 'admin@north.test',
        full_name: 'North Admin',
        password: 'LongTemporaryPassword123!',
      }),
    ))
    expect(await screen.findByRole('status')).toHaveTextContent('Institution administrator created.')
  })
})
