import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Login from '@/pages/Login'
import Register from '@/pages/Register'
import api from '@/services/api'

const { login } = vi.hoisted(() => ({ login: vi.fn() }))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ login }),
}))

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

function renderPage(page: React.ReactNode) {
  return render(<MemoryRouter>{page}</MemoryRouter>)
}

describe('authentication pages', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
    login.mockReset()
  })

  it('submits email and password, and displays a login failure', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { enabled: true } } as never)
    login.mockRejectedValue(new Error('login failed'))
    renderPage(<Login />)

    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'student@example.test' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'not-the-password' } })
    fireEvent.click(screen.getByRole('button', { name: /^Sign in$/ }))

    await waitFor(() => expect(login).toHaveBeenCalledWith('student@example.test', 'not-the-password'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Sign-in failed.')
    expect(await screen.findByRole('button', { name: 'Sign in with Google' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Show password' }))
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'text')
  })

  it('shows Google as unavailable when backend credentials are not configured', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { enabled: false } } as never)
    renderPage(<Login />)

    expect(await screen.findByText('Google Sign-In is not configured.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in with Google' })).toBeDisabled()
  })

  it('explains why registration is unavailable when no active institutions exist', async () => {
    vi.mocked(api.get).mockImplementation((url) => Promise.resolve({
      data: url.includes('registration-options') ? [] : { enabled: false },
    } as never))
    renderPage(<Register />)

    expect(await screen.findByText(/No active institutions are available yet/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create student account' })).toBeDisabled()
  })

  it('rejects mismatched registration passwords before posting', async () => {
    vi.mocked(api.get).mockImplementation((url) => Promise.resolve({
      data: url.includes('registration-options') ? [{ id: 8, name: 'Example University' }] : { enabled: true },
    } as never))
    renderPage(<Register />)

    await screen.findByRole('option', { name: 'Example University' })
    fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Test Student' } })
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'new@example.test' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'StrongPass123!' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'DifferentPass123!' } })
    fireEvent.change(screen.getByLabelText('Institution'), { target: { value: '8' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create student account' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match.')
    expect(api.post).not.toHaveBeenCalled()
    expect(await screen.findByRole('button', { name: 'Continue with Google' })).toBeEnabled()
  })

  it('submits a valid student registration to the existing authentication API', async () => {
    vi.mocked(api.get).mockImplementation((url) => Promise.resolve({
      data: url.includes('registration-options') ? [{ id: 8, name: 'Example University' }] : { enabled: true },
    } as never))
    vi.mocked(api.post).mockResolvedValue({ data: { message: 'registered' } } as never)
    renderPage(<Register />)

    await screen.findByRole('option', { name: 'Example University' })
    fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Test Student' } })
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'new@example.test' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'StrongPass123!' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'StrongPass123!' } })
    fireEvent.change(screen.getByLabelText('Institution'), { target: { value: '8' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create student account' }))

    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/auth/register', {
      email: 'new@example.test',
      phone: undefined,
      password: 'StrongPass123!',
      full_name: 'Test Student',
      institution_id: 8,
      role_requested: 'student',
    }))
  })

  it('submits lecturer registration as a pending approval request', async () => {
    vi.mocked(api.get).mockImplementation((url) => Promise.resolve({
      data: url.includes('registration-options') ? [{ id: 8, name: 'Example University' }] : { enabled: true },
    } as never))
    vi.mocked(api.post).mockResolvedValue({ data: { message: 'request saved' } } as never)
    renderPage(<Register />)

    await screen.findByRole('option', { name: 'Example University' })
    fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Test Lecturer' } })
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'lecturer@example.test' } })
    fireEvent.change(screen.getByLabelText('Account type'), { target: { value: 'lecturer' } })
    fireEvent.change(screen.getByLabelText('Staff / employee number'), { target: { value: 'STAFF-8' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'StrongPass123!' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'StrongPass123!' } })
    fireEvent.change(screen.getByLabelText('Institution'), { target: { value: '8' } })
    fireEvent.click(screen.getByRole('button', { name: 'Submit account request' }))

    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/auth/register', {
      email: 'lecturer@example.test',
      phone: undefined,
      password: 'StrongPass123!',
      full_name: 'Test Lecturer',
      institution_id: 8,
      role_requested: 'lecturer',
      staff_number: 'STAFF-8',
    }))
    expect(await screen.findByText(/institution must approve the request/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeDisabled()
  })
})
