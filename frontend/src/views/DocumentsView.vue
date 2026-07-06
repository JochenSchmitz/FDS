<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import UploadZone from '../components/UploadZone.vue'
import { useDocumentsStore } from '../stores/documents'
import type { DocumentOut } from '../api'

const store = useDocumentsStore()

onMounted(async () => {
  await Promise.all([store.fetch(), store.fetchStatus()])
  if (store.busyCount > 0) store.ensurePolling()
})

// Live-Suche: ab dem 4. Zeichen sofort (debounced) suchen,
// bei leerem Feld wieder alle Dokumente zeigen.
let debounce = 0 as ReturnType<typeof setTimeout> | 0
watch(
  () => store.query,
  (q) => {
    if (debounce) clearTimeout(debounce)
    if (q.trim().length >= 4 || q.trim().length === 0) {
      debounce = setTimeout(() => store.fetch(), 250)
    }
  },
)
onUnmounted(() => {
  if (debounce) clearTimeout(debounce)
})

const statusLabel: Record<DocumentOut['status'], string> = {
  pending: '⏳ wartet',
  processing: '⚙️ liest …',
  done: '✅ fertig',
  error: '❌ Fehler',
}

function fmtSize(bytes: number): string {
  return bytes > 1048576
    ? `${(bytes / 1048576).toFixed(1)} MB`
    : `${Math.round(bytes / 1024)} kB`
}

function fmtDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString('de-DE') : '—'
}

async function remove(doc: DocumentOut) {
  if (confirm(`„${doc.filename}" wirklich löschen?`)) await store.remove(doc.id)
}
</script>

<template>
  <div class="page">
    <UploadZone />

    <div class="toolbar">
      <input
        v-model="store.query"
        type="search"
        placeholder="Live-Suche ab 4 Zeichen — Dateiname, Schlagworte, Volltext …"
      />
      <span v-if="store.query && store.query.trim().length < 4" class="hint">
        noch {{ 4 - store.query.trim().length }} Zeichen …
      </span>
      <span v-if="store.busyCount" class="busy">
        {{ store.busyCount }} in Arbeit …
      </span>
    </div>

    <div
      v-if="store.status && (store.status.processing.length || store.status.pending)"
      class="statusbar"
    >
      <span class="pulse" />
      <span v-if="store.status.processing.length">
        Liest gerade: <strong>{{ store.status.processing.join(', ') }}</strong>
        ({{ store.status.runningRequests }} Seiten parallel)
      </span>
      <span v-if="store.status.pending">
        · Warteschlange: {{ store.status.pending }}
      </span>
      <span class="tokens">
        {{ store.status.generatedTokens.toLocaleString('de-DE') }} Tokens erzeugt
        <template v-if="store.tokensPerSecond">
          — {{ store.tokensPerSecond }} Tokens/s
        </template>
      </span>
    </div>

    <p v-if="store.error" class="error">{{ store.error }}</p>

    <table v-if="store.docs.length">
      <thead>
        <tr>
          <th>Dokument</th>
          <th>Status</th>
          <th>Seiten</th>
          <th>Dok.-Datum</th>
          <th>Schlagworte</th>
          <th>Größe</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="doc in store.docs" :key="doc.id">
          <td>
            <RouterLink
              v-if="doc.status === 'done'"
              :to="{ name: 'viewer', params: { id: doc.id } }"
              class="doc-link"
            >{{ doc.filename }}</RouterLink>
            <span v-else>{{ doc.filename }}</span>
            <div v-if="doc.summary" class="summary">{{ doc.summary }}</div>
            <div v-if="doc.error" class="error">{{ doc.error }}</div>
          </td>
          <td>{{ statusLabel[doc.status] }}</td>
          <td>{{ doc.page_count ?? '—' }}</td>
          <td>{{ fmtDate(doc.doc_date) }}</td>
          <td>
            <span v-for="tag in doc.tags" :key="tag" class="tag">{{ tag }}</span>
          </td>
          <td>{{ fmtSize(doc.size_bytes) }}</td>
          <td class="actions">
            <a
              v-if="doc.status === 'done'"
              :href="`/api/documents/${doc.id}/file/docx`"
              title="Word-Datei herunterladen"
            ><button>.docx</button></a>
            <button
              v-if="doc.status === 'done' || doc.status === 'error'"
              title="Neu verarbeiten"
              @click="store.reprocess(doc.id)"
            >↻</button>
            <button title="Löschen" @click="remove(doc)">🗑</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!store.loading" class="empty">
      Noch keine Dokumente — einfach oben hochladen.
    </p>
  </div>
</template>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.toolbar {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.busy {
  color: var(--warn);
}
.hint {
  color: var(--text-dim);
  font-size: 0.85rem;
}
.statusbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.5rem 0.8rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-soft);
  font-size: 0.88rem;
}
.statusbar .tokens {
  margin-left: auto;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
}
.pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--ok);
  animation: pulse 1.2s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.35; transform: scale(0.75); }
}
table {
  width: 100%;
  border-collapse: collapse;
}
th {
  text-align: left;
  color: var(--text-dim);
  font-weight: 600;
  font-size: 0.85rem;
  border-bottom: 2px solid var(--border);
  padding: 0.4rem 0.6rem;
}
td {
  border-bottom: 1px solid var(--border);
  padding: 0.5rem 0.6rem;
  vertical-align: top;
}
.doc-link {
  color: var(--accent);
  font-weight: 600;
  text-decoration: none;
}
.doc-link:hover {
  text-decoration: underline;
}
.summary {
  color: var(--text-dim);
  font-size: 0.85rem;
  max-width: 42ch;
}
.tag {
  display: inline-block;
  background: var(--accent-bg);
  color: var(--accent);
  border-radius: 999px;
  padding: 0.05rem 0.55rem;
  font-size: 0.78rem;
  margin: 0 0.25rem 0.25rem 0;
  white-space: nowrap;
}
.actions {
  white-space: nowrap;
}
.actions > * {
  margin-left: 0.25rem;
}
.error {
  color: var(--err);
  font-size: 0.85rem;
}
.empty {
  color: var(--text-dim);
  text-align: center;
  padding: 2rem;
}
</style>
