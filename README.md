# mashang-fetch

获取网页正文、表格与 PDF 附件，保存为本地文件，在 **Inbox → 资料库** 两个空间之间预览、分类、归档。

**链接 → 获取资料 → Inbox → 查看与整理 → 移入资料库**

mashang-fetch 的成功标准只有一个：**资料有没有被正确获取并保存**，而不是 AI 有没有理解内容。

## 两个文件空间

```
① Fetch / Convert
   网页正文 / 表格 → Resolver → Extractor → Normalizer → Exporter → .md / .csv
   PDF 直链 / 网页附件 → 识别附件 → 选择（多个时）→ 下载与校验 → .pdf

② Inbox → 资料库
   Inbox（output/，暂存）  →  File（列表 / 选中）
                              ├─ Preview            只读展示
                              ├─ Rename / Download / Delete
                              └─ 移入资料库 ──移动──▶ 资料库
                                                      （50_外部资料 / myknbase 导入源）
```

```
URL
 ↓
mashang-fetch
 ↓
Inbox（output/）        ← 暂存区，抓取结果先落在这里
└─ File                 文件资源层：列表、搜索、选中与生命周期操作
    ├─ Preview          忠实呈现转换结果（只读）
    ├─ Rename           重命名文件
    ├─ Delete           永久删除
    ├─ Download         下载一份到本地
    └─ 移入资料库        移动到资料库
        ↓
资料库（50_外部资料）    ← 长期保存，可直接浏览 / 搜索 / 改名 / 删除 / 下载
    ↓
myknbase Import
```

- **Fetch / Convert**：能力集中在外部资源的获取与解析，输出可追溯的本地文件。
- **Inbox / 资料库**：两个文件空间。Inbox 是 `output/` 暂存区；资料库是长期保存目录（默认 `50_外部资料`）。左侧用标签页切换。
- **File**：文件资源层。列表、搜索、选中以及 Rename / 移入资料库 / Download / Delete 都归于此。单文件操作在右侧详情顶部，批量操作在左侧选择工具栏。
- **Preview**：第一职责是忠实呈现转换结果。`.md` → Markdown 渲染，`.csv` → 表格，`.json` → 格式化，`.pdf` → PDF.js 原文件预览（支持翻页）。
- **移入资料库**：把 Inbox 文件**按原相对目录移动**到资料库，Inbox 中不再保留；同名时不覆盖、不创建副本，直接提示「已存在」并保留源文件。资料库中的文件不再显示该操作。
- **Rename / Delete / Download**：在两个空间分别生效，互不影响。

## 主要功能

- **链接转文件**：输入 URL，按域名解析抓取策略，导出 Markdown 或 CSV，或下载 PDF 直链及网页中的 PDF 附件；单附件自动获取，多附件支持选择。
- **结构化输出**：`.md` 带 YAML front matter（title / source / author / fetched_at），文件自描述、可追溯来源。
- **忠实预览**：按文件类型渲染，不经过任何模型。
- **双空间管理**：Inbox 暂存、资料库长期保存；两处都支持搜索、Rename、Download、Delete（删除前确认）。
- **批量操作**：勾选多个文件后可**批量移入资料库**（Inbox）与**批量删除**；支持全选当前列表或搜索结果。移入时同名文件跳过并保留源文件，其余正常移动。
- **长期保存**：一键把 Inbox 文件移入资料库，作为 myknbase 的导入来源。

## 技术架构

- **核心引擎（Node.js）**：`Resolver → Extractor → Normalizer → Exporter`，负责抓取与转换。
- **Web 服务（Python + FastAPI）**：`server.py` 提供 `/api` 接口，并托管前端构建产物。
- **前端（React + Vite）**：`web/`，三段式界面（顶部任务栏 + 左文件 + 右预览），状态机 `EMPTY → FETCHING → READY / ERROR`，多个 PDF 附件先进入选择流程。

数据流：

```
React (web/dist)  ──REST──▶  FastAPI (server.py)  ──▶  app/service.py
                                                     ├─▶ app/fetch.py    (Node CLI)
                                                     ├─▶ app/preview.py  (读取 / 渲染)
                                                     ├─▶ app/manage.py   (Keep / Rename / Delete)
                                                     └─▶ app/storage.py  (Inbox / 资料库路径)
```

## 安装与配置

### 前提条件

- Node.js 22.13+（前端 PDF.js 依赖要求）
- Python 3.10+（后端使用现代类型注解）

### 安装步骤

