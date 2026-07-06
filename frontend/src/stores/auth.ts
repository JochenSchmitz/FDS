import { defineStore } from 'pinia'

async function post(url: string, body?: unknown): Promise<Response> {
  return fetch(url, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    email: null as string | null,
    checked: false,
    error: '' as string,
  }),

  getters: {
    loggedIn: (s) => s.email !== null,
  },

  actions: {
    /** Beim App-Start: gibt es eine gültige Sitzung (Cookie)? */
    async check() {
      if (this.checked) return
      try {
        const resp = await fetch('/api/auth/me')
        this.email = resp.ok ? (await resp.json()).email : null
      } catch {
        this.email = null
      } finally {
        this.checked = true
      }
    },

    async login(email: string, password: string): Promise<boolean> {
      this.error = ''
      const resp = await post('/api/auth/login', { email, password })
      if (!resp.ok) {
        this.error =
          resp.status === 401
            ? 'E-Mail oder Passwort falsch'
            : `Anmeldung fehlgeschlagen (${resp.status})`
        return false
      }
      this.email = (await resp.json()).email
      return true
    },

    async logout() {
      await post('/api/auth/logout')
      this.email = null
    },
  },
})
