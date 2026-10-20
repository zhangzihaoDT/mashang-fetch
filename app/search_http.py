"""Bounded read-only HTTP retries; shared wall-clock budget for a complete search."""
import json
from functools import wraps
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from contextvars import ContextVar

_deadline = ContextVar('search_deadline', default=None)


@contextmanager
def budget(seconds=60, deadline=None):
    parent = _deadline.get()
    end = deadline if deadline is not None else time.monotonic()+seconds
    token = _deadline.set(min(parent,end) if parent else end)
    try:
        yield _deadline.get()
    finally:
        _deadline.reset(token)


def deadline():
    return _deadline.get() or time.monotonic()+60


def request_json(request):
    end = min(deadline(), time.monotonic()+30)
    for attempt in range(3):
        remaining = end-time.monotonic()
        if remaining <= 0:
            raise ValueError('搜索总耗时达到上限，请稍后重试')
        try:
            with urllib.request.urlopen(request, timeout=min(10,remaining)) as response:
                chunks = []
                size = 0
                while True:
                    if time.monotonic() >= end:
                        raise ValueError('搜索总耗时达到上限，请稍后重试')
                    # read1 avoids waiting to fill an entire buffer on a slow streaming peer.
                    sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
                    if sock is not None:
                        sock.settimeout(min(10, max(.001, end-time.monotonic())))
                    chunk = response.read1(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 8*1024*1024:
                        raise ValueError('搜索响应过大')
                    chunks.append(chunk)
                return json.loads(b''.join(chunks))
        except urllib.error.HTTPError as exc:
            transient = exc.code in (408,429) or 500 <= exc.code <= 599
            if not transient or attempt == 2:
                raise
        except OSError:
            if attempt == 2:
                raise
        delay = .25 * 2**attempt
        if end-time.monotonic() <= delay:
            raise ValueError('搜索总耗时达到上限，请稍后重试')
        time.sleep(delay)


def bounded(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        with budget(60):
            return fn(*args, **kwargs)
    return call