```bash
git clone https://github.com/zhangzihaoDT/mashang-fetch.git
cd mashang-fetch

# Node 核心引擎依赖
npm install

# Python 服务依赖
pip install -r requirements.txt

# 前端依赖 + 构建（首次）
npm --prefix web install
npm run build
```

> 首次执行 `npm run up` 时若 `web/dist` 不存在，脚本会自动安装并构建前端。

## 使用方法

### 界面

```bash
npm run up     # 启动（后台运行）
npm run down   # 停止
```

在浏览器打开 `http://127.0.0.1:7860`：输入 URL → 选择获取方式（网页正文 / 网页表格 / PDF 附件） → **Fetch** → 自动进入 **Inbox** 并选中新文件预览。左侧 **打开文件夹** 打开当前 Inbox 或资料库；详情顶部 **在 Finder 中显示** 定位选中的文件（macOS）。目录路径收在「目录信息」中，可查看和复制。

左侧文件面板切换 **Inbox** 与 **资料库**，支持搜索、文件夹分组与键盘上下选择。

- **当前文件**：右侧详情顶部可在 Finder 中定位、移入资料库（仅 Inbox）；「更多」包含重命名、下载副本和删除。正文区域只负责预览，来源信息默认折叠。
- **批量整理**：左侧点击「选择」，勾选文件后批量移入资料库或删除；支持全选当前搜索结果。
- **文件夹归档**：Inbox 文件夹行的「移入资料库」递归归档该文件夹内的全部普通文件，包括当前搜索未展示的文件。
- **保留分类**：`Inbox/规划公示/项目A.pdf` → `资料库/规划公示/项目A.pdf`。同名目录合并；完整目标路径冲突时跳过并保留源文件，不影响其他文件。来源记录随 PDF 移动，移动后空出的目录自动清理。

Fetch 成功后资料已保存到项目的 `output/`，不会自动在浏览器下载第二份。只有主动选择「下载副本」才另存一份。

- 后台运行时 PID 与日志统一放在 `.local/`（`app.pid`、`app.log`）。
- 可用 `HOST` / `PORT` 覆盖服务的地址与端口，例如 `PORT=7861 npm run up`。
- **资料库目录**：默认 `~/Documents/github/notes/50_外部资料`，可用环境变量 `MASHANG_FETCH_KEEP_DIR` 覆盖（例如指向 myknbase 的导入目录）：

```bash
MASHANG_FETCH_KEEP_DIR=/path/to/library npm run up
```

- 前端开发模式（热更新，API 反向代理到 7860）：

```bash
npm run up       # 先启动后端
npm run web:dev  # 另开一个终端跑 Vite（http://127.0.0.1:5173）
```

- 修改前端后重新构建：`npm run build`。

### 命令行

核心引擎也可直接当作 CLI 使用：

```bash
node src/cli.js <url> --format md|csv|pdf [--out DIR]
```

成功时 stdout 输出 JSON：

```json
{"ok":true,"path":"output/20261002_120000_标题.md","format":"md","meta":{"title":"标题","source":"https://..."}}
```

### 下载 PDF

界面中选择 **PDF 附件**，粘贴 PDF 直链或包含 PDF 附件的网页链接并点击 Fetch。文件保存到 Inbox（`output/`），支持 Rename、Download、Delete 和移入资料库。支持重定向，以及没有 `.pdf` 后缀的下载地址；下载时校验 PDF 文件头，错误页不会保存为 PDF。

```bash
node src/cli.js https://example.com/report.pdf --format pdf
```

此功能下载 PDF 原文件，也会查找当前网页中的 PDF 附件链接：单个附件自动下载，多个附件可勾选或全部下载，单个失败不影响其余文件。Fetch 成功后保存文件到 Inbox，不自动下载副本。暂不支持需要 JavaScript 动态加载的附件。来源页面与下载地址保存在隐藏的来源记录中，随文件重命名、移入资料库和删除。右侧通过 PDF.js 直接预览 PDF，支持翻页；详情顶部提供 Finder 定位和移入资料库，「更多」包含重命名、下载副本和删除，来源信息默认折叠。PDF 文件名包含时间、来源文件名和随机后缀，避免重复下载覆盖。

## 输出文件

- Markdown / CSV：`{YYYYMMDD_HHMMSS}_{标题}.{md|csv}`。
- PDF：`{YYYYMMDD_HHMMSS}_{附件名称}_{随机后缀}.pdf`（时间戳使用 UTC，避免重复下载覆盖）；界面使用资料名称展示标题。
- PDF 来源记录：同目录下的隐藏文件 `.{PDF文件名}.source.json`，包含 `title / source / download_url / fetched_at`；不在文件列表中显示，随 PDF 的重命名、归档和删除维护。
- `.md` 头部包含 YAML front matter：

