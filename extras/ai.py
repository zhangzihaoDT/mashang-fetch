"""可选 AI 能力（Summary / Q&A / Flomo）。

不属于核心链路，仅在用户显式操作且配置了 ARK_API_KEY 时才会被调用。
依赖见 requirements-ai.txt。
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

FLOMO_API_URL = "https://flomoapp.com/iwh/NDIwOTAx/c62bd115ef72eb46a2289296744fe0dc/"
CONTEXT_CHAR_LIMIT = 8000


def available():
    """AI 功能是否可用：需要 ARK_API_KEY 且依赖已安装。"""
    if not os.getenv("ARK_API_KEY"):
        return False
    try:
        from langchain_openai import ChatOpenAI  # noqa: F401
    except Exception:
        return False
    return True


def _get_llm():
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        raise RuntimeError("未找到 ARK_API_KEY，请检查 .env 文件")
    model_name = os.getenv("deepseek0324") or "deepseek0324"
    return ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://ark.cn-beijing.volces.com/api/v3",
        model_name=model_name,
        temperature=0,
    )


def summarize(text, title=""):
    if not text:
        return "没有可总结的内容。"
    try:
        llm = _get_llm()
        messages = [
            {"role": "system", "content": "你是一个擅长提炼文章要点的助手。"},
            {"role": "user", "content": f"请用 3-5 个要点总结下面这篇《{title}》：\n\n{text[:CONTEXT_CHAR_LIMIT]}"},
        ]
        return llm.invoke(messages).content
    except Exception as e:
        return f"总结失败：{e}"


def answer(question, text, title="", history=None):
    if not question:
        return ""
    try:
        llm = _get_llm()
        context = f"文章《{title}》内容摘要：\n{text[:CONTEXT_CHAR_LIMIT]}\n\n"
        messages = [
            {"role": "system", "content": "你是一个阅读助手，请基于给定文章内容简洁回答用户问题。"},
            {"role": "user", "content": f"{context}现在回答我的问题。"},
        ]
        for user_msg, assistant_msg in history or []:
            messages.append({"role": "user", "content": user_msg})
            if assistant_msg:
                messages.append({"role": "assistant", "content": assistant_msg})
        messages.append({"role": "user", "content": question})
        return llm.invoke(messages).content
    except Exception as e:
        return f"回答失败：{e}"


def send_to_flomo(note, title=""):
    if not note:
        return "笔记内容为空，未发送"
    try:
        tag = f"#mashang-fetch #{title.replace(' ', '_')}" if title else "#mashang-fetch"
        response = requests.post(
            FLOMO_API_URL,
            json={"content": f"{note}\n\n{tag}"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if response.status_code == 200:
            return "笔记已成功发送到 Flomo"
        return f"发送到 Flomo 失败：HTTP {response.status_code}"
    except Exception as e:
        return f"发送到 Flomo 失败：{e}"
