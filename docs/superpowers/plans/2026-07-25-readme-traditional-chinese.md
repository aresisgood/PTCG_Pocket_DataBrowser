# README 繁體中文化實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將專案 README 改寫為適合台灣求職閱讀的繁體中文版本，並維持所有技術事實、指令與限制不變。

**Architecture:** 僅修改 `README.md` 的人類可讀內容，不改動程式碼、API 契約或執行流程。保留英文技術名稱與所有可執行字串，並以文件掃描及既有介面檢查驗證翻譯沒有破壞內容。

**Tech Stack:** Markdown、Mermaid、FastAPI、Python、GitHub

## Global Constraints

- 使用繁體中文，不使用中國大陸用語或簡體字。
- 保留 `Python`、`FastAPI`、`SQLModel`、`ETL`、`API`、`Docker`、`SQLite`、`GitHub Actions`、`pytest`、`ML` 等英文技術名稱。
- API 路徑、指令、網址、檔案路徑、環境變數與程式碼區塊不得翻譯。
- 修正 `Pok矇mon` 為 `Pokémon`。
- 保留 AUC 約 0.55、ML log-loss 0.69、查表法 log-loss 1.55、約 25% 未見對戰覆蓋率及其限制。
- SQLite 是唯一已驗證的持久化後端。
- Docker 尚未在本機完成建置與執行驗證。
- 不宣稱公開部署、PostgreSQL 支援、正式環境可用性或保證性的模型表現。

---

### Task 1: 將 README 改寫為繁體中文

**Files:**

- Modify: `README.md:1-161`

**Interfaces:**

- Consumes: 目前 README 的技術事實、指令、API 路徑、數據與限制。
- Produces: 繁體中文的專案介紹文件，供 GitHub 訪客與台灣招聘者閱讀。

- [ ] **Step 1: 改寫標題、摘要與專案特色**

保留專案名稱 `PTCG Pocket DataBrowser`，將開場定位改寫為：

```markdown
# PTCG Pocket DataBrowser

這是一個以 Python 後端與資料管線為核心的作品集專案，用於探索 Pokémon TCG Pocket 卡牌、賽事結果、牌組原型，以及提供輕量的牌組表現估計。
```

將 `Highlights` 改為「專案特色」，並保留 FastAPI、SQLModel、ML、Docker、pytest 與 GitHub Actions 等技術名稱。

- [ ] **Step 2: 中文化架構與 ETL 圖**

將章節改為「系統架構」與「ETL 資料流程」，並使用以下節點語意：

```text
Limitless TCG → scraper → cards.json / tournament dataset
tournament dataset → analysis → analysis.json / model.joblib
cards.json 與分析產物 → FastAPI → SQLite / 靜態網頁介面

擷取 Fetch → 解析 Parse → 驗證 Validate → 檢查點 Checkpoint
→ 輸出 Output → 彙整／模型 Aggregate / Model → REST API
```

保持 Mermaid `flowchart LR` 語法與節點連線有效。

- [ ] **Step 3: 中文化操作說明與 API 表格**

將本機執行、資料蒐集與分析、測試、Docker 等說明改為繁體中文，但完整保留：

```bash
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --port 8000
DATABASE_URL=sqlite:///data/decks.db
python -m scraper --test
python -m analysis
python -m scraper --help
python -m pytest --cov=scraper --cov=analysis --cov=api --cov-report=term-missing
docker build -t ptcg-pocket-databrowser .
docker run --rm -p 8000:8000 ptcg-pocket-databrowser
```

API 表格欄名改為「方法／路徑／用途」，用途依序翻譯為健康檢查、牌組列表或建立、單一牌組讀取／取代／刪除、牌組表現估計、目前牌組原型環境。

- [ ] **Step 4: 中文化資料、模型與限制說明**

保留資料來源連結與所有數字，並明確說明：

```text
AUC 約 0.55
ML log-loss 0.69
查表法 log-loss 1.55
ML 約可涵蓋 25% 查表法未見的對戰組合
模型輸出不是未來勝率保證
SQLite 是已驗證的持久化後端
缺少模型產物時，API 的 ML 輸出為 null
沒有公開部署
Docker 尚未在本機實際建置或啟動驗證
```

- [ ] **Step 5: 驗證文件完整性**

執行：

```bash
python -m scraper --help
python -m analysis --help
python -m uvicorn api.main:app --help
python -m pytest --help
git ls-files api analysis scraper web data README.md Dockerfile .dockerignore .env.example .github/workflows/tests.yml
git diff --check
```

掃描：

```bash
rg -n "Pok矇mon|TBD|TODO|public demo|PostgreSQL|production-ready" README.md
```

預期：四個說明指令成功、引用檔案存在、無空白錯誤，且不出現錯碼、未完成標記或不支援的英文宣稱。

- [ ] **Step 6: 提交**

```bash
git add README.md
git commit -m "docs: translate README to Traditional Chinese"
```
