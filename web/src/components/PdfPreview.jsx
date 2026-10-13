import { useEffect, useRef, useState } from 'react'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { api } from '../api.js'

GlobalWorkerOptions.workerSrc = workerUrl

export default function PdfPreview({ preview }) {
  const [pdf, setPdf] = useState(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const canvas = useRef(null)
  useEffect(() => {
    let active = true
    const task = getDocument({ url: api.viewUrl(preview.scope, preview.id) })
    task.promise.then(doc => { if (active) setPdf(doc) }).catch(err => { if (active) { setError(err.message); setLoading(false) } })
    return () => { active = false; task.destroy() }
  }, [preview.scope, preview.id])
  useEffect(() => {
    if (!pdf) return
    let active = true
    let render
    setLoading(true)
    pdf.getPage(page).then(async sheet => {
      if (!active || !canvas.current) return
      const base = sheet.getViewport({ scale: 1 })
      const width = canvas.current.parentElement.clientWidth - 24
      const scale = Math.min(width / base.width, 2)
      const ratio = window.devicePixelRatio || 1
      const viewport = sheet.getViewport({ scale })
      canvas.current.width = Math.floor(viewport.width * ratio)
      canvas.current.height = Math.floor(viewport.height * ratio)
      canvas.current.style.width = `${viewport.width}px`
      canvas.current.style.height = `${viewport.height}px`
      render = sheet.render({ canvasContext: canvas.current.getContext('2d'), viewport,
        transform: ratio === 1 ? null : [ratio, 0, 0, ratio, 0, 0] })
      await render.promise
      if (active) setLoading(false)
    }).catch(err => { if (active) { setError(err.message); setLoading(false) } })
    return () => { active = false; render?.cancel() }
  }, [pdf, page])
  return <div className="pdf-reader">
    <div className="pdf-controls">
      <button className="mini-btn" disabled={!pdf || page === 1 || loading} onClick={() => setPage(page - 1)}>上一页</button>
      <span>{pdf ? `${page} / ${pdf.numPages}` : '加载 PDF…'}</span>
      <button className="mini-btn" disabled={!pdf || page === pdf.numPages || loading} onClick={() => setPage(page + 1)}>下一页</button>
    </div>
    {error ? <p role="alert">预览失败：{error}。可通过「在 Finder 中显示」打开原文件。</p> : <div className="pdf-page">{loading && <p className="muted">正在渲染…</p>}<canvas ref={canvas} aria-label={`PDF 第 ${page} 页`} /></div>}
  </div>
}
