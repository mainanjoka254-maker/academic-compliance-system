import { useEffect, useState } from 'react'
import api from '@/services/api'

export default function Settings() {
  const [settings, setSettings] = useState<any>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get('/settings/me').then((r: any) => setSettings(r.data)).catch(() => setSettings(null))
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      await api.patch('/settings/me', settings)
    } finally {
      setSaving(false)
    }
  }

  if (!settings) return <div className="p-8">Loading settings...</div>

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <label className="block mb-4">
        Theme
        <select className="ml-4 border rounded px-2 py-1" value={settings.theme}
          onChange={(e) => setSettings({ ...settings, theme: e.target.value })}>
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </label>
      <label className="block mb-4">
        Language
        <input className="ml-4 border rounded px-2 py-1" value={settings.language}
          onChange={(e) => setSettings({ ...settings, language: e.target.value })} />
      </label>
      <label className="block mb-4">
        Timezone
        <input className="ml-4 border rounded px-2 py-1" value={settings.timezone}
          onChange={(e) => setSettings({ ...settings, timezone: e.target.value })} />
      </label>
      <label className="block mb-4">
        <input type="checkbox" checked={settings.email_notifications}
          onChange={(e) => setSettings({ ...settings, email_notifications: e.target.checked })} />
        <span className="ml-2">Email notifications</span>
      </label>
      <label className="block mb-4">
        <input type="checkbox" checked={settings.in_app_notifications}
          onChange={(e) => setSettings({ ...settings, in_app_notifications: e.target.checked })} />
        <span className="ml-2">In-app notifications</span>
      </label>
      <button onClick={save} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded">
        {saving ? 'Saving...' : 'Save'}
      </button>
    </div>
  )
}