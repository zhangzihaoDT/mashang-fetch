function hostOf(url) {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

function formatDate(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' })
  } catch {
    return ''
  }
}

export default function ResultPreview({ item, state, disabled, onSave }) {
  if (!item) {
    return (
      <section className="panel preview-panel result-preview-panel" aria-label="搜索结果预览">
        <div className="empty-state">
          <img className="empty-icon" src="/zh_monogram.png" alt="" aria-hidden="true" />
          <div className="empty-title">选择一条搜索结果</div>
          <div className="empty-sub">点击左侧结果标题，在这里查看摘要、检索依据，并保存到 Inbox。</div>
        </div>
      </section>
    )
  }
  const date = formatDate(item.date)
  const saved = state?.status === 'saved'
  const loading = state?.status === 'loading'
  return (
    <section className="panel preview-panel result-preview-panel" aria-label="搜索结果预览">
      <div className="preview-head"><h2 className="preview-title">{item.title}</h2></div>
      <p className="file-summary">
        摘要 · {item.site_name || hostOf(item.url)}
        {date && ` · ${date}`}
        {' · '}尚未获取正文
      </p>
      <div className="detail-actions">
        <a className="btn secondary" href={item.url} target="_blank" rel="noreferrer">打开原文 ↗</a>
        {saved ? (
          <span className="saved-state">已保存到 Inbox · 可在「已保存资料」中阅读</span>
        ) : (
          <button className="btn secondary" type="button" disabled={disabled || loading} onClick={onSave}>
            {loading ? '获取中…' : '保存到 Inbox'}
          </button>
        )}
      </div>
      {state?.status === 'error' && <p className="confirm-error" role="alert">{state.error}</p>}
      <p className="angle-tags">{item.angles?.length ? item.angles.join(' · ') : '暂未确认内容角度'}</p>
      <p className="result-snippet result-preview-snippet">{item.snippet}</p>
      <details className="source-details" open>
        <summary>检索依据</summary>
        <p>命中 {item.matched_queries?.length || 1} 条查询 · 内容标签：{Object.entries(item.angle_evidence || {}).map(([angle, evidence]) => `${angle}（${evidence.join('、')}）`).join('；') || '标题与摘要不足以确认角度'}</p>
        {!!item.matched_queries?.length && <ul>{item.matched_queries.map((query, i) => <li key={i}>{query}</li>)}</ul>}
        {!!item.duplicate_sources?.length && <ul>{item.duplicate_sources.map(source => <li key={source.url}>相同内容来源：<a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a></li>)}</ul>}
        <p><a href={item.url} target="_blank" rel="noreferrer">{item.url}</a></p>
      </details>
    </section>
  )
}
