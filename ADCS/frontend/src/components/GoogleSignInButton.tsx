interface GoogleSignInButtonProps {
  label: string
  disabled?: boolean
  onClick: () => void
}

export default function GoogleSignInButton({
  label,
  disabled = false,
  onClick,
}: GoogleSignInButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex w-full items-center justify-center gap-3 rounded border border-gray-300 bg-white px-4 py-2.5 font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5">
        <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.2-2.27H12v4.3h6.44c-.28 1.4-1.12 2.58-2.38 3.38v2.77h3.86c2.26-2.08 3.57-5.14 3.57-8.18Z" />
        <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.95-2.9l-3.86-2.77c-1.07.72-2.44 1.15-4.09 1.15-3.14 0-5.8-2.12-6.75-4.97H1.27v2.85A12 12 0 0 0 12 24Z" />
        <path fill="#FBBC05" d="M5.25 14.51a7.2 7.2 0 0 1 0-5.02V6.64H1.27a12 12 0 0 0 0 10.72l3.98-2.85Z" />
        <path fill="#EA4335" d="M12 4.77c1.77 0 3.35.61 4.6 1.8l3.44-3.44C17.95 1.15 15.24 0 12 0A12 12 0 0 0 1.27 6.64l3.98 2.85C6.2 6.89 8.86 4.77 12 4.77Z" />
      </svg>
      <span>{label}</span>
    </button>
  )
}
