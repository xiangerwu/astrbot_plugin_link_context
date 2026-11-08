"""Additional public readers inspired by ermiana; no Discord output or video download."""

import asyncio
import json
import re
from urllib.parse import parse_qs, quote, urljoin, urlsplit, urlunsplit

import aiohttp
from bs4 import BeautifulSoup

from .fetch import Page, ReadError, host_is


FETCH_ERRORS = (ReadError, aiohttp.ClientError, asyncio.TimeoutError)
CRAWLER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)"
}


async def twitter_data(web, identifier):
    try:
        data = await asyncio.wait_for(
            web.json(f"https://api.fxtwitter.com/status/{identifier}"), 5
        )
        if str((data.get("tweet") or {}).get("id")) != identifier:
            raise ReadError("X 解析服務未提供目標貼文")
        return data
    except FETCH_ERRORS:
        item = await asyncio.wait_for(
            web.json(f"https://api.vxtwitter.com/i/status/{identifier}"), 5
        )
        source = item.get("tweetURL", "")
        if not (
            host_is(source, "x.com") or host_is(source, "twitter.com")
        ) or not re.fullmatch(
            r"/[^/]+/status/" + identifier + r"/?", urlsplit(source).path
        ):
            raise ReadError("X 備援服務未提供目標貼文")
        media = item.get("media_extended") or []
        return {
            "tweet": {
                "id": identifier,
                "text": item.get("text", ""),
                "author": {"screen_name": item.get("user_screen_name", "")},
                "quote": item.get("qrt") or {},
                "media": {
                    "photos": [p for p in media if p.get("type") == "image"],
                    "videos": [p for p in media if p.get("type") in ("video", "gif")],
                },
            }
        }


def preview_page(url, body):
    soup = BeautifulSoup(body, "html.parser")

    def meta(name):
        tag = soup.find("meta", property=name) or soup.find(
            "meta", attrs={"name": name}
        )
        return tag.get("content", "").strip() if tag else ""

    title = meta("og:title") or meta("twitter:title")
    text = meta("og:description") or meta("twitter:description") or meta("description")
    if (
        not title
        or not text
        or re.search(
            r"log in|login|sign up|access denied|just a moment|登入|登录|安全驗證|安全验证",
            title,
            re.I,
        )
    ):
        raise ReadError("來源未提供可用的貼文預覽，可能需要登入或已被限制")
    image = meta("og:image") or meta("twitter:image")
    return Page(
        url,
        title,
        meta("author"),
        text,
        images=[urljoin(url, image)] if image else [],
        has_video=bool(meta("og:video") or meta("og:video:url")),
        notes=["僅公開預覽，文字可能截斷；預覽圖片不代表完整相簿或影片內容。"],
    )


async def preview(web, url, hosts):
    """Read fixed preview providers, keeping the shared URL out of arbitrary hosts."""
    parts = urlsplit(url)
    for host in hosts:
        candidate = urlunsplit(("https", host, parts.path, parts.query, ""))
        try:
            final, kind, body = await asyncio.wait_for(
                web.read(candidate, headers=CRAWLER_HEADERS), 5
            )
            # A preview redirect to a login/home page is not this post.
            if (
                urlsplit(final).path.rstrip("/") != parts.path.rstrip("/")
                or not (host_is(final, host) or host_is(final, parts.hostname))
                or "html" not in kind
            ):
                raise ReadError("預覽來源重新導向其他頁面，未採用內容")
            page = preview_page(url, body)
            page.notes.append(f"透過 {host} 取得公開預覽；該第三方會收到此網址。")
            return page
        except FETCH_ERRORS:
            continue
    raise ReadError("公開預覽來源均無法讀取此連結")


