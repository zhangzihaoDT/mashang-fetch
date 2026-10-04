import { fileIcon, formatTime } from '../utils.js'

export default function FileSidebar({ files, activeId, onSelect, onRefresh }) {
  return (
    <aside className="panel files-panel">
      <div className="panel-head">
        <h2>Files</h2>
        <button className="icon-btn" type="button" onClick={onRefresh} title="刷新列表">
          ↻
        </button>
      </div>

      <div className="file-list">
        {files.length === 0 && <p className="muted small">暂无文件，先 Fetch 一个链接。</p>}
        {files.map((f) => (
          <button
            key={f.id}
            type="button"
            className={`file-item${f.id === activeId ? ' active' : ''}`}
            onClick={() => onSelect(f.id)}
          >
            <span className="file-title">
              {fileIcon(f.format)} {f.title}
            </span>
            <span className="file-sub">
              {f.format.toUpperCase()} · {formatTime(f.mtime)}
            </span>
          </button>
        ))}
      </div>
    </aside>
  )
}
