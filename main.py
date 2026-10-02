import gradio as gr

from app.fetch import FORMATS, fetch
from app.preview import describe, list_outputs, load
from extras import ai as ai_extra

AI_AVAILABLE = ai_extra.available()


def _blank_preview():
    return (
        gr.update(value="", visible=False),
        gr.update(value=[], headers=[], visible=False),
        gr.update(value="", visible=False),
        gr.update(value=None, visible=False),
        gr.update(value="", visible=False),
    )


def _render(path):
    """按扩展名准备 Preview 组件更新，返回 5 元组。"""
    data = load(path)
    kind = data.get("kind")

    if kind == "markdown":
        return (
            gr.update(value=data["content"], visible=True),
            gr.update(value=[], headers=[], visible=False),
            gr.update(value="", visible=False),
            gr.update(value=path, visible=True),
            gr.update(value=describe(path), visible=True),
        )
    if kind == "table":
        return (
            gr.update(value="", visible=False),
            gr.update(value=data["rows"], headers=data["header"], visible=True),
            gr.update(value="", visible=False),
            gr.update(value=path, visible=True),
            gr.update(value=describe(path), visible=True),
        )
    if kind in ("json", "text"):
        return (
            gr.update(value="", visible=False),
            gr.update(value=[], headers=[], visible=False),
            gr.update(value=data["content"], visible=True),
            gr.update(value=path, visible=True),
            gr.update(value=describe(path), visible=True),
        )
    return (
        gr.update(value=f"⚠️ {data.get('error', '无法预览该文件')}", visible=True),
        *_blank_preview()[1:],
    )


def do_fetch(url, fmt_label):
    if not url or not url.strip():
        return ("请先输入 URL", gr.update(), *_blank_preview())

    result = fetch(url.strip(), FORMATS.get(fmt_label, "md"))
    if not result.get("ok"):
        return (f"❌ 转换失败：{result.get('error')}", gr.update(), *_blank_preview())

    path = result["path"]
    status = f"✅ 已生成 `{result['filename']}`"
    return (
        status,
        gr.update(choices=list_outputs(), value=path),
        *_render(path),
    )


def do_select(path):
    if not path:
        return (gr.update(), *_blank_preview())
    return (gr.update(), *_render(path))


def do_refresh():
    return gr.update(choices=list_outputs())


def _selected_text(path):
    data = load(path) if path else {}
    if data.get("kind") == "markdown":
        from app.preview import parse_front_matter

        meta, body = parse_front_matter(data["content"])
        return meta, body
    return {}, data.get("content", "")


with gr.Blocks(title="mashang-fetch") as demo:
    gr.Markdown("# 🔗 mashang-fetch")
    gr.Markdown("把外部链接转换为本地结构化文件：**Link → File → Preview → Download**")

    with gr.Row():
        url_input = gr.Textbox(
            label="Paste URL",
            placeholder="https://mp.weixin.qq.com/s/...",
            scale=6,
        )
        fmt_dropdown = gr.Dropdown(
            label="Format",
            choices=list(FORMATS.keys()),
            value="Markdown",
            scale=1,
        )
        fetch_btn = gr.Button("Fetch", variant="primary", scale=1)

    status_output = gr.Markdown()

    with gr.Row():
        with gr.Column(scale=1, min_width=240):
            gr.Markdown("### 🗂 生成的文件")
            refresh_btn = gr.Button("刷新列表")
            files_dropdown = gr.Dropdown(
                label="选择文件预览",
                choices=list_outputs(),
                interactive=True,
                filterable=True,
            )

        with gr.Column(scale=4, min_width=420):
            gr.Markdown("### 👁 Preview")
            preview_meta = gr.Markdown()
            preview_md = gr.Markdown(visible=False)
            preview_table = gr.Dataframe(visible=False, wrap=True)
            preview_code = gr.Code(visible=False, language="json")
            preview_file = gr.File(label="Download", visible=False, interactive=False)

    if AI_AVAILABLE:
        with gr.Accordion("✨ AI 工具（可选，不会自动调用）", open=False):
            gr.Markdown("以下功能仅在点击时调用模型，需要 `.env` 中的 `ARK_API_KEY`。")
            ai_summary_btn = gr.Button("对当前文件生成摘要")
            ai_summary_output = gr.Markdown()
            ai_question = gr.Textbox(label="向当前文件提问", placeholder="输入问题...")
            ai_ask_btn = gr.Button("提问")
            ai_answer_output = gr.Markdown()
            flomo_input = gr.Textbox(label="发送笔记到 Flomo", lines=4)
            flomo_btn = gr.Button("发送到 Flomo")
            flomo_status = gr.Textbox(label="状态", interactive=False)

        def ai_summarize(path):
            meta, body = _selected_text(path)
            if not body:
                return "请先在左侧选择一个 Markdown 文件。"
            return ai_extra.summarize(body, meta.get("title", ""))

        def ai_ask(question, path):
            meta, body = _selected_text(path)
            if not body:
                return "请先在左侧选择一个 Markdown 文件。"
            return ai_extra.answer(question, body, meta.get("title", ""))

        ai_summary_btn.click(
            fn=ai_summarize, inputs=[files_dropdown], outputs=[ai_summary_output]
        )
        ai_ask_btn.click(
            fn=ai_ask,
            inputs=[ai_question, files_dropdown],
            outputs=[ai_answer_output],
        )
        flomo_btn.click(
            fn=lambda note: ai_extra.send_to_flomo(note),
            inputs=[flomo_input],
            outputs=[flomo_status],
        )

    preview_outputs = [preview_md, preview_table, preview_code, preview_file, preview_meta]

    fetch_btn.click(
        fn=do_fetch,
        inputs=[url_input, fmt_dropdown],
        outputs=[status_output, files_dropdown, *preview_outputs],
    )
    url_input.submit(
        fn=do_fetch,
        inputs=[url_input, fmt_dropdown],
        outputs=[status_output, files_dropdown, *preview_outputs],
    )
    files_dropdown.change(
        fn=do_select,
        inputs=[files_dropdown],
        outputs=[status_output, *preview_outputs],
    )
    refresh_btn.click(fn=do_refresh, inputs=[], outputs=[files_dropdown])

if __name__ == "__main__":
    demo.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
        theme=gr.themes.Base(),
    )
