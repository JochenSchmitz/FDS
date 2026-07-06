/** Lädt die OnlyOffice-DocsAPI einmalig und erzeugt Viewer-Instanzen. */

declare global {
  interface Window {
    DocsAPI?: {
      DocEditor: new (
        elementId: string,
        config: Record<string, unknown>,
      ) => { destroyEditor: () => void }
    }
  }
}

let loader: Promise<void> | null = null

export function loadDocsApi(onlyofficeUrl: string): Promise<void> {
  if (window.DocsAPI) return Promise.resolve()
  if (!loader) {
    loader = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = `${onlyofficeUrl}/web-apps/apps/api/documents/api.js`
      script.onload = () => resolve()
      script.onerror = () =>
        reject(new Error(`OnlyOffice nicht erreichbar: ${onlyofficeUrl}`))
      document.head.appendChild(script)
    })
  }
  return loader
}

export function createViewer(
  elementId: string,
  config: Record<string, unknown>,
): { destroyEditor: () => void } {
  if (!window.DocsAPI) throw new Error('DocsAPI nicht geladen')
  return new window.DocsAPI.DocEditor(elementId, {
    ...config,
    width: '100%',
    height: '100%',
    type: 'desktop',
  })
}
