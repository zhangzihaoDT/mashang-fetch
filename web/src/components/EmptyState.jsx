export default function EmptyState() {
  return (
    <div className="empty-state">
      <img className="empty-icon" src="/raccoon_avatar_light.png" alt="" aria-hidden="true" />
      <div className="empty-title">Paste a link to create a local file</div>
      <div className="empty-sub">输入 URL 并点击 Fetch，生成的文件会出现在左侧，点击即可预览。</div>
    </div>
  )
}
