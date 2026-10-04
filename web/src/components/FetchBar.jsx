export default function FetchBar({
  url,
  onUrlChange,
  format,
  onFormatChange,
  formats,
  onFetch,
  busy,
  message,
  error,
}) {
  return (
    <div className="fetch-area">
      <form
        className="fetch-bar"
        onSubmit={(e) => {
          e.preventDefault()
          onFetch()
        }}
      >
        <input
          className="url-input"
          value={url}
          onChange={(e) => onUrlChange(e.target.value)}
          placeholder="Paste URL, e.g. https://mp.weixin.qq.com/s/..."
          spellCheck={false}
        />
        <select
          className="format-select"
          value={format}
          onChange={(e) => onFormatChange(e.target.value)}
          aria-label="Format"
        >
          {formats.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
        <button className="btn primary" type="submit" disabled={busy}>
          {busy ? 'Fetching…' : 'Fetch'}
        </button>
      </form>

      <div className={`status-line${error ? ' error' : ''}`}>
        {error ? `✗ ${error}` : message ? `✓ ${message}` : ''}
      </div>
    </div>
  )
}
