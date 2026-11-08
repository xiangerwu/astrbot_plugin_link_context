"""Read public links into data; this module never sends chat messages."""

import asyncio
import ipaddress
import json
import re
import socket
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import aiohttp
from aiohttp.resolver import DefaultResolver
from bs4 import BeautifulSoup


class ReadError(Exception):
    """A safe, user-readable reason, without upstream credentials or bodies."""


def checked_url(url: str) -> str:
    try:
        p = urlsplit(url)
        if (
            p.scheme not in ("http", "https")
            or not p.hostname
            or p.username
            or p.password
        ):
            raise ValueError
        if p.port not in (None, 80, 443):
            raise ValueError
        host = p.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith((".localhost", ".local")):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError
        return urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
    except (ValueError, TypeError):
        raise ReadError("拒絕非公開 HTTP(S) 網址或非標準連接埠") from None


def host_is(url: str, domain: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def links_in(text: str) -> list[str]:
    links = []
    for match in re.finditer(r"https?://[^\s<>\"`|\u3000]+", text):
        raw = match.group().rstrip("。，、！？；：.,!?;:'\"》】」』")
        while raw.endswith(")") and raw.count(")") > raw.count("("):
            raw = raw[:-1]
        raw = raw.rstrip("]")
        try:
            url = checked_url(raw)
        except ReadError:
            continue
        if url not in links:
            links.append(url)
    return links


class PublicResolver(DefaultResolver):
    async def resolve(self, host, port=0, family=socket.AF_INET):
        records = await super().resolve(host, port, family)
        # Check the exact addresses the connector will use, including redirects.
        if not records or any(
            not ipaddress.ip_address(r["host"]).is_global for r in records
        ):
            raise ReadError("網域解析到非公開位址，已拒絕連線")
        return records


class Web:
    def __init__(self, cookies: dict[str, str]):
        self.cookies = cookies
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(resolver=PublicResolver()),
            cookie_jar=aiohttp.DummyCookieJar(),
            timeout=aiohttp.ClientTimeout(total=90, sock_read=30),
            headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip, deflate"},
            trust_env=False,
        )

    async def close(self):
        await self.session.close()

    def headers(self, url: str) -> dict[str, str]:
        headers = {}
        for domain, cookie in self.cookies.items():
            # A pasted http URL or HTTPS-to-HTTP redirect must not expose a login Cookie.
            if cookie and urlsplit(url).scheme == "https" and host_is(url, domain):
                headers["Cookie"] = cookie
        if host_is(url, "ptt.cc"):
            headers["Cookie"] = "over18=1"
        if (
            host_is(url, "bilibili.com")
            or host_is(url, "bilivideo.com")
            or host_is(url, "hdslb.com")
        ):
            headers["Referer"] = "https://www.bilibili.com/"
        if host_is(url, "pximg.net"):
            headers["Referer"] = "https://www.pixiv.net/"
        return headers

    async def read(
        self,
        url: str,
        *,
        limit=4 * 1024 * 1024,
        destination: Path | None = None,
        method="GET",
        json_data=None,
        form_data=None,
        headers=None,
    ):
        for _ in range(6):
            url = checked_url(url)
            async with self.session.request(
                method,
                url,
                headers={**self.headers(url), **(headers or {})},
                allow_redirects=False,
                json=json_data,
                data=form_data,
            ) as response:
                if response.status in (301, 302, 303, 307, 308):
                    if method != "GET":
                        raise ReadError("資料 API 重新導向，未轉送請求")
                    url = urljoin(url, response.headers.get("Location", ""))
                    continue
                if response.status != 200:
                    raise ReadError(f"來源回傳 HTTP {response.status}，內容未讀取")
                if response.content_length and response.content_length > limit:
                    raise ReadError("來源檔案超過大小上限，未完整讀取")
                chunks, size = [], 0
                output = destination.open("wb") if destination else None
                try:
                    async for block in response.content.iter_chunked(65536):
                        size += len(block)
                        if size > limit:
                            raise ReadError("來源檔案超過大小上限，未完整讀取")
                        if output:
                            output.write(block)
                        else:
                            chunks.append(block)
                finally:
                    if output:
                        output.close()
                return url, response.headers.get("Content-Type", ""), b"".join(chunks)
        raise ReadError("連結重新導向次數過多")

    async def json(self, url, **kwargs):
        _, _, body = await self.read(url, **kwargs)
        try:
            return json.loads(body)
        except (ValueError, UnicodeError):
            raise ReadError("來源未回傳可讀取的 JSON 資料") from None


