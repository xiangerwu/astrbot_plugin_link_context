"""Exercise the real readers with bounded HTTP/API fixtures, without model charges."""

import json
import os
import types
import unittest
from unittest.mock import AsyncMock, patch

from core.fetch import Reader, ReadError, Web, parse_html, threads_preview
from core.platforms import preview


def html_preview(text="目標摘要"):
    return f'<meta property="og:title" content="目標標題"><meta property="og:description" content="{text}"><meta property="og:image" content="https://example.com/preview.jpg">'.encode()


class PlatformTests(unittest.IsolatedAsyncioTestCase):
    async def test_preview_platform_routes_and_no_video_download(self):
        cases = [
            ("https://www.instagram.com/p/abc/", "oginstagram.com", False),
            ("https://www.instagram.com/alice/reels/abc/2/", "oginstagram.com", True),
            ("https://www.instagram.com/stories/alice/123/", "oginstagram.com", False),
            ("https://www.facebook.com/share/p/abc/", "facebed.com", False),
            ("https://www.facebook.com/reel/123/", "facebed.com", True),
            ("https://www.tiktok.com/@alice/video/123", "tnktok.com", True),
            ("https://home.gamer.com.tw/artwork.php?sn=12345", "gamer.com.tw", False),
            (
                "https://m.gamer.com.tw/forum/C.php?bsn=60076&snA=12345",
                "forum.gamer.com.tw",
                False,
            ),
        ]
        for url, host, video in cases:
            with self.subTest(url=url):

                async def read(source, **kwargs):
                    self.assertIn(host, source)
                    return source, "text/html", html_preview()

                web = types.SimpleNamespace(read=AsyncMock(side_effect=read))
                page = await Reader(web).read(url)
                self.assertEqual(page.text, "目標摘要")
                self.assertEqual(page.has_video, video)
                self.assertIn("公開預覽", page.notes[0])
                web.read.assert_awaited_once()

    async def test_preview_fallback_rejects_login_and_wrong_redirect(self):
        url = "https://www.instagram.com/p/target/"
        web = types.SimpleNamespace(
            read=AsyncMock(
                side_effect=[
                    (
                        "https://www.oginstagram.com/p/target/",
                        "text/html",
                        html_preview().replace(
                            "目標標題".encode(), b"Log in or sign up"
                        ),
                    ),
                    (
                        "https://www.vxinstagram.com/p/target/",
                        "text/html",
                        html_preview(),
                    ),
                ]
            )
        )
        page = await Reader(web).read(url)
        self.assertEqual(page.text, "目標摘要")
        self.assertEqual(web.read.await_count, 2)
        web.read = AsyncMock(
            return_value=("https://www.vxinstagram.com/", "text/html", html_preview())
        )
        with self.assertRaises(ReadError):
            await preview(web, url, ("www.vxinstagram.com",))

    async def test_tiktok_short_url_and_bilibili_api_fallback(self):
        target = "https://www.tiktok.com/@alice/video/123"
        web = types.SimpleNamespace(
            read=AsyncMock(
                side_effect=[
                    (target, "text/html", b""),
                    (
                        target.replace("tiktok.com", "tnktok.com"),
                        "text/html",
                        html_preview(),
                    ),
                ]
            )
        )
        self.assertTrue(
            (await Reader(web).read("https://vm.tiktok.com/abc/")).has_video
        )
        for source, expected in [
            ("https://www.bilibili.com/video/BVtest?p=2", "/video/BVtest?p=2"),
            ("https://t.bilibili.com/123", "/opus/123"),
        ]:

            async def read(url, **kwargs):
                self.assertTrue(url.endswith(expected))
                return url, "text/html", html_preview()

            web = types.SimpleNamespace(
                json=AsyncMock(side_effect=ReadError("HTTP 412")),
                read=AsyncMock(side_effect=read),
            )
            page = await Reader(web).read(source)
            self.assertEqual(page.text, "目標摘要")
            web.read.assert_awaited_once()

    async def test_x_backup_identity_media_and_quote(self):
        vx = {
            "tweetURL": "https://x.com/alice/status/123",
            "text": "正文",
            "user_screen_name": "alice",
            "qrt": {"text": "引用"},
            "media_extended": [
                {"type": "image", "url": "https://example.com/a.jpg"},
                {"type": "video", "url": "https://example.com/v.mp4"},
            ],
        }
        web = types.SimpleNamespace(
            json=AsyncMock(side_effect=[ReadError("HTTP 503"), vx])
        )
        page = await Reader(web).read("https://x.com/alice/status/123")
        self.assertIn("引用", page.text)
        self.assertEqual(page.images, ["https://example.com/a.jpg"])
        self.assertTrue(page.has_video)
        web.json = AsyncMock(
            side_effect=[
                ReadError("HTTP 503"),
                {**vx, "tweetURL": "https://x.com/alice/status/999"},
            ]
        )
        with self.assertRaises(ReadError):
            await Reader(web).read("https://x.com/alice/status/123")

    async def test_api_platforms_extract_only_matching_records(self):
        cases = [
            (
                "https://misskey.io/notes/abc",
                {
                    "id": "abc",
                    "user": {"username": "alice"},
                    "text": "正文",
                    "files": [
                        {"type": "image/png", "url": "https://example.com/a.png"}
                    ],
                },
                "abc",
            ),
            (
                "https://www.pixiv.net/artworks/123",
                {
                    "body": {
                        "id": "123",
                        "title": "畫作",
                        "description": "正文",
                        "userName": "alice",
                        "urls": {"regular": "https://example.com/a.png"},
                        "pageCount": 3,
                    }
                },
                "123",
            ),
            (
                "https://steamcommunity.com/sharedfiles/filedetails/?id=123",
                {
                    "response": {
                        "publishedfiledetails": [
                            {
                                "publishedfileid": "123",
                                "result": 1,
                                "title": "作品",
                                "description": "正文",
                                "preview_url": "https://example.com/a.png",
                            }
                        ]
                    }
                },
                "123",
            ),
            (
                "https://e-hentai.org/g/123/abc/",
                {
                    "gmetadata": [
                        {
                            "gid": 123,
                            "title": "圖庫",
                            "tags": ["正文"],
                            "thumb": "https://example.com/a.png",
                        }
                    ]
                },
                "123",
            ),
            (
                "https://exhentai.org/g/123/abc/",
                {
                    "gmetadata": [
                        {
                            "gid": 123,
                            "title": "圖庫",
                            "tags": ["正文"],
                            "thumb": "https://example.com/a.png",
                        }
                    ]
                },
                "123",
            ),
            (
                "https://nhentai.net/g/123/",
                {
                    "id": 123,
                    "media_id": "456",
                    "title": {"english": "圖庫"},
                    "tags": [{"name": "正文"}],
                    "pages": [{"path": "galleries/456/1.jpg"}],
                    "num_pages": 10,
                },
                "123",
            ),
        ]
        for url, data, identifier in cases:
            with self.subTest(url=url):
                web = types.SimpleNamespace(
                    json=AsyncMock(return_value=data),
                    read=AsyncMock(side_effect=ReadError("no preview")),
                )
                page = await Reader(web).read(url)
                self.assertIn("正文", page.text)
                self.assertEqual(len(page.images), 1)
                web.json.assert_awaited_once()
                wrong = json.loads(
                    json.dumps(data, ensure_ascii=False)
                    .replace('"' + identifier + '"', '"999"')
                    .replace(": " + identifier, ": 999")
                )
                web.json = AsyncMock(return_value=wrong)
                with self.assertRaises(ReadError):
                    await Reader(web).read(url)

    async def test_bluesky_official_and_backup_match_uri(self):
        uri = "at://did:plc:alice/app.bsky.feed.post/abc"
        post = {
            "uri": uri,
            "author": {"handle": "alice.test"},
            "record": {"text": "正文"},
            "embed": {"images": [{"fullsize": "https://example.com/a.png"}]},
        }
        for result in [{"thread": {"post": post}}, ReadError("HTTP 503")]:
            web = types.SimpleNamespace(
                json=AsyncMock(
                    side_effect=[{"did": "did:plc:alice"}, result, {"posts": [post]}]
                )
            )
            page = await Reader(web).read(
                "https://bsky.app/profile/alice.test/post/abc"
            )
            self.assertEqual(page.text, "正文")
            self.assertEqual(len(page.images), 1)
        web.json = AsyncMock(
            side_effect=[
                {"did": "did:plc:alice"},
                {"thread": {"post": {**post, "uri": uri + "wrong"}}},
                {"posts": []},
            ]
        )
        with self.assertRaises(ReadError):
            await Reader(web).read("https://bsky.app/profile/alice.test/post/abc")

    async def test_pchome_jsonp_and_plurk_body(self):
        web = types.SimpleNamespace(
            read=AsyncMock(
                side_effect=[
                    (
                        "api",
                        "text/javascript",
                        b'jsonp_prod({"ABCDEF-123456789":{"Name":"Product","Price":{"P":99},"Pic":{"B":"/pic.jpg"}}});',
                    ),
                    (
                        "api",
                        "text/javascript",
                        b'jsonp_desc({"ABCDEF-123456789":{"SloganInfo":["Description"]}});',
                    ),
                ]
            )
        )
        page = await Reader(web).read("https://24h.pchome.com.tw/prod/ABCDEF-123456789")
        self.assertEqual(page.title, "Product")
        self.assertIn("99", page.text)
        self.assertIn("Description", page.text)
        self.assertEqual(page.images, ["https://img.pchome.com.tw/cs/pic.jpg"])
        web.read = AsyncMock(
            return_value=(
                "url",
                "text/html",
                b'<div class="name">Alice</div><div class="text_holder">body<br>line<img src="https://images.plurk.com/a.jpg"></div><script>{"content_raw":"https://images.plurk.com/b.jpg"}</script>',
            )
        )
        page = await Reader(web).read("https://www.plurk.com/m/p/abc")
        self.assertEqual(page.author, "Alice")
        self.assertEqual(page.text, "body\nline")
        self.assertEqual(
            page.images,
            ["https://images.plurk.com/a.jpg", "https://images.plurk.com/b.jpg"],
        )

    async def test_post_redirect_is_not_replayed_and_cookies_stay_at_origin(self):
        web = Web({"threads.com": "secret=TEST", "bilibili.com": "secret=TEST"})
        real = web.session

        class Response:
            status = 302
            headers = {"Location": "https://example.com/"}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        from unittest.mock import Mock

        web.session = types.SimpleNamespace(request=Mock(return_value=Response()))
        try:
            with self.assertRaises(ReadError):
                await web.json(
                    "https://misskey.io/api/notes/show",
                    method="POST",
                    json_data={"noteId": "abc"},
                )
            self.assertEqual(web.session.request.call_count, 1)
            self.assertEqual(web.session.request.call_args.args[0], "POST")
            self.assertEqual(
                web.session.request.call_args.kwargs["json"], {"noteId": "abc"}
            )
            for host in [
                "www.vxbilibili.com",
                "www.oginstagram.com",
                "api.vxtwitter.com",
                "facebed.com",
                "fixthreads.seria.moe",
            ]:
                self.assertNotIn("Cookie", web.headers("https://" + host + "/"))
        finally:
            await real.close()

    async def test_threads_browser_redirect_keeps_post_identity(self):
        from playwright.async_api import BrowserType

        original = BrowserType.launch

        async def launch(browser_type, **kwargs):
            if os.environ.get("LINK_CONTEXT_TEST_BROWSER"):
                kwargs["executable_path"] = os.environ["LINK_CONTEXT_TEST_BROWSER"]
            return await original(browser_type, **kwargs)

        final = "https://www.threads.com/@alice/post/target"
        post = {
            "code": "target",
            "user": {"username": "alice"},
            "caption": {"text": "正文"},
        }
        body = (
            '<script type="application/json">' + json.dumps(post) + "</script>"
        ).encode()
        calls = []

        async def read(url, **kwargs):
            calls.append(url)
            if len(calls) == 1:
                raise ReadError("temporary failure before browser")
            return final, "text/html", body

        web = types.SimpleNamespace(read=AsyncMock(side_effect=read), cookies={})
        with patch.object(BrowserType, "launch", launch):
            page = await Reader(web).read("https://www.threads.com/share/short")
        self.assertEqual(page.url, final)
        self.assertEqual(page.text, "正文")
        self.assertIn(final, calls)

    def test_fast_threads_preserves_photos_and_generic_preview(self):
        url = "https://www.threads.com/@alice/post/target"
        node = {
            "code": "target",
            "user": {"username": "alice"},
            "caption": {"text": "正文"},
            "image_versions2": {
                "candidates": [{"url": "https://example.com/photo.jpg"}]
            },
        }
        body = f'<meta property="og:url" content="{url}"><meta property="og:description" content="摘要"><script type="application/json">{json.dumps(node)}</script>'
        page = threads_preview(url, body)
        self.assertEqual(page.text, "正文")
        self.assertEqual(page.images, ["https://example.com/photo.jpg"])
        with self.assertRaises(ReadError):
            threads_preview(url.replace("target", "wrong"), body)
        page = parse_html("https://example.com/article", html_preview())
        self.assertEqual(page.text, "目標摘要")
        self.assertIn("公開預覽", page.notes[0])
