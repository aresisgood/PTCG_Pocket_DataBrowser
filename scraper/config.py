"""爬蟲設定常數。

集中管理 URL、HTTP 標頭、限流與檔案路徑,避免魔術數值散落在邏輯模組中。
"""
from __future__ import annotations

from project_config import (
    CARD_CHECKPOINT_JSON as CHECKPOINT_JSON,
    CARDS_JSON as OUTPUT_JSON,
    DATA_DIR,
    FAILED_CARD_URLS_JSON as FAILED_URLS_JSON,
    ROOT,
)

BASE_URL = "https://pocket.limitlesstcg.com"
CARDS_INDEX_URL = f"{BASE_URL}/cards"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# 禮貌性設定:每次請求之間的延遲與重試策略。
REQUEST_DELAY = 0.5      # 每張卡請求之間的秒數
REQUEST_TIMEOUT = 20     # 每次請求逾時秒數
MAX_RETRIES = 4
RETRY_BACKOFF = 1.5      # 指數退避基數（秒）
RATE_LIMIT_WAIT = 15     # 遇到 HTTP 429 時的基礎等待秒數（無 Retry-After 時使用）

# 每爬 N 張卡就寫一次 checkpoint,讓崩潰時不致遺失太多進度。
SAVE_EVERY = 50
