# PTCG Pocket DataBrowser 作品集強化設計

日期：2026-07-25

## 1. 目標

將 `PTCG_Pocket_DataBrowser` 強化為以 Python 後端工程師為主要投遞方向、
資料工程師為次要方向的求職作品。

完成後，專案應能清楚證明以下能力：

- 使用 FastAPI 建立具備明確資料契約與錯誤處理的 REST API。
- 使用 SQLModel 管理資料持久化，並以環境變數切換資料庫連線。
- 使用 Docker 建立可重現的執行環境。
- 使用自動化流程執行測試與品質檢查。
- 將外部資料經過擷取、解析、驗證、儲存與分析後提供給應用服務。
- 能誠實說明模型準確度、資料限制與技術取捨。

## 2. 設計原則

1. 保留現有的 `scraper → analysis → api → web` 架構，不重寫已穩定運作的核心。
2. 優先補齊後端職缺常見的工程證據：驗證、設定、測試、容器化與 CI。
3. 資料工程能力透過現有資料流程與資料品質紀錄呈現，不另建過度複雜的平台。
4. SQLite 保留為本機預設，資料庫連線可由環境變數覆寫，方便後續接 PostgreSQL。
5. 不在本階段加入登入、Redis、Kafka、微服務或雲端基礎設施。

## 3. 範圍

### 3.1 API 資料契約與驗證

為牌組與預測請求建立明確的 Pydantic／SQLModel schema：

- 牌組名稱去除前後空白後須為 1–100 個字元。
- 卡片必須包含 `set`、`number` 與 `count`。
- `set` 與 `number` 去除前後空白後須為 1–20 個字元。
- `count` 必須是 1 或 2。
- 預測請求至少要包含一張卡片。
- 驗證失敗沿用 FastAPI 的 `422` 回應，README 提供範例。

資料庫模型與外部 API schema 保持分離，避免將資料庫欄位直接暴露成所有寫入契約。

### 3.2 應用設定與資料庫

新增集中式設定模組：

- `DATABASE_URL`：預設使用目前的 `data/decks.db`。
- 由 `create_db_engine(database_url)` 建立引擎；設定值在建立應用時讀取。
- SQLite 自動套用 `check_same_thread=False`。
- 非 SQLite 連線不傳入 SQLite 專用參數。

本階段只保證 SQLite 測試通過；程式介面需允許後續加入 PostgreSQL 整合測試，
但不宣稱尚未驗證的 PostgreSQL 相容性。

### 3.3 健康檢查

新增 `GET /api/health`：

- 應用正常時回傳 HTTP `200`。
- 回應包含固定狀態值，例如 `{"status": "ok"}`。
- 此端點不讀取大型卡牌資料或 ML 模型，避免健康檢查產生不必要負擔。

### 3.4 Docker 執行環境

新增：

- `Dockerfile`
- `.dockerignore`

容器設計：

- 使用正式 Python 基底映像。
- 安裝 `requirements.txt`。
- 以 Uvicorn 啟動 FastAPI。
- 對外開放應用連接埠。
- 保留掛載 `data/` 的方式，使 SQLite 與資料成品可持久化。

本階段不加入 PostgreSQL 容器，以免作品說明超過實際驗證範圍。

### 3.5 自動化品質檢查

新增 GitHub Actions workflow，在 push 與 pull request 時：

1. 建立 Python 3.11 與 3.12 測試環境。
2. 安裝開發依賴。
3. 執行完整 pytest 測試。
4. 對 `scraper`、`analysis` 與 `api` 產生終端機覆蓋率摘要。

CI 失敗時應明確阻止錯誤被誤認為可交付狀態。初期不設定過高的覆蓋率門檻，
避免為了數字撰寫低價值測試；README 只呈現實際量測結果。

### 3.6 資料流程可觀測性

保留現有 checkpoint 與 failed URL 機制，補上可供作品展示的執行摘要：

- 發現的資料集合數量。
- 成功產出的卡牌數量。
- 失敗數量。
- 輸出檔案位置。

若現有日誌已提供上述資訊，只補文件與測試，不重複建立新的資料管線框架。

### 3.7 README 作品集化

README 重新組織為：

1. 一句話專案摘要與核心成果。
2. 功能展示區，預留實際截圖或 GIF 位置；沒有素材時不放假圖。
3. 系統架構圖。
4. ETL／資料流圖。
5. 技術選型與取捨。
6. 本機與 Docker 快速開始。
7. API 端點及成功／失敗範例。
8. 測試與 CI 說明。
9. 模型評估與限制。
10. 後續可擴充項目。

README 不宣稱線上 Demo、PostgreSQL、部署平台或模型成果，除非實際完成並驗證。

## 4. 系統結構

```text
Limitless TCG
    │
    ▼
scraper
  fetch → parse → validate → checkpoint/output
    │
    ├──────────────► data/cards.json
    ▼
analysis
  classify → matchup aggregation → optional ML model
    │
    └──────────────► data/analysis.json
                         │
                         ▼
FastAPI
  health / deck CRUD / prediction / meta
       │                 │
       ▼                 ▼
   SQLite           static web client
```

新增內容應保持邊界清楚：

- 設定模組只負責讀取與正規化設定。
- API schema 只負責外部資料契約。
- router 負責 HTTP 協定與流程協調。
- 現有分析函式保留純函式設計。
- 爬蟲保留擷取、解析、驗證與儲存的分工。

## 5. 錯誤處理

- 使用者輸入錯誤：回傳 `422` 與欄位級錯誤。
- 找不到牌組：維持 `404 deck not found`。
- 分析資料不足：維持成功回應，但使用 `null`、信心度及說明文字明確揭露限制。
- 啟動設定錯誤：在啟動階段明確失敗，不靜默切換到未知資料庫。
- 爬蟲單筆失敗：記錄失敗來源後繼續處理其餘資料。

錯誤回應不得包含密碼、完整資料庫連線憑證或本機敏感路徑。

## 6. 測試策略

所有行為變更採測試先行：

1. 先新增會因缺少功能而失敗的測試。
2. 確認失敗原因符合預期。
3. 以最小修改讓測試通過。
4. 執行完整測試避免回歸。

新增測試至少涵蓋：

- 空白牌組名稱被拒絕。
- 無效卡片欄位與數量被拒絕。
- 空預測請求被拒絕。
- 健康檢查成功。
- 預設 SQLite 與自訂資料庫 URL 的設定行為。
- Docker 映像可建置，且容器啟動後健康檢查可回應。

既有爬蟲、分析、API 測試必須保留。若第三方套件產生棄用警告，應確認來源並在
不破壞相容性的前提下處理或記錄，不以全域忽略掩蓋未知警告。

## 7. 完成條件

- 完整測試套件通過。
- 新增行為均有測試證明。
- Docker 映像可建置，容器內健康檢查可成功。
- CI workflow 語法有效且會執行完整測試。
- README 所有命令均經本機驗證。
- README 中沒有未完成標記、虛構成果或無效連結。
- Git diff 僅包含此設計範圍內的修改。

## 8. 預計成果

履歷可將此專案描述為：

> 建立 Pokémon TCG Pocket 資料應用，使用 Python 完成卡牌與賽事資料的擷取、
> 驗證及分析，透過 FastAPI 與 SQLModel 提供牌組 CRUD、Meta 查詢與勝率預測
> API，並以 pytest、Docker 與 CI 建立可重現的開發及驗證流程。
