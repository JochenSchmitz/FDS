<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import {
  mdiClose,
  mdiMagnify,
  mdiMenuDown,
  mdiMenuUp,
  mdiRefresh,
  mdiTagOutline,
} from '@mdi/js'
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
import { useLibraryColumns } from '../columns'

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

// Spalten-Layout (Reihenfolge + Breiten, persistent im localStorage)
const { cols, setWidth, moveColumn, reset } = useLibraryColumns()

// --- Spalten per Drag & Drop der Kopfzellen neu anordnen ---
let dragFrom = -1
const dragOver = ref(-1)
let resizing = false
let suppressClick = false

function onColDragStart(idx: number, e: DragEvent) {
  if (resizing) {
    e.preventDefault() // beim Breite-Ziehen keinen Spalten-Umzug starten
    return
  }
  dragFrom = idx
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}
function onColDragOver(idx: number) {
  dragOver.value = idx
}
function onColDrop(idx: number) {
  moveColumn(dragFrom, idx)
  dragFrom = -1
  dragOver.value = -1
  suppressClick = true // Klick direkt nach dem Ablegen nicht als Sortierung werten
}
function onColDragEnd() {
  dragFrom = -1
  dragOver.value = -1
}
function onHeaderClick(key: SortKey) {
  if (suppressClick) {
    suppressClick = false
    return
  }
  setSort(key)
}

// --- Spaltenbreite ziehen ---
let resizeKey: SortKey | '' = ''
let startX = 0
let startW = 0
function startResize(key: SortKey, width: number, e: PointerEvent) {
  resizing = true
  resizeKey = key
  startX = e.clientX
  startW = width
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
}
function onResizeMove(e: PointerEvent) {
  if (!resizeKey) return
  setWidth(resizeKey, startW + (e.clientX - startX))
}
function onResizeEnd(e: PointerEvent) {
  resizeKey = ''
  ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
  // resizing erst nach diesem Ereigniszyklus lösen, damit ein direkt
  // folgender dragstart noch unterdrückt wird
  setTimeout(() => (resizing = false), 0)
}
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
      <span class="spacer" />
      <button
        class="reset"
        title="Spaltenbreiten und -reihenfolge zurücksetzen"
        @click="reset"
      >
        <MdiIcon :path="mdiRefresh" :size="15" /> Spalten
      </button>
    </header>

    <div class="body">
      <p v-if="store.error" class="error">{{ store.error }}</p>
      <table v-if="doneDocs.length">
        <thead>
          <tr>
            <th
              v-for="(col, idx) in cols"
              :key="col.key"
              class="sortable"
              :class="{ dropzone: dragOver === idx }"
              :style="{ width: col.width + 'px' }"
              draggable="true"
              :title="`Nach ${col.label} sortieren · Kopf ziehen zum Verschieben`"
              @click="onHeaderClick(col.key)"
              @dragstart="onColDragStart(idx, $event)"
              @dragover.prevent="onColDragOver(idx)"
              @dragend="onColDragEnd"
              @drop="onColDrop(idx)"
            >
              <span class="th-label">{{ col.label }}</span>
              <MdiIcon
                v-if="sortKey === col.key"
                :path="sortDir === 1 ? mdiMenuUp : mdiMenuDown"
                :size="16"
              />
              <span
                class="col-resize"
                title="Breite ziehen"
                @click.stop
                @dragstart.prevent
                @pointerdown.stop="startResize(col.key, col.width, $event)"
                @pointermove="onResizeMove"
                @pointerup="onResizeEnd"
              />
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in doneDocs" :key="doc.id">
            <td
              v-for="col in cols"
              :key="col.key"
              :class="{
                imported: col.key === 'uploaded_at' || col.key === 'processed_at',
              }"
            >
              <template v-if="col.key === 'filename'">
                <RouterLink
                  :to="{ name: 'editor', params: { id: doc.id } }"
                  class="doc-link"
                  title="In OnlyOffice öffnen und bearbeiten"
                >{{ stem(doc.filename) }}</RouterLink>
                <div v-if="doc.summary" class="summary">{{ doc.summary }}</div>
              </template>
              <template v-else-if="col.key === 'page_count'">
                {{ doc.page_count ?? '—' }}
              </template>
              <template v-else-if="col.key === 'doc_date'">
                {{ fmtDate(doc.doc_date) }}
              </template>
              <template v-else-if="col.key === 'uploaded_at'">
                {{ fmtDateTime(doc.uploaded_at) }}
              </template>
              <template v-else-if="col.key === 'processed_at'">
                {{ doc.processed_at ? fmtDateTime(doc.processed_at) : '—' }}
              </template>
              <template v-else-if="col.key === 'tags'">
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
              </template>
              <template v-else-if="col.key === 'entities'">
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
              </template>
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
.spacer {
  flex: 1;
}
.reset {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.82rem;
  color: var(--text-dim);
}
.body {
  overflow: auto;
  min-height: 0;
  flex: 1;
}
table {
  border-collapse: collapse;
  table-layout: fixed;
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
  overflow: hidden;
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
th.dropzone {
  box-shadow: inset 3px 0 0 var(--accent);
}
.th-label {
  pointer-events: none; /* Text soll den Drag der Kopfzelle nicht stören */
}
.col-resize {
  position: absolute;
  top: 0;
  right: 0;
  width: 9px;
  height: 100%;
  cursor: col-resize;
}
.col-resize::before {
  content: '';
  position: absolute;
  right: 3px;
  top: 20%;
  height: 60%;
  width: 2px;
  background: transparent;
}
th:hover .col-resize::before {
  background: var(--border);
}
.col-resize:hover::before {
  background: var(--accent);
}
.imported {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
td {
  border-bottom: 1px solid var(--border);
  padding: 0.5rem 0.6rem;
  vertical-align: top;
  overflow: hidden;
  word-break: break-word;
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
