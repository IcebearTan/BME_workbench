import { api } from './api/client.js'
import { store } from './store/index.js'

api.interceptors.request.use((config) => {
  if (!['get', 'head', 'options'].includes((config.method || 'get').toLowerCase()) && store.state.csrfToken) {
    config.headers['X-CSRF-Token'] = store.state.csrfToken
  }
  return config
})
export default api
