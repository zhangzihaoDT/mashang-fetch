"""URL normalization shared by all web search results."""
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def canonical_url(url):
    p = urlsplit(url)
    port = p.port
    host = p.hostname.lower()
    netloc = host if port is None or (p.scheme == 'https' and port == 443) or (p.scheme == 'http' and port == 80) else f'{host}:{port}'
    pairs = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid', 'msclkid')]
    return urlunsplit((p.scheme.lower(), netloc, p.path or '/', urlencode(sorted(pairs)), ''))
