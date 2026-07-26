# README Docker 驗證紀錄實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 更新 README 的 Docker 章節，準確記錄映像已完成實際建置、健康檢查與非 root 執行驗證。

**Architecture:** 只替換 `README.md` Docker 章節中的過時聲明，不修改應用程式、Dockerfile 或測試。文件內容以目前分支重新執行的 Docker 建置與容器檢查為依據，完成後透過獨立 draft pull request 交付。

**Tech Stack:** Markdown、Docker Desktop、Docker Engine、FastAPI、PowerShell、Git、GitHub

## Global Constraints

- 只修改 `README.md` 的 Docker 驗證說明；不修改程式碼、Dockerfile、測試或其他 README 章節。
- README 必須使用繁體中文。
- 必須記錄 `/api/health` 回傳 `{"status":"ok"}`、容器 `HEALTHCHECK` 為 `healthy`，以及服務由非 root 的 `app` 使用者執行。
- 不記錄 Docker Desktop 或 Docker Engine 版本。
- 不記錄一次性的容器名稱或主機連接埠。
- 所有驗證必須在目前分支重新執行，且驗證用容器完成後必須移除。
- 不移除或修改任何非本次驗證所建立的容器。

---

### Task 1: 更新並驗證 Docker 文件

**Files:**

- Modify: `README.md:98`

**Interfaces:**

- Consumes: `Dockerfile` 所定義的 `/api/health` 健康檢查、`app` 執行使用者，以及 README 現有 Docker 建置與執行指令。
- Produces: 與實際 Docker 驗證結果一致的繁體中文 README 說明。

- [ ] **Step 1: 確認修改前狀態**

執行：

```powershell
git status --short --branch
git diff -- README.md
Select-String -Path README.md -Pattern '沒有 Docker|不宣稱本機容器|/api/health|HEALTHCHECK' -Context 1,1
```

預期：目前位於 `docs/docker-verification-readme`，工作目錄沒有未提交的 README 修改，且第 98 行仍包含「本機驗證環境沒有 Docker」的過時聲明。

- [ ] **Step 2: 替換過時的 Docker 說明**

只將 `README.md` 第 98 行替換為：

```markdown
上述映像已完成實際建置與執行驗證：`/api/health` 回傳 `{"status":"ok"}`、容器 `HEALTHCHECK` 為 `healthy`，且服務以非 root 的 `app` 使用者執行。驗證完成後已移除測試容器。
```

- [ ] **Step 3: 檢查文件差異**

執行：

```powershell
git diff --check
git diff -- README.md
rg -n "沒有 Docker|不宣稱本機容器|尚未.*Docker|/api/health|HEALTHCHECK|非 root" README.md
```

預期：`git diff --check` 通過；舊有未驗證聲明消失；新的健康檢查、`HEALTHCHECK` 與非 root 說明各出現一次。

- [ ] **Step 4: 確認 Docker 工具與測試資源沒有衝突**

將 Docker CLI 加入本次 PowerShell 工作階段：

```powershell
$dockerBin = 'C:\Program Files\Docker\Docker\resources\bin'
$env:PATH = "$dockerBin;$env:PATH"
docker version
```

確認固定驗證容器不存在，且主機連接埠 `18000` 未被占用：

```powershell
docker ps -a --filter "name=^/ptcg-pocket-databrowser-readme-verify-20260726$" --format "{{.Names}}"
Get-NetTCPConnection -LocalPort 18000 -State Listen -ErrorAction SilentlyContinue
```

預期：Docker client 與 server 都可用；兩個資源檢查都沒有輸出。若容器名稱或連接埠已被占用，停止本 Task 並回報衝突，不刪除或停止既有資源。

- [ ] **Step 5: 建置目前分支的 Docker 映像**

執行：

```powershell
docker build -t ptcg-pocket-databrowser .
```

預期：命令結束碼為 0，且產生或更新本機映像 `ptcg-pocket-databrowser:latest`。

- [ ] **Step 6: 啟動、驗證並清理容器**

使用 `try/finally`，確保檢查失敗時仍只會移除本次建立的固定名稱容器：

