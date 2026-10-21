import { useState } from 'react'
import { api } from '../api.js'
import ResultPreview from './ResultPreview.jsx'

export default function SearchWorkspace({ onSaved, onSavedFile, renderSaved, savedCount = 0 }) {
  const [mode, setMode] = useState('results')
  const [angleFilter, setAngleFilter] = useState('')
  const [query, setQuery] = useState('')
  const [domains, setDomains] = useState('')
  const [after, setAfter] = useState('')
  const [before, setBefore] = useState('')
  const [timeIntent, setTimeIntent] = useState(null)
  const [results, setResults] = useState([])
  const [activeResultId, setActiveResultId] = useState(null)
  const [selected, setSelected] = useState([])
  const [searching, setSearching] = useState(false)
  const [getting, setGetting] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState('')
  const [states, setStates] = useState({})
  const [diagnostics, setDiagnostics] = useState(null)
  const reasonLabels = {source_mismatch: '来源不符', unknown_publication_date: '发布时间未知', publication_out_of_range: '发布时间超出范围', invalid_url: '链接无效', duplicate_url_in_query: '查询内重复链接', topic_mismatch: '主题不符', low_relevance_and_authority: '相关性与来源质量均偏低', timeout: '达到耗时上限', provider_error: '搜索服务失败', authentication: '凭据无效', balance: '账户余额不足', rate_limit: '服务限流', provider_http_error: '服务响应失败', connection: '连接失败', invalid_response: '响应格式无效'}
  function constraints() {
    return { query, domains: domains.split(/[,，\s]+/).filter(Boolean), after, before }
  }
  async function search(e) {
    e.preventDefault()
    setSearching(true); setError(''); setResults([]); setDiagnostics(null); setTimeIntent(null); setSearched(false); setSelected([]); setActiveResultId(null); setMode('results')
    try {
      const response = await api.search(constraints())
      setTimeIntent(response.diagnostics.time_intent); setDiagnostics(response.diagnostics); setResults(response.results); setSelected([]); setActiveResultId(response.results[0]?.id || null)
      setSearched(true); setAngleFilter('')
    } catch (err) { setError(err.message); if (err.diagnostics) { setDiagnostics(err.diagnostics); setTimeIntent(err.diagnostics.time_intent); setSearched(true) } }
    finally { setSearching(false) }
  }
  async function getSelected() {
    setGetting(true)
    let lastFile = null
    try {
      for (const item of results.filter(r => selected.includes(r.id) && states[r.id]?.status !== 'saved')) {
        setStates(s => ({ ...s, [item.id]: { status: 'loading' } }))
        try {
          const result = await api.fetchUrl(item.url, 'md')
          if (!result.ok || !result.file) throw new Error(result.error || '未获取到正文')
          lastFile = result.file
          setStates(s => ({ ...s, [item.id]: { status: 'saved', file: result.file } }))
          await onSaved?.()
        } catch (err) {
          setStates(s => ({ ...s, [item.id]: { status: 'error', error: err.message } }))
        }
      }
    } finally { setGetting(false) }
    if (lastFile) await onSavedFile?.(lastFile)
  }
  async function saveResult(item) {
    if (!item) return
    setGetting(true)
    setStates(s => ({ ...s, [item.id]: { status: 'loading' } }))
    try {
      const result = await api.fetchUrl(item.url, 'md')
      if (!result.ok || !result.file) throw new Error(result.error || '未获取到正文')
      setStates(s => ({ ...s, [item.id]: { status: 'saved', file: result.file } }))
      await onSaved?.()
      await onSavedFile?.(result.file)
      setMode('saved')
    } catch (err) {
      setStates(s => ({ ...s, [item.id]: { status: 'error', error: err.message } }))
    } finally { setGetting(false) }
  }
  const visibleResults = results.filter(r => !angleFilter || r.angles?.includes(angleFilter))
  const angles = [...new Set(results.flatMap(r => r.angles || []))]
  const selectable = visibleResults.filter(r => states[r.id]?.status !== 'saved')
  const count = selected.filter(id => states[id]?.status !== 'saved').length
  const activeResult = visibleResults.find(r => r.id === activeResultId) || visibleResults[0] || null
  return <>
    <form className="search-form" onSubmit={search}>
      <div className="fetch-bar">
        <input className="url-input" required aria-label="搜索问题" value={query} disabled={searching || getting} onChange={e => { setQuery(e.target.value); setTimeIntent(null) }} placeholder="描述你想了解的问题，例如：智己汽车 昨日发布" spellCheck={false} />
        <button className="btn primary" disabled={searching || getting}>{searching ? '搜索中…' : '搜索'}</button>
      </div>
      <details className="search-options">
        <summary>来源与日期条件</summary>
        <fieldset disabled={searching || getting}>
          <label>限定来源域名（最多两个）<input aria-label="限定来源域名" placeholder="例如 gov.cn, arxiv.org" value={domains} onChange={e => { setDomains(e.target.value); setTimeIntent(null) }} /></label>
          <div className="date-fields"><label>晚于<input type="date" aria-label="开始日期" value={after} onChange={e => { setAfter(e.target.value); setTimeIntent(null) }} /></label><label>早于<input type="date" aria-label="结束日期" value={before} onChange={e => { setBefore(e.target.value); setTimeIntent(null) }} /></label></div>
          <p className="muted">最多 6 次搜索；生成查询计划额外调用一次模型。日期未知的结果在限定日期时排除。</p>
        </fieldset>
      </details>
      {error && <p role="alert" className="confirm-error">{error}</p>}
    </form>
    {mode === 'results' && searching && <p className="muted" role="status">正在规划检索角度并搜索资料…</p>}
    {mode === 'results' && timeIntent && <p className="time-intent" role="status">检索时间：{timeIntent.label} · 北京时间。按网页发布时间筛选，事件发生日期仍需核对原文。</p>}
    {mode === 'results' && searched && diagnostics && <p className="muted" role="status">执行 {diagnostics.request_count} 次搜索，融合为 {diagnostics.returned_count} 条资料。{diagnostics.warnings?.length > 0 && '有检索提示，可在搜索详情查看。'}</p>}
    {mode === 'results' && searched && diagnostics && <details className="search-diagnostics"><summary>搜索详情</summary><p>已执行 {diagnostics.request_count} 次搜索 · 服务返回 {diagnostics.provider_count} 条 · 融合后 {diagnostics.returned_count} 条 · 合并重复 {diagnostics.duplicates_removed} 条</p><ul>{diagnostics.plan_issues?.map((issue, i) => <li key={`plan-${i}`}>查询规划：{issue.message}</li>)}{Object.entries(diagnostics.filter_reasons || {}).map(([reason, n]) => <li key={reason}>{reasonLabels[reason] || reason}：{n} 条候选</li>)}{Object.entries(diagnostics.failure_reasons || {}).map(([reason, n]) => <li key={`failure-${reason}`}>{reasonLabels[reason] || reason}：{n} 次查询</li>)}{diagnostics.content_duplicates_removed > 0 && <li>合并高度一致的内容：{diagnostics.content_duplicates_removed} 条，来源链接保留在结果详情。</li>}{diagnostics.warnings?.map((warning, i) => <li key={i}>{warning}</li>)}</ul><ol>{diagnostics.requests?.map((r, i) => <li key={i}>{r.angle && `${r.angle} · `}{r.query} — {r.error || `返回 ${r.provider_count}，符合条件 ${r.accepted_count}`}</li>)}</ol></details>}
    {mode === 'results' && !!angles.length && <div className="angle-filters"><button aria-pressed={!angleFilter} onClick={() => setAngleFilter('')}>全部角度 · {results.length}</button>{angles.map(angle => <button key={angle} aria-pressed={angleFilter === angle} onClick={() => setAngleFilter(angle)}>{angle} · {results.filter(r => r.angles?.includes(angle)).length}</button>)}</div>}

    <div className="workspace discovery-workspace">
      {mode === 'saved' ? renderSaved(() => setMode('results')) : <>
        <section className="panel search-list" aria-label="搜索结果">
          <div className="scope-tabs search-pane-tabs">
            <button type="button" className="scope-tab active">搜索结果<span className="scope-count">{results.length}</span></button>
            <button type="button" className="scope-tab" onClick={() => setMode('saved')}>已保存资料<span className="scope-count">{savedCount}</span></button>
          </div>
          <div className="search-list-head"><strong>{searched ? `${visibleResults.length} 条${angleFilter ? ` / 共 ${results.length} 条` : ''}` : '等待搜索'}</strong>
            {!!results.length && <label><input type="checkbox" disabled={getting || !selectable.length} checked={!!selectable.length && selectable.every(r => selected.includes(r.id))} onChange={e => { const checked = e.target.checked; setSelected(current => checked ? [...new Set([...current, ...selectable.map(r => r.id)])] : current.filter(id => !selectable.some(r => r.id === id))) }} /> 全选当前角度</label>}
          </div>
          <div className="search-items">
            {!results.length && <p className="empty-search">{searched ? (error ? '搜索未完成，请查看错误提示或搜索详情。' : diagnostics?.provider_count > 0 ? '搜索返回了候选，但没有符合来源与时间条件的资料。' : '搜索服务本次未返回匹配结果。可以调整关键词后重试。') : '输入问题并搜索，从不同角度发现资料。'}</p>}
            {visibleResults.map(item => <article key={item.id} className={`search-item${activeResult?.id === item.id ? ' active' : ''}`}>
              <input type="checkbox" aria-label={`选择 ${item.title}`} disabled={getting || states[item.id]?.status === 'saved'} checked={selected.includes(item.id)} onChange={e => setSelected(s => e.target.checked ? [...s, item.id] : s.filter(id => id !== item.id))} />
              <div><button type="button" className="result-title" onClick={() => setActiveResultId(item.id)}>{item.title}</button>
                <p className="result-meta">{item.site_name || new URL(item.url).hostname}{item.date && ` · ${new Date(item.date).toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' })}`}{' · '}<a href={item.url} target="_blank" rel="noreferrer">原文 ↗</a></p>
                <p className="angle-tags">{item.angles?.length ? item.angles.join(' · ') : '暂未确认内容角度'}</p><p className="result-snippet">{item.snippet}</p>
                <details className="result-evidence"><summary>命中 {item.matched_queries?.length || 1} 条查询 · 查看详情</summary><p>查询命中角度：{item.matched_angles?.join(' · ')}</p><p>内容标签依据：{Object.entries(item.angle_evidence || {}).map(([angle, evidence]) => `${angle}（${evidence.join('、')}）`).join('；') || '标题与摘要不足以确认角度'}</p><ul>{item.duplicate_sources?.map(source => <li key={source.url}>相同内容来源：<a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a></li>)}</ul><ul>{item.matched_queries?.map((q, i) => <li key={i}>{q}</li>)}</ul><a href={item.url} target="_blank" rel="noreferrer">{item.url}</a></details>
                {states[item.id]?.status === 'loading' && <p role="status">正在获取正文…</p>}
                {states[item.id]?.status === 'saved' && <p className="saved-state">已保存到 Inbox · 可在「已保存资料」中阅读</p>}
                {states[item.id]?.status === 'error' && <details className="confirm-error"><summary>获取失败 · 可重新勾选重试</summary>{states[item.id].error}</details>}
              </div>
            </article>)}
          </div>
          <div className="search-list-footer"><span>已选 {count} 条{angleFilter && `（当前角度 ${visibleResults.filter(r => selected.includes(r.id) && states[r.id]?.status !== 'saved').length} 条）`}</span><button className="btn primary" disabled={!count || getting || searching} onClick={getSelected}>{getting ? '获取中…' : '获取所选'}</button></div>
        </section>
        <ResultPreview
          item={activeResult}
          state={activeResult ? states[activeResult.id] : null}
          disabled={getting || searching}
          onSave={() => saveResult(activeResult)}
        />
      </>}
    </div>
  </>
}
