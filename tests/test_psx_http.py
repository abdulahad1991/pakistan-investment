from urllib.error import HTTPError

import pytest

from fetchers import psx_http


def test_public_feed_bootstrap_is_reused_and_post_body_is_preserved(monkeypatch):
    calls = []
    def read(url, **kwargs):
        calls.append((url, kwargs))
        if url == psx_http.HOME:
            return '<script>window.__ps = {"_k":"test-public-header","tz":"Asia/Karachi"};</script>'
        assert kwargs['headers']['X-Req-Id'] == 'test-public-header'
        return 'data'
    monkeypatch.setattr(psx_http, 'http_get', read)
    monkeypatch.setattr(psx_http, '_request_id', None)
    assert psx_http.get(psx_http.HOME + 'market-watch') == 'data'
    psx_http.get(psx_http.HOME + 'company/payouts', data='symbol=OGDC',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    assert len(calls) == 3
    assert calls[-1][1]['data'] == 'symbol=OGDC'
    assert calls[-1][1]['headers']['Content-Type'] == 'application/x-www-form-urlencoded'


def test_header_rotation_refreshes_once_then_surfaces_failure(monkeypatch):
    calls = []
    def read(url, **kwargs):
        calls.append(url)
        if url == psx_http.HOME:
            return 'window.__ps = {"_k":"refreshed-test-header"};'
        raise HTTPError(url, 404, 'Unavailable', {}, None)
    monkeypatch.setattr(psx_http, 'http_get', read)
    monkeypatch.setattr(psx_http, '_request_id', 'expired-test-header')
    with pytest.raises(HTTPError):
        psx_http.get(psx_http.HOME + 'market-watch')
    assert len(calls) == 3


def test_missing_configuration_and_unrelated_hosts_are_rejected():
    with pytest.raises(ValueError):
        psx_http.public_request_id('<html>Unavailable</html>')
    with pytest.raises(ValueError):
        psx_http.get('https://example.com/market-watch')
