import { defineStore } from 'pinia'
import {
  api,
  type AppConfig,
  type DocumentOut,
  type ProcessingStatus,
} from '../api'

export const useDocumentsStore = defineStore('documents', {
  state: () => ({
    docs: [] as DocumentOut[],
    query: '',
    loading: false,
    uploading: false,
    error: '' as string,
    config: null as AppConfig | null,
    pollTimer: 0 as ReturnType<typeof setInterval> | 0,
    status: null as ProcessingStatus | null,
    tokensPerSecond: 0,
    lastTokenSample: null as { tokens: number; at: number } | null,
  }),

  getters: {
    busyCount: (s) =>
      s.docs.filter((d) => d.status === 'pending' || d.status === 'processing')
        .length,
  },

  actions: {
    async loadConfig() {
      if (!this.config) this.config = await api.config()
      return this.config
    },

    async fetch() {
      this.loading = true
      try {
        this.docs = await api.list(this.query)
        this.error = ''
      } catch (e) {
        this.error = (e as Error).message
      } finally {
        this.loading = false
      }
    },

    async upload(files: File[]) {
      if (!files.length) return
      this.uploading = true
      try {
        await api.upload(files)
        this.error = ''
        await this.fetch()
        this.ensurePolling()
      } catch (e) {
        this.error = (e as Error).message
      } finally {
        this.uploading = false
      }
    },

    async remove(id: string) {
      await api.remove(id)
      await this.fetch()
    },

    async reprocess(id: string) {
      await api.reprocess(id)
      await this.fetch()
      this.ensurePolling()
    },

    /** Lebenszeichen: was wird verarbeitet, wie viele Tokens fließen? */
    async fetchStatus() {
      try {
        const s = await api.status()
        if (this.lastTokenSample && s.generatedTokens >= this.lastTokenSample.tokens) {
          const seconds = (Date.now() - this.lastTokenSample.at) / 1000
          if (seconds > 0) {
            this.tokensPerSecond = Math.round(
              (s.generatedTokens - this.lastTokenSample.tokens) / seconds,
            )
          }
        }
        this.lastTokenSample = { tokens: s.generatedTokens, at: Date.now() }
        this.status = s
      } catch {
        /* Statusanzeige ist unkritisch */
      }
    },

    /** Solange Dokumente in Arbeit sind, Liste + Status alle 5 s aktualisieren. */
    ensurePolling() {
      if (this.pollTimer) return
      this.pollTimer = setInterval(async () => {
        await Promise.all([this.fetch(), this.fetchStatus()])
        if (this.busyCount === 0 && this.pollTimer) {
          clearInterval(this.pollTimer)
          this.pollTimer = 0
        }
      }, 5000)
    },
  },
})
