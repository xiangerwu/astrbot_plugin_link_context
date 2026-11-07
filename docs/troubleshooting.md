# 常見問題與排錯

[返回首頁](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.md) · [English overview](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.en.md)

Cookie 的取得、填寫與更新請分別參考 [Bilibili 教學](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/bilibili-cookie.md)與 [Threads 教學](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/threads-cookie.md)。

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
