# README Docker 驗證紀錄設計

## 背景

`README.md` 的 Docker 章節目前表示本機環境沒有 Docker，因而未宣稱容器執行結果。實際上，專案映像已在本機 Docker Desktop 的 Linux 容器環境完成建置與執行驗證，因此該說明已不符合目前狀態。

## 目標

以精簡且不易過時的文字，讓求職面試官或專案使用者知道 Docker 設定已經過實際驗證，而非僅提供未測試的啟動指令。

## 變更範圍

只修改 `README.md` 的 Docker 章節，將舊有的「本機沒有 Docker、未驗證容器」說明替換為實際驗證結果。

預計採用的文字如下：

> 上述映像已完成實際建置與執行驗證：`/api/health` 回傳 `{"status":"ok"}`、容器 `HEALTHCHECK` 為 `healthy`，且服務以非 root 的 `app` 使用者執行。驗證完成後已移除測試容器。

不修改應用程式程式碼、Dockerfile、測試或其他 README 章節。

## 文件策略

- 記錄與作品集品質直接相關的可驗證成果：映像建置、API 健康檢查、容器健康狀態與非 root 執行。
- 不記錄 Docker Desktop 或 Docker Engine 版本，避免環境升級後產生過時資訊。
- 不保留測試容器名稱、連接埠檢查過程等一次性細節。

## 驗證標準

在 README 修改完成後重新驗證目前分支：

1. Docker 映像可以成功建置。
2. 容器可以啟動，且 `/api/health` 回傳 `{"status":"ok"}`。
3. Docker `HEALTHCHECK` 最終為 `healthy`。
4. 容器設定與執行中的使用者皆為非 root 的 `app`。
5. 驗證用容器在檢查完成後移除。
6. `git diff --check` 通過，且 README 不再包含舊有的未驗證聲明。

## GitHub 交付

規格與 README 更新會放在由最新 `origin/main` 建立的獨立文件分支。完成驗證後提交變更、推送分支，並建立新的 draft pull request，供合併前檢閱。