async def read_platform(web, url):
    path = urlsplit(url).path
    if host_is(url, "instagram.com") and re.fullmatch(
        r"/(?:(?:[\w.]+/)?(?:p|reels?|tv)/[\w-]+(?:/[1-9]\d*)?|stories/[\w.]+/\d+)/?",
        path,
    ):
        page = await preview(web, url, ("www.oginstagram.com", "www.vxinstagram.com"))
        page.has_video |= "/reel" in path or "/tv/" in path
        return page
    if host_is(url, "facebook.com") and (
        re.search(r"/(?:share|reel|posts|videos|watch|photo|groups)(?:/|\.|$)", path)
        or path in ("/permalink.php", "/story.php")
    ):
        page = await preview(web, url, ("facebed.com",))
        page.has_video |= bool(
            re.search(r"/(?:reel|videos|watch|share/[vr])(?:/|$)", path)
        )
        return page
    if host_is(url, "tiktok.com"):
        if host_is(url, "vm.tiktok.com") or host_is(url, "vt.tiktok.com"):
            url, _, _ = await asyncio.wait_for(web.read(url), 5)
            path = urlsplit(url).path
        if not host_is(url, "tiktok.com") or not re.fullmatch(
            r"/@[\w.-]*/video/\d+/?", path
        ):
            raise ReadError("請提供 TikTok 單篇影片連結，短網址必須可轉址到原站")
        page = await preview(web, url, ("www.tnktok.com", "www.tiktokez.com"))
        page.has_video = True
        return page
    if host_is(url, "bsky.app") and (
        match := re.fullmatch(r"/profile/([^/]+)/post/([\w]+)/*", path)
    ):
        return await bluesky(web, url, *match.groups())
    if host_is(url, "misskey.io") and (
        match := re.fullmatch(r"/notes/([\w]+)/*", path)
    ):
        note = await web.json(
            "https://misskey.io/api/notes/show",
            method="POST",
            json_data={"noteId": match[1]},
        )
        if str(note.get("id")) != match[1] or not note.get("user"):
            raise ReadError("Misskey 未回傳目標貼文")
        files = note.get("files") or []
        page = Page(
            url,
            "Misskey 貼文",
            note["user"].get("username", ""),
            note.get("text") or "",
            [
                f["url"]
                for f in files
                if f.get("url") and f.get("type", "").startswith("image/")
            ],
            any(f.get("type", "").startswith("video/") for f in files),
        )
        if note.get("cw"):
            page.text = note["cw"] + "\n" + page.text
        if note.get("renote"):
            page.text += "\n引用貼文：" + (note["renote"].get("text") or "")
        return page
    if host_is(url, "pixiv.net") and (
        match := re.fullmatch(r"/(?:en/)?artworks/(\d+)/?", path)
    ):
        return await pixiv(web, url, match[1])
    if host_is(url, "steamcommunity.com") and path.rstrip("/") in (
        "/sharedfiles/filedetails",
        "/workshop/filedetails",
    ):
        identifier = parse_qs(urlsplit(url).query).get("id", [""])[0]
        if not identifier.isdecimal():
            raise ReadError("Steam Workshop 連結缺少作品 ID")
        data = await web.json(
            "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
            method="POST",
            form_data={"itemcount": "1", "publishedfileids[0]": identifier},
        )
        items = (data.get("response") or {}).get("publishedfiledetails") or []
        item = next(
            (i for i in items if str(i.get("publishedfileid")) == identifier), {}
        )
        if item.get("result") != 1 or item.get("banned") or not item.get("title"):
            raise ReadError("Steam 未提供可用的目標工作坊作品")
        return Page(
            url,
            item["title"],
            str(item.get("creator", "")),
            item.get("description", ""),
            [item["preview_url"]] if item.get("preview_url") else [],
            notes=["工作坊說明與預覽圖；未下載模組或遊戲檔案。"],
        )
    if host_is(url, "24h.pchome.com.tw") and (
        match := re.fullmatch(r"/prod/([A-Za-z0-9]+-[A-Za-z0-9]+)/?", path)
    ):
        return await pchome(web, url, match[1].upper())
    if host_is(url, "plurk.com") and (
        match := re.fullmatch(r"/(?:m/)?p/([\w]+)/?", path)
    ):
        canonical = "https://www.plurk.com/p/" + match[1]
        _, _, body = await web.read(canonical)
        soup = BeautifulSoup(body, "html.parser")
        root = soup.select_one(".text_holder")
        if root is None or not root.get_text(strip=True):
            return preview_page(url, body)
        name = soup.select_one(".name")
        images = [urljoin(canonical, img["src"]) for img in root.select("img[src]")]
        for script in soup.find_all("script"):
            source = script.get_text()
            start = source.find('"content_raw"')
            if start < 0:
                continue
            for literal in re.findall(r'"(?:[^"\\]|\\.)*"', source[start:]):
                try:
                    value = json.loads(literal)
                except ValueError:
                    continue
                images.extend(
                    re.findall(r'https://images\.plurk\.com/[^\s"<>]+', value)
                )
        return Page(
            url,
            "Plurk 貼文",
            name.get_text(" ", strip=True) if name else "",
            root.get_text("\n", strip=True),
            list(dict.fromkeys(images)),
        )
    if host_is(url, "gamer.com.tw") and (".php" in path):
        if host_is(url, "m.gamer.com.tw") and path.startswith("/forum/"):
            url = urlunsplit(
                (
                    "https",
                    "forum.gamer.com.tw",
                    path.removeprefix("/forum"),
                    urlsplit(url).query,
                    "",
                )
            )
        _, _, body = await web.read(url)
        return preview_page(url, body)
    if (host_is(url, "e-hentai.org") or host_is(url, "exhentai.org")) and (
        match := re.fullmatch(r"/g/(\d+)/([a-zA-Z0-9]+)/?", path)
    ):
        data = await web.json(
            "https://api.e-hentai.org/api.php",
            method="POST",
            json_data={
                "method": "gdata",
                "gidlist": [[int(match[1]), match[2]]],
                "namespace": 1,
            },
        )
        item = next(
            (g for g in data.get("gmetadata", []) if str(g.get("gid")) == match[1]), {}
        )
        if not item or item.get("error"):
            raise ReadError("圖庫 API 未提供目標資料；不繞過登入限制")
        return Page(
            url,
            item.get("title_jpn") or item.get("title", ""),
            item.get("uploader", ""),
            "\n".join(item.get("tags") or []),
            [item["thumb"]] if item.get("thumb") else [],
            notes=["僅圖庫標題、標籤與封面，未閱讀整本內容；透過 E-Hentai 公開 API。"],
        )
    if host_is(url, "nhentai.net") and (match := re.fullmatch(r"/g/(\d+)/?", path)):
        item = await web.json("https://nhentai.net/api/v2/galleries/" + match[1])
        if str(item.get("id")) != match[1]:
            raise ReadError("圖庫 API 未回傳目標圖庫")
        title = item.get("title") or {}
        pages = item.get("pages") or []
        first = pages[0].get("path", "").lstrip("/") if pages else ""
        valid = re.fullmatch(
            r"galleries/"
            + re.escape(str(item.get("media_id")))
            + r"/1\.(?:jpe?g|png|gif|webp)",
            first,
        )
        return Page(
            url,
            title.get("japanese") or title.get("english") or title.get("pretty", ""),
            text="\n".join(
                t.get("type", "tag") + ": " + t["name"]
                for t in item.get("tags", [])
                if t.get("name")
            ),
            images=["https://i.nhentai.net/" + first] if valid else [],
            notes=[
                f"僅圖庫標籤與第一頁，總頁數 {item.get('num_pages', '未知')}；未閱讀整本內容。"
            ],
        )
    return None


