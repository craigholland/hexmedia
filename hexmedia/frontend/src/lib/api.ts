import axios from 'axios'

const baseURL = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000/api'
export const http = axios.create({
  baseURL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' }
})

// Convenience for GET with generics
export async function getJSON<T>(url: string, params?: Record<string, any>) {
  const { data } = await http.get<T>(url, { params })
  return data
}
export async function postJSON<T>(url: string, body?: any, params?: Record<string, any>) {
  const { data } = await http.post<T>(url, body, { params })
  return data
}
