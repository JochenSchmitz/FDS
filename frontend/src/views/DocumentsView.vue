<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import UploadZone from '../components/UploadZone.vue'
import { useDocumentsStore } from '../stores/documents'
import type { DocumentOut } from '../api'

const store = useDocumentsStore()

onMounted(async () => {
  await store.fetch()
  if (store.busyCount > 0) store.ensurePolling()
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
        placeholder="Suche in Dateiname, Schlagworten, Zusammenfassung …"
        @keyup.enter="store.fetch()"
      />
      <button @click="store.fetch()">Suchen</button>
      <span v-if="store.busyCount" class="busy">
        {{ store.busyCount }} in Arbeit …
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
