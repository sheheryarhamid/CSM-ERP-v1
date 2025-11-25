import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

// attach token if present
client.interceptors.request.use(cfg => {
  const token = localStorage.getItem('hub_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export default client
