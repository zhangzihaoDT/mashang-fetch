"""DeepSeek search adapter. Search snippets are never treated as saved originals."""
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from app.search_http import request_json


def failure(message, reason):
    error = ValueError(message)
    error.reason = reason
    return error


def search(query, count=20, *, effective_query=None):
    query = query.strip()
    if not query:
        raise ValueError("请输入搜索词")
    effective = query
    if effective_query is not None:
        effective = effective_query
    if len(effective) > 128:
        raise ValueError("搜索条件过长，请缩短关键词（含范围限制最多 128 字符）")
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise ValueError("搜索尚未启用，请完成搜索凭据配置后重启服务")
    request = urllib.request.Request("https://api.deepseek.com/v1/tools/search",
        data=json.dumps({"query": effective, "count": count, "need_content": False, "ori_question": query}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        payload = request_json(request)
    except urllib.error.HTTPError as exc:
        messages = {401: "搜索凭据无效", 402: "搜索账户余额不足", 429: "搜索请求过于频繁，请稍后重试"}
        reasons = {401:'authentication',402:'balance',429:'rate_limit',408:'timeout',504:'timeout'}
        raise failure(messages.get(exc.code, "搜索服务暂时不可用，请稍后重试"), reasons.get(exc.code,'provider_http_error')) from None
    except (TimeoutError, OSError) as exc:
        reason = 'timeout' if isinstance(exc, TimeoutError) or isinstance(getattr(exc, 'reason', None), TimeoutError) else 'connection'
        raise failure("搜索服务连接失败，请稍后重试", reason) from None
    except ValueError as exc:
        if '耗时' in str(exc):
            raise failure(str(exc), 'timeout') from None
        raise failure("搜索服务返回了无法识别的结果，请稍后重试", 'invalid_response') from None
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("搜索服务返回了无法识别的结果，请稍后重试")
    results, seen = [], set()
    for item in payload.get("results", []):
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        url = item.get("url", "")
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            continue
        identity = url
        if identity in seen:
            continue
        seen.add(identity)
        results.append({"id": identity, "url": url, "title": item.get("title", "") or url,
            "snippet": item.get("snippet", ""), "summary": item.get("summary", ""), "date": item.get("date"),
            "site_name": item.get("site_name"), "provider_authority": item.get("authority"), "provider_score": item.get("rerank_score")})
    return {"results": results, "diagnostics": {"provider_count": len(payload["results"]), "returned_count": len(results), "query": effective}}
