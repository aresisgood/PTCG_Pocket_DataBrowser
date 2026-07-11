"""HTTP 層:以禮貌方式抓取頁面,含重試與退避。

與解析邏輯隔離,使網路關注點可獨立測試/掛載,並讓套件其餘部分保持純函式。
"""
from __future__ import annotations

import time
from typing import Any

import requests

from .config import (
    HEADERS, MAX_RETRIES, RATE_LIMIT_WAIT, REQUEST_TIMEOUT, RETRY_BACKOFF,
)


class FetchError(RuntimeError):
    """在所有重試皆失敗、仍無法抓取某 URL 時拋出。"""


def _retry_after(response: requests.Response, attempt: int) -> float:
    """HTTP 429 的等待秒數:優先用伺服器的 Retry-After,否則線性退避。"""
    header = response.headers.get("Retry-After")
    if header and header.isdigit():
        return float(header)
    return RATE_LIMIT_WAIT * attempt


def _get(url: str, params: dict[str, Any] | None,
         session: requests.Session | None) -> requests.Response:
    """GET ``url``,遇到暫時性錯誤時以指數退避重試。

    針對 HTTP 429（Too Many Requests）以較長、且尊重 Retry-After 的等待重試;
    其餘暫時性錯誤採指數退避。MAX_RETRIES 次皆失敗後拋出 FetchError,讓呼叫端
    可記錄後繼續,而非讓整個流程崩潰。
    """
    get = (session or requests).get
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = get(url, params=params, headers=HEADERS,
                           timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:  # 網路層錯誤
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF ** attempt)
            continue
        if response.status_code == 429:           # 被限流
            last_exc = FetchError(f"429 Too Many Requests for {url}")
            if attempt < MAX_RETRIES:
                time.sleep(_retry_after(response, attempt))
            continue
        try:
            response.raise_for_status()
            return response
        except requests.HTTPError as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF ** attempt)
    raise FetchError(f"failed to fetch {url}: {last_exc}") from last_exc


def fetch_html(url: str, session: requests.Session | None = None) -> str:
    """GET ``url`` 並回傳回應文字（HTML）。"""
    return _get(url, None, session).text


def fetch_json(url: str, params: dict[str, Any] | None = None,
               session: requests.Session | None = None) -> Any:
    """GET ``url`` 並回傳解析後的 JSON（供 Limitless API 使用）。"""
    return _get(url, params, session).json()