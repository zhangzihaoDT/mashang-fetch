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
- **外围可选**（默认不触发）：Download、AI Summary、AI Q&A、Save to notes。

## 主要功能

- **链接转文件**：输入 URL，按域名解析抓取策略，导出 Markdown 或 CSV。
- **结构化输出**：`.md` 带 YAML front matter（title / source / author / fetched_at），文件自描述、可追溯来源。
- **忠实预览**：按文件类型渲染，不经过 AI。
- **本地下载**：直接下载生成的文件。
- **可选 AI**：仅在手动点击且配置 API Key 时调用，不进入核心链路。

## 技术架构

- **核心引擎（Node.js）**：`Resolver → Extractor → Normalizer → Exporter`，负责抓取与转换。
- **预览界面（Python + Gradio）**：只负责读取本地文件并渲染预览、下载。
- **可选 AI（Python）**：`extras/ai.py`，独立于核心链路。

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

# Python 预览界面依赖
pip install -r requirements.txt

# （可选）AI 能力依赖
pip install -r requirements-ai.txt
```

可选 AI 需在 `.env` 中配置：

```
ARK_API_KEY=your_api_key_here
deepseek0324=your_model_endpoint_id
```

## 使用方法

### 界面

```bash
python main.py
```

在浏览器打开 `http://127.0.0.1:7860`：输入 URL → 选择 Format → **Fetch** → 预览 → **Download**。

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
├── main.py                 # Gradio Preview 界面
├── app/
│   ├── fetch.py            # 调用 Node CLI，解析 JSON 结果
│   └── preview.py          # 按扩展名读取 / 渲染文件
├── src/                    # Node 核心引擎
│   ├── cli.js              # 统一入口
│   ├── resolver.js         # URL 分类 → 选择抓取策略
│   ├── extractor/          # 抓取与正文/表格抽取
│   ├── normalizer.js       # 结构化文档模型
│   └── exporter/           # Markdown / CSV 导出
├── extras/ai.py            # 可选 AI / Flomo
└── output/                 # 生成的本地文件
```

## v0.1 非目标

- 视频站（B 站等）的专用 Resolver
- PDF / 图片导出与预览（仅预留分发位）
- 微信正文内图片抓取

## 许可证

本项目采用 MIT 许可证 - 详情请参见 LICENSE 文件
