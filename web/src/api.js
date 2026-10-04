const JSON_HEADERS = { 'Content-Type': 'application/json' }

async function parse(res) {
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  formats: () => fetch('/api/formats').then(parse),
  files: () => fetch('/api/files').then(parse),
  preview: (id) => fetch(`/api/preview?id=${encodeURIComponent(id)}`).then(parse),
  downloadUrl: (id) => `/api/download?id=${encodeURIComponent(id)}`,
  fetchUrl: (url, format) =>
    fetch('/api/fetch', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ url, format }),
    }).then(parse),
}
