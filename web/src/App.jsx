import { useCallback, useEffect, useReducer, useState } from 'react'

import { api } from './api.js'
import { initialState, reducer, STATUS } from './state.js'
import FetchBar from './components/FetchBar.jsx'
import FileSidebar from './components/FileSidebar.jsx'
import Header from './components/Header.jsx'
import PreviewPane from './components/PreviewPane.jsx'

const FALLBACK_FORMATS = [
  { label: 'Markdown', value: 'md' },
  { label: 'CSV', value: 'csv' },
]

const EMPTY_LISTS = { workspace: [], library: [] }

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState('md')
  const [formats, setFormats] = useState(FALLBACK_FORMATS)
  const [scope, setScope] = useState('workspace')
  const [lists, setLists] = useState(EMPTY_LISTS)
  const [dirs, setDirs] = useState({ workspace_dir: '', library_dir: '' })

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

  const runFetch = useCallback(async () => {
    if (!url.trim()) {
      dispatch({ type: 'fetch/error', error: '请先输入 URL' })
      return
    }
    dispatch({ type: 'fetch/start' })
    try {
      const result = await api.fetchUrl(url.trim(), format)
      if (!result.ok) {
        dispatch({ type: 'fetch/error', error: result.error || '转换失败' })
        return
      }
      const next = await loadFiles()
      const preview = await api.preview('workspace', result.file.id)
      setScope('workspace')
      dispatch({
        type: 'fetch/success',
        message: `已生成 ${result.file.name}`,
        files: next.workspace,
        preview,
      })
    } catch (err) {
      dispatch({ type: 'fetch/error', error: err.message })
    }
  }, [url, format, loadFiles])

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
      if (state.activeScope === targetScope && ids.includes(state.activeId)) {
        dispatch({ type: 'preview/clear' })
      }
      const done = result.succeeded.length
      const skipped = result.failed.length
      if (done === 0 && skipped > 0) {
        dispatch({ type: 'notice', error: result.failed[0].error })
      } else if (action === 'move_to_library') {
        dispatch({
          type: 'notice',
          message: `已移入资料库 ${done} 个文件${skipped ? `，跳过 ${skipped} 个同名文件` : ''}`,
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
        onUrlChange={setUrl}
        format={format}
        onFormatChange={setFormat}
        formats={formats}
        onFetch={runFetch}
        busy={state.status === STATUS.FETCHING}
        message={state.message}
        error={state.error}
      />

      <div className="workspace">
        <FileSidebar
          scope={scope}
          onScopeChange={setScope}
          lists={lists}
          activeId={state.activeId}
          activeScope={state.activeScope}
          libraryDir={dirs.library_dir}
          onSelect={selectFile}
          onRefresh={refresh}
          onKeep={keepFile}
          onRename={renameFile}
          onDelete={deleteFile}
          onBatch={batchFiles}
        />
        <PreviewPane preview={state.preview} loading={state.previewLoading} />
      </div>
    </div>
  )
}
