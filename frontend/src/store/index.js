import { createStore } from 'vuex'
import { api, apiError } from '../api/client.js'

export const store = createStore({
  state: () => ({
    identityState: 'unknown',
    actor: null,
    admission: null,
    permissions: [],
    csrfToken: null,
    provider: null,
    lastError: null,
  }),
  getters: {
    authenticated: (state) => state.identityState === 'authenticated',
    canManage: (state) => state.identityState === 'authenticated' && state.permissions.includes('governance:view'),
  },
  mutations: {
    acceptIdentity(state, data) {
      state.actor = data.actor
      state.admission = data.admission
      state.permissions = data.permissions || []
      state.csrfToken = data.csrf_token
      state.identityState = 'authenticated'
      state.lastError = null
    },
    setProvider(state, data) { state.provider = data },
    identityFailure(state, error) {
      state.lastError = error.code
      if (error.status === 401 || error.status === 403) {
        state.actor = null
        state.admission = null
        state.permissions = []
        state.csrfToken = null
        state.identityState = error.status === 401 ? 'anonymous' : 'forbidden'
      } else {
        // An unavailable provider says nothing about whether the session was revoked.
        // Retain the in-memory identity, but hide protected content until revalidation.
        state.identityState = 'unavailable'
      }
    },
    clearIdentity(state) {
      state.actor = null
      state.admission = null
      state.permissions = []
      state.csrfToken = null
      state.identityState = 'anonymous'
      state.lastError = null
    },
  },
  actions: {
    async loadProvider({ commit }) {
      try { commit('setProvider', (await api.get('/auth/status')).data) }
      catch { commit('setProvider', null) }
    },
    async refreshIdentity({ commit }) {
      try {
        const { data } = await api.get('/auth/me')
        if (!data.actor || data.admission?.community_active !== true || !Array.isArray(data.permissions) || !data.csrf_token) {
          commit('identityFailure', { status: 0, code: 'INVALID_IDENTITY_RESPONSE' })
          return
        }
        commit('acceptIdentity', data)
      } catch (error) { commit('identityFailure', apiError(error)) }
    },
    async logout({ state, commit }) {
      try {
        await api.post('/auth/logout', null, { headers: { 'X-CSRF-Token': state.csrfToken } })
        commit('clearIdentity')
        return true
      } catch (error) {
        if (apiError(error).status === 401) { commit('clearIdentity'); return true }
        // A failed request must not claim that the server session has ended.
        return false
      }
    },
  },
})
