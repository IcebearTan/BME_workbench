import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.BASE_URL.replace(/\/$/, '') + '/api',
  withCredentials: true,
  timeout: 12_000,
  headers: { Accept: 'application/json' },
})

export function apiError(error) {
  return {
    status: error?.response?.status || 0,
    code: error?.response?.data?.error?.code || 'SERVICE_UNAVAILABLE',
  }
}
