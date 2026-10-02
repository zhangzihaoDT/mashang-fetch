[用户输入链接]
       ↓
[Resolver]    识别域名 / 选择抓取策略
       ↓
[Extractor]   axios 或 puppeteer 抓取 + 正文/表格抽取
       ↓
[Normalizer]  结构化文档：title / source / author / fetched_at / body / tables
       ↓
[Exporter]    导出 .md / .csv
       ↓
[本地文件]    output/{时间}_{标题}.{md|csv}
       ↓
[Preview]     读取 → 按类型渲染（Markdown / 表格 / JSON / 文本）
       ↓
[Download]

## 设计原则

mashang-fetch 的核心是 **Fetch / Convert**：把外部资源尽可能转换成用户需要的
本地结构化文件。成功标准是「文件有没有正确生成」，而不是「AI 有没有理解」。

Preview 的第一职责是忠实呈现转换结果，不经过任何模型。

外围能力（默认不触发）：
- AI Summary / AI Q&A（可选，需配置 ARK_API_KEY）
- Save to notes / Flomo（可选）

## Pipeline 说明

1. Resolver：规范化 URL，按域名分类策略（`mp.weixin.qq.com` 走 Axios，其余走 Puppeteer），短链解析留作扩展点。
2. Extractor：抓取页面并抽取正文与表格数据。
3. Normalizer：清洗并组织为统一文档模型，附来源与抓取时间。
4. Exporter：渲染为 Markdown（含 front matter）或 CSV。
5. Preview：按扩展名分发渲染，绝不改写内容。
