<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { mdiClose, mdiMagnify, mdiMenuDown, mdiMenuUp, mdiTagOutline } from '@mdi/js'
import MdiIcon from '../components/MdiIcon.vue'
import type { DocumentEntity } from '../api'
import { useDocumentsStore } from '../stores/documents'
import {
  ROLE_LABEL,
  entityLabel,
  fmtDate,
  fmtDateTime,
  stem,
  useDocSort,
  type SortKey,
} from '../docsort'

const store = useDocumentsStore()

/** Zusatzangaben eines Beteiligten als Tooltip (Firma · Anschrift · …). */
function entityTitle(e: DocumentEntity): string {
  return [e.company, e.address, e.phone, e.email].filter(Boolean).join(' · ')
}

onMounted(async () => {
  await store.fetch()
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
      debounce = setTimeout(() => store.search(), 250)
    }
  },
)
onUnmounted(() => {
  if (debounce) clearTimeout(debounce)
})

// Sortierung: Klick auf Spaltenkopf, zweiter Klick dreht die Richtung
const { sortKey, sortDir, setSort, sorted: doneDocs } = useDocSort(() =>
  (store.results ?? store.docs).filter((d) => d.status === 'done'),
)
</script>

<template>
  <div class="library">
    <header class="head">
      <span class="title">Dokumente ({{ doneDocs.length }})</span>
      <span class="search">
        <MdiIcon :path="mdiMagnify" :size="16" />
        <input
          v-model="store.query"
          type="search"
          placeholder="Live-Suche ab 4 Zeichen — Name, Schlagworte, Volltext …"
        />
        <span v-if="store.query && store.query.trim().length < 4" class="hint">
          noch {{ 4 - store.query.trim().length }} Zeichen …
        </span>
      </span>
      <span v-if="store.selectedTags.length" class="tag-filter">
        <button
          v-for="tag in store.selectedTags"
          :key="tag"
          class="tag active"
          :class="{ unreadable: tag === 'Unlesbar' }"
          title="Filter entfernen"
          @click="store.toggleTag(tag)"
        >
          <MdiIcon :path="mdiTagOutline" :size="13" />
          {{ tag }}
          <MdiIcon :path="mdiClose" :size="13" />
        </button>
      </span>
    </header>

    <div class="body">
      <p v-if="store.error" class="error">{{ store.error }}</p>
      <table v-if="doneDocs.length">
        <thead>
          <tr>
            <th
              v-for="col in ([
                ['filename', 'Dokument'],
                ['page_count', 'Seiten'],
                ['doc_date', 'Dok.-Datum'],
                ['uploaded_at', 'Importiert am'],
                ['processed_at', 'Verarbeitet am'],
                ['tags', 'Schlagworte'],
                ['entities', 'Beteiligte'],
              ] as [SortKey, string][])"
              :key="col[0]"
              class="sortable"
              :title="`Nach ${col[1]} sortieren`"
              @click="setSort(col[0])"
            >
              {{ col[1] }}
              <MdiIcon
                v-if="sortKey === col[0]"
                :path="sortDir === 1 ? mdiMenuUp : mdiMenuDown"
                :size="16"
              />
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in doneDocs" :key="doc.id">
            <td>
              <RouterLink
                :to="{ name: 'editor', params: { id: doc.id } }"
                class="doc-link"
                title="In OnlyOffice öffnen und bearbeiten"
              >{{ stem(doc.filename) }}</RouterLink>
              <div v-if="doc.summary" class="summary">{{ doc.summary }}</div>
            </td>
            <td>{{ doc.page_count ?? '—' }}</td>
            <td>{{ fmtDate(doc.doc_date) }}</td>
            <td class="imported">{{ fmtDateTime(doc.uploaded_at) }}</td>
            <td class="imported">
              {{ doc.processed_at ? fmtDateTime(doc.processed_at) : '—' }}
            </td>
            <td>
              <button
                v-for="tag in doc.tags"
                :key="tag"
                class="tag"
                :class="{
                  active: store.selectedTags.includes(tag),
                  unreadable: tag === 'Unlesbar',
                }"
                :title="store.selectedTags.includes(tag)
                  ? 'Filter entfernen'
                  : 'Nach diesem Schlagwort filtern'"
                @click="store.toggleTag(tag)"
              >{{ tag }}</button>
            </td>
            <td>
              <ul v-if="doc.entities.length" class="ents">
                <li
                  v-for="(e, i) in doc.entities"
                  :key="i"
                  :title="entityTitle(e)"
                >
                  <span class="erole" :class="e.role">{{ ROLE_LABEL[e.role] }}</span>
                  {{ entityLabel(e) }}
                </li>
              </ul>
              <span v-else class="dim">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">
        Noch keine fertigen Dokumente —
        <RouterLink :to="{ name: 'upload' }">zum Upload</RouterLink>.
      </p>
    </div>
  </div>
</template>

<style scoped>
.library {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0.8rem 1.2rem;
  gap: 0.5rem;
}
.head {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.title {
  font-weight: 600;
}
.search {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.search input {
  min-width: 24rem;
  padding: 0.25rem 0.6rem;
}
.hint {
  color: var(--text-dim);
  font-size: 0.8rem;
}
.body {
  overflow: auto;
  min-height: 0;
  flex: 1;
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
  position: sticky;
  top: 0;
  background: var(--bg);
}
th.sortable {
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
th.sortable:hover {
  color: var(--text);
}
th.sortable :deep(svg) {
  vertical-align: -3px;
}
.imported {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
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
  max-width: 72ch;
}
.tag {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  background: var(--accent-bg);
  color: var(--accent);
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 0.05rem 0.55rem;
  font-size: 0.78rem;
  margin: 0 0.25rem 0.25rem 0;
  white-space: nowrap;
  cursor: pointer;
}
.tag:hover {
  border-color: var(--accent);
}
.tag.active {
  background: var(--accent);
  color: #fff;
}
.tag.unreadable {
  background: rgba(220, 38, 38, 0.12);
  color: var(--err);
}
.tag.unreadable:hover {
  border-color: var(--err);
}
.tag.unreadable.active {
  background: var(--err);
  color: #fff;
}
.tag-filter {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.15rem;
}
.ents {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  font-size: 0.82rem;
  max-width: 26ch;
}
.ents li {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
  min-width: 0;
}
.ents li > :last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.erole {
  flex-shrink: 0;
  border-radius: 999px;
  padding: 0 0.4rem;
  font-size: 0.68rem;
  font-weight: 600;
  background: var(--bg-soft);
  color: var(--text-dim);
  border: 1px solid var(--border);
}
.erole.sender {
  background: var(--accent-bg);
  color: var(--accent);
  border-color: transparent;
}
.erole.recipient {
  background: rgba(22, 163, 74, 0.12);
  color: var(--ok);
  border-color: transparent;
}
.dim {
  color: var(--text-dim);
}
.error {
  color: var(--err);
}
.empty {
  color: var(--text-dim);
  text-align: center;
  padding: 2rem;
}
</style>
