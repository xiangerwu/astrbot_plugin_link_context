# 靜默連結閱讀

![靜默連結閱讀：讀懂連結，接上話題](intro.png)

原始碼倉庫：[xiangerwu/astrbot_plugin_link_context](https://github.com/xiangerwu/astrbot_plugin_link_context)。授權：MIT。

群組貼出 HTTP(S) 連結時，在背景閱讀，之後聊天時將閱讀記錄提供給目前的 AstrBot 模型。主要使用情境是 Discord 伺服器文字頻道與討論串。插件本身不發送全文、摘要、圖片、影片或成功／失敗通知，也不因連結而主動喚醒聊天。

文字直接存成閱讀記錄；配圖呼叫 AstrBot 已設定的圖片模型理解。依本專案需求選用 OpenAI，不需要 MiniMax。**不下載影片、不抽幀、不轉錄、不讀字幕。** 影片標題、簡介或封面不等於影片內容。

## 來源與限制

| 來源 | 讀取方式 | 限制 |
| --- | --- | --- |
| PTT | HTML 主文、推文、作者、內嵌及文字／超連結中的圖片 | 已刪文、連線限制仍會失敗；外連圖片可能無法下載 |
| Twitter / X | FxEmbed 公開貼文 API，正文、引用文字、配圖 | 連結 ID 會送到第三方；不支援私密／需登入內容 |
| Threads | Chromium 載入後核對貼文 shortcode 的結構化資料 | 沒有正文時只取核對過網址的公開預覽，明確標示缺漏；預覽不提供配圖 |
| Bilibili | 影片資訊 API、動態／Opus 圖文 API，支援短網址 | 僅影片標題、簡介、封面；風控可能回傳 412，Cookie 也不保證成功 |
| 其他網頁 | HTML article／main／body 文字與圖片 | 不保證動態、登入、付費牆內容；不解析 PDF／檔案下載 |

這不是「所有網址都能完整閱讀」的保證。失敗、處理中、截斷與未理解的圖片都會留在記錄裡，讓聊天模型知道哪些內容不能聲稱看過。

## Linux 安裝

以 AstrBot **4.29.4** 的 API 為開發依據，該版要求 Python **3.12 以上**。將此資料夾放到 AstrBot 的 `data/plugins/astrbot_plugin_link_context`，在 **執行 AstrBot 的同一 Python 環境、同一帳號**執行：

```bash
cd /path/to/AstrBot/data/plugins/astrbot_plugin_link_context
python -m pip install -r requirements.txt
python -m playwright install chromium
```

若 Linux 缺少 Chromium 的系統套件，依 Playwright 安裝提示執行 `python -m playwright install-deps chromium`；此步驟可能需要系統管理員權限。Docker 部署必須在容器的環境安裝，並讓瀏覽器與依賴在容器重建後仍可取得。

在 AstrBot WebUI 掃描／載入插件，開啟「靜默連結閱讀」的配置：

- `vision_provider_id`：選擇已有且支援圖片輸入的 OpenAI 提供商；留空沿用該會話的聊天模型。沒有可用圖片模型時仍會保留文字及圖片未理解的原因。
- `max_images`：預設每個連結最多 8 張，每張呼叫模型一次，會產生 API 費用；只讀文字時不額外呼叫模型。
- `retention_hours`：預設 24 小時。會話最多選取最近 20 筆記錄，再依上下文預算裁短；重啟後已完成記錄仍保留。
- `bilibili_cookie`、`threads_cookie`：選填，在插件配置中填寫，不要貼到聊天。只送給對應平台的 HTTPS 網址；HTTP 或降級重新導向不會帶登入 Cookie。X 使用公開 FxEmbed，沒有 X Cookie 選項。配置頁的遮罩不是儲存加密，請保護 AstrBot 配置檔。

儲存後重載此插件。若是手動放入資料夾而 WebUI 無法發現新插件，再按你的既有部署方式重啟 AstrBot；不需要重新啟動整台 Linux。

## Discord 設定

沿用 AstrBot 的 Discord adapter 與官方 Bot 帳號，不需要另一個 Discord 客戶端或使用者 Token。

- **Gateway Intents**：要被動讀取沒有 @ 機器人的一般訊息，必須在 Developer Portal → Bot 啟用 **Message Content Intent**，並在 Discord 要求時完成審核；只有 @ 提及時能讀到內容不代表被動閱讀已正常。AstrBot v4.29.4 的 adapter 也會請求 **Server Members Intent**，需一併正確設定；本插件不自行增加 intents。[官方 Gateway 文件](https://docs.discord.com/developers/events/gateway)、[AstrBot Discord client](https://github.com/AstrBotDevs/AstrBot/blob/v4.29.4/astrbot/core/platform/sources/discord/client.py)
- **頻道權限**：背景讀取需要能檢視該頻道（View Channel）。一般聊天回覆另需 Send Messages；討論串回覆需 Send Messages in Threads。這個閱讀流程不發預覽、不抓歷史，因此不額外要求 Embed Links、Attach Files、Manage Messages、Manage Webhooks 或 Administrator；AstrBot 其他功能的需求另計。[官方權限文件](https://docs.discord.com/developers/topics/permissions)
- **隔離**：AstrBot 將頻道／討論串的 ID 作為 session ID，本插件沿用完整 `unified_msg_origin`。不同頻道、討論串與 Bot 平台實例不共享閱讀記錄；想讓同頻道成員一起討論，請使用 AstrBot 的群組共用會話設定。私密討論串仍須讓 Bot 有權存取，不擴大權限。
- **文字格式**：支援一般網址、`<https://example.com>`、`[標籤](https://example.com)`、反引號及 `||劇透網址||` 裡的連結。尖括號僅抑制 Discord 預覽，劇透標記也不代表退出 AI 閱讀；應在伺服器使用說明中告知成員。只處理新訊息文字，不回補歷史、不解析 Discord 自動 embed，也不監聽編輯／刪除事件。
- **機器人訊息**：沿用 AstrBot 的 `discord_allow_bot_messages`；預設關閉可避免把其他預覽 Bot 的輸出重複拿來閱讀。插件不更改這項設定。
- **靜默驗收**：普通連結訊息不應帶來本插件的回覆或表情。AstrBot 的預回應表情只在 `is_at_or_wake_command` 成立時觸發，本插件不設定它；@ Bot 或原本設定的聊天觸發條件仍可能帶來正常回覆。

## Discord 資料使用與管理

部署者應先取得伺服器管理者的允許，清楚告知成員：貼出的連結會被擷取、配圖送至所選模型理解，閱讀記錄會在同一會話提供給聊天模型。可透過 AstrBot 的會話插件設定停用本插件，或撤銷 Bot 的頻道存取權。不要將 Discord Bot Token、平台 Cookie 或私密網址貼到公開 Issue。

本插件保存連結、分享者顯示名稱、會話識別、分享時間及閱讀結果，不保存整段 Discord 原始訊息，也不做模型訓練。X 貼文 ID 會送給 FxEmbed；網頁／圖片會向其來源站請求；文字記錄與圖片會按功能需要交給你配置的模型提供商。部署者仍須確認該提供商的資料使用政策，並提供自己的隱私告知、聯絡方式及刪除申請管道。[Discord Developer Policy](https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy)

到期資料在插件啟動或收到含可辨識連結的新群組訊息時清理；閒置／停用期間不會定時刪除，但查詢時會排除過期記錄。原 Discord 訊息被刪除不會自動清除閱讀記錄。若收到刪除申請，管理者應先停用插件，針對 `links.sqlite3` 的 `links` 表按會話／連結刪除對應記錄，並處理 AstrBot 對話歷史與備份中可能保留的副本；需要協助時請勿在公開 Issue 附上資料庫。暫存清理失敗會留日誌，管理者也應處理遺留工作檔。

以上是本插件的行為與部署指引，不代表 Discord 已審核或核准你的 Bot。軟體問題可透過 [GitHub Issues](https://github.com/xiangerwu/astrbot_plugin_link_context/issues) 回報；涉及個資的資料申請應聯絡實際 Bot 部署者。

## 使用與資料

1. 群組貼一個連結，插件排入背景工作，不發消息。
2. 背景讀取完成後，在同一會話問「剛剛那篇在講什麼」或自然討論；由目前人格與聊天模型回答。
3. 太早詢問時模型只會取得「正在讀取」記錄。完成後不會自動補發回覆，需下一次聊天才會注入新內容。

閱讀記錄依 AstrBot 的 `unified_msg_origin` 隔離。若 AstrBot 設為群組內按使用者分開會話，就會跟著分開，其他人的會話不會自動共享記錄。只辨識訊息文字裡完整的 HTTP(S) 網址；QQ 分享卡片、圖片中的網址與單獨 BV 號不在第一版範圍。

每輪暫時注入最多 18,000 字元，單筆先放 6,000 字元；模型可以透過 `link_context_read` 工具分頁讀取已保存的記錄。網頁正文最多保留 24,000 字元，圖片理解後的總記錄有大小限制，所有截斷都會標記。這是近期記憶，沒有永久知識庫。

資料寫入 AstrBot 管理的 `data/plugin_data/astrbot_plugin_link_context/links.sqlite3`。圖片工作檔完成後移除。預設單一背景工作、最多排隊 32 個連結；滿載、整筆失敗或重載中斷後可重貼以重試。同一會話內仍在處理或已完成的相同網址會略過，不會重複付費讀圖。`ready` 只代表流程完成，仍可能包含圖片失敗、公開預覽或截斷；這類記錄在保留期限內重貼也不會重讀，重載插件不會清除已完成記錄。

本插件不會改動其他插件。若原本的連結解析插件仍在轉發，需要在它自己的設定停用自動轉發或停用該插件。AstrBot 本身原有的聊天觸發規則也仍然有效。

## 常見問題

| 現象 | 檢查方式 |
| --- | --- |
| 貼連結後沒有訊息 | 這是預期行為。等日誌出現 `[link_context] 背景讀取完成`，再在同一會話喚醒 Bot 詢問；不會補發完成通知。 |
| 詢問時沒有閱讀記錄 | 確認插件已啟用、會話設定允許插件、Discord Message Content Intent 與頻道存取正常，並使用完整 HTTP(S) 網址。私訊不會排入閱讀。 |
| 一直正在讀取 | 背景只有一個工作者，多圖與 Threads 載入需要時間。查看日誌是否有資料庫寫入失敗；修復檔案權限／資料庫占用後重載，原 pending 會標為中斷，再重貼連結。 |
| 文字可讀，圖片不懂 | 確認所選提供商支援圖片、憑證及額度有效；圖片來源也可能拒絕下載。記錄會列出未讀原因，保留期限內重貼已完成記錄不會重試配圖。 |
| Threads 報瀏覽器錯誤 | 在執行 AstrBot 的同一環境與帳號安裝 Chromium 及系統依賴。能啟動瀏覽器仍不保證站方提供正文，只有公開預覽時會明確標示。 |
| Bilibili 回傳 412 | 站方風控。Cookie 是選填且不保證有效；插件不繞過驗證，也不把封面當成影片內容。 |
| 網頁連線失敗 | 確認執行環境能直接連外。擷取器不自動繼承環境 HTTP 代理或 Discord adapter 的代理設定。內網／本機網址會被拒絕。 |
| 仍看到轉發或預覽 | 檢查其他解析插件與 Discord 自動嵌入預覽；本插件沒有發送解析結果的路徑。 |
| SQLite 錯誤 | 日誌會顯示錯誤類型；檢查插件資料目錄權限、磁碟空間與資料庫占用。本輪略過無法讀取的上下文，不應把資料庫錯誤帶到正常聊天。不要公開資料庫或配置檔。 |

## 驗證

```bash
python -m unittest discover -s . -p 'test_*.py' -v
```

2026-11-07 本機已通過 **20 項測試**（Python 3.14、Windows），覆蓋範圍如下。AstrBot、模型與遠端站台由邊界替身替代；瀏覽器測試使用本機 Chromium 與受控頁面，不能當作 Linux 部署、真實站台成功率或 OpenAI 模型效果驗證。

| 範圍 | 已檢查行為 |
| --- | --- |
| 插件流程 | 貼連結不發消息、不喚醒；背景結果與暫時上下文；既有人格保留；純文字不額外呼叫模型 |
| 會話與保存 | Discord 頻道／討論串／平台實例隔離、SQLite 持久化、重載中斷、保留期限與內容截斷 |
| 平台解析 | PTT 主文及圖片連結、X ID／配圖、Bilibili 影片資訊及動態、Threads 核對目標貼文與預覽缺漏 |
| 圖片與影片 | 真實圖片解碼與縮放；影片不下載、不理解，記錄明確標示 |
| 網路邊界 | 私有位址及 DNS／重新導向檢查、無 Content-Length 時的串流大小上限、Cookie 網域與 HTTPS 降級隔離 |
| 故障與工具 | 暫存建立／清理／SQLite 寫入失敗後後續工作仍能處理；觀察與注入時 SQLite 錯誤不外拋；分頁接受 `12000`／`12000.0`，拒絕負數、非整數等輸入 |

測試前安裝本節上方的依賴與 Chromium。若使用自行安裝的 Chromium，可透過環境變數 `LINK_CONTEXT_TEST_BROWSER` 指定執行檔；其餘情況使用 Playwright 的 Chromium。

此外，以官方 v4.29.4 的原始函式進行獨立檢查：元資料校驗及版本範圍通過；Discord adapter 的訊息轉換在隔離物件測試中保留頻道／討論串 ID 與網址。這些檢查沒有登入 Discord，也不是完整 AstrBot 啟動測試。

提交前使用 Ruff（本次核對版本 0.15.22）：

```bash
ruff format --check .
ruff check .
```

2026-11-07 無 Cookie 的實際連線：PTT 文章正文可讀；X 的公開貼文成功經 FxEmbed 讀到作者與正文；Bilibili 影片資訊 API 回傳 HTTP 412；Threads 透過完整 Reader 流程讀到目標貼文的 268 字元公開預覽，但沒有完整結構化正文／配圖。平台結果會因網路、登入與站方變更而異。

尚未在你的 Linux AstrBot 實機載入，也未使用你的 OpenAI 額度測試圖片效果。部署後請依序驗收：

1. 在已啟用插件的頻道貼一則公開文字連結，不 @ Bot，確認插件不回覆、不加表情。
2. 等背景完成後，在同一會話 @ Bot 詢問內容；確認回答依記錄而非憑網址猜測。
3. 在另一頻道／討論串詢問同一內容，確認沒有跨會話取得記錄。
4. 貼一則有圖片的連結，確認所選 OpenAI 圖片模型能描述；這一步會產生模型費用。
5. 貼影片連結並詢問畫面／語音，確認 Bot 說明未觀看；重載後再查已完成的文字記錄，確認保存正常。

## 插件市場發布

倉庫網址填在 `metadata.yaml`；根目錄的 `logo.png` 是透明背景、1:1 圖示，`intro.png` 用於本頁介紹。這些檔案須隨原始碼一同推送，市場才能取得。建立 GitHub 空倉庫本身不會上架。

依 [官方發布說明](https://docs.astrbot.app/dev/star/plugin-publish.html)，先將可安裝版本推送至公開 GitHub 倉庫，再登入 [AstrBot 插件發布平台](https://cloud.astrbot.app/publish) 提交倉庫，核對自動載入的名稱、版本、描述與圖示，依頁面流程完成發布。ZIP 上傳限制為 16 MB；只打包程式、配置結構、依賴清單、文件與圖片，不包含虛擬環境、瀏覽器、Cookie、資料庫或工作檔。是否已被市場收錄，以發布平台與市場實際結果為準。

## 開源與參考

本專案程式碼採 [MIT License](LICENSE)。介紹圖及圖示是依 AstrBot 使用的角色美術製作的非官方 AI 衍生圖；原角色與品牌權利仍屬原權利人，MIT 不代表取得其品牌或角色授權，也不代表 AstrBot 官方背書。美術來源與生成提示詞見 [REFERENCES.md](REFERENCES.md)。依 [AstrBot 開發原則](https://docs.astrbot.app/dev/star/plugin-new.html)，在此列出主要設計與實作思路的來源：

- [canaria3406/ermiana](https://github.com/canaria3406/ermiana)：參考解析與 Discord 輸出分離的設計，以及 PTT 圖片網址／作者欄位的擷取思路。獨立以 Python 實作，沒有移植其發送、embed 或鏡像預覽流程；該專案採 MIT。
- [web_access](https://github.com/Dashu-Li/astrbot_plugin_web_access)：工具回傳正文與分頁。
- [video_context](https://github.com/ZAKOsiesta/astrbot_plugin_video_context)：靜默接收與暫時上下文注入；未使用影片處理部分。
- [media_parser](https://github.com/drdon1234/astrbot_plugin_media_parser)：X／Bilibili 資料取得途徑。
- [threads-dl](https://github.com/Quidyz/threads-dl)、[PTT-Crawler](https://github.com/chenjr0719/PTT-Crawler)：平台讀取方式。

完整查閱清單與取捨見 [REFERENCES.md](REFERENCES.md)。發布資訊依 [AstrBot 官方發布說明](https://docs.astrbot.app/dev/star/plugin-publish.html)維護；程式碼不捆綁瀏覽器、虛擬環境或執行資料。