@dataclass
class Page:
    url: str
    title: str = ""
    author: str = ""
    text: str = ""
    images: list[str] = field(default_factory=list)
    has_video: bool = False
    notes: list[str] = field(default_factory=list)


class Reader:
    def __init__(self, web: Web):
        self.web = web

    async def read(self, url: str) -> Page:
        from .platforms import FETCH_ERRORS, preview, read_platform

        url = checked_url(url)
        if re.search(r"\.(?:jpe?g|png|gif|webp)$", urlsplit(url).path, re.I):
            # Keep signed queries intact; describe() downloads and validates the image.
            return Page(url, title="圖片連結", images=[url])
        if host_is(url, "b23.tv") or host_is(url, "bili2233.cn"):
            url, _, _ = await self.web.read(url)
        if host_is(url, "x.com") or host_is(url, "twitter.com"):
            return await self.twitter(url)
        if host_is(url, "bilibili.com") and (
            host_is(url, "t.bilibili.com") or "/opus/" in urlsplit(url).path
        ):
            try:
                return await asyncio.wait_for(self.bilibili_post(url), 5)
            except FETCH_ERRORS:
                identifier = re.fullmatch(r"/(?:opus/)?(\d+)/?", urlsplit(url).path)
                if not identifier:
                    raise
                return await preview(
                    self.web,
                    "https://www.bilibili.com/opus/" + identifier[1],
                    ("www.vxbilibili.com",),
                )
        if host_is(url, "bilibili.com") and re.search(
            r"/(?:video/|BV|av)", urlsplit(url).path
        ):
            try:
                return await asyncio.wait_for(self.bilibili(url), 5)
            except FETCH_ERRORS:
                page = await preview(self.web, url, ("www.vxbilibili.com",))
                page.has_video = True
                page.notes.append("僅影片預覽資料，未觀看影片。")
                return page
        if host_is(url, "threads.net") or host_is(url, "threads.com"):
            return await self.threads(url)
        extra = await asyncio.wait_for(read_platform(self.web, url), 12)
        if extra is not None:
            return extra
        final, content_type, body = await self.web.read(url)
        if "html" not in content_type:
            raise ReadError("此連結不是可讀取的網頁；目前不解析文件下載或直播串流")
        return parse_html(final, body)

    async def twitter(self, url):
        from .platforms import twitter_data

        match = re.search(r"/status/(\d+)", urlsplit(url).path)
        if not match:
            raise ReadError("請提供 X 單篇貼文連結")
        # FxEmbed is the same extraction service used by media_parser; no forwarding.
        data = await twitter_data(self.web, match[1])
        tweet = data.get("tweet") or {}
        if str(tweet.get("id")) != match[1]:
            raise ReadError("X 解析服務未提供目標貼文，可能已刪除或需要登入")
        raw = tweet.get("raw_text") or {}
        text = raw.get("text") or tweet.get("text", "")
        article = tweet.get("article") or {}
        blocks = (article.get("content") or {}).get("blocks") or []
        if blocks:
            text = "\n".join(str(b.get("text", "")) for b in blocks)
        quote = tweet.get("quote") or {}
        if quote.get("text"):
            text += "\n引用貼文：" + quote["text"]
        media = tweet.get("media") or {}
        return Page(
            url=url,
            title=article.get("title") or "X 貼文",
            author=(tweet.get("author") or {}).get("screen_name", ""),
            text=text,
            images=[p["url"] for p in media.get("photos", []) if p.get("url")],
            has_video=bool(media.get("videos")),
            notes=[
                "X 內容經第三方 FxEmbed／VXTwitter 讀取，只能取得該服務可見的公開內容。"
            ],
        )

    async def bilibili(self, url):
        match = re.search(r"/(BV[0-9A-Za-z]+|av\d+)", urlsplit(url).path)
        if not match:
            raise ReadError("無法辨識 Bilibili 影片 ID")
        key = f"bvid={match[1]}" if match[1].startswith("BV") else f"aid={match[1][2:]}"
        info = await self.web.json(
            "https://api.bilibili.com/x/web-interface/view?" + key
        )
        if info.get("code") != 0:
            raise ReadError("Bilibili 未提供影片資訊，可能需要有效 Cookie")
        data = info["data"]
        page = Page(
            url,
            data.get("title", ""),
            (data.get("owner") or {}).get("name", ""),
            data.get("desc", ""),
        )
        page.has_video = True
        page.images = [data["pic"]] if data.get("pic") else []
        page.notes.append("僅影片標題、作者、簡介與封面；封面描述不能當作影片內容。")
        return page

    async def bilibili_post(self, url):
        match = re.fullmatch(r"/(?:opus/)?(\d+)/?", urlsplit(url).path)
        if not match:
            raise ReadError("請提供 Bilibili 單篇動態／Opus 連結")
        data = await self.web.json(
            "https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id=" + match[1]
        )
        item = (data.get("data") or {}).get("item") or {}
        if data.get("code") != 0 or str(item.get("id_str")) != match[1]:
            raise ReadError("Bilibili 未提供目標圖文動態，請檢查連結或 Cookie")
        page = Page(url, "Bilibili 圖文動態")
        for post in [item] + (
            [item["orig"]] if isinstance(item.get("orig"), dict) else []
        ):
            modules = post.get("modules") or {}
            author = (modules.get("module_author") or {}).get("name", "")
            dynamic = modules.get("module_dynamic") or {}
            major = dynamic.get("major") or {}
            opus = major.get("opus") or {}
            text = (dynamic.get("desc") or {}).get("text") or (
                opus.get("summary") or {}
            ).get("text", "")
            label = "正文" if post is item else "引用動態"
            page.text += f"\n{label}（{author}）：{text}"
            if post is item:
                page.author = author
                page.title = opus.get("title") or page.title
            for picture in (major.get("draw") or {}).get("items", []) + opus.get(
                "pics", []
            ):
                source = picture.get("src") or picture.get("url")
                if source:
                    page.images.append(urljoin(url, source))
            archive = major.get("archive") or {}
            if archive:
                page.has_video = True
                page.text += f"\n影片標題：{archive.get('title', '')}\n影片簡介：{archive.get('desc', '')}"
        return page

    async def threads(self, url):
        try:
            final, kind, body = await asyncio.wait_for(self.web.read(url), 5)
            if any(host_is(final, h) for h in ("threads.com", "threads.net")):
                url = final
                if "html" in kind:
                    return threads_preview(url, body.decode("utf-8", errors="replace"))
        except (ReadError, aiohttp.ClientError, asyncio.TimeoutError):
            pass
        # Browser rendering follows threads-dl's approach; exact post identity is required.
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                context = await browser.new_context(service_workers="block")
                cookies = SimpleCookie()
                cookies.load(self.web.cookies.get("threads.com", ""))
                if cookies:
                    await context.add_cookies(
                        [
                            {
                                "name": key,
                                "value": value.value,
                                "domain": "." + domain,
                                "path": "/",
                                "secure": True,
                            }
                            for key, value in cookies.items()
                            for domain in ("threads.com", "threads.net")
                        ]
                    )

                navigation_url = url

                async def route_request(route):
                    nonlocal navigation_url
                    req = route.request
                    if (
                        req.resource_type in ("image", "media", "font")
                        or req.method != "GET"
                    ):
                        await route.abort()
                        return
                    allowed = (
                        "threads.com",
                        "threads.net",
                        "cdninstagram.com",
                        "fbcdn.net",
                    )
                    if not any(host_is(req.url, h) for h in allowed):
                        await route.abort()
                        return
                    try:
                        # Fulfil through the checked resolver; Chromium never fetches arbitrary URLs.
                        final, kind, body = await self.web.read(req.url)
                        if req.is_navigation_request() and req.frame == page.main_frame:
                            navigation_url = final
                        await route.fulfill(status=200, content_type=kind, body=body)
                    except (ReadError, aiohttp.ClientError, asyncio.TimeoutError):
                        await route.abort()

                await context.route("**/*", route_request)
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                if navigation_url != page.url:
                    # Explicit navigation is intercepted again; a fulfilled 302 can bypass routing.
                    await page.goto(
                        navigation_url, wait_until="domcontentloaded", timeout=45000
                    )
                for _ in range(15):
                    match = re.search(r"/post/([\w-]+)", urlsplit(page.url).path)
                    if match:
                        data = await page.evaluate(THREADS_POST, match[1])
                        if data:
                            return Page(
                                page.url,
                                "Threads 貼文",
                                data["author"],
                                data["text"],
                                data["images"],
                                bool(data["videos"]),
                            )
                    await asyncio.sleep(1)
                return threads_preview(page.url, await page.content())
            finally:
                await browser.close()


