"""Read PSX's public feeds using the request header issued by its public page.

The September 2026 portal still uses the same feed URLs, but its script now
copies window.__ps._k into X-Req-Id for AJAX requests. Without that header the
feeds return a 404 page. No JavaScript is executed and no key is persisted.
"""
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit

from .base import http_get

HOME = 'https://dps.psx.com.pk/'
_request_id = None


def public_request_id(html):
    match = re.search(r'window\.__ps\s*=\s*(\{[^;]+\})\s*;', html)
    if not match:
        raise ValueError('PSX public request configuration is unavailable')
    value = json.loads(match.group(1)).get('_k')
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError('PSX public request header is invalid')
    return value


def get(url, headers=None, data=None, **kwargs):
    global _request_id
    target = urlsplit(url)
    if target.scheme != 'https' or target.netloc != 'dps.psx.com.pk':
        raise ValueError('PSX request headers are restricted to the public PSX host')
    for attempt in range(2):
        if _request_id is None:
            _request_id = public_request_id(http_get(HOME))
        request_headers = {'Referer': HOME, 'X-Requested-With': 'XMLHttpRequest',
                           **(headers or {}), 'X-Req-Id': _request_id}
        try:
            return http_get(url, headers=request_headers, data=data, **kwargs)
        except HTTPError as exc:
            if attempt or exc.code not in (401, 403, 404):
                raise
            # The page-issued header can rotate. Refresh once, then fail closed.
            _request_id = None
