# Bilibili Cookie 取得與設定教學

[返回首頁](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.md) · [安裝與配置](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/installation.md) · [Threads Cookie](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/threads-cookie.md)

本教學適用於本插件的 `bilibili_cookie` 欄位，以桌面版 Chrome 示範。Cookie 是選填；先留空測試公開內容，遇到需要登入的回應時才考慮設定。**Cookie 不保證解決 HTTP 412，也不會讓本插件開始下載或理解影片。**

## 先確認用途

本插件讀取 Bilibili 影片的標題、作者、簡介與封面，以及動態／Opus 圖文。登入 Cookie 只補上請求的登入狀態；沒有高畫質選項、會員影片下載、字幕或語音轉錄功能。

只使用自己有權管理的帳號。Cookie 可能代表登入身分，不是「只有讀取權限」的 API 金鑰；插件只讀取網頁，不代表 Cookie 本身只有唯讀權限。分享連結的內容可能交給群組聊天模型及同會話成員使用，不要透過權限較高的帳號讀取不適合分享的內容。

## 1. 在瀏覽器登入 Bilibili

1. 用自己的瀏覽器開啟 [Bilibili](https://www.bilibili.com/)，完成正常登入。
2. 開啟一則自己能觀看的公開影片或動態，確認頁面能正常載入。
3. 開啟開發者工具：Windows／Linux 按 `Ctrl+Shift+I`，macOS 按 `Command+Option+I`；也可使用瀏覽器選單的「更多工具 → 開發人員工具」。
4. 切換到 **Network（網路）**，再重新整理頁面。先開 Network 才重新整理，才能看到該次請求。

瀏覽器操作依 [Chrome Network 官方文件](https://developer.chrome.com/docs/devtools/network/reference?hl=en#headers)；介面名稱可能隨語言或版本不同。

## 2. 複製請求的 Cookie 值

1. 在 Network 的篩選框輸入 `bilibili.com`。
2. 選擇已完成的 Bilibili 網頁或 API 請求。點入 **Headers（標頭）**，在 **General → Request URL** 確認主機是 `www.bilibili.com`、`api.bilibili.com` 或其他真正的 `bilibili.com` 子網域。不要選廣告、圖片 CDN 或短網址跳轉請求。
3. 展開 **Request Headers（要求標頭）**，找到 `cookie` 或 `Cookie`。
4. 只複製它的**值**，保留原本的 `名稱=值; 名稱=值` 格式。不要複製前面的 `Cookie:`，不要加入引號或換行，也不要解碼 `%xx` 或修改值。

格式示意，以下是假值，不能直接使用：

```text
cookie_name_a=EXAMPLE_VALUE_A; cookie_name_b=EXAMPLE_VALUE_B
```

此欄位不接受下列內容：

- 只有某一個 Cookie 的值，卻沒有 `名稱=`。
- Response Headers 裡的 `Set-Cookie`，或它的 `Path`、`Expires`、`HttpOnly` 等屬性。
- 整段「Copy as cURL」、HAR 網路紀錄、JSON、瀏覽器匯出的 Cookie 檔案。

如果看不到 Cookie，先確認登入仍有效、選的是正確站點且請求已完成。若顯示 `Provisional headers are shown`，可在 Network 勾選 **Disable cache** 後重新整理，再選新的請求；不要把尚未實際送出的暫存標頭當成成功證據。[Chrome 對暫存標頭的說明](https://developer.chrome.com/docs/devtools/network/reference?hl=en#provisional-headers)

也可用 **Application → Storage → Cookies** 檢查站點、名稱與有效期，但本插件要的是請求 Cookie 字串，不是該表格的匯出內容。不需要在 Console 執行程式；`document.cookie` 也不會提供 HttpOnly Cookie。[Chrome Cookie 官方文件](https://developer.chrome.com/docs/devtools/application/cookies)

## 3. 填入 AstrBot

1. 打開自己管理的 AstrBot WebUI，進入「插件 → 靜默連結閱讀 → 配置」。
2. 找到 **Bilibili Cookie（選填）**，也就是 `bilibili_cookie`。
3. 貼上剛才的單行 Cookie 值，儲存配置，重載此插件。
4. 清除剪貼簿中的敏感內容；不要把 Cookie 放進群組、Issue、README、截圖或 Git。

本插件只把此值送往 `bilibili.com` 及其子網域的 **HTTPS** 請求；不送給 `b23.tv`、`hdslb.com`、`bilivideo.com` 或 HTTP 重新導向目標。WebUI 的 `secret` 遮罩不是儲存加密，請限制 WebUI、配置檔與備份的存取權限。此欄位目前不支援環境變數名稱或 Cookie 檔案路徑。

## 4. 驗證是否有幫助

1. 在已允許 Bot 存取且啟用插件的群組／頻道，貼一則**尚未在該會話成功讀取過**的公開 Bilibili 連結。
2. 等日誌出現 `[link_context] 背景讀取完成`，再在同一會話喚醒 Bot 詢問標題、簡介或動態正文。
3. 檢查內容是否符合原文，以及是否標示失敗、圖片未理解或截斷。只看到「背景完成」不代表 Cookie 已驗證有效；公開內容本來就可能不需要登入。

含封面／圖片的連結可能觸發圖片模型費用。同一會話內 `pending`／`ready` 的網址會去重；**更新 Cookie 或重載插件不會清除已完成記錄**。可用另一則公開連結驗收，或等該筆超過保留期限。整筆失敗的連結可在修正後重貼。

## 常見問題與更新

| 情況 | 處理方式 |
| --- | --- |
| 仍回傳 HTTP 412 | 可能是站方風控或部署網路差異，不等於一定貼錯 Cookie。停止密集重試；瀏覽器成功也不保證伺服器 IP 能成功。 |
| 只有標題、簡介與封面 | 影片連結的預期範圍；本插件不觀看影片。 |
| 已填 Cookie，圖片仍失敗 | Cookie 不會送給圖片 CDN；另查圖片下載、模型設定及額度，見[排錯說明](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/troubleshooting.md)。 |
| 原本可讀，後來失敗 | 在瀏覽器確認登入狀態，必要時重新登入並重取 Cookie；沒有固定保證的有效天數。 |
| 想停用登入請求 | 清空 `bilibili_cookie`，儲存並重載插件；已保存的閱讀記錄不會因此刪除。 |
| 不小心公開 Cookie | 先移除公開內容，並透過平台帳號安全／登入管理撤銷相關工作階段，再更換配置。只清空本地欄位不等於撤銷已洩漏的登入身分。 |

## 參考與驗證範圍

參考 [media_parser 的 Bilibili Cookie 說明](https://github.com/drdon1234/astrbot_plugin_media_parser/blob/9bd2c3170e3cd6ce301137175e5c869cd25a3f79/README.md)，採用瀏覽器 Request Headers 的取得方式；其高畫質、管理員掃碼與續期功能不屬於本插件。實際傳送範圍依本專案 [core/fetch.py](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/core/fetch.py) 的 `Web.headers`。

查核日期：2026-11-07。已核對本插件配置、傳送範圍與瀏覽器官方操作文件；未使用你的登入 Cookie 做實機驗收。
