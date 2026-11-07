# Threads Cookie 取得與設定教學

[返回首頁](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.md) · [安裝與配置](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/installation.md) · [Bilibili Cookie](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/bilibili-cookie.md)

本教學適用於 Meta **Threads**，配置欄位是 `threads_cookie`，以桌面版 Chrome 示範。公開貼文可先留空測試；Cookie 只提供登入狀態，**不保證取得完整正文或配圖，也不會啟用影片理解**。

## 先了解本插件的讀取方式

Threads 使用 Playwright／Chromium 載入頁面，再核對目標貼文 shortcode，避免誤讀推薦貼文。若沒有完整結構化資料，可能只保存來源一致的公開預覽；該預覽不提供配圖。

目前只放行指定網域的 **GET** 請求，依賴 POST 的 GraphQL 等請求不會送出，也不協助互動登入或通過驗證挑戰。即使 Cookie 有效，依賴其他請求或登入狀態儲存的內容仍可能讀不到。Cookie 不能取代 Chromium 安裝，亦不是官方 Threads API 的 access token。

只使用自己有權管理的帳號。登入 Cookie 可能代表帳號身分，不是唯讀 API 金鑰；不要將只有該帳號能看到、卻不適合提供給群組與模型的內容拿來測試。

## 1. 登入 Threads 並開啟目標貼文

1. 在自己的桌面瀏覽器開啟 [Threads](https://www.threads.com/)，完成正常登入。
2. 開啟一則公開貼文，網址應包含 `/@使用者/post/貼文代碼`，不要使用個人首頁作為測試連結。
3. 開啟開發者工具：Windows／Linux 按 `Ctrl+Shift+I`，macOS 按 `Command+Option+I`；也可從瀏覽器選單進入。
4. 切換到 **Network（網路）**，再重新整理貼文頁面。

使用舊的 `threads.net` 連結時，請以瀏覽器實際重新導向後的 Threads 網域為準。不要從 Instagram、Facebook 或第三方 Threads 鏡像服務複製 Cookie。

## 2. 找到 Threads 請求的 Cookie

1. 在 Network 篩選框輸入 `threads.com`；若實際頁面仍在 `threads.net`，就篩選該網域。
2. 優先選擇貼文頁面的 **Doc／Document** 請求。點入 **Headers → General → Request URL**，確認是 `https://www.threads.com/...` 或真正的 Threads 網域，而非圖片 CDN、廣告或登入到其他站點的請求。
3. 在 **Request Headers（要求標頭）** 找到 `cookie`／`Cookie`，只複製它的值。
4. 保持單行 `名稱=值; 名稱=值`，保留原始編碼；不要帶入 `Cookie:` 標頭名稱、外層引號或換行。

以下只有格式示意，名稱與值均為假資料：

```text
cookie_name_a=EXAMPLE_VALUE_A; cookie_name_b=EXAMPLE_VALUE_B
```

不要貼入 `Set-Cookie`、cURL 命令、HAR、JSON、`storage_state` 或 Cookie 檔案路徑。不要自行拼接 Instagram／Facebook 的 Cookie。本插件不要求你在 Console 執行程式，也不會要求你提供帳號密碼。

瀏覽器標頭操作依 [Chrome Network 官方文件](https://developer.chrome.com/docs/devtools/network/reference?hl=en#headers)。若找不到 Cookie，確認已登入、請求已完成且網域正確；若只有 `Provisional headers are shown`，可勾選 Network 的 **Disable cache** 後重新整理，再檢查新的請求。必要時用 **Application → Storage → Cookies** 查看對應站點是否有 Cookie，但不要直接貼整張表格。HttpOnly Cookie 無法透過 `document.cookie` 取得。[Chrome Cookie 官方文件](https://developer.chrome.com/docs/devtools/application/cookies)

## 3. 填入 AstrBot 並重載

1. 到 AstrBot WebUI「插件 → 靜默連結閱讀 → 配置」。
2. 在 **Threads Cookie（選填）**，也就是 `threads_cookie`，貼上單行值。
3. 儲存配置並重載此插件；不需要重啟整台 Linux。
4. 確認執行 AstrBot 的同一 Python 環境與帳號已安裝 Chromium：

   ```bash
   python -m playwright install chromium
   ```

   Docker 應在容器環境處理，Linux 系統依賴另見[安裝說明](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/installation.md)。缺瀏覽器執行檔／系統函式庫的錯誤，不能靠換 Cookie 解決。

此值會用於 `threads.com` 與 `threads.net` 及其子網域的 HTTPS 請求；插件也將其中 Cookie 加入這兩個網域的暫時瀏覽器 context。它不會把該值送給 `cdninstagram.com`、`fbcdn.net` 或其他站點，也不保存你的完整瀏覽器 profile 或自動更新登入 Cookie。

WebUI 遮罩不代表儲存加密。限制 WebUI、配置檔與備份的存取；不要把 Cookie 貼到聊天、Issue、截圖或 Git，填完後清除剪貼簿。此欄位目前不支援環境變數、檔案路徑或 Playwright `storage_state` 匯入。

## 4. 驗收內容，而不是只看「完成」

1. 在已啟用插件的群組／頻道貼一則尚未成功讀取過的公開 Threads **貼文**連結。
2. 等背景讀取完成，再在同一會話詢問正文；對照原文確認是否有完整內容。
3. 如果記錄只說「公開預覽」，就表示尚未取得完整正文，不能推論配圖已看懂。
4. 有取得配圖時會呼叫圖片模型，可能產生費用。影片畫面、語音與字幕仍不處理。

同一網址的 `pending`／`ready` 記錄會去重。**換 Cookie、重載插件都不會清除已完成的預覽記錄**；用另一則公開貼文驗收，或等該筆過期。整筆失敗的連結可在修正後重貼。沒有群組回覆是靜默設計，不是 Cookie 無效的證據。

## 常見問題與更新

| 情況 | 處理方式 |
| --- | --- |
| 只有公開預覽、沒有配圖 | 站方可能未在目前流程中提供完整資料；Cookie 不保證改善，也可能涉及目前只放行 GET 的限制。 |
| 瀏覽器登入後能看，Bot 仍失敗 | 比較部署網路、瀏覽器依賴及站方登入挑戰；本插件不重現整個個人瀏覽器狀態。不要因此把更多站點的 Cookie 拼進欄位。 |
| 貼的是個人首頁 | 改用包含 `/post/` 的單則貼文網址。 |
| 改完 Cookie 回答仍一樣 | 可能命中已完成的閱讀記錄；使用另一則公開貼文驗收，見上節。 |
| 原本成功，後來失效 | 重新確認瀏覽器登入，必要時重取 Cookie，再儲存並重載。沒有固定有效天數或自動續期保證。 |
| 要停止使用登入狀態 | 清空 `threads_cookie`，儲存並重載；舊閱讀記錄仍依保留期限處理。 |
| Cookie 意外洩漏 | 移除公開內容，透過平台帳號安全／登入管理撤銷相關工作階段，再更新配置。只刪除本地值不等於遠端撤銷。 |

## 參考與驗證範圍

[threads-dl 的 Authentication 說明](https://github.com/Quidyz/threads-dl/blob/6062be8b264a7a6624820bf1ed7d416d1e88f7ab/README.md)採用 Playwright `storage_state`；本插件只有原始 Cookie 字串欄位，兩者格式不能互換。實際限制依本專案 [Reader.threads 與 Web.headers](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/core/fetch.py)。

查核日期：2026-11-07。已核對程式與瀏覽器官方文件；未使用你的登入 Cookie 做實機驗收，也未保證私密／登入限制貼文能讀取。
