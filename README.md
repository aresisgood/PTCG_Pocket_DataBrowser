# PTCG Pocket 卡牌檢索 + 牌組實驗室

從 [pocket.limitlesstcg.com](https://pocket.limitlesstcg.com) 爬取 **Pokémon TCG
Pocket** 的所有卡牌與近期賽事資料,提供兩項功能:

1. **卡牌檢索** — 免依賴的靜態網頁,可搜尋/篩選/排序全部卡牌
2. **牌組實驗室** — 組牌、存牌,並依真實賽事對戰結果**預測勝率**

- **`scraper/`** — 卡牌與賽事爬蟲(fetch → parse → validate → save)
- **`analysis/`** — 由賽事對戰計算原型對戰矩陣、Meta 佔比、勝率預測
- **`api/`** — FastAPI + SQLite 後端(牌組 CRUD、勝率預測、Meta）
- **`web/`** — 前端:卡牌檢索頁 + 牌組實驗室頁
- **`data/cards.json`** — 卡牌權威資料;**`data/analysis.json`** — 勝率分析成品

## 快速開始

```bash
# 1. 安裝依賴
python -m pip install -r requirements.txt

# 2. 爬取所有卡牌 -> data/cards.json(約 3300 張,~30 分鐘,可續爬)
python -m scraper

# 3. 瀏覽:從 repo 根目錄以 HTTP 提供並開啟網頁
python -m http.server 8000
#   然後開啟  http://localhost:8000/web/
```

網頁必須透過 HTTP 提供(不能直接以 `file://` 開啟),因為它會 `fetch` 載入
`data/cards.json`。

## 牌組實驗室(勝率預測)

以 FastAPI 後端啟動,即可組牌、存牌並預測勝率。前端與 API 同源,無 CORS 問題。

```bash
# 1. 安裝依賴(含 FastAPI）
python -m pip install -r requirements.txt

# 2.(選配)更新賽事對戰資料 -> data/analysis.json
python -m analysis            # 讀 data/tournaments/dataset.json 重算
#   若要重新抓賽事:python -m scraper.tournaments
#   訓練 ML 勝率模型(選配):python -m analysis.train_ml -> data/model.joblib

# 3. 啟動應用
python -m uvicorn api.main:app --port 8000
#   卡牌檢索:  http://localhost:8000/
#   牌組實驗室:http://localhost:8000/deck.html
```

**預測原理(兩種方法並陳)**:

1. **原型對戰查表**:把你的牌組以卡片重疊度分類到最接近的**已知原型**,再依
   當前 Meta 各原型佔比,加權其歷史對戰勝率。可解釋、附最有利/最不利對戰。
2. **ML 模型(選配)**:以牌組「內容」特徵(屬性分布、EX 數、進化階段、HP、
   撤退、特性)訓練的邏輯迴歸,預測對 Meta 的勝率。**即使查表認不出**(自製
   牌組)也能給估計。

資料來自 [play.limitlesstcg.com](https://play.limitlesstcg.com) 的官方賽事 API
(近期大型賽事的逐場對戰結果)。

> **關於準確度的誠實說明**:PTCG Pocket 單場對戰變異極大,逐場預測本質接近
> 擲硬幣(ML 與查表的 AUC 皆約 0.55)。查表在「見過的對戰」上略準但校準差
> (小樣本的 0%/100% 格子);ML 校準較好(log-loss 0.69 vs 1.55),且能覆蓋
> **約 25% 查表沒看過的對戰**。因此兩者**並陳互補**,並一律附上信心度,不會
> 給出假裝很準的單一數字。

### 主要 API 端點

| 方法 | 路徑 | 說明 |
| :-- | :-- | :-- |
| `GET/POST` | `/api/decks` | 列出 / 建立牌組 |
| `GET/PUT/DELETE` | `/api/decks/{id}` | 讀取 / 更新 / 刪除牌組 |
| `POST` | `/api/predict` | 輸入牌組卡片 → 預估勝率 + 對戰優劣 |
| `GET` | `/api/meta` | 當前 Meta 原型佔比與整體勝率 |

## 爬蟲 CLI

```bash
python -m scraper                # 全量爬取,從 checkpoint 續爬
python -m scraper --test         # 冒煙測試:只爬前 2 個卡包
python -m scraper --set A1       # 只爬單一卡包
python -m scraper --no-resume    # 忽略既有 checkpoint 重新開始
```

每爬 50 張會寫一次 checkpoint 到 `data/cards.checkpoint.json`,中斷後可從斷點續爬。
失敗的 URL 記錄在 `data/failed_urls.json`。

## 卡牌資料結構

`data/cards.json` 中每筆紀錄:

| 欄位 | 範例 |
| :-- | :-- |
| `name`、`set_id`、`number` | `"Gardevoir"`、`"A1"`、`"132"` |
| `card_type`、`trainer_type` | `"pokemon"` / `"trainer"`、`"Supporter"` |
| `element`、`stage`、`evolves_from` | `"Psychic"`、`"Stage 2"`、`"Kirlia"` |
| `hp`、`weakness`、`retreat_cost` | `110`、`"Darkness"`、`2` |
| `ability_name`、`ability_text` | `"Psy Shadow"`、`"Once during your turn…"` |
| `attacks[]` | `{cost:["P","P","C"], name, damage, effect}` |
| `rarity`、`pack`、`illustrator` | `"Three Diamond"`、`"Mewtwo"`、… |
| `set_name`、`image_url`、`url` | `"Genetic Apex"`、CDN webp 圖片、來源頁面 |

## 測試

```bash
python -m pip install -r requirements-dev.txt
python -m pytest --cov=scraper
```

解析邏輯以 `tests/fixtures/` 中儲存的真實 HTML 為斷言基準,因此測試可完全離線執行。
目前 scraper 套件覆蓋率約 89%。

## 部署網頁

`web/` 為純靜態內容。只要把 `web/` 與 `data/cards.json` 從**同一個來源**提供
(例如以 repo 根目錄部署 GitHub Pages),網頁即可直接運作。