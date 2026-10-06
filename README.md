# mashang-fetch

把外部资源链接转换为本地结构化文件，在 **Inbox → 资料库** 两个空间之间预览、整理、留存。

**Link → File → Preview → 移入资料库 / Rename / Delete / Download**

mashang-fetch 的成功标准只有一个：**文件有没有被正确生成**，而不是 AI 有没有理解内容。

## 两个文件空间

```
① Fetch / Convert
   URL → Resolver → Extractor → Normalizer → Exporter → 本地文件 (.md / .csv)

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
- **File**：文件资源层。列表、搜索、选中以及 Rename / 移入资料库 / Download / Delete 都归于此；Preview 不承载操作。
- **Preview**：第一职责是忠实呈现转换结果。`.md` → Markdown 渲染，`.csv` → 表格，`.json` → 格式化，其余 → 文本兜底。
- **移入资料库**：把 Inbox 文件**移动**到资料库，Inbox 中不再保留；同名时不覆盖、不创建副本，直接提示「已存在」并保留源文件。资料库中的文件不再显示该操作。
- **Rename / Delete / Download**：在两个空间分别生效，互不影响。

## 主要功能

- **链接转文件**：输入 URL，按域名解析抓取策略，导出 Markdown 或 CSV。
- **结构化输出**：`.md` 带 YAML front matter（title / source / author / fetched_at），文件自描述、可追溯来源。
- **忠实预览**：按文件类型渲染，不经过任何模型。
- **双空间管理**：Inbox 暂存、资料库长期保存；两处都支持搜索、Rename、Download、Delete（行内二次确认）。
- **批量操作**：勾选多个文件后可**批量移入资料库**（Inbox）与**批量删除**；支持全选当前列表或搜索结果。移入时同名文件跳过并保留源文件，其余正常移动。
- **长期保存**：一键把 Inbox 文件移入资料库，作为 myknbase 的导入来源。

## 技术架构

- **核心引擎（Node.js）**：`Resolver → Extractor → Normalizer → Exporter`，负责抓取与转换。
- **Web 服务（Python + FastAPI）**：`server.py` 提供 `/api` 接口，并托管前端构建产物。
- **前端（React + Vite）**：`web/`，三段式界面（顶部任务栏 + 左文件 + 右预览），状态机 `EMPTY → FETCHING → SUCCESS / ERROR`。

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

- Node.js 14+
- Python 3.8+

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

在浏览器打开 `http://127.0.0.1:7860`：输入 URL → 选择 Format → **Fetch** → 自动进入 **Inbox** 并选中新文件预览。

左侧 **Files** 面板顶部可切换两个空间：**Inbox**（暂存）与 **资料库**（长期保存），各自带文件数量与搜索框。点击 **选择** 进入选择模式，文件行出现复选框，顶部工具栏按选中数量显示可用操作：

- **选中 1 个**：移入资料库（仅 Inbox）/ Rename / Download / Delete；
- **选中多个**：批量移入资料库（仅 Inbox）/ 批量删除（Rename、Download 暂不支持批量）；
- 支持全选当前列表或搜索结果，删除会在工具栏内二次确认并列出文件名。

文件操作统一收敛在顶部工具栏，右侧 Preview 只负责忠实展示当前文件，不承载操作。「移入资料库」是空间之间的移动，Inbox 中不再保留该文件。

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
node src/cli.js <url> --format md|csv [--out DIR]
```

成功时 stdout 输出 JSON：

```json
{"ok":true,"path":"output/20261002_120000_标题.md","format":"md","meta":{"title":"标题","source":"https://..."}}
```

## 输出文件

- 命名：`{YYYYMMDD_HHMMSS}_{标题}.{md|csv}`
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
│       └── components/     # Header / FetchBar / FileSidebar / FileActions / PreviewPane ...
├── src/                    # Node 核心引擎
│   ├── cli.js              # 统一入口
│   ├── resolver.js         # URL 分类 → 选择抓取策略
│   ├── extractor/          # 抓取与正文/表格抽取
│   ├── normalizer.js       # 结构化文档模型
│   └── exporter/           # Markdown / CSV 导出
├── tests/test_api.py       # API 冒烟测试
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
| POST | `/api/fetch` | `{url, format}` → 生成文件到 Inbox |
| GET | `/api/preview?scope=&id=` | 预览数据（markdown / table / json / text） |
| POST | `/api/keep` | `{id}` → 把 Inbox 文件移入资料库 |
| POST | `/api/rename` | `{scope, id, name}` → 重命名文件 |
| POST | `/api/delete` | `{scope, id}` → 永久删除文件 |
| POST | `/api/batch` | `{scope, action, ids}` → 批量操作（`move_to_library` / `delete`） |
| GET | `/api/download?scope=&id=` | 下载文件 |

## 测试

```bash
npm test    # 运行 API 冒烟测试（unittest + FastAPI TestClient）
```

## v0.1 非目标

- 视频站（B 站等）的专用 Resolver
- PDF / 图片导出与预览（仅预留分发位）
- 微信正文内图片抓取

## 许可证

本项目采用 MIT 许可证 - 详情请参见 LICENSE 文件
