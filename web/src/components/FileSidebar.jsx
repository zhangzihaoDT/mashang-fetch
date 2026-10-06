import { useEffect, useMemo, useRef, useState } from 'react'

import { fileIcon, formatTime } from '../utils.js'

const SCOPES = [
  { value: 'workspace', label: 'Inbox', hint: '抓取结果，待整理' },
  { value: 'library', label: '资料库', hint: '长期保存' },
]

function dirOf(id) {
  const i = id.lastIndexOf('/')
  return i === -1 ? '' : id.slice(0, i)
}

function baseOf(id) {
  const i = id.lastIndexOf('/')
  return i === -1 ? id : id.slice(i + 1)
}

function stemOf(name) {
  return name.replace(/\.[^.]+$/, '')
}

export default function FileSidebar({
  scope,
  onScopeChange,
  lists,
  activeId,
  activeScope,
  libraryDir,
  onSelect,
  onRefresh,
  onKeep,
  onRename,
  onDelete,
  onBatch,
}) {
  const [query, setQuery] = useState('')
  const [expanded, setExpanded] = useState(() => new Set())
  const [selectMode, setSelectMode] = useState(false)
  const [selected, setSelected] = useState(() => new Set())
  const [renaming, setRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const listRef = useRef(null)

  useEffect(() => {
    setQuery('')
    setExpanded(new Set())
    setSelectMode(false)
    setSelected(new Set())
    setRenaming(false)
    setConfirming(false)
    setBusy(false)
    setError('')
  }, [scope])

  const files = lists[scope] || []
  const filtering = query.trim().length > 0
  const inWorkspace = scope === 'workspace'

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return files
    return files.filter(
      (f) => f.title.toLowerCase().includes(q) || f.name.toLowerCase().includes(q),
    )
  }, [files, query])

  const groups = useMemo(() => {
    const map = new Map()
    for (const f of filtered) {
      const dir = dirOf(f.id)
      if (!map.has(dir)) map.set(dir, [])
      map.get(dir).push(f)
    }
    return [...map.entries()]
      .map(([dir, items]) => ({ dir, items }))
      .sort((a, b) => (a.dir === '' ? -1 : b.dir === '' ? 1 : a.dir.localeCompare(b.dir)))
  }, [filtered])

  const visibleFiles = useMemo(() => {
    const list = []
    for (const { dir, items } of groups) {
      if (dir === '' || filtering || expanded.has(dir)) list.push(...items)
    }
    return list
  }, [groups, filtering, expanded])

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
      if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return
      if (selectMode || renaming) return
      const target = e.target
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.tagName === 'SELECT' ||
          target.isContentEditable)
      ) {
        return
      }
      if (visibleFiles.length === 0) return
      e.preventDefault()
      const currentIndex = visibleFiles.findIndex(
        (f) => f.id === activeId && activeScope === scope,
      )
      let nextIndex
      if (currentIndex === -1) {
        nextIndex = e.key === 'ArrowDown' ? 0 : visibleFiles.length - 1
      } else {
        nextIndex = currentIndex + (e.key === 'ArrowDown' ? 1 : -1)
        nextIndex = Math.max(0, Math.min(visibleFiles.length - 1, nextIndex))
      }
      const next = visibleFiles[nextIndex]
      if (next && !(next.id === activeId && activeScope === scope)) {
        onSelect(scope, next.id)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [visibleFiles, activeId, activeScope, scope, selectMode, renaming, onSelect])

  useEffect(() => {
    if (!activeId || activeScope !== scope) return
    const node = [...(listRef.current?.querySelectorAll('[data-file-id]') || [])].find(
      (el) => el.dataset.fileId === activeId,
    )
    if (node) node.scrollIntoView({ block: 'nearest' })
  }, [activeId, activeScope, scope])

  const selectedFiles = useMemo(
    () => files.filter((f) => selected.has(f.id)),
    [files, selected],
  )
  const count = selectedFiles.length
  const single = count === 1 ? selectedFiles[0] : null
  const allSelected = filtered.length > 0 && filtered.every((f) => selected.has(f.id))

  const reset = () => {
    setSelectMode(false)
    setSelected(new Set())
    setRenaming(false)
    setConfirming(false)
    setError('')
  }

  const openSelect = () => {
    setSelectMode(true)
    setSelected(new Set())
    setRenaming(false)
    setConfirming(false)
    setError('')
  }

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
    setRenaming(false)
    setConfirming(false)
    setError('')
  }

  const toggleAll = () => {
    setSelected(allSelected ? new Set() : new Set(filtered.map((f) => f.id)))
  }

  const toggleFolder = (dir) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(dir)) next.delete(dir)
      else next.add(dir)
      return next
    })
  }

  const startRename = () => {
    if (!single) return
    setRenameValue(stemOf(single.name))
    setRenaming(true)
    setConfirming(false)
    setError('')
  }

  const submitRename = async (e) => {
    e.preventDefault()
    if (!single) return
    const value = renameValue.trim()
    if (!value || value === stemOf(single.name)) {
      setRenaming(false)
      return
    }
    setBusy(true)
    setError('')
    try {
      await onRename(scope, single.id, value)
      reset()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const runKeep = async () => {
    setBusy(true)
    setError('')
    try {
      if (count === 1) await onKeep(single.id)
      else await onBatch(scope, 'move_to_library', selectedFiles.map((f) => f.id))
      reset()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const runDelete = async () => {
    setBusy(true)
    setError('')
    try {
      if (count === 1) await onDelete(scope, single.id)
      else await onBatch(scope, 'delete', selectedFiles.map((f) => f.id))
      reset()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const renderFile = (f) => {
    const isActive = f.id === activeId && activeScope === scope
    return (
      <div
        key={f.id}
        data-file-id={f.id}
        className={`file-item${isActive ? ' active' : ''}${selectMode ? ' selecting' : ''}`}
      >
        <div className="file-row">
          {selectMode && (
            <input
              type="checkbox"
              className="file-check"
              checked={selected.has(f.id)}
              onChange={() => toggleSelect(f.id)}
              aria-label={`选择 ${f.name}`}
            />
          )}
          <button
            className="file-main"
            type="button"
            onClick={() => (selectMode ? toggleSelect(f.id) : onSelect(scope, f.id))}
          >
            <span className="file-title">
              {fileIcon(f.format)} {f.title}
            </span>
            <span className="file-sub">
              {baseOf(f.id)} · {formatTime(f.mtime)}
            </span>
          </button>
        </div>
      </div>
    )
  }

  return (
    <aside className="panel files-panel">
      <div className="scope-tabs">
        {SCOPES.map((s) => (
          <button
            key={s.value}
            type="button"
            className={`scope-tab${s.value === scope ? ' active' : ''}`}
            onClick={() => onScopeChange(s.value)}
            title={s.hint}
          >
            <span className="scope-label">{s.label}</span>
            <span className="scope-count">{(lists[s.value] || []).length}</span>
          </button>
        ))}
      </div>

      <div className="panel-head">
        <button className="icon-btn" type="button" onClick={onRefresh} title="刷新列表">
          ↻
        </button>
        <input
          className="file-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={scope === 'library' ? '在资料库中搜索…' : '在 Inbox 中搜索…'}
          spellCheck={false}
        />
        {!selectMode ? (
          <button className="mini-btn" type="button" onClick={openSelect}>
            选择
          </button>
        ) : (
          <button className="mini-btn" type="button" onClick={reset} disabled={busy}>
            完成
          </button>
        )}
      </div>

      {selectMode && (
        <div className="files-toolbar">
          <div className="toolbar-top">
            <span className="toolbar-count">已选 {count} 个</span>
            <button className="toolbar-link" type="button" onClick={toggleAll} disabled={busy}>
              {allSelected ? '取消全选' : '全选'}
            </button>
          </div>

          {count === 0 && <p className="toolbar-hint">勾选文件后可批量处理。</p>}

          {count > 0 && !renaming && !confirming && (
            <div className="toolbar-actions">
              {inWorkspace && (
                <button
                  className="mini-btn primary"
                  type="button"
                  disabled={busy}
                  onClick={runKeep}
                  title={libraryDir ? `移入资料库：${libraryDir}` : '移入资料库'}
                >
                  {busy ? '处理中…' : '移入资料库'}
                </button>
              )}
              <button
                className="mini-btn"
                type="button"
                disabled={busy || !single}
                onClick={startRename}
                title={single ? '重命名文件名' : '批量不支持重命名'}
              >
                Rename
              </button>
              {single ? (
                <a
                  className="mini-btn"
                  href={`/api/download?scope=${encodeURIComponent(scope)}&id=${encodeURIComponent(single.id)}`}
                  download
                  title="下载一份"
                >
                  ↓ Download
                </a>
              ) : (
                <button className="mini-btn" type="button" disabled title="批量不支持下载">
                  ↓ Download
                </button>
              )}
              <button
                className="mini-btn danger"
                type="button"
                disabled={busy}
                onClick={() => setConfirming(true)}
              >
                Delete
              </button>
            </div>
          )}

          {renaming && single && (
            <form className="toolbar-rename" onSubmit={submitRename}>
              <input
                className="rename-input"
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                placeholder="新文件名（不含扩展名）"
                autoFocus
                spellCheck={false}
              />
              <button className="mini-btn primary" type="submit" disabled={busy}>
                确定
              </button>
              <button
                className="mini-btn"
                type="button"
                disabled={busy}
                onClick={() => setRenaming(false)}
              >
                取消
              </button>
            </form>
          )}

          {confirming && (
            <div className="toolbar-confirm">
              <p className="confirm-text">
                确定从{inWorkspace ? ' Inbox ' : '资料库'}永久删除 {count} 个文件？该操作不可恢复。
              </p>
              <ul className="batch-list">
                {selectedFiles.slice(0, 8).map((f) => (
                  <li key={f.id}>{f.name}</li>
                ))}
                {selectedFiles.length > 8 && <li>…等 {selectedFiles.length} 个</li>}
              </ul>
              <div className="toolbar-actions">
                <button
                  className="mini-btn danger"
                  type="button"
                  disabled={busy}
                  onClick={runDelete}
                >
                  {busy ? '删除中…' : '永久删除'}
                </button>
                <button
                  className="mini-btn"
                  type="button"
                  disabled={busy}
                  onClick={() => setConfirming(false)}
                >
                  取消
                </button>
              </div>
            </div>
          )}

          {error && <span className="confirm-error">{error}</span>}
        </div>
      )}

      <div className="file-list" ref={listRef}>
        {filtered.length === 0 && (
          <p className="muted small">
            {filtering
              ? '没有匹配的文件。'
              : scope === 'library'
                ? '资料库为空。把 Inbox 的文件「移入资料库」。'
                : '暂无文件，先 Fetch 一个链接。'}
          </p>
        )}
        {groups.map(({ dir, items }) => {
          if (dir === '') return items.map(renderFile)
          const open = filtering || expanded.has(dir)
          return (
            <div className="folder-group" key={dir}>
              <button
                className="folder-head"
                type="button"
                onClick={() => toggleFolder(dir)}
                title={dir}
              >
                <span className="folder-caret">{open ? '▾' : '▸'}</span>
                <span className="folder-name">{dir}</span>
                <span className="folder-count">{items.length}</span>
              </button>
              {open && <div className="folder-children">{items.map(renderFile)}</div>}
            </div>
          )
        })}
      </div>
    </aside>
  )
}
