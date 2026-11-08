# 開源參考與技術來源

[返回首頁](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.md) · [English overview](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.en.md)

查閱日期：2026-11-08。本專案參考既有專案的讀取途徑、API 欄位與插件整合方式，獨立實作靜默流程，沒有把下列專案整包複製或當作執行依賴。以下分清「提供資料給聊天模型」與「直接輸出解析結果」；有解析能力不代表符合靜默需求。

| 專案 | 實際查閱 | 參考與取捨 |
| --- | --- | --- |
| [canaria3406/ermiana](https://github.com/canaria3406/ermiana/tree/3a64cab7937c71b5c243cd3c990d60d05e46f336) | README、LICENSE、preview-service、PTT／X／Threads／Bilibili providers、Discord client／message-handler、Threads mirror service | MIT。參考擷取與輸出分層，以及 PTT 正文中的圖片網址、anchor 與作者欄位；獨立 Python 實作，不移植 JS 原始碼。保留推文，不採用其為 embed 裁短正文的處理。0.2.0 另對照全部平台 provider、鏡像服務與上游 API；新增 Instagram／Facebook／TikTok 預覽讀取、Bluesky／Misskey／Pixiv／Steam／PChome／圖庫 API，以及巴哈／Plurk 擷取。X 增加 VXTwitter 備援，Bilibili 增加 vxbilibili 預覽。這些服務回傳的預覽會實際擷取並標記缺漏，不只改寫網址，也不轉發卡片。不移植登入帳密、Discord 發送、影片下載或整本翻頁。 |
| [Dashu-Li/astrbot_plugin_web_access](https://github.com/Dashu-Li/astrbot_plugin_web_access) | README、main.py | 網頁工具回傳正文與 next_offset，由會話模型使用；不額外做文字摘要。本插件採用已讀記錄分頁工具，但加上群組被動背景閱讀。它本身不是貼連結就背景讀取。 |
| [ZAKOsiesta/astrbot_plugin_video_context](https://github.com/ZAKOsiesta/astrbot_plugin_video_context) | README、main.py | 群組被動分享保持靜默；在 on_llm_request 用暫時內容供目前人格回答。它的群組被動階段只記錄、不呼叫模型，與本插件背景讀圖不同。依目前需求不引入其影片、字幕、轉錄功能。 |
| [drdon1234/astrbot_plugin_media_parser](https://github.com/drdon1234/astrbot_plugin_media_parser) | README、core/parser/platform/twitter.py、bilibili.py | X 使用 FxEmbed、Bilibili 影片資訊與動態 API 的欄位。本插件只把資料交給閱讀記錄，不採用下載／轉發結果流程。 |
| [Qfxaile/astrbot_plugin_multi_parser](https://github.com/Qfxaile/astrbot_plugin_multi_parser) | README | 對照對話歷史與轉發選項。forward_mode=never 表示不使用合併轉發，仍可能普通發送，不能視作靜默模式。 |
| [Quidyz/threads-dl](https://github.com/Quidyz/threads-dl) | README、threads_dl/extractor.py | 使用 Playwright 讀取 Threads。此處自行核對目標 shortcode，避免讀成推薦貼文；無完整資料時只保存已核對來源的預覽並標記缺漏。沒有移植其下載器。 |
| [chenjr0719/PTT-Crawler](https://github.com/chenjr0719/PTT-Crawler) | README、PTT_Crawler.py | PTT HTML／BeautifulSoup、over18 Cookie、主文與推文讀取方式。沒有引入其命令列爬取或資料輸出框架。 |
| [Sakura520222/astrbot_plugin_web_analyzer](https://github.com/Sakura520222/astrbot_plugin_web_analyzer) | README、core/message_handler.py | 自動網址辨識與網頁分析；預設分析／截圖與發送結果的路徑，不直接採用。 |
| [Limoies/astrbot_plugin_web_reader](https://github.com/Limoies/astrbot_plugin_web_reader) | README | /readweb、瀏覽器／HTTP 讀取與輸出檔案；不符合本次被動群組記憶流程，也不採用其另設模型金鑰的方式。 |
| [cmdst/astrbot_plugin_browser_llm](https://github.com/cmdst/astrbot_plugin_browser_llm) | README | 通用瀏覽器 Agent；本次只需讀取連結，不引入完整瀏覽器操作 Agent。 |
| [piexian/astrbot_plugin_mmx_cli_tool](https://github.com/piexian/astrbot_plugin_mmx_cli_tool/tree/22494ead9ead6cf763a0d3e4b406a312e59b1943) | README、docs/plugin-api.md、mmx/plugin_service.py 與相關 SDK 實作 | 使用者提供的專案。查過插件間 get_service(api_version=1)、圖片描述與轉錄服務；SDK 回傳資料的方式有參考價值。其影片工具含生成用途，不能當作影片理解能力。依最新決定不使用 MiniMax SDK、金鑰或付費服務。 |

外部服務與官方介面：

- [FxEmbed API 文件](https://docs.fxembed.com/api/introduction)：讀取公開 X 貼文。本插件用既有 status 端點，會將貼文 ID 傳給此第三方；並非 X 官方登入 API。
- [AstrBot 訊息事件與 LLM request 文件](https://docs.astrbot.app/en/dev/star/guides/listen-message-event.html)：事件監聽與請求鉤子。
- [AstrBot v4.29.4 原始碼](https://github.com/AstrBotDevs/AstrBot/tree/v4.29.4)：核對 Context.llm_generate、get_current_chat_provider_id、ProviderRequest、TextPart.mark_as_temp 與 StarTools.get_data_dir；未直接串接另一套 OpenAI SDK。
- [AstrBot 開發原則](https://docs.astrbot.app/dev/star/plugin-new.html)、[發布說明](https://docs.astrbot.app/dev/star/plugin-publish.html)：資料目錄、異步網路、錯誤處理、Ruff、README 引用及 metadata。
- [AstrBot Discord adapter](https://github.com/AstrBotDevs/AstrBot/blob/v4.29.4/astrbot/core/platform/sources/discord/discord_platform_adapter.py)、[client](https://github.com/AstrBotDevs/AstrBot/blob/v4.29.4/astrbot/core/platform/sources/discord/client.py)：頻道／討論串 ID、原始訊息文字、Bot 訊息過濾與已請求的 intents。
- [Discord Gateway](https://docs.discord.com/developers/events/gateway)、[權限](https://docs.discord.com/developers/topics/permissions)、[Developer Policy](https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy)：被動閱讀的 Message Content Intent、頻道／討論串權限與資料用途限制。不另建立 Discord 客戶端，不移植 Ermiana 的發送權限要求。

參考不代表來源保證穩定，也不代表本插件已通過各專案的測試。來源各自的授權仍以其 LICENSE 為準；若未來直接移植程式碼，需另行遵守對應授權，不能僅靠這份列表代替授權條件。

圖片來源另見[美術來源與生成記錄](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/artwork.md)。
