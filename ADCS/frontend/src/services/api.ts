import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    config.headers.setContentType(false)
  }
  const token = localStorage.getItem('adcs_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const url = err.config?.url || ''
    const publicAuthFlow = [
      '/auth/login',
      '/auth/register',
      '/auth/verify-otp',
      '/auth/resend-otp',
      '/auth/forgot-password',
      '/auth/reset-password',
      '/auth/google/session',
      '/auth/google/status',
    ].some((path) => url.startsWith(path))
    if (err.response?.status === 401 && localStorage.getItem('adcs_token') && !publicAuthFlow) {
      localStorage.removeItem('adcs_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
