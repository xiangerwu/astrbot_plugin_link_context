# 插件市場發布

[返回首頁](../README.md) · [English overview](../README.en.md)

倉庫網址填在 `metadata.yaml`；根目錄的 `logo.png` 是透明背景、1:1 圖示，`assets/intro.png` 用於 README 介紹。這些檔案須隨原始碼一同推送，市場才能取得。建立 GitHub 空倉庫本身不會上架。

## 發布包路徑

根目錄需保留 `main.py`、`metadata.yaml`、`_conf_schema.json`、`requirements.txt`、`logo.png`、`LICENSE` 及中英文 README；保留 `core/`、`tests/`、`assets/`、`docs/` 的相對位置。不要將所有檔案攤平成一層，否則 Python 匯入、README 圖片與文件連結都會失效。

本機 ZIP 放在 `dist/`，不提交產物。完成[驗證](development.md)並提交預計發布的變更後，可在專案根目錄使用 Git 打包已提交版本：

```bash
mkdir -p dist
git archive --format=zip --output=dist/astrbot_plugin_link_context-0.1.0.zip HEAD
```

以上是 Linux shell 命令。`git archive HEAD` 只包含已提交且被追蹤的檔案，不包含工作目錄未提交的變更；打包前先確認 `git status --short` 與版本號。`dist/` ZIP、虛擬環境及執行資料應維持不受 Git 追蹤。

## 提交市場

依 [官方發布說明](https://docs.astrbot.app/dev/star/plugin-publish.html)，先將可安裝版本推送至公開 GitHub 倉庫，再登入 [AstrBot 插件發布平台](https://cloud.astrbot.app/publish) 提交倉庫，核對自動載入的名稱、版本、描述與圖示，依頁面流程完成發布。ZIP 上傳限制為 16 MB；只打包程式、配置結構、依賴清單、文件與圖片，不包含虛擬環境、瀏覽器、Cookie、資料庫或工作檔。是否已被市場收錄，以發布平台與市場實際結果為準。
