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
[Inbox]       output/{时间}_{标题}.{md|csv}   ← 暂存区
       ↓
[Preview]     读取 → 按类型渲染（Markdown / 表格 / JSON / 文本）
       ↓
[Manage]      Rename / Delete / Download
       ↓
[移入资料库]    移动到 50_外部资料（Inbox 不再保留）
       ↓
[资料库]       浏览 / 搜索 / 改名 / 删除 / 下载
       ↓
myknbase Import

## 设计原则

mashang-fetch 的核心是 **Fetch / Convert**：把外部资源尽可能转换成用户需要的
本地结构化文件。成功标准是「文件有没有正确生成」，而不是「AI 有没有理解」。

Preview 的第一职责是忠实呈现转换结果，不经过任何模型。

Inbox（output/）是暂存区：抓取结果先落在这里，可预览、可改名、可删除、可下载。
「移入资料库」把文件移动到 50_外部资料（供 myknbase 导入），是空间之间的转移，
Inbox 中不再保留；同名不覆盖、不建副本，源文件保留。
资料库中的文件也可以直接浏览、搜索、改名、删除、下载。

## 管理动作语义

- 移入资料库：我要留下（从 Inbox 移动到资料库）
- Rename：我想改文件名（只改文件名，不动内容）
- Download：我要拿一份出来
- Delete：我不要了（从所在空间永久删除）

## Pipeline 说明

1. Resolver：规范化 URL，按域名分类策略（`mp.weixin.qq.com` 走 Axios，其余走 Puppeteer），短链解析留作扩展点。
2. Extractor：抓取页面并抽取正文与表格数据。
3. Normalizer：清洗并组织为统一文档模型，附来源与抓取时间。
4. Exporter：渲染为 Markdown（含 front matter）或 CSV。
5. Preview：按扩展名分发渲染，绝不改写内容。
