# 安裝與配置

[返回首頁](../README.md) · [English overview](../README.en.md)

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

## 更新已有安裝

使用 AstrBot 的插件更新功能，或更新整份專案，並保留 `core/`、`tests/`、`assets/`、`docs/` 的目錄結構；不要只複製新的 `main.py`，它需要 `core/` 內的模組。ZIP 應解壓到插件根目錄，使 `main.py` 與 `metadata.yaml` 在同一層。

執行記錄位於 AstrBot 的 `data/plugin_data/astrbot_plugin_link_context/`，不在原始碼資料夾內。此次結構整理不改變資料庫位置或結構，不需要資料遷移。更新完成後重載插件；若環境依賴有變更，先使用相同 Python 環境更新依賴。接著依[人工驗收步驟](development.md#部署後人工驗收)確認。

Discord 的 intents、頻道權限與隱私告知另見 [Discord 設定與資料管理](discord.md)；讀取不到內容時見[排錯說明](troubleshooting.md)。
