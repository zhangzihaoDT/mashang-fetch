# mashang-fetch

把外部资源链接转换为本地结构化文件，然后忠实预览。

**Link → File → Preview → Download**

mashang-fetch 的成功标准只有一个：**文件有没有被正确生成**，而不是 AI 有没有理解内容。

## 两层架构

```
① Fetch / Convert
   URL → Resolver → Extractor → Normalizer → Exporter → 本地文件 (.md / .csv)

② Preview
   本地文件 → 读取 / 渲染 → 预览
```

- **Fetch / Convert**：能力集中在外部资源的获取与解析，输出可追溯的本地文件。
- **Preview**：第一职责是忠实呈现转换结果。`.md` → Markdown 渲染，`.csv` → 表格，`.json` → 格式化，其余 → 文本兜底。
- **Download**：把生成的文件直接下载到本地。

## 主要功能

- **链接转文件**：输入 URL，按域名解析抓取策略，导出 Markdown 或 CSV。
- **结构化输出**：`.md` 带 YAML front matter（title / source / author / fetched_at），文件自描述、可追溯来源。
- **忠实预览**：按文件类型渲染，不经过任何模型。
- **本地下载**：直接下载生成的文件。

## 技术架构

- **核心引擎（Node.js）**：`Resolver → Extractor → Normalizer → Exporter`，负责抓取与转换。
- **Web 服务（Python + FastAPI）**：`server.py` 提供 `/api` 接口，并托管前端构建产物。
- **前端（React + Vite）**：`web/`，三段式界面（顶部任务栏 + 左文件 + 右预览），状态机 `EMPTY → FETCHING → SUCCESS / ERROR`。

数据流：

```
React (web/dist)  ──REST──▶  FastAPI (server.py)  ──▶  app/service.py
                                                     ├─▶ app/fetch.py  (Node CLI)
                                                     └─▶ app/preview.py
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

在浏览器打开 `http://127.0.0.1:7860`：输入 URL → 选择 Format → **Fetch** → 自动选中新文件并预览 → **Download**。

- 后台运行时 PID 与日志统一放在 `.local/`（`app.pid`、`app.log`）。
- 可用 `HOST` / `PORT` 覆盖服务的地址与端口，例如 `PORT=7861 npm run up`。
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
│   └── service.py          # 服务层：把核心能力整理成 JSON
├── web/                    # React + Vite 前端
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx         # 装配 + 状态机
│       ├── api.js          # API 客户端
│       ├── state.js        # reducer / 初始状态
│       ├── styles.css
│       └── components/     # Header / FetchBar / FileSidebar / PreviewPane ...
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
└── output/                 # 生成的本地文件
```

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/formats` | 支持的输出格式 |
| GET | `/api/files` | 文件列表（结构化记录） |
| POST | `/api/fetch` | `{url, format}` → 生成文件 |
| GET | `/api/preview?id=` | 预览数据（markdown / table / json / text） |
| GET | `/api/download?id=` | 下载文件 |

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