```yaml
---
title: 标题
source: https://example.com/article
author: 作者
fetched_at: 2026-10-02T12:00:00.000Z
format: markdown
---
```

## 项目结构

```
mashang-fetch/
├── server.py               # FastAPI：/api 接口 + 托管前端
├── app/
│   ├── fetch.py            # Link → File：调用 Node CLI，解析 JSON 结果
│   ├── preview.py          # File → Preview：按扩展名读取 / 渲染文件
│   ├── manage.py           # Keep / Rename / Delete：两空间文件管理
│   ├── storage.py          # 路径配置：Inbox（output/）与资料库目录
│   └── service.py          # 服务层：把核心能力整理成 JSON
├── web/                    # React + Vite 前端
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx         # 装配 + 状态机
│       ├── api.js          # API 客户端
│       ├── state.js        # reducer / 初始状态
│       ├── styles.css
│       └── components/     # Header / FetchBar / FileSidebar / PreviewPane / PdfPreview ...
├── src/                    # Node 核心引擎
│   ├── cli.js              # 统一入口
│   ├── pdf.js              # PDF 直链下载、网页附件识别与选择
│   ├── resolver.js         # URL 分类 → 选择抓取策略
│   ├── extractor/          # 抓取与正文/表格抽取
│   ├── normalizer.js       # 结构化文档模型
│   └── exporter/           # Markdown / CSV 导出
├── tests/                  # API / PDF 下载 / 保留目录归档测试
├── scripts/dev.sh          # 本地进程管理（up / down）
├── scripts/test.sh         # 测试运行器
├── .local/                 # 运行期 PID 与日志（不纳入版本管理）
└── output/                 # Inbox：抓取结果暂存区
```

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/formats` | 支持的输出格式 |
| GET | `/api/config` | 运行配置（Inbox 与资料库目录） |
| GET | `/api/files?scope=` | 指定空间的文件列表（`workspace` / `library`） |
| POST | `/api/fetch` | `{url, format, attachments?}` → 获取资料；`format` 为 `md` / `csv` / `pdf` |
| GET | `/api/preview?scope=&id=` | 预览数据（markdown / table / json / text / pdf） |
| GET | `/api/view?scope=&id=` | PDF 原文件流（inline，供 PDF.js 读取） |
| POST | `/api/open-inbox?scope=&id=` | macOS Finder 打开当前空间；传入 id 时定位文件 |
| POST | `/api/keep` | `{id}` → 保留相对目录，把 Inbox 文件移入资料库 |
| POST | `/api/rename` | `{scope, id, name}` → 重命名文件 |
| POST | `/api/delete` | `{scope, id}` → 永久删除文件 |
| POST | `/api/batch` | `{scope, action, ids}` → 批量操作（`move_to_library` / `delete`）；归档 ids 可包含文件夹路径 |
| GET | `/api/download?scope=&id=` | 下载文件 |

### PDF 返回结果

PDF 直链返回单文件结果（`path / filename / format / meta`）；网页附件下载返回 `results` 和 `failed`，单项失败不影响其他附件。API 额外提供 `file`，多个结果时提供 `files`。

网页发现多个附件且尚未选择时，返回 `needs_selection: true`、`source` 和 `attachments: [{url, name}]`，此时还没有生成文件。界面展示选择列表；CLI 可再次执行：

```bash
node src/cli.js 'https://example.com/page' --format pdf \
  --attachments '["https://example.com/report.pdf"]'
```

API 对应在 `/api/fetch` 请求中传入 `attachments` URL 列表，后端验证其属于该页面的候选附件。全部失败时 `ok: false`；部分成功时返回成功结果和失败原因。

## 测试

```bash
npm test    # API、PDF 获取、目录归档回归测试（PDF 测试使用本机 HTTP 服务）
```

## 当前限制

- PDF 附件识别限于当前页面中的普通 HTML 链接，不递归爬取其他页面；暂不支持动态加载、登录后才能访问的附件。
- 多附件 CLI 调用先返回候选列表，不自动下载全部附件。
- Finder 入口仅支持运行在本机 macOS 的服务。
- 视频站（B 站等）的专用 Resolver
- 网页转 PDF、PDF 正文解析、图片导出
- 微信正文内图片抓取

## 许可证

本项目采用 MIT 许可证 - 详情请参见 LICENSE 文件