async def bluesky(web, url, handle, rkey):
    # Resolve the identity first so a mirror cannot silently supply another user's post.
    did = handle
    if not handle.startswith("did:"):
        identity = await web.json(
            "https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle="
            + quote(handle, safe="")
        )
        did = identity.get("did", "")
    if not did.startswith("did:"):
        raise ReadError("Bluesky 無法核對作者識別碼")
    uri = f"at://{did}/app.bsky.feed.post/{rkey}"
    try:
        data = await asyncio.wait_for(
            web.json(
                "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri="
                + quote(uri, safe="")
            ),
            5,
        )
        post = (data.get("thread") or {}).get("post") or {}
        if post.get("uri") != uri:
            raise ReadError("Bluesky 未回傳目標貼文")
    except FETCH_ERRORS:
        data = await web.json(
            f"https://bskx.app/profile/{quote(handle, safe='')}/post/{rkey}/json"
        )
        post = next((p for p in data.get("posts", []) if p.get("uri") == uri), {})
        if not post:
            raise ReadError("Bluesky 預覽未回傳目標貼文")
    embed = post.get("embed") or {}
    media = embed.get("media") or embed
    return Page(
        url,
        "Bluesky 貼文",
        (post.get("author") or {}).get("handle", handle),
        (post.get("record") or {}).get("text", ""),
        [p["fullsize"] for p in media.get("images", []) if p.get("fullsize")],
        "video" in media.get("$type", ""),
        notes=["公開貼文；API 失敗時會向 bskx.app 請求相同貼文。"],
    )


