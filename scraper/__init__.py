"""PTCG Pocket 卡牌爬蟲套件。

模組:
    config   - 常數(URL、標頭、路徑、延遲）
    models   - 卡牌 schema 與驗證
    parse    - HTML -> 卡牌 dict（純函式,不涉及網路）
    fetch    - HTTP 層（重試、限流）
    sets     - 卡包清單與卡牌 URL 探索
    card_catalog       - 卡牌目錄的最高層蒐集介面
    tournament_dataset - 賽事資料集的最高層蒐集介面
"""
