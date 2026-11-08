# 靜默連結閱讀

[繁體中文](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.md) | [English](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.en.md)

![靜默連結閱讀：讀懂連結，接上話題](https://raw.githubusercontent.com/xiangerwu/astrbot_plugin_link_context/main/assets/intro.png)

讓 AstrBot 默默讀取群組分享的連結，在之後的聊天中自然參與討論。插件不自動轉發全文、摘要、配圖或完成通知，也不因連結而喚醒聊天。主要使用情境是 Discord 文字頻道與討論串。

- 支援 PTT、X、Threads、Bilibili、Instagram、Facebook、Bluesky、Misskey.io、TikTok、巴哈姆特、Plurk、Pixiv、Steam Workshop、PChome 24h、E-Hentai／ExHentai、nhentai 與一般 HTML 網頁；各站的公開內容與預覽限制見[平台支援](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/usage.md#平台支援)。
- 正文直接存成近期記錄；圖片透過 AstrBot 已配置的 OpenAI 圖片模型理解，每張圖會產生模型費用。
- 支援 JPG／PNG／WebP／GIF 直接網址（含 Discord 圖片連結）；GIF 最多抽取 8 幀，合併一次讀圖請求，可能漏掉短暫動作且會增加圖片用量。
- **不處理影片畫面、語音或字幕**；標題、簡介與封面不代表看過影片。
- 記錄依會話隔離，預設保留 24 小時；重啟後已完成記錄仍保留。
- 讀取由插件／會話啟用設定控制；自然接話沿用 AstrBot 的主動回覆機率，不必每條連結都回覆。[設定方式](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/usage.md#%E8%AE%80%E5%8F%96%E9%96%8B%E9%97%9C%E8%88%87%E5%9B%9E%E8%A6%86%E6%A9%9F%E7%8E%87)

## 快速開始

需要 AstrBot **4.29.4 以上**、Python **3.12 以上**，以及支援圖片輸入的已配置模型。

1. 在 AstrBot WebUI 透過倉庫網址安裝，或將專案放到 `data/plugins/astrbot_plugin_link_context`：

   ```text
   https://github.com/xiangerwu/astrbot_plugin_link_context
   ```

2. 在執行 AstrBot 的同一 Python 環境與帳號中安裝依賴及 Threads 使用的 Chromium：

   ```bash
   cd /path/to/AstrBot/data/plugins/astrbot_plugin_link_context
   python -m pip install -r requirements.txt
   python -m playwright install chromium
   ```

3. 在插件配置選擇圖片模型；Discord 啟用 Message Content Intent，並依[Discord 設定](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/discord.md)核對 AstrBot adapter 請求的其他 intents 與頻道權限。
4. 重載插件，在群組貼出連結。背景完成後，在同一會話喚醒 Bot 詢問或接著討論；插件不會發送完成通知。

同一則訊息直接 @ Bot 並附上完整連結時，會在本輪回答前最多等待 15 秒取得讀取結果。一般貼連結不等待；超時後背景工作繼續，但不自動補發回覆。

要重讀舊 GIF 或重試已完成的連結，在原頻道輸入 `/link_reread 完整網址`。指令回覆一次排隊狀態，之後靜默重讀；圖片會再次產生模型費用。詳見[手動重新讀取](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/usage.md#%E6%89%8B%E5%8B%95%E9%87%8D%E6%96%B0%E8%AE%80%E5%8F%96)。

Linux 系統依賴、Docker、Cookie 與各項配置見[安裝與配置](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/installation.md)。部署前請告知成員連結與圖片的處理方式，詳見[資料使用與管理](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/discord.md#%E8%B3%87%E6%96%99%E4%BD%BF%E7%94%A8%E8%88%87%E7%AE%A1%E7%90%86)。

## 文件導覽

| 文件 | 內容 |
| --- | --- |
| [安裝與配置](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/installation.md) | Linux、Docker、圖片模型、Cookie、更新與重載 |
| [Bilibili Cookie 教學](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/bilibili-cookie.md) | 取得請求 Cookie、填寫欄位、驗收、失效與 412 排錯 |
| [Threads Cookie 教學](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/threads-cookie.md) | 取得 Cookie、Chromium、公開預覽限制與更新方式 |
| [使用方式與限制](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/usage.md) | 各平台支援、背景流程、記錄保存、分頁與重試 |
| [Discord 設定與資料管理](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/discord.md) | Intents、頻道／討論串權限、會話隔離、隱私與刪除 |
| [常見問題與排錯](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/troubleshooting.md) | 無記錄、圖片失敗、Threads、Bilibili 412、網路與資料庫 |
| [開發與驗證](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/development.md) | 目錄結構、測試命令、驗證範圍與實機驗收 |
| [插件市場發布](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/publishing.md) | 必要檔案、打包與上架流程 |
| [開源參考](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/references.md) | 查閱專案、官方介面與採用／未採用的設計 |
| [美術來源](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/artwork.md) | 介紹圖、圖示、角色來源與完整生成提示詞 |

## 已知限制

0.2.0 起 Threads 分享網址先解析轉址，優先讀取可核對的靜態貼文／公開預覽；已有文字時不必啟動 Chromium。其他新增平台參考 ermiana 的公開 API 與預覽來源，只保存資料，不轉發卡片，也不讀取其他 Bot 的 Discord 訊息。

Threads 可能只有公開預覽，Bilibili 可能被風控拒絕；並非所有網址都能完整讀取。`ready` 表示流程完成，仍可能包含未讀圖片或截斷。影片內容、私訊、歷史訊息、訊息編輯／刪除同步與永久知識庫不在目前範圍。其他插件與 Discord 自己的連結預覽需要各自設定。

已有 33 項自動化測試，包含事件排序、GIF 8 幀抽樣與短 GIF 不重複幀檢查。自動化測試不等於完整部署驗收。測試邊界與實際站台檢查結果見[開發與驗證](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/development.md)。

## 授權與致謝

程式碼採 [MIT License](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/LICENSE)。參考 [Ermiana](https://github.com/canaria3406/ermiana) 的解析與輸出分離、PTT 擷取思路，以及 [web_access](https://github.com/Dashu-Li/astrbot_plugin_web_access)、[video_context](https://github.com/ZAKOsiesta/astrbot_plugin_video_context)、[media_parser](https://github.com/drdon1234/astrbot_plugin_media_parser) 等專案；完整來源與取捨見[開源參考](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/references.md)。

介紹圖與圖示為非官方 AI 衍生美術，MIT 不重新授權原角色／品牌，也不代表 AstrBot 官方背書；詳見[美術來源](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/artwork.md)。問題回報請使用 [GitHub Issues](https://github.com/xiangerwu/astrbot_plugin_link_context/issues)，不要附上 Cookie、Token、私密網址或資料庫。
