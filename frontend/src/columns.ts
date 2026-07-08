/** Spalten-Layout der Bibliothekstabelle: Reihenfolge + Breiten.
 *
 * Persistent im localStorage — pro Browser/Gerät, da es (noch) keine
 * serverseitige Benutzerverwaltung gibt. Bei Versionsdrift (Spalten
 * kommen/gehen) werden unbekannte Keys verworfen und neue hinten
 * angehängt, sodass ein alter gespeicherter Stand nie kaputtgeht.
 */
import { computed, reactive, ref, watch } from 'vue'
import type { SortKey } from './docsort'

export interface ColumnDef {
  key: SortKey
  label: string
  defaultWidth: number
}

// Reihenfolge hier = Standardreihenfolge
const COLUMNS: ColumnDef[] = [
  { key: 'filename', label: 'Dokument', defaultWidth: 340 },
  { key: 'page_count', label: 'Seiten', defaultWidth: 72 },
  { key: 'doc_date', label: 'Dok.-Datum', defaultWidth: 110 },
  { key: 'uploaded_at', label: 'Importiert am', defaultWidth: 130 },
  { key: 'processed_at', label: 'Verarbeitet am', defaultWidth: 130 },
  { key: 'tags', label: 'Schlagworte', defaultWidth: 200 },
  { key: 'entities', label: 'Beteiligte', defaultWidth: 240 },
]
const BY_KEY = new Map(COLUMNS.map((c) => [c.key, c]))
const DEFAULT_ORDER = COLUMNS.map((c) => c.key)
const MIN_WIDTH = 50
const STORAGE_KEY = 'fds.library.columns.v1'

interface Persisted {
  order: SortKey[]
  widths: Partial<Record<SortKey, number>>
}

function load(): Persisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const p = JSON.parse(raw) as Persisted
      const known = (p.order ?? []).filter((k) => BY_KEY.has(k))
      const order = [...known, ...DEFAULT_ORDER.filter((k) => !known.includes(k))]
      const widths: Partial<Record<SortKey, number>> = {}
      for (const k of order) {
        const w = p.widths?.[k]
        if (typeof w === 'number' && w >= MIN_WIDTH) widths[k] = w
      }
      return { order, widths }
    }
  } catch {
    /* defekter Eintrag -> Standard */
  }
  return { order: [...DEFAULT_ORDER], widths: {} }
}

export function useLibraryColumns() {
  const initial = load()
  const order = ref<SortKey[]>(initial.order)
  const widths = reactive<Partial<Record<SortKey, number>>>(initial.widths)

  watch(
    [order, widths],
    () => {
      try {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ order: order.value, widths }),
        )
      } catch {
        /* localStorage nicht verfügbar -> Einstellung bleibt für diese Sitzung */
      }
    },
    { deep: true },
  )

  const cols = computed(() =>
    order.value.map((key) => {
      const def = BY_KEY.get(key)!
      return { ...def, width: widths[key] ?? def.defaultWidth }
    }),
  )

  function setWidth(key: SortKey, px: number) {
    widths[key] = Math.max(MIN_WIDTH, Math.round(px))
  }

  function moveColumn(from: number, to: number) {
    if (from === to || from < 0 || to < 0) return
    const next = [...order.value]
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    order.value = next
  }

  function reset() {
    order.value = [...DEFAULT_ORDER]
    for (const k of Object.keys(widths) as SortKey[]) delete widths[k]
  }

  return { cols, setWidth, moveColumn, reset }
}