THREADS_POST = """(id) => {
    // Prefer structured post data, matching the requested shortcode, never a suggested post.
    function find(node) {
        if (!node || typeof node !== 'object') return null;
        if (node.code === id && node.user && (node.caption || node.image_versions2 || node.video_versions)) {
            const media = node.carousel_media || [node];
            return {author: node.user.username || '', text: node.caption?.text || '',
                images: media.filter(m => !(m.video_versions?.length)).map(m => m.image_versions2?.candidates?.[0]?.url).filter(Boolean),
                videos: media.map(m => m.video_versions?.[0]?.url).filter(Boolean)};
        }
        for (const child of Object.values(node)) {
            const result = find(child); if (result) return result;
        }
        return null;
    }
    for (const script of document.querySelectorAll('script[type="application/json"]')) {
        try { const result = find(JSON.parse(script.textContent)); if (result) return result; } catch {}
    }
    return null;
}"""


def threads_preview(url: str, html: str) -> Page:
    soup = BeautifulSoup(html, "html.parser")
    canonical = soup.find("meta", property="og:url")
    description = soup.find("meta", property="og:description")
    expected = re.search(r"/post/([\w-]+)", urlsplit(url).path)
    actual = canonical.get("content", "") if canonical else ""
    identity = re.search(r"/post/([\w-]+)", urlsplit(actual).path)
    if not (
        expected
        and identity
        and expected[1] == identity[1]
        and any(host_is(actual, host) for host in ("threads.com", "threads.net"))
        and description
        and description.get("content", "").strip()
    ):
        raise ReadError("Threads 未取得可核對的貼文正文；可能是登入限制或網頁改版")
    title = soup.find("meta", property="og:title")
    # Static JSON often already contains the exact post and its photos; no browser needed.
    stack = []
    for script in soup.select('script[type="application/json"]'):
        try:
            stack.append(json.loads(script.get_text()))
        except ValueError:
            continue
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            if (
                node.get("code") == expected[1]
                and node.get("user")
                and any(
                    k in node for k in ("caption", "image_versions2", "video_versions")
                )
            ):
                media = node.get("carousel_media") or [node]
                images = []
                for item in media:
                    candidates = (item.get("image_versions2") or {}).get(
                        "candidates"
                    ) or []
                    if (
                        not item.get("video_versions")
                        and candidates
                        and candidates[0].get("url")
                    ):
                        images.append(candidates[0]["url"])
                return Page(
                    url,
                    "Threads 貼文",
                    node["user"].get("username", ""),
                    (node.get("caption") or {}).get("text", ""),
                    images,
                    any(item.get("video_versions") for item in media),
                )
            stack.extend(node.values())
    # og:image can be the author's avatar, so it is not evidence of a post image.
    return Page(
        url,
        title.get("content", "Threads 貼文") if title else "Threads 貼文",
        text=description["content"],
        notes=[
            "僅取得這篇 Threads 的公開預覽文字，可能截斷；正文、配圖、回覆與影片均未確認。"
        ],
    )


