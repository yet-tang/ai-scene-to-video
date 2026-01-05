import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request Interceptor: Add Authorization Header
client.interceptors.request.use(
  (config) => {
    const apiKey = import.meta.env.VITE_API_KEY
    if (apiKey) {
      config.headers['Authorization'] = `ApiKey ${apiKey}`
    }
    // TODO: Hardcoded user ID for now, should be dynamic in production
    config.headers['X-User-Id'] = '123'
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response Interceptor: Basic Error Handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    // You can handle 401/403 here or just pass it to caller
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default client
