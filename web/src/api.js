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
  openInbox: (scope = 'workspace', id) => fetch(`/api/open-inbox?scope=${encodeURIComponent(scope)}${id !== undefined ? '&id=' + encodeURIComponent(id) : ''}`, { method: 'POST' }).then(parse),
  viewUrl: (scope, id) => `/api/view?scope=${encodeURIComponent(scope)}&id=${encodeURIComponent(id)}`,
  config: () => fetch('/api/config').then(parse),
  formats: () => fetch('/api/formats').then(parse),
  files: (scope = 'workspace') =>
    fetch(`/api/files?scope=${encodeURIComponent(scope)}`).then(parse),
  preview: (scope, id) =>
    fetch(`/api/preview?scope=${encodeURIComponent(scope)}&id=${encodeURIComponent(id)}`).then(
      parse,
    ),
  downloadUrl: (scope, id) =>
    `/api/download?scope=${encodeURIComponent(scope)}&id=${encodeURIComponent(id)}`,
  fetchUrl: (url, format, attachments) =>
    fetch('/api/fetch', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ url, format, attachments }),
    }).then(parse),
  keep: (id) =>
    fetch('/api/keep', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ id }),
    }).then(parse),
  rename: (scope, id, name) =>
    fetch('/api/rename', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ scope, id, name }),
    }).then(parse),
  remove: (scope, id) =>
    fetch('/api/delete', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ scope, id }),
    }).then(parse),
  batch: (scope, action, ids) =>
    fetch('/api/batch', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ scope, action, ids }),
    }).then(parse),
}