```powershell
$containerName = 'ptcg-pocket-databrowser-readme-verify-20260726'
$containerStarted = $false
try {
    docker run -d --name $containerName -p 127.0.0.1:18000:8000 ptcg-pocket-databrowser
    if ($LASTEXITCODE -ne 0) { throw 'docker run failed' }
    $containerStarted = $true

    $health = ''
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        $health = docker inspect --format '{{.State.Health.Status}}' $containerName
        if ($health -eq 'healthy') { break }
        Start-Sleep -Seconds 1
    }
    if ($health -ne 'healthy') { throw "Container health status: $health" }

    $response = Invoke-RestMethod -Uri 'http://127.0.0.1:18000/api/health'
    $configuredUser = docker inspect --format '{{.Config.User}}' $containerName
    $runtimeUid = docker exec $containerName id -u
    $runtimeUser = docker exec $containerName whoami

    if ($response.status -ne 'ok') { throw "Unexpected API status: $($response.status)" }
    if ($configuredUser -ne 'app') { throw "Unexpected configured user: $configuredUser" }
    if ($runtimeUid -eq '0') { throw 'Container is running as root' }
    if ($runtimeUser -ne 'app') { throw "Unexpected runtime user: $runtimeUser" }

    [pscustomobject]@{
        ApiStatus = $response.status
        Health = $health
        ConfiguredUser = $configuredUser
        RuntimeUid = $runtimeUid
        RuntimeUser = $runtimeUser
    }
}
finally {
    if ($containerStarted) {
        docker rm -f $containerName
    }
}
```

確認測試容器已清理：

```powershell
docker ps -a --filter "name=^/ptcg-pocket-databrowser-readme-verify-20260726$" --format "{{.Names}}"
```

預期：驗證結果顯示 API 狀態為 `ok`、健康狀態為 `healthy`、設定使用者為 `app`、執行 UID 不為 `0`、執行使用者為 `app`；清理檢查沒有輸出。本機映像保留供後續使用。

- [ ] **Step 7: 執行最終文件驗證並提交**

執行：

```powershell
git diff --check
rg -n "沒有 Docker|不宣稱本機容器|尚未.*Docker" README.md
git status --short
```

預期：沒有空白錯誤、舊聲明掃描沒有結果，且只有 `README.md` 尚未提交。

提交：

```powershell
git add README.md
git commit -m "docs: record verified Docker runtime"
```

### Task 2: 發布 draft pull request

**Files:**

- No repository file changes.

**Interfaces:**

- Consumes: `docs/docker-verification-readme` 分支上的規格提交與已驗證 README 提交。
- Produces: 以 `main` 為基底的 GitHub draft pull request。

- [ ] **Step 1: 確認分支與提交範圍**

執行：

```powershell
git status --short --branch
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
```

預期：工作目錄乾淨；分支僅包含設計規格、實作計畫與 README 修改；差異不包含程式碼或 Dockerfile。

- [ ] **Step 2: 推送分支**

執行：

```powershell
git push -u origin docs/docker-verification-readme
```

預期：遠端分支建立成功，且本機分支追蹤 `origin/docs/docker-verification-readme`。

- [ ] **Step 3: 建立 draft pull request**

使用 GitHub 建立以 `main` 為 base、`docs/docker-verification-readme` 為 head 的 draft PR。

標題：

```text
docs: 記錄 Docker 實際驗證結果
```

內文：

```markdown
## 摘要

- 移除 README 中「本機沒有 Docker、未實際驗證」的過時聲明
- 記錄映像已完成建置與容器執行驗證
- 記錄 `/api/health`、Docker `HEALTHCHECK` 與非 root 使用者驗證結果

## 驗證

- `docker build -t ptcg-pocket-databrowser .`
- `/api/health` 回傳 `{"status":"ok"}`
- 容器 `HEALTHCHECK` 為 `healthy`
- 設定與執行使用者皆為非 root 的 `app`
- 驗證容器已移除
- `git diff --check`
```

- [ ] **Step 4: 核對 PR**

確認：

```text
狀態：Draft
Base：main
Head：docs/docker-verification-readme
Files changed：README.md 與本次規格／計畫文件
```

回報 PR 網址與 Docker 驗證結果，不宣稱 PR 已合併。
