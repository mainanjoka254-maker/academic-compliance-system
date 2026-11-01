import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '@/services/api'

interface User { id: number; email: string; full_name: string; institution_id?: number; roles: string[]; is_active: boolean; is_verified: boolean }

interface AuthCtx {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  completeGoogleLogin: () => Promise<void>
  logout: () => void
  loading: boolean
}

const Ctx = createContext<AuthCtx>({} as any)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('adcs_token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      api.get('/auth/me').then((r) => setUser(r.data)).catch(() => { localStorage.removeItem('adcs_token'); setToken(null) }).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token])

  const login = async (email: string, password: string) => {
    const r = await api.post('/auth/login', { email, password })
    localStorage.setItem('adcs_token', r.data.access_token)
    setToken(r.data.access_token)
    const me = await api.get('/auth/me')
    setUser(me.data)
  }

  const completeGoogleLogin = async () => {
    const r = await api.post('/auth/google/session', {}, { withCredentials: true })
    localStorage.setItem('adcs_token', r.data.access_token)
    setToken(r.data.access_token)
    const me = await api.get('/auth/me')
    setUser(me.data)
  }

  const logout = () => {
    localStorage.removeItem('adcs_token')
    setToken(null)
    setUser(null)
  }

  return <Ctx.Provider value={{ user, token, login, completeGoogleLogin, logout, loading }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
