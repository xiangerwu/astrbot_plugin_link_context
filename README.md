# 靜默連結閱讀

群組貼出 HTTP(S) 連結時，在背景閱讀，之後聊天時將閱讀記錄提供給目前的 AstrBot 模型。插件本身不發送全文、摘要、圖片、影片或成功／失敗通知，也不因連結而主動喚醒聊天。

文字直接存成閱讀記錄；配圖呼叫 AstrBot 已設定的圖片模型理解。依本專案需求選用 OpenAI，不需要 MiniMax。**不下載影片、不抽幀、不轉錄、不讀字幕。** 影片標題、簡介或封面不等於影片內容。

## 來源與限制

| 來源 | 讀取方式 | 限制 |
| --- | --- | --- |
| PTT | HTML 主文、推文與內嵌圖片 | 已刪文、連線限制仍會失敗；外連圖片可能無法下載 |
| Twitter / X | FxEmbed 公開貼文 API，正文、引用文字、配圖 | 連結 ID 會送到第三方；不支援私密／需登入內容 |
| Threads | Chromium 載入後核對貼文 shortcode 的結構化資料 | 沒有正文時只取核對過網址的公開預覽，明確標示缺漏；預覽不提供配圖 |
| Bilibili | 影片資訊 API、動態／Opus 圖文 API，支援短網址 | 僅影片標題、簡介、封面；風控可能回傳 412，Cookie 也不保證成功 |
| 其他網頁 | HTML article／main／body 文字與圖片 | 不保證動態、登入、付費牆內容；不解析 PDF／檔案下載 |

這不是「所有網址都能完整閱讀」的保證。失敗、處理中、截斷與未理解的圖片都會留在記錄裡，讓聊天模型知道哪些內容不能聲稱看過。

## Linux 安裝

以 AstrBot **4.29.4** 的 API 為開發依據。將此資料夾放到 AstrBot 的 `data/plugins/astrbot_plugin_link_context`，在 **執行 AstrBot 的同一 Python 環境、同一帳號**執行：

```bash
cd /path/to/AstrBot/data/plugins/astrbot_plugin_link_context
python -m pip install -r requirements.txt
python -m playwright install chromium
```

若 Linux 缺少 Chromium 的系統套件，依 Playwright 安裝提示執行 `python -m playwright install-deps chromium`；此步驟可能需要系統管理員權限。Docker 部署必須在容器的環境安裝，並讓瀏覽器與依賴在容器重建後仍可取得。

在 AstrBot WebUI 掃描／載入插件，開啟「靜默連結閱讀」的配置：

- `vision_provider_id`：選擇已有且支援圖片輸入的 OpenAI 提供商；留空沿用該會話的聊天模型。沒有可用圖片模型時仍會保留文字及圖片未理解的原因。
- `max_images`：預設每個連結最多 8 張，每張呼叫模型一次，會產生 API 費用；只讀文字時不額外呼叫模型。
- `retention_hours`：預設 24 小時。會話最多提供最近 20 筆記錄；重啟後已完成記錄仍保留。
- `bilibili_cookie`、`threads_cookie`：選填，在插件配置中填寫，不要貼到聊天。只送給對應平台網域。X 使用公開 FxEmbed，沒有 X Cookie 選項。

儲存後重載此插件。若是手動放入資料夾而 WebUI 無法發現新插件，再按你的既有部署方式重啟 AstrBot；不需要重新啟動整台 Linux。

## 使用與資料

1. 群組貼一個連結，插件排入背景工作，不發消息。
2. 背景讀取完成後，在同一會話問「剛剛那篇在講什麼」或自然討論；由目前人格與聊天模型回答。
3. 太早詢問時模型只會取得「正在讀取」記錄。完成後不會自動補發回覆，需下一次聊天才會注入新內容。

閱讀記錄依 AstrBot 的 `unified_msg_origin` 隔離。若 AstrBot 設為群組內按使用者分開會話，就會跟著分開，其他人的會話不會自動共享記錄。只辨識訊息文字裡完整的 HTTP(S) 網址；QQ 分享卡片、圖片中的網址與單獨 BV 號不在第一版範圍。

每輪暫時注入最多 18,000 字元，單筆先放 6,000 字元；模型可以透過 `link_context_read` 工具分頁讀取已保存的記錄。網頁正文最多保留 24,000 字元，圖片理解後的總記錄有大小限制，所有截斷都會標記。這是近期記憶，沒有永久知識庫。

資料寫入 AstrBot 管理的 `data/plugin_data/astrbot_plugin_link_context/links.sqlite3`。圖片工作檔完成後移除。到期記錄在插件啟動或新群組訊息時清理。預設單一背景工作、最多排隊 32 個連結；滿載、失敗或重載中斷後可重貼以重試。

本插件不會改動其他插件。若原本的連結解析插件仍在轉發，需要在它自己的設定停用自動轉發或停用該插件。AstrBot 本身原有的聊天觸發規則也仍然有效。

## 驗證

```bash
python -m unittest discover -s . -p 'test_*.py' -v
```

本機已通過 15 項檢查：靜默背景流程、來源隔離、持久化、內容截斷、各平台資料解析、真實 Chromium 的目標貼文核對、真實圖片解碼與縮放、不請求影片、Cookie 與公開網路邊界。AstrBot 與模型呼叫以測試邊界替身替代，不能當作 Linux 部署或 OpenAI 模型效果驗證。

2026-11-07 無 Cookie 的實際連線：PTT 文章正文可讀；X 的公開貼文成功經 FxEmbed 讀到作者與正文；Bilibili 影片資訊 API 回傳 HTTP 412；Threads 透過完整 Reader 流程讀到目標貼文的 268 字元公開預覽，但沒有完整結構化正文／配圖。平台結果會因網路、登入與站方變更而異。

尚未在你的 Linux AstrBot 實機載入，也未使用你的 OpenAI 額度測試圖片效果。安裝後先用一則文字貼文和一則配圖貼文確認。

參考來源與選用理由見 [REFERENCES.md](REFERENCES.md)。
