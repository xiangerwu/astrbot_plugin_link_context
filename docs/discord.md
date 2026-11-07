# Discord 設定與資料管理

[返回首頁](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.md) · [English overview](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.en.md)

沿用 AstrBot 的 Discord adapter 與官方 Bot 帳號，不需要另一個 Discord 客戶端或使用者 Token。

- **Gateway Intents**：要被動讀取沒有 @ 機器人的一般訊息，必須在 Developer Portal → Bot 啟用 **Message Content Intent**，並在 Discord 要求時完成審核；只有 @ 提及時能讀到內容不代表被動閱讀已正常。AstrBot v4.29.4 的 adapter 也會請求 **Server Members Intent**，需一併正確設定；本插件不自行增加 intents。[官方 Gateway 文件](https://docs.discord.com/developers/events/gateway)、[AstrBot Discord client](https://github.com/AstrBotDevs/AstrBot/blob/v4.29.4/astrbot/core/platform/sources/discord/client.py)
- **頻道權限**：背景讀取需要能檢視該頻道（View Channel）。一般聊天回覆另需 Send Messages；討論串回覆需 Send Messages in Threads。這個閱讀流程不發預覽、不抓歷史，因此不額外要求 Embed Links、Attach Files、Manage Messages、Manage Webhooks 或 Administrator；AstrBot 其他功能的需求另計。[官方權限文件](https://docs.discord.com/developers/topics/permissions)
- **隔離**：AstrBot 將頻道／討論串的 ID 作為 session ID，本插件沿用完整 `unified_msg_origin`。不同頻道、討論串與 Bot 平台實例不共享閱讀記錄；想讓同頻道成員一起討論，請使用 AstrBot 的群組共用會話設定。私密討論串仍須讓 Bot 有權存取，不擴大權限。
- **文字格式**：支援一般網址、`<https://example.com>`、`[標籤](https://example.com)`、反引號及 `||劇透網址||` 裡的連結。尖括號僅抑制 Discord 預覽，劇透標記也不代表退出 AI 閱讀；應在伺服器使用說明中告知成員。只處理新訊息文字，不回補歷史、不解析 Discord 自動 embed，也不監聽編輯／刪除事件。
- **機器人訊息**：沿用 AstrBot 的 `discord_allow_bot_messages`；預設關閉可避免把其他預覽 Bot 的輸出重複拿來閱讀。插件不更改這項設定。
- **靜默驗收**：普通連結訊息不應帶來本插件的回覆或表情。AstrBot 的預回應表情只在 `is_at_or_wake_command` 成立時觸發，本插件不設定它；@ Bot 或原本設定的聊天觸發條件仍可能帶來正常回覆。

## 資料使用與管理

部署者應先取得伺服器管理者的允許，清楚告知成員：貼出的連結會被擷取、配圖送至所選模型理解，閱讀記錄會在同一會話提供給聊天模型。可透過 AstrBot 的會話插件設定停用本插件，或撤銷 Bot 的頻道存取權。不要將 Discord Bot Token、平台 Cookie 或私密網址貼到公開 Issue。

本插件保存連結、分享者顯示名稱、會話識別、分享時間及閱讀結果，不保存整段 Discord 原始訊息，也不做模型訓練。X 貼文 ID 會送給 FxEmbed；網頁／圖片會向其來源站請求；文字記錄與圖片會按功能需要交給你配置的模型提供商。部署者仍須確認該提供商的資料使用政策，並提供自己的隱私告知、聯絡方式及刪除申請管道。[Discord Developer Policy](https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy)

到期資料在插件啟動或收到含可辨識連結的新群組訊息時清理；閒置／停用期間不會定時刪除，但查詢時會排除過期記錄。原 Discord 訊息被刪除不會自動清除閱讀記錄。若收到刪除申請，管理者應先停用插件，針對 `links.sqlite3` 的 `links` 表按會話／連結刪除對應記錄，並處理 AstrBot 對話歷史與備份中可能保留的副本；需要協助時請勿在公開 Issue 附上資料庫。暫存清理失敗會留日誌，管理者也應處理遺留工作檔。

以上是本插件的行為與部署指引，不代表 Discord 已審核或核准你的 Bot。軟體問題可透過 [GitHub Issues](https://github.com/xiangerwu/astrbot_plugin_link_context/issues) 回報；涉及個資的資料申請應聯絡實際 Bot 部署者。
