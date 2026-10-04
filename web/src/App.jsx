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

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState('md')
  const [formats, setFormats] = useState(FALLBACK_FORMATS)

  const loadFiles = useCallback(async () => {
    const { files } = await api.files()
    dispatch({ type: 'files/loaded', files })
    return files
  }, [])

  useEffect(() => {
    api.formats().then((r) => setFormats(r.formats)).catch(() => {})
    loadFiles().catch(() => {})
  }, [loadFiles])

  const selectFile = useCallback(async (id) => {
    dispatch({ type: 'preview/loading', id })
    try {
      const preview = await api.preview(id)
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
      const files = await loadFiles()
      const preview = await api.preview(result.file.id)
      dispatch({
        type: 'fetch/success',
        message: `已生成 ${result.file.name}`,
        files,
        preview,
      })
    } catch (err) {
      dispatch({ type: 'fetch/error', error: err.message })
    }
  }, [url, format, loadFiles])

  const refresh = useCallback(async () => {
    const files = await loadFiles()
    if (state.activeId && !files.some((f) => f.id === state.activeId)) {
      dispatch({ type: 'preview/clear' })
    }
  }, [loadFiles, state.activeId])

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
          files={state.files}
          activeId={state.activeId}
          onSelect={selectFile}
          onRefresh={refresh}
        />
        <PreviewPane
          preview={state.preview}
          loading={state.previewLoading}
          status={state.status}
        />
      </div>
    </div>
  )
}
