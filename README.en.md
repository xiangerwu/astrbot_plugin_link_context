# Silent Link Context for AstrBot

[繁體中文](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.md) | [English](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/README.en.md)

![Silent Link Context: read shared links and join the conversation](https://raw.githubusercontent.com/xiangerwu/astrbot_plugin_link_context/main/assets/intro.png)

An AstrBot plugin that quietly reads links shared in group messages and makes their content available to later conversations. It does not automatically forward articles, summaries, images, or completion notices, and sharing a link does not trigger a chat response. The primary use case is Discord text channels and threads.

## What it reads

| Source | Available content | Limitations |
| --- | --- | --- |
| PTT | Article text, comments, author, embedded and linked images | Deleted posts and inaccessible image hosts can fail. |
| Twitter / X | Public post text, quoted text, and post images through FxEmbed | Post IDs are sent to a third-party service. Private or login-only posts are unsupported. |
| Threads | Structured post data matched to the requested shortcode using Chromium | May fall back to a verified public preview without images; missing content is marked. |
| Bilibili | Video title, description and cover; dynamic / Opus text and images; short links | Anti-bot checks may return HTTP 412. Cookies do not guarantee access. |
| Other websites | HTML article / main / body text and images | Dynamic pages, authenticated content and paywalls are not guaranteed. PDFs and file downloads are unsupported. |

**Video frames, audio and subtitles are not processed.** A title, description or cover image does not mean the bot has watched the video.

Text is stored directly without an extra summarization call. Images use the vision provider configured in AstrBot, intended here for OpenAI. Each processed image requires a paid model call. There is no MiniMax dependency or separate OpenAI SDK configuration.

## Quick start

Requirements: **AstrBot 4.29.4 or later**, **Python 3.12 or later**, and a configured provider supporting image input for image understanding. Compatibility was checked against AstrBot 4.29.4; future releases are not automatically verified.

1. Install through AstrBot WebUI using the repository URL, or place the project in `data/plugins/astrbot_plugin_link_context`:

   ```text
   https://github.com/xiangerwu/astrbot_plugin_link_context
   ```

2. Install dependencies and Chromium in the **same Python environment and under the same account that runs AstrBot**:

   ```bash
   cd /path/to/AstrBot/data/plugins/astrbot_plugin_link_context
   python -m pip install -r requirements.txt
   python -m playwright install chromium
   ```

   If Linux browser libraries are missing, follow Playwright's instructions for `python -m playwright install-deps chromium`; system administrator privileges may be needed. For Docker, install inside the container environment and preserve the dependencies across rebuilds.

3. Configure the plugin in AstrBot WebUI:

   | Setting | Purpose |
   | --- | --- |
   | `vision_provider_id` | Existing OpenAI provider supporting images. Empty uses the conversation's current chat provider. Text remains available when images cannot be understood. |
   | `max_images` | Maximum images per link: default 8, range 1–30. Each image makes one model call. |
   | `retention_hours` | Default 24 hours, range 1–720. Expired records are excluded from queries; physical cleanup runs at startup or on a new group message containing a recognized link. No periodic deletion timer. |
   | `bilibili_cookie`, `threads_cookie` | Optional. Sent only to the corresponding platform's HTTPS domains, never to HTTP or unrelated image hosts. UI masking is not encryption. |

4. For Discord, enable **Message Content Intent** so ordinary messages without mentions are available. AstrBot 4.29.4 also requests **Server Members Intent**. Configure any required Discord approvals and allow access to the channel. Normal chat replies require Send Messages; thread replies require Send Messages in Threads. The reader itself sends no messages or attachments. See [Discord setup](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/discord.md) (Traditional Chinese) and the [official Gateway documentation](https://docs.discord.com/developers/events/gateway).
5. Reload the plugin. Share a link without mentioning the bot, then wait for the `[link_context]` completion log and ask about it in the same conversation. There is no completion message and no automatic follow-up if you asked too early.

## Memory, privacy and limits

- Reading follows AstrBot's plugin/session enablement. Natural replies follow AstrBot's existing `provider_ltm_settings.active_reply` settings: enable `possibility_reply` and set `possibility_reply` to a value from 0 to 1 (for example, `0.05` means a 5% chance per eligible message, not exactly one reply every 20 messages). This applies to ordinary group messages, not only links. Mentions/wake commands and other proactive plugins have their own triggers. Disabling proactive replies does not disable background reading. See [reading and reply controls](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/usage.md#%E8%AE%80%E5%8F%96%E9%96%8B%E9%97%9C%E8%88%87%E5%9B%9E%E8%A6%86%E6%A9%9F%E7%8E%87).
- Since 0.1.1, links are queued before AstrBot's built-in group-chat handler. A reply may still start while reading is pending; the plugin reports that state and never waits for every image or sends an automatic completion reply.
- Records follow AstrBot's full `unified_msg_origin`. Different channels, threads and bot instances are isolated; per-user session settings can also separate members in the same channel. Use shared group sessions if members should discuss the same records.
- Up to 20 recent records are considered. Temporary context is limited to 18,000 characters total and initially 6,000 characters per record. The `link_context_read` tool pages through stored records only; it does not fetch new URLs.
- One background worker handles a queue of up to 32 links. Pending and completed URLs are deduplicated within their retention period. `ready` means the pipeline finished, not that all content was available. Reposting a completed record does not retry failed images; reloading does not erase completed records.
- Data lives in AstrBot's `data/plugin_data/astrbot_plugin_link_context/links.sqlite3`, outside the plugin source. Completed records survive reloads. Image work files are removed after processing; cleanup failures are logged.
- Only new group-message text is observed. Private messages, historical messages, edits/deletions, Discord embeds, URLs inside images and bare Bilibili BV identifiers are not processed. Spoiler markup and angle brackets do not opt a URL out of reading.
- Inform server administrators and members before enabling link reading. Stored data includes URLs, sender display names, session identifiers, timestamps and extracted content. Websites receive requests, FxEmbed receives X post IDs, and configured model providers receive relevant text or images. The plugin does not train models; verify your provider's data policy separately.
- Disable the plugin for a session or revoke channel access to stop reading there. Deleting a Discord message does not delete the stored record. Operators should provide a private contact and deletion process, covering the plugin database, AstrBot conversation history and backups. See [data administration](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/discord.md#%E8%B3%87%E6%96%99%E4%BD%BF%E7%94%A8%E8%88%87%E7%AE%A1%E7%90%86) (Traditional Chinese).

Network restrictions and platform changes may prevent reading. The fetcher rejects private/local addresses and does not inherit environment HTTP proxies or the Discord adapter's proxy settings. Other plugins and Discord's native previews remain independently configured.

## Documentation

The detailed guides below are currently in **Traditional Chinese**. This English README provides installation, configuration, behavior and privacy essentials.

| Guide | Contents |
| --- | --- |
| [Installation](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/installation.md) | Linux, Docker, provider settings, cookies and updates |
| [Bilibili Cookie tutorial](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/bilibili-cookie.md) | Copy the request Cookie value, configure it, validate results and troubleshoot HTTP 412 |
| [Threads Cookie tutorial](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/threads-cookie.md) | Cookie setup, Chromium, preview limitations and session renewal |
| [Usage and limitations](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/usage.md) | Platform support, memory, pagination and retries |
| [Discord setup and data administration](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/discord.md) | Intents, permissions, isolation and deletion |
| [Troubleshooting](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/troubleshooting.md) | Missing records, image failures, browsers, network and database errors |
| [Development and validation](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/development.md) | Directory layout, test commands and manual acceptance checks |
| [Publishing](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/publishing.md) | Packaging and AstrBot marketplace submission |
| [References](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/references.md) | Reviewed projects, official APIs and design choices |
| [Artwork](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/artwork.md) | Character sources and image-generation prompts |

## Development

Run from the repository root after installing dependencies and Chromium:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
ruff format --check .
ruff check .
```

Set `LINK_CONTEXT_TEST_BROWSER` to an existing Chromium executable if needed. Ruff 0.15.22 was used for validation. The 20 tests cover silent processing, event ordering, session isolation, parsing, network boundaries, images, database failures and pagination. Tests replace AstrBot/model/network boundaries; browser execution and image decoding are real. Deployment acceptance for the 0.1.1 fix on Linux with Discord/OpenAI remains outstanding.

`main.py`, metadata, configuration schema, requirements and `logo.png` remain at the root for AstrBot. Internal modules are in `core/`, tests in `tests/`, detailed guides in `docs/`, and the introduction image in `assets/`. Runtime database paths are unchanged by this layout.

## License and acknowledgements

Code is licensed under [MIT](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/LICENSE). Design references include [Ermiana](https://github.com/canaria3406/ermiana), [web_access](https://github.com/Dashu-Li/astrbot_plugin_web_access), [video_context](https://github.com/ZAKOsiesta/astrbot_plugin_video_context), [media_parser](https://github.com/drdon1234/astrbot_plugin_media_parser), and others listed in [References](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/references.md). Their forwarding or video pipelines are not included.

The illustration and icon are unofficial AI-derived artwork based on character artwork used by AstrBot. The code's MIT license does not relicense the original character or brand, and this project is not officially endorsed by AstrBot. See [Artwork](https://github.com/xiangerwu/astrbot_plugin_link_context/blob/main/docs/artwork.md).

Report software issues through [GitHub Issues](https://github.com/xiangerwu/astrbot_plugin_link_context/issues). Do not attach cookies, tokens, private URLs or databases. Data requests should go to the operator of the bot you use.
