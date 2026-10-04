import MarkdownPreview from './MarkdownPreview.jsx'

function DataTable({ header = [], rows = [] }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {header.map((cell, i) => (
              <th key={i}>{cell}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, c) => (
                <td key={c}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function PreviewBody({ preview }) {
  switch (preview.kind) {
    case 'markdown':
      return <MarkdownPreview content={preview.content} />
    case 'table':
      return <DataTable header={preview.header} rows={preview.rows} />
    case 'json':
    case 'text':
      return <pre className="code-block">{preview.content}</pre>
    default:
      return <p className="muted">{preview.error || '无法预览该文件'}</p>
  }
}
