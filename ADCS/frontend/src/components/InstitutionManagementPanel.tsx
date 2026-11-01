import { FormEvent, useEffect, useState } from 'react'
import { isAxiosError } from 'axios'

import api from '@/services/api'

type Institution = {
  id: number
  name: string
  code: string
  type: string
  email: string | null
  phone: string | null
  address: string | null
  country: string | null
  is_active: boolean
}

type InstitutionAdmin = {
  id: number
  email: string
  full_name: string
  is_active: boolean
  is_verified: boolean
}

const emptyInstitutionForm = {
  name: '',
  code: '',
  type: 'university',
  email: '',
  phone: '',
  address: '',
  country: '',
}

function errorMessage(error: unknown, fallback: string) {
  if (isAxiosError<{ detail?: string }>(error)) {
    return error.response?.data?.detail ?? fallback
  }
  return fallback
}

export default function InstitutionManagementPanel() {
  const [institutions, setInstitutions] = useState<Institution[]>([])
  const [selectedId, setSelectedId] = useState<number | ''>('')
  const [admins, setAdmins] = useState<InstitutionAdmin[]>([])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(emptyInstitutionForm)
  const [adminForm, setAdminForm] = useState({ email: '', full_name: '', password: '', phone: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const selected = institutions.find((institution) => institution.id === selectedId)

  async function loadInstitutions(preferredId?: number) {
    setLoading(true)
    setError('')
    try {
      const response = await api.get<Institution[]>('/institutions')
      setInstitutions(response.data)
      setSelectedId((current) => {
        const desiredId = preferredId ?? current
        return desiredId && response.data.some((institution) => institution.id === desiredId)
          ? desiredId
          : response.data[0]?.id ?? ''
      })
    } catch (requestError) {
      setError(errorMessage(requestError, 'Institutions could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadInstitutions()
  }, [])

  useEffect(() => {
    if (!selectedId) {
      setAdmins([])
      return
    }
    api.get<InstitutionAdmin[]>(`/institutions/${selectedId}/administrators`)
      .then((response) => setAdmins(response.data))
      .catch((requestError: unknown) => setError(errorMessage(requestError, 'Institution administrators could not be loaded.')))
  }, [selectedId])

  function editInstitution(institution: Institution) {
    setEditingId(institution.id)
    setSelectedId(institution.id)
    setForm({
      name: institution.name,
      code: institution.code,
      type: institution.type,
      email: institution.email ?? '',
      phone: institution.phone ?? '',
      address: institution.address ?? '',
      country: institution.country ?? '',
    })
    setError('')
    setNotice('')
  }

  async function saveInstitution(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    const payload = {
      ...form,
      email: form.email || undefined,
      phone: form.phone || undefined,
      address: form.address || undefined,
      country: form.country || undefined,
    }
    try {
      if (editingId) {
        await api.patch(`/institutions/${editingId}`, payload)
        setNotice('Institution details updated.')
      } else {
        const response = await api.post<Institution>('/institutions', payload)
        await loadInstitutions(response.data.id)
        setNotice('Institution created and activated.')
      }
      setEditingId(null)
      setForm(emptyInstitutionForm)
      if (editingId) {
        await loadInstitutions(editingId)
      }
    } catch (requestError) {
      setError(errorMessage(requestError, 'Institution could not be saved.'))
    } finally {
      setSaving(false)
    }
  }

  async function toggleInstitution(institution: Institution) {
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await api.patch(`/institutions/${institution.id}/activate`, null, {
        params: { is_active: !institution.is_active },
      })
      setNotice(`Institution ${institution.is_active ? 'deactivated' : 'activated'}.`)
      await loadInstitutions()
    } catch (requestError) {
      setError(errorMessage(requestError, 'Institution status could not be changed.'))
    } finally {
      setSaving(false)
    }
  }

  async function createAdmin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected || !selected.is_active) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await api.post(`/institutions/${selected.id}/administrators`, {
        ...adminForm,
        phone: adminForm.phone || undefined,
      })
      setAdminForm({ email: '', full_name: '', password: '', phone: '' })
      setNotice('Institution administrator created.')
      const response = await api.get<InstitutionAdmin[]>(`/institutions/${selected.id}/administrators`)
      setAdmins(response.data)
    } catch (requestError) {
      setError(errorMessage(requestError, 'Institution administrator could not be created.'))
    } finally {
      setSaving(false)
    }
  }

  async function toggleAdmin(admin: InstitutionAdmin) {
    if (!selected) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      await api.patch(`/institutions/${selected.id}/administrators/${admin.id}`, {
        is_active: !admin.is_active,
      })
      setNotice(`Administrator ${admin.is_active ? 'deactivated' : 'activated'}.`)
      const response = await api.get<InstitutionAdmin[]>(`/institutions/${selected.id}/administrators`)
      setAdmins(response.data)
    } catch (requestError) {
      setError(errorMessage(requestError, 'Administrator status could not be changed.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-6 rounded-xl bg-white p-5 shadow" aria-label="Institution management">
      <div>
        <h2 className="text-xl font-semibold">Institution management</h2>
        <p className="mt-1 text-sm text-gray-600">
          Create real institutions, control registration availability, and manage institution administrators.
        </p>
      </div>
      {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {notice && <p role="status" className="rounded bg-green-50 p-3 text-sm text-green-700">{notice}</p>}

      <div className="grid gap-6 xl:grid-cols-2">
        <div>
          <h3 className="mb-3 font-semibold">Registered institutions</h3>
          {loading ? <p role="status">Loading institutions…</p> : institutions.length === 0 ? (
            <p className="rounded bg-amber-50 p-3 text-sm text-amber-900">
              No institutions exist yet. Create the first one below; public users cannot create institutions.
            </p>
          ) : (
            <ul className="divide-y rounded border">
              {institutions.map((institution) => (
                <li key={institution.id} className="flex flex-wrap items-center justify-between gap-3 p-3">
                  <button
                    type="button"
                    onClick={() => setSelectedId(institution.id)}
                    className="text-left"
                    aria-pressed={selectedId === institution.id}
                  >
                    <span className="block font-medium">{institution.name} ({institution.code})</span>
                    <span className="text-sm text-gray-600">{institution.is_active ? 'Active' : 'Inactive'}</span>
                  </button>
                  <div className="flex gap-2">
                    <button type="button" className="rounded border px-3 py-1 text-sm" onClick={() => editInstitution(institution)}>Edit</button>
                    <button type="button" disabled={saving} className="rounded border px-3 py-1 text-sm disabled:opacity-60" onClick={() => void toggleInstitution(institution)}>
                      {institution.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <form onSubmit={saveInstitution} className="space-y-3 rounded border p-4">
          <h3 className="font-semibold">{editingId ? 'Edit institution' : 'Create institution'}</h3>
          <label className="block text-sm">Institution name
            <input required minLength={2} maxLength={255} className="mt-1 w-full rounded border px-3 py-2" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">Institution code
              <input required minLength={2} maxLength={50} pattern="[A-Za-z0-9_-]+" className="mt-1 w-full rounded border px-3 py-2" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} />
            </label>
            <label className="block text-sm">Type
              <select className="mt-1 w-full rounded border px-3 py-2" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}>
                <option value="university">University</option>
                <option value="college">College</option>
              </select>
            </label>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">Contact email
              <input type="email" className="mt-1 w-full rounded border px-3 py-2" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
            </label>
            <label className="block text-sm">Phone
              <input type="tel" maxLength={50} className="mt-1 w-full rounded border px-3 py-2" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
            </label>
          </div>
          <label className="block text-sm">Address
            <input maxLength={2000} className="mt-1 w-full rounded border px-3 py-2" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
          </label>
          <label className="block text-sm">Country
            <input maxLength={100} className="mt-1 w-full rounded border px-3 py-2" value={form.country} onChange={(event) => setForm({ ...form, country: event.target.value })} />
          </label>
          <div className="flex gap-2">
            <button disabled={saving} className="rounded bg-primary-600 px-4 py-2 text-white disabled:opacity-60">
              {saving ? 'Saving…' : editingId ? 'Save changes' : 'Create active institution'}
            </button>
            {editingId && <button type="button" className="rounded border px-4 py-2" onClick={() => { setEditingId(null); setForm(emptyInstitutionForm) }}>Cancel edit</button>}
          </div>
        </form>
      </div>

      <div className="border-t pt-5">
        <h3 className="mb-3 font-semibold">Institution administrators</h3>
        <label className="mb-4 block max-w-lg text-sm">Choose institution
          <select aria-label="Administrator institution" className="mt-1 w-full rounded border px-3 py-2" value={selectedId} onChange={(event) => setSelectedId(event.target.value ? Number(event.target.value) : '')}>
            <option value="">Select an institution</option>
            {institutions.map((institution) => <option key={institution.id} value={institution.id}>{institution.name}</option>)}
          </select>
        </label>
        {!selected ? <p className="text-sm text-gray-600">Create an institution before assigning an administrator.</p> : (
          <div className="grid gap-5 lg:grid-cols-2">
            <ul className="divide-y rounded border">
              {admins.length === 0 && <li className="p-3 text-sm text-gray-600">No institution administrators.</li>}
              {admins.map((admin) => (
                <li key={admin.id} className="flex items-center justify-between gap-3 p-3">
                  <div>
                    <p className="font-medium">{admin.full_name}</p>
                    <p className="text-sm text-gray-600">{admin.email} · {admin.is_active ? 'Active' : 'Inactive'}</p>
                  </div>
                  <button type="button" disabled={saving} className="rounded border px-3 py-1 text-sm disabled:opacity-60" onClick={() => void toggleAdmin(admin)}>
                    {admin.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </li>
              ))}
            </ul>
            <form onSubmit={createAdmin} className="space-y-3 rounded border p-4">
              <h4 className="font-medium">Create administrator for {selected.name}</h4>
              {!selected.is_active && <p role="status" className="text-sm text-amber-800">Activate the institution before adding an administrator.</p>}
              <label className="block text-sm">Full name
                <input required minLength={2} maxLength={255} className="mt-1 w-full rounded border px-3 py-2" value={adminForm.full_name} onChange={(event) => setAdminForm({ ...adminForm, full_name: event.target.value })} />
              </label>
              <label className="block text-sm">Email
                <input type="email" required className="mt-1 w-full rounded border px-3 py-2" value={adminForm.email} onChange={(event) => setAdminForm({ ...adminForm, email: event.target.value })} />
              </label>
              <label className="block text-sm">Temporary password (12+ characters)
                <input type="password" required minLength={12} maxLength={128} autoComplete="new-password" className="mt-1 w-full rounded border px-3 py-2" value={adminForm.password} onChange={(event) => setAdminForm({ ...adminForm, password: event.target.value })} />
              </label>
              <label className="block text-sm">Phone
                <input type="tel" maxLength={50} className="mt-1 w-full rounded border px-3 py-2" value={adminForm.phone} onChange={(event) => setAdminForm({ ...adminForm, phone: event.target.value })} />
              </label>
              <button disabled={saving || !selected.is_active} className="rounded bg-primary-600 px-4 py-2 text-white disabled:opacity-60">
                {saving ? 'Saving…' : 'Create institution administrator'}
              </button>
            </form>
          </div>
        )}
      </div>
    </section>
  )
}