def parse_html(url: str, body: bytes) -> Page:
    soup = BeautifulSoup(body, "html.parser", from_encoding="utf-8")

    def meta(key):
        tag = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
        return tag.get("content", "") if tag else ""

    title = meta("og:title") or (
        soup.title.get_text(" ", strip=True) if soup.title else ""
    )
    page = Page(url, title, meta("author"))
    root = (
        soup.select_one("#main-content")
        if host_is(url, "ptt.cc")
        else soup.find("article") or soup.find("main") or soup.body
    )
    if root is None:
        if host_is(url, "ptt.cc"):
            raise ReadError("網頁沒有可讀取的正文")
        from .platforms import preview_page

        return preview_page(url, body)
    for tag in root.select("script, style, nav, footer, header, noscript, form"):
        tag.decompose()
    page.text = root.get_text("\n", strip=True)
    page.images = list(
        dict.fromkeys(
            urljoin(url, img["src"]) for img in root.find_all("img", src=True)
        )
    )
    if host_is(url, "ptt.cc"):
        # PTT often exposes article pictures as text/anchors, not img elements (Ermiana).
        candidates = links_in(page.text) + [
            urljoin(url, a["href"]) for a in root.find_all("a", href=True)
        ]
        page.images = list(
            dict.fromkeys(
                page.images
                + [
                    source
                    for source in candidates
                    if re.search(
                        r"\.(?:jpe?g|png|gif|webp)$",
                        urlsplit(source).path,
                        re.IGNORECASE,
                    )
                ]
            )
        )
        for line in root.select(".article-metaline"):
            label, value = (
                line.select_one(".article-meta-tag"),
                line.select_one(".article-meta-value"),
            )
            if label and value and label.get_text(strip=True) == "作者":
                page.author = value.get_text(strip=True)
    page.has_video = bool(
        root.find("video") or meta("og:video") or meta("og:video:url")
    )
    if not page.text and not page.images and not page.has_video:
        if host_is(url, "ptt.cc"):
            raise ReadError("網頁沒有可理解的內容")
        from .platforms import preview_page

        return preview_page(url, body)
    if not host_is(url, "ptt.cc"):
        page.notes.append(
            "一般網頁以可取得的 HTML 正文為準，動態載入／登入後內容可能缺漏。"
        )
    return page