async def pixiv(web, url, identifier):
    try:
        data = await asyncio.wait_for(
            web.json(f"https://www.pixiv.net/ajax/illust/{identifier}"), 5
        )
        item = data.get("body") or {}
        if data.get("error") or str(item.get("id")) != identifier:
            raise ReadError("Pixiv 未回傳目標作品")
        image = (item.get("urls") or {}).get("regular")
        return Page(
            url,
            item.get("title", ""),
            item.get("userName", ""),
            BeautifulSoup(item.get("description", ""), "html.parser").get_text(
                "\n", strip=True
            ),
            [image] if image else [],
            item.get("illustType") == 2,
            notes=[
                f"僅作品說明與第一張預覽，共 {item.get('pageCount', '未知')} 頁；未取得完整作品或動畫。"
            ],
        )
    except FETCH_ERRORS:
        return await preview(
            web, f"https://www.pixiv.net/artworks/{identifier}", ("www.phixiv.net",)
        )


async def pchome(web, url, identifier):
    base = "https://ecapi-cdn.pchome.com.tw/"
    endpoints = [
        f"ecshop/prodapi/v2/prod/{identifier}&fields=Name,Nick,Price,Pic&_callback=jsonp_prod",
        f"cdn/ecshop/prodapi/v2/prod/{identifier}/desc&fields=Meta,SloganInfo&_callback=jsonp_desc",
    ]
    responses = await asyncio.gather(
        *(web.read(base + endpoint) for endpoint in endpoints)
    )
    items = []
    for _, _, body in responses:
        text = body.decode("utf-8")
        start = re.search(r"[\[{]", text)
        try:
            data, _ = json.JSONDecoder().raw_decode(
                text[start.start() :] if start else ""
            )
            item = data.get(identifier) or (data.get("data") or {}).get(identifier)
        except (ValueError, AttributeError):
            raise ReadError("PChome 未提供可核對的商品資料") from None
        if not isinstance(item, dict):
            raise ReadError("PChome 商品 ID 不符")
        items.append(item)
    product, description = items
    pic = product.get("Pic") or {}
    image = (pic.get("B") or pic.get("S")) if isinstance(pic, dict) else pic
    slogan = description.get("SloganInfo") or []
    price = product.get("Price") or {}
    price = price.get("P", "未知") if isinstance(price, dict) else price
    return Page(
        url,
        BeautifulSoup(
            product.get("Name") or product.get("Nick", ""), "html.parser"
        ).get_text(" ", strip=True),
        text=BeautifulSoup(
            "\n".join(slogan) if isinstance(slogan, list) else slogan, "html.parser"
        ).get_text("\n", strip=True)
        + f"\n讀取時價格：{price}",
        images=["https://img.pchome.com.tw/cs/" + image.lstrip("/")] if image else [],
        notes=["商品預覽資料；價格、庫存與促銷可能變動。"],
    )
