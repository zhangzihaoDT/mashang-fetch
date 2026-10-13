import { useState } from 'react'
import { formatSize } from '../utils.js'
import { api } from '../api.js'
import EmptyState from './EmptyState.jsx'
import PreviewBody from './PreviewBody.jsx'

export default function PreviewPane({ preview, loading, onReveal, onKeep, onRename, onDelete }) {
  const [mode, setMode] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  if (loading) return <section className="panel preview-panel"><p className="muted">加载中…</p></section>
  if (!preview) return <section className="panel preview-panel"><EmptyState /></section>
  const { meta = {} } = preview
  const run = async (action) => {
    setBusy(true)
    setError('')
    try { await action(); setMode('') } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  const fetched = meta.fetched_at || preview.mtime
  return (
    <section className={`panel preview-panel${preview.kind === 'pdf' ? ' pdf-panel' : ''}`}>
      <div className="preview-head"><h2 className="preview-title">{preview.title}</h2></div>
      <p className="file-summary">{preview.format.toUpperCase()} · {formatSize(preview.size)}
        {fetched && ` · ${new Date(fetched).toLocaleString('zh-CN')}`}</p>
      <div className="detail-actions">
        <button className="btn secondary" disabled={busy} onClick={() => run(onReveal)}>在 Finder 中显示</button>
        {preview.scope === 'workspace' && <button className="btn secondary" disabled={busy} onClick={() => run(() => onKeep(preview.id))}>移入资料库</button>}
        <details className="more-actions">
          <summary>更多 ⋯</summary>
          <div className="more-menu">
            <button disabled={busy} onClick={() => { setName(preview.name.replace(/\.[^.]+$/, '')); setMode('rename') }}>重命名</button>
            <a href={api.downloadUrl(preview.scope, preview.id)} download={preview.name}>下载副本</a>
            <button className="danger" disabled={busy} onClick={() => setMode('delete')}>删除</button>
          </div>
        </details>
      </div>
      {mode === 'rename' && <form className="detail-edit" onSubmit={e => { e.preventDefault(); run(() => onRename(preview.scope, preview.id, name)) }}>
        <input className="rename-input" value={name} onChange={e => setName(e.target.value)} aria-label="新文件名" autoFocus />
        <button className="mini-btn primary" disabled={busy || !name.trim()}>保存</button>
        <button className="mini-btn" type="button" disabled={busy} onClick={() => setMode('')}>取消</button>
      </form>}
      {mode === 'delete' && <div className="detail-edit"><span>永久删除「{preview.title}」？</span>
        <button className="mini-btn danger" disabled={busy} onClick={() => run(() => onDelete(preview.scope, preview.id))}>确认删除</button>
        <button className="mini-btn" disabled={busy} onClick={() => setMode('')}>取消</button>
      </div>}
      {error && <p className="confirm-error" role="alert">{error}</p>}
      <details className="source-details">
        <summary>来源信息</summary>
        <dl className="preview-meta">
          <div className="meta-item"><dt>文件名</dt><dd>{preview.name}</dd></div>
          {meta.source && <div className="meta-item"><dt>来源页面</dt><dd><a href={meta.source} target="_blank" rel="noreferrer">{meta.source}</a></dd></div>}
          {meta.download_url && <div className="meta-item"><dt>附件地址</dt><dd><a href={meta.download_url} target="_blank" rel="noreferrer">{meta.download_url}</a></dd></div>}
          {meta.author && <div className="meta-item"><dt>作者</dt><dd>{meta.author}</dd></div>}
        </dl>
      </details>
      <div className="preview-content"><PreviewBody preview={preview} /></div>
    </section>
  )
}
