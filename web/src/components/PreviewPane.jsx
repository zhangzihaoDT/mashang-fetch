import { formatSize } from '../utils.js'
import EmptyState from './EmptyState.jsx'
import PreviewBody from './PreviewBody.jsx'

function MetaRow({ preview }) {
  const { meta = {}, format, size, mtime } = preview
  const items = []
  if (meta.source) items.push(['Source', meta.source])
  if (meta.author) items.push(['Author', meta.author])
  if (meta.fetched_at) items.push(['Fetched', meta.fetched_at])
  if (items.length === 0) {
    items.push(['Type', format.toUpperCase()])
    items.push(['Size', formatSize(size)])
    if (mtime) items.push(['Modified', new Date(mtime).toLocaleString('zh-CN')])
  }
  return (
    <dl className="preview-meta">
      {items.map(([label, value]) => (
        <div className="meta-item" key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

export default function PreviewPane({ preview, loading }) {
  if (loading) {
    return (
      <section className="panel preview-panel">
        <p className="muted">加载中…</p>
      </section>
    )
  }

  if (!preview) {
    return (
      <section className="panel preview-panel">
        <EmptyState />
      </section>
    )
  }

  return (
    <section className="panel preview-panel">
      <div className="preview-head">
        <h2 className="preview-title">{preview.title}</h2>
      </div>
      <MetaRow preview={preview} />
      <PreviewBody preview={preview} />
    </section>
  )
}
