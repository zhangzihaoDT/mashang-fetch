import { useCallback, useEffect, useReducer, useState } from 'react'

import { api } from './api.js'
import { initialState, reducer, STATUS } from './state.js'
import FetchBar from './components/FetchBar.jsx'
import FileSidebar from './components/FileSidebar.jsx'
import Header from './components/Header.jsx'
import PreviewPane from './components/PreviewPane.jsx'

const FALLBACK_FORMATS = [
  { label: '网页正文（Markdown）', value: 'md' },
  { label: '网页表格（CSV）', value: 'csv' },
  { label: 'PDF 附件', value: 'pdf' },
]

const EMPTY_LISTS = { workspace: [], library: [] }

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState('md')
  const [formats, setFormats] = useState(FALLBACK_FORMATS)
  const [pending, setPending] = useState(null)
  const [selected, setSelected] = useState([])
  const [scope, setScope] = useState('workspace')
  const [lists, setLists] = useState(EMPTY_LISTS)
  const [dirs, setDirs] = useState({ workspace_dir: '', library_dir: '' })
  const [openingInbox, setOpeningInbox] = useState(false)

  const openInbox = async (targetScope = scope, id) => {
    setOpeningInbox(true)
    try {
      await api.openInbox(targetScope, id)
    } catch (err) {
      dispatch({ type: 'notice', error: err.message })
    } finally {
      setOpeningInbox(false)
    }
  }

  const loadFiles = useCallback(async () => {
    const [workspace, library] = await Promise.all([api.files('workspace'), api.files('library')])
    const next = { workspace: workspace.files, library: library.files }
    setLists(next)
    return next
  }, [])

  useEffect(() => {
    api.formats().then((r) => setFormats(r.formats)).catch(() => {})
    api
      .config()
      .then((r) => setDirs(r))
      .catch(() => {})
    loadFiles().catch(() => {})
  }, [loadFiles])

  const selectFile = useCallback(async (targetScope, id) => {
    dispatch({ type: 'preview/loading', scope: targetScope, id })
    try {
      const preview = await api.preview(targetScope, id)
      dispatch({ type: 'preview/loaded', preview })
    } catch (err) {
      dispatch({ type: 'fetch/error', error: err.message })
    }
  }, [])

  const runFetch = useCallback(async (attachments) => {
    if (!url.trim()) {
      dispatch({ type: 'fetch/error', error: '请先输入 URL' })
      return
    }
    dispatch({ type: 'fetch/start' })
    try {
      const result = await api.fetchUrl(pending && attachments ? pending.source : url.trim(), attachments ? 'pdf' : format, attachments)
      if (!result.ok) {
        dispatch({ type: 'fetch/error', error: result.error || '转换失败' })
        return
      }
      if (result.needs_selection) {
        setPending(result)
        setSelected(result.attachments.map(item => item.url))
        dispatch({ type: 'fetch/selection' })
        return
      }
      setPending(null)
      const pdfFiles = (result.files || [result.file]).filter(file => file.format === 'pdf')
      const next = await loadFiles()
      const preview = await api.preview('workspace', result.file.id)
      setScope('workspace')
      dispatch({
        type: 'fetch/success',
        message: pdfFiles.length ? `已整理 ${pdfFiles.length} 个 PDF 到 Inbox${result.failed?.length ? '；失败：' + result.failed.map(item => item.name + '（' + item.error + '）').join('、') : ''}` : `已生成 ${result.file.name}`,
        files: next.workspace,
        preview,
      })
    } catch (err) {
      dispatch({ type: 'fetch/error', error: err.message })
    }
  }, [url, format, pending, loadFiles])

  const refresh = useCallback(async () => {
    const next = await loadFiles()
    if (
      state.activeScope &&
      state.activeId &&
      !next[state.activeScope].some((f) => f.id === state.activeId)
    ) {
      dispatch({ type: 'preview/clear' })
    }
  }, [loadFiles, state.activeScope, state.activeId])

  const keepFile = useCallback(
    async (id) => {
      try {
        const result = await api.keep(id)
        await loadFiles()
        if (state.activeScope === 'workspace' && state.activeId === id) {
          await selectFile('library', result.file.id)
        }
        dispatch({ type: 'notice', message: `已移入资料库：${result.file.name}` })
      } catch (err) {
        dispatch({ type: 'notice', error: err.message })
        throw err
      }
    },
    [loadFiles, selectFile, state.activeScope, state.activeId],
  )

  const renameFile = useCallback(
    async (targetScope, id, name) => {
      try {
        const result = await api.rename(targetScope, id, name)
        await loadFiles()
        if (state.activeScope === targetScope && state.activeId === id) {
          await selectFile(targetScope, result.file.id)
        }
        dispatch({ type: 'notice', message: `已重命名为 ${result.file.name}` })
      } catch (err) {
        dispatch({ type: 'notice', error: err.message })
        throw err
      }
    },
    [loadFiles, selectFile, state.activeScope, state.activeId],
  )

  const deleteFile = useCallback(
    async (targetScope, id) => {
      await api.remove(targetScope, id)
      const next = await loadFiles()
      if (state.activeScope === targetScope && state.activeId === id) {
        const prevList = lists[targetScope]
        const idx = prevList.findIndex((f) => f.id === id)
        const remaining = next[targetScope]
        const nextFile = remaining[Math.min(idx, remaining.length - 1)]
        if (nextFile) await selectFile(targetScope, nextFile.id)
        else dispatch({ type: 'preview/clear' })
      }
      dispatch({ type: 'notice', message: '已删除' })
    },
    [loadFiles, selectFile, lists, state.activeScope, state.activeId],
  )

  const batchFiles = useCallback(
    async (targetScope, action, ids) => {
      const result = await api.batch(targetScope, action, ids)
      await loadFiles()
      if (state.activeScope === targetScope && result.succeeded.includes(state.activeId)) {
        dispatch({ type: 'preview/clear' })
      }
      const done = result.succeeded.length
      const skipped = result.failed.length
      if (done === 0 && skipped > 0) {
        dispatch({ type: 'notice', error: result.failed[0].error })
      } else if (action === 'move_to_library') {
        dispatch({
          type: 'notice',
          message: `已移入资料库 ${done} 个文件${skipped ? `，未移入 ${skipped} 个：${result.failed.map(item => item.id + '（' + item.error + '）').join('、')}` : ''}`,
        })
      } else {
        dispatch({ type: 'notice', message: `已删除 ${done} 个文件` })
      }
      return result
    },
    [loadFiles, state.activeScope, state.activeId],
  )

  return (
    <div className="app">
      <Header />

      <FetchBar
        url={url}
        onUrlChange={(value) => { setUrl(value); setPending(null) }}
        format={format}
        onFormatChange={(value) => { setFormat(value); setPending(null) }}
        formats={formats}
        onFetch={() => runFetch()}
        busy={state.status === STATUS.FETCHING}
        message={state.message}
        error={state.error}
      />

      {pending && (
        <section className="panel" aria-label="PDF 附件选择">
          <h2>找到 {pending.attachments.length} 个 PDF 附件</h2>
          {pending.attachments.map(item => (
            <p key={item.url}>
              <label><input type="checkbox" checked={selected.includes(item.url)}
                disabled={state.status === STATUS.FETCHING}
                onChange={e => setSelected(e.target.checked ? [...selected, item.url] : selected.filter(link => link !== item.url))} /> {item.name}</label>
              {' '}<a href={item.url} target="_blank" rel="noreferrer">查看原链接</a>
            </p>
          ))}
          <button className="btn primary" disabled={!selected.length || state.status === STATUS.FETCHING} onClick={() => runFetch(selected)}>下载所选（{selected.length}）</button>
          {' '}<button className="btn" disabled={state.status === STATUS.FETCHING} onClick={() => runFetch(pending.attachments.map(item => item.url))}>全部下载</button>
          {' '}<button className="btn" disabled={state.status === STATUS.FETCHING} onClick={() => setPending(null)}>取消</button>
        </section>
      )}

      <div className="workspace">
        <FileSidebar
          scope={scope}
          onScopeChange={setScope}
          lists={lists}
          activeId={state.activeId}
          activeScope={state.activeScope}
          libraryDir={dirs.library_dir}
          directory={scope === 'workspace' ? dirs.workspace_dir : dirs.library_dir}
          onOpenFolder={() => openInbox(scope)}
          openingFolder={openingInbox}
          onSelect={selectFile}
          onRefresh={refresh}
          onKeep={keepFile}
          onRename={renameFile}
          onDelete={deleteFile}
          onBatch={batchFiles}
        />
        <PreviewPane key={`${state.activeScope}:${state.activeId}`} preview={state.preview} loading={state.previewLoading}
          onReveal={() => openInbox(state.activeScope, state.activeId)} onKeep={keepFile}
          onRename={renameFile} onDelete={deleteFile} />
      </div>
    </div>
  )
}
