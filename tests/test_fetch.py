"""scraper.fetch 重試/退避的單元測試（不涉及真實網路,不 sleep）。"""
import pytest
import requests

from scraper import fetch as fetch_mod
from scraper.fetch import FetchError, fetch_html


class _Resp:
    def __init__(self, text="<html>ok</html>", status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


class _Session:
    """假的 session:先失敗 ``fail_times`` 次,之後成功。"""

    def __init__(self, fail_times):
        self.fail_times = fail_times
        self.calls = 0

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise requests.ConnectionError("boom")
        return _Resp("<html>ok</html>")


class _RateLimitedSession:
    """假的 session:先回 429 ``limited_times`` 次,之後回 200。"""

    def __init__(self, limited_times):
        self.limited_times = limited_times
        self.calls = 0

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls += 1
        if self.calls <= self.limited_times:
            return _Resp(status_code=429, headers={"Retry-After": "1"})
        return _Resp("<html>ok</html>")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fetch_mod.time, "sleep", lambda *_: None)


def test_returns_text_on_first_success():
    sess = _Session(fail_times=0)
    assert fetch_html("http://x", session=sess) == "<html>ok</html>"
    assert sess.calls == 1


def test_retries_then_succeeds():
    sess = _Session(fail_times=2)
    assert fetch_html("http://x", session=sess) == "<html>ok</html>"
    assert sess.calls == 3


def test_raises_after_exhausting_retries():
    sess = _Session(fail_times=99)
    with pytest.raises(FetchError):
        fetch_html("http://x", session=sess)
    assert sess.calls == fetch_mod.MAX_RETRIES


def test_backs_off_on_429_then_succeeds():
    sess = _RateLimitedSession(limited_times=2)
    assert fetch_html("http://x", session=sess) == "<html>ok</html>"
    assert sess.calls == 3


def test_raises_after_persistent_429():
    sess = _RateLimitedSession(limited_times=99)
    with pytest.raises(FetchError):
        fetch_html("http://x", session=sess)
    assert sess.calls == fetch_mod.MAX_RETRIES
