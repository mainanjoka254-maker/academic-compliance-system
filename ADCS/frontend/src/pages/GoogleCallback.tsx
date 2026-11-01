import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { isAxiosError } from 'axios'

import { useAuth } from '@/contexts/AuthContext'

const errorMessages: Record<string, string> = {
  account_already_exists: 'An account with this email already exists. Sign in with that account, then link Google from your account settings.',
  account_link_required: 'Sign in with your existing ADCS account before linking Google.',
  account_not_linkable: 'This ADCS account is inactive or not yet verified.',
  account_verification_required: 'Verify your existing ADCS account before signing in with Google.',
  different_google_account_linked: 'A different Google account is already linked to this ADCS account.',
  google_account_already_linked: 'This Google account is already linked to a different ADCS account.',
  google_authorization_failed: 'Google sign-in was cancelled or could not be completed.',
  google_email_mismatch: 'The verified Google email must match your ADCS account email to link accounts.',
  google_identity_verification_failed: 'Google identity verification failed. Please try again.',
  institution_selection_required: 'Choose your institution on the registration page before creating an account with Google.',
  oauth_state_expired: 'The sign-in request expired. Please start again.',
  oauth_state_invalid: 'The sign-in request could not be verified. Please start again.',
}

export default function GoogleCallback() {
  const [searchParams] = useSearchParams()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const started = useRef(false)
  const navigate = useNavigate()
  const { completeGoogleLogin } = useAuth()

  useEffect(() => {
    if (started.current) return
    started.current = true
    if (searchParams.get('linked') === '1') {
      setLoading(false)
      setError('')
      window.setTimeout(() => navigate('/'), 1200)
      return
    }
    const code = searchParams.get('error')
    if (code) {
      setError(errorMessages[code] || 'Google sign-in could not be completed.')
      setLoading(false)
      return
    }
    completeGoogleLogin()
      .then(() => navigate('/'))
      .catch((requestError: unknown) => {
        const detail = isAxiosError<{ detail?: string }>(requestError)
          ? requestError.response?.data?.detail
          : undefined
        setError(detail || 'Could not complete the Google sign-in session. Please try again.')
        setLoading(false)
      })
  }, [completeGoogleLogin, navigate, searchParams])

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <section className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-lg">
        {loading ? (
          <>
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
            <h1 className="text-xl font-semibold">Completing sign-in…</h1>
          </>
        ) : searchParams.get('linked') === '1' ? (
          <h1 className="text-xl font-semibold text-green-700">Google account linked successfully.</h1>
        ) : (
          <>
            <h1 className="mb-3 text-xl font-semibold">Google sign-in could not be completed</h1>
            <p role="alert" className="mb-5 text-sm text-red-700">{error}</p>
            <div className="flex justify-center gap-4 text-sm">
              <Link to="/login" className="text-primary-600 hover:underline">Sign in</Link>
              <Link to="/register" className="text-primary-600 hover:underline">Create account</Link>
            </div>
          </>
        )}
      </section>
    </main>
  )
}
