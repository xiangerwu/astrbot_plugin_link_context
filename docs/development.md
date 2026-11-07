# 開發與驗證

[返回首頁](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.md) · [English overview](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.en.md)

## 專案結構

```text
astrbot_plugin_link_context/
├── main.py                 # AstrBot 入口、事件、背景工作與 LLM 工具
├── metadata.yaml           # 插件名稱、版本、作者、倉庫與版本限制
├── _conf_schema.json       # WebUI 配置結構
├── requirements.txt        # 執行依賴
├── logo.png                # AstrBot 按根目錄固定檔名載入的市場圖示
├── README.md               # 繁體中文入口
├── README.en.md            # 英文入口
├── LICENSE
├── core/
│   ├── __init__.py
│   ├── fetch.py            # 網路邊界與平台內容擷取
│   ├── media.py            # 圖片準備與既有模型提供商整合
│   └── store.py            # SQLite 近期記錄與上下文預算
├── tests/
│   ├── __init__.py
│   └── test_link_context.py
├── assets/
│   └── intro.png           # README 介紹圖
└── docs/
    ├── installation.md
    ├── bilibili-cookie.md
    ├── threads-cookie.md
    ├── usage.md
    ├── discord.md
    ├── troubleshooting.md
    ├── development.md
    ├── publishing.md
    ├── references.md
    └── artwork.md
```

根目錄保留 AstrBot 需要直接辨識的入口與檔案，其餘依用途分類。[官方載入器](https://github.com/AstrBotDevs/AstrBot/blob/v4.29.4/astrbot/core/star/star_manager.py)會搜尋插件資料夾的 `main.py`，並使用 `logo.png` 作為圖示檔名；一般插件的 `core/`、`docs/` 分層可見 [media_parser](https://github.com/drdon1234/astrbot_plugin_media_parser)。目錄名稱是本專案選擇，不是 AstrBot 強制的統一架構。

`main.py` 以 `.core.fetch`、`.core.media`、`.core.store` 匯入內部模組；`core/media.py` 使用同層 `.fetch`。測試從自身位置計算專案根目錄，再載入真實模組及根目錄配置，不依賴目前工作目錄尋找配置檔。`tests/__init__.py` 保留由根目錄遞迴探索測試的能力。

執行資料仍由 `StarTools.get_data_dir` 決定，這次目錄整理不搬動 `data/plugin_data/astrbot_plugin_link_context/links.sqlite3`。本機 `.venv/`、`__pycache__/` 與 `dist/*.zip` 是忽略的環境／產物，不納入 Git 或發布包。

## 自動化檢查

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

2026-11-07 本機已通過 **22 項測試**（Python 3.14、Windows），覆蓋範圍如下。AstrBot、模型與遠端站台由邊界替身替代；瀏覽器測試使用本機 Chromium 與受控頁面，不能當作 Linux 部署、真實站台成功率或 OpenAI 模型效果驗證。

| 範圍 | 已檢查行為 |
| --- | --- |
| 插件流程 | 貼連結不發消息、不喚醒；依 AstrBot 的降序事件契約，在內建群聊前排隊且注入 pending 狀態；背景結果與暫時上下文；既有人格保留；純文字不額外呼叫模型 |
| 會話與保存 | Discord 頻道／討論串／平台實例隔離、SQLite 持久化、重載中斷、保留期限與內容截斷 |
| 手動重讀 | 指令先於普通讀取執行並停止後續事件；舊記錄更新、最近 20 筆之外的記錄、處理中去重、跨會話隔離、錯誤網址／私訊拒絕、佇列滿或寫入失敗時保留舊記錄 |
| 平台解析 | PTT 主文及圖片連結、X ID／配圖、Bilibili 影片資訊及動態、Threads 核對目標貼文與預覽缺漏 |
| 圖片與影片 | 真實圖片解碼與縮放；直接 GIF 網址保留簽名參數、只下載一次、8 幀順序、短 GIF 不重複幀及單次模型請求；影片不下載、不理解，記錄明確標示 |
| 網路邊界 | 私有位址及 DNS／重新導向檢查、無 Content-Length 時的串流大小上限、Cookie 網域與 HTTPS 降級隔離 |
| 故障與工具 | 暫存建立／清理／SQLite 寫入失敗後後續工作仍能處理；觀察與注入時 SQLite 錯誤不外拋；分頁接受 `12000`／`12000.0`，拒絕負數、非整數等輸入 |

請先依[安裝說明](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/installation.md)安裝依賴與 Chromium，並在專案根目錄執行測試。若使用自行安裝的 Chromium，可透過環境變數 `LINK_CONTEXT_TEST_BROWSER` 指定執行檔；其餘情況使用 Playwright 的 Chromium。

此外，以官方 v4.29.4 的原始函式進行獨立檢查：元資料校驗及版本範圍通過；Discord adapter 的訊息轉換在隔離物件測試中保留頻道／討論串 ID 與網址。這些檢查沒有登入 Discord，也不是完整 AstrBot 啟動測試。

提交前使用 Ruff（本次核對版本 0.15.22）：

```bash
ruff format --check .
ruff check .
```

2026-11-07 無 Cookie 的實際連線：PTT 文章正文可讀；X 的公開貼文成功經 FxEmbed 讀到作者與正文；Bilibili 影片資訊 API 回傳 HTTP 412；Threads 透過完整 Reader 流程讀到目標貼文的 268 字元公開預覽，但沒有完整結構化正文／配圖。平台結果會因網路、登入與站方變更而異。

## 部署後人工驗收

0.1.1 的事件排序修正已在本機回歸測試通過；更新到 Linux AstrBot 後仍需驗收。部署後請依序驗收：

1. 在已啟用插件的頻道貼一則公開文字連結，不 @ Bot，確認插件不發送解析結果、不加表情；AstrBot 既有主動回覆仍可按機率正常接話，見[讀取與回覆設定](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/usage.md#%E8%AE%80%E5%8F%96%E9%96%8B%E9%97%9C%E8%88%87%E5%9B%9E%E8%A6%86%E6%A9%9F%E7%8E%87)。
2. 等背景完成後，在同一會話 @ Bot 詢問內容；確認回答依記錄而非憑網址猜測。
3. 在另一頻道／討論串詢問同一內容，確認沒有跨會話取得記錄。
4. 貼一則有圖片的連結，確認所選 OpenAI 圖片模型能描述；這一步會產生模型費用。
5. 貼影片連結並詢問畫面／語音，確認 Bot 說明未觀看；重載後再查已完成的文字記錄，確認保存正常。
