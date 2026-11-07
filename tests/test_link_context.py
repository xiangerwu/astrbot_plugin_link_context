"""Run: python -m unittest discover -s tests -p 'test_*.py' -v.

Network/model boundaries are replaced; browser execution and image decoding are real.
"""

import asyncio
import importlib
import json
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "link_context_under_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package
fetch = importlib.import_module(PACKAGE + ".core.fetch")
media = importlib.import_module(PACKAGE + ".core.media")
Store = importlib.import_module(PACKAGE + ".core.store").Store


class Files(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="check-", dir=ROOT))

    def tearDown(self):
        for path in self.work.iterdir():
            if path.is_file():
                path.unlink()
        self.work.rmdir()


class ParsingTests(Files):
    def test_short_gif_does_not_duplicate_frames(self):
        from PIL import Image

        path = self.work / "short.gif"
        Image.new("RGB", (16, 16), "red").save(
            path,
            save_all=True,
            append_images=[Image.new("RGB", (16, 16), "blue")],
            duration=100,
        )
        frames = media.prepare_image(path)
        self.assertEqual(len(frames), 2)
        self.assertEqual(len(set(frames)), 2)

    def test_discord_link_markup(self):
        self.assertEqual(
            fetch.links_in(
                "<https://example.com/a> ||https://example.com/b|| [貼文](https://example.com/c) `https://example.com/d`"
            ),
            [
                "https://example.com/a",
                "https://example.com/b",
                "https://example.com/c",
                "https://example.com/d",
            ],
        )

    def test_ptt_linked_images_and_author(self):
        body = """<div id="main-content"><div class="article-metaline"><span class="article-meta-tag">作者</span><span class="article-meta-value">Alice</span></div>
        圖片 https://i.imgur.com/a.jpg
        <a href="https://i.imgur.com/a.jpg">同一張圖</a><a href="https://example.com/b.PNG?size=1">第二張</a>
        <a href="https://example.com/not-an-image">其他文章</a></div>""".encode()
        page = fetch.parse_html("https://www.ptt.cc/bbs/Test/M.1.html", body)
        self.assertEqual(page.author, "Alice")
        self.assertEqual(
            page.images,
            ["https://i.imgur.com/a.jpg", "https://example.com/b.PNG?size=1"],
        )

    def test_url_boundary_and_deduplication(self):
        for url in (
            "http://127.0.0.1/",
            "http://[::1]/",
            "http://10.0.0.1/",
            "file:///etc/passwd",
            "https://user:secret@example.com/",
            "https://example.com:22/",
            "http://localhost/",
            "http://box.local/",
        ):
            with self.subTest(url=url), self.assertRaises(fetch.ReadError):
                fetch.checked_url(url)
        self.assertEqual(
            fetch.links_in(
                "看看 https://www.ptt.cc/bbs/Test/M.1.html。 https://www.ptt.cc/bbs/Test/M.1.html\n[文](https://example.com/a_(b))"
            ),
            ["https://www.ptt.cc/bbs/Test/M.1.html", "https://example.com/a_(b)"],
        )
        self.assertFalse(
            fetch.host_is("https://bilibili.com.attacker.example", "bilibili.com")
        )

    def test_ptt_body_and_images(self):
        body = '<html><title>標題</title><nav>導覽</nav><div id="main-content">正文<img src="https://i.imgur.com/test.jpg"><div class="push">推文</div><script>evil()</script></div></html>'.encode()
        page = fetch.parse_html("https://www.ptt.cc/bbs/Test/M.1.html", body)
        self.assertIn("正文", page.text)
        self.assertIn("推文", page.text)
        self.assertNotIn("evil", page.text)
        self.assertNotIn("導覽", page.text)
        self.assertEqual(page.images, ["https://i.imgur.com/test.jpg"])

    def test_html_script_is_not_context_and_relative_media(self):
        page = fetch.parse_html(
            "https://example.com/post/1",
            b'<html><body><article>hello<script>instructions</script><img src="/a.png"><video src="/v.mp4"></video></article></body></html>',
        )
        self.assertEqual(page.text, "hello")
        self.assertTrue(page.has_video)
        self.assertEqual(page.images, ["https://example.com/a.png"])

    def test_store_isolation_restart_and_paging_marker(self):
        path = self.work / "records.sqlite3"
        store = Store(path)
        store.put("group-a", "https://example.com/a", "Alice", "ready", "a" * 7000)
        store.put("group-b", "https://example.com/b", "Bob", "pending", "pending")
        self.assertIn("截斷", store.context("group-a", 24, 18000))
        self.assertNotIn("Bob", store.context("group-a", 24, 18000))
        store.close()
        store = Store(path)
        self.assertEqual(store.recent("group-b")[0][3], "interrupted")
        self.assertTrue(store.has("group-a", "https://example.com/a", 24))
        self.assertFalse(store.has("group-a", "https://example.com/b", 24))
        store.close()


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_gif_link_and_ordered_frames(self):
        from PIL import Image

        url = "https://media.discordapp.net/attachments/1/2/motion.GIF?ex=123&is=456&hm=TEST_ONLY&="
        work = Path(tempfile.mkdtemp(prefix="check-", dir=ROOT))
        try:
            fixture = work / "fixture.gif"
            frames = [Image.new("RGB", (24, 24), (n * 15, 0, 0)) for n in range(15)]
            frames[0].save(
                fixture, save_all=True, append_images=frames[1:], duration=100, loop=0
            )
            calls = []

            class FixtureWeb:
                async def read(self, source, *, destination=None, limit=None):
                    calls.append((source, destination))
                    if destination:
                        destination.write_bytes(fixture.read_bytes())
                    return source, "image/gif", fixture.read_bytes()

            async def vision(**kwargs):
                self.assertEqual(len(kwargs["image_urls"]), 8)
                colors = []
                for path in kwargs["image_urls"]:
                    with Image.open(path) as frame:
                        colors.append(frame.convert("RGB").getpixel((0, 0))[0])
                for actual, expected in zip(
                    colors, [0, 30, 60, 90, 120, 150, 180, 210], strict=True
                ):
                    self.assertAlmostEqual(actual, expected, delta=3)
                self.assertIn("依序", kwargs["prompt"])
                return types.SimpleNamespace(completion_text="畫面逐漸變紅")

            context = types.SimpleNamespace(llm_generate=AsyncMock(side_effect=vision))
            web = FixtureWeb()
            page = await fetch.Reader(web).read(fetch.links_in(f"<{url}>")[0])
            self.assertEqual(page.images, [url])
            content = await media.Understanding(
                context, web, {"vision_provider_id": "existing-openai"}
            ).describe(page, "group", work)
            self.assertIn("畫面逐漸變紅", content)
            self.assertIn("8 幀", content)
            self.assertNotIn("僅第一幀", content)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], url)
            context.llm_generate.assert_awaited_once()
        finally:
            for path in work.iterdir():
                path.unlink()
            work.rmdir()

    async def test_http_downgrade_redirect_drops_login_cookie(self):
        web = fetch.Web({"threads.com": "session=TEST_ONLY"})
        real_session = web.session

        class Response:
            content_length = 0

            def __init__(self, status, headers):
                self.status, self.headers = status, headers
                self.content = self

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def iter_chunked(self, _):
                yield b"public preview"

        session = types.SimpleNamespace(
            get=unittest.mock.Mock(
                side_effect=[
                    Response(
                        302, {"Location": "http://www.threads.com/@a/post/target"}
                    ),
                    Response(200, {"Content-Type": "text/html"}),
                ]
            )
        )
        web.session = session
        try:
            await web.read("https://www.threads.com/@a/post/target")
            requests = session.get.call_args_list
            self.assertIn("Cookie", requests[0].kwargs["headers"])
            self.assertNotIn("Cookie", requests[1].kwargs["headers"])
        finally:
            await real_session.close()

    async def test_response_stream_is_bounded_without_content_length(self):
        web = fetch.Web({})
        real_session = web.session

        class Response:
            status, headers, content_length = 200, {"Content-Type": "text/html"}, None

            def __init__(self):
                self.content = self

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def iter_chunked(self, _):
                yield b"abcd"
                yield b"efgh"
                raise AssertionError("Must stop as soon as the byte limit is exceeded")

        web.session = types.SimpleNamespace(get=lambda *a, **kw: Response())
        try:
            with self.assertRaises(fetch.ReadError):
                await web.read("https://example.com/large", limit=6)
        finally:
            await real_session.close()

    async def test_text_only_reading_has_no_extra_model_call(self):
        context = types.SimpleNamespace(llm_generate=AsyncMock())
        web = types.SimpleNamespace(read=AsyncMock())
        engine = media.Understanding(context, web, {"max_images": 8})
        page = fetch.Page("https://example.com/a", text="x" * 24001, has_video=True)
        result = await engine.describe(page, "discord:GroupMessage:1", ROOT)
        self.assertIn("24000", result)
        self.assertIn("未讀取任何影片畫面", result)
        context.llm_generate.assert_not_called()
        web.read.assert_not_called()

    async def test_threads_preview_is_partial_and_matches_target(self):
        html = '<meta property="og:url" content="https://www.threads.com/@a/post/target"><meta property="og:description" content="public preview"><meta property="og:image" content="https://example.com/avatar.jpg">'
        page = fetch.threads_preview("https://www.threads.net/@a/post/target", html)
        self.assertEqual(page.text, "public preview")
        self.assertEqual(page.images, [])
        self.assertIn("公開預覽", page.notes[0])
        with self.assertRaises(fetch.ReadError):
            fetch.threads_preview("https://www.threads.com/@a/post/wrong", html)

    async def test_dns_private_address_is_rejected_at_connector(self):
        resolver = fetch.PublicResolver()
        try:
            with patch.object(
                fetch.DefaultResolver,
                "resolve",
                AsyncMock(return_value=[{"host": "192.168.1.2"}]),
            ):
                with self.assertRaises(fetch.ReadError):
                    await resolver.resolve("example.com")
        finally:
            await resolver.close()

    async def test_redirect_to_internal_address_never_makes_second_request(self):
        web = fetch.Web({})
        real_session = web.session

        class Response:
            status = 302
            headers = {"Location": "http://169.254.169.254/latest/meta-data/"}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        session = types.SimpleNamespace(get=unittest.mock.Mock(return_value=Response()))
        web.session = session
        try:
            with self.assertRaises(fetch.ReadError):
                await web.read("https://example.com/redirect")
            self.assertEqual(session.get.call_count, 1)
        finally:
            await real_session.close()

    async def test_cookies_never_go_to_media_or_third_party(self):
        web = fetch.Web({"bilibili.com": "secret=1", "threads.com": "session=2"})
        try:
            self.assertEqual(
                web.headers("https://api.bilibili.com/x")["Cookie"], "secret=1"
            )
            for url in (
                "https://api.fxtwitter.com/status/1",
                "https://x.bilivideo.com/a",
                "https://bilibili.com.attacker.example",
            ):
                self.assertNotIn("Cookie", web.headers(url))
        finally:
            await web.close()

    async def test_twitter_text_images_video_and_wrong_id(self):
        payload = {
            "tweet": {
                "id": "123",
                "text": "貼文",
                "author": {"screen_name": "alice"},
                "quote": {"text": "引用"},
                "media": {
                    "photos": [{"url": "https://pbs.twimg.com/a.jpg"}],
                    "videos": [{"url": "https://video.twimg.com/a.mp4"}],
                },
            }
        }
        web = types.SimpleNamespace(json=AsyncMock(return_value=payload))
        page = await fetch.Reader(web).twitter("https://x.com/alice/status/123")
        self.assertIn("引用", page.text)
        self.assertEqual(len(page.images), 1)
        self.assertTrue(page.has_video)
        with self.assertRaises(fetch.ReadError):
            await fetch.Reader(web).twitter("https://x.com/alice/status/456")

    async def test_bilibili_metadata_only_never_requests_stream(self):
        web = types.SimpleNamespace(
            json=AsyncMock(
                side_effect=[
                    {
                        "code": 0,
                        "data": {
                            "title": "test",
                            "desc": "簡介",
                            "pic": "https://i.hdslb.com/cover.jpg",
                        },
                    }
                ]
            )
        )
        page = await fetch.Reader(web).bilibili(
            "https://www.bilibili.com/video/BVtest?p=2"
        )
        self.assertEqual(web.json.call_count, 1)
        self.assertTrue(page.has_video)
        self.assertEqual(page.text, "簡介")
        self.assertIn("封面", page.notes[0])

    async def test_threads_exact_post_in_browser(self):
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            options = {"headless": True}
            if os.environ.get("LINK_CONTEXT_TEST_BROWSER"):
                options["executable_path"] = os.environ["LINK_CONTEXT_TEST_BROWSER"]
            browser = await pw.chromium.launch(**options)
            try:
                page = await browser.new_page()
                data = [
                    {
                        "code": "wrong",
                        "user": {"username": "wrong"},
                        "caption": {"text": "不可混入"},
                    },
                    {
                        "code": "target",
                        "user": {"username": "author"},
                        "caption": {"text": "目標正文"},
                        "image_versions2": {
                            "candidates": [{"url": "https://example.com/p.jpg"}]
                        },
                    },
                ]
                await page.set_content(
                    '<script type="application/json">' + json.dumps(data) + "</script>"
                )
                result = await page.evaluate(fetch.THREADS_POST, "target")
                self.assertEqual(result["text"], "目標正文")
                self.assertEqual(result["images"], ["https://example.com/p.jpg"])
                self.assertIsNone(await page.evaluate(fetch.THREADS_POST, "missing"))
            finally:
                await browser.close()

    async def test_bilibili_post_text_images_and_quoted_post(self):
        item = {
            "id_str": "123",
            "modules": {
                "module_author": {"name": "作者"},
                "module_dynamic": {
                    "desc": {"text": "正文"},
                    "major": {"draw": {"items": [{"src": "//i.hdslb.com/image.jpg"}]}},
                },
            },
            "orig": {
                "modules": {
                    "module_author": {"name": "原作者"},
                    "module_dynamic": {"desc": {"text": "引用內容"}},
                }
            },
        }
        web = types.SimpleNamespace(
            json=AsyncMock(return_value={"code": 0, "data": {"item": item}})
        )
        page = await fetch.Reader(web).read("https://t.bilibili.com/123")
        self.assertIn("引用內容", page.text)
        self.assertEqual(page.author, "作者")
        self.assertEqual(page.images, ["https://i.hdslb.com/image.jpg"])

    async def test_real_image_decode_and_video_not_downloaded(self):
        work = Path(tempfile.mkdtemp(prefix="check-", dir=ROOT))
        try:
            from PIL import Image

            fixture = work / "fixture.png"
            Image.new("RGB", (2000, 1000), "red").save(fixture)

            class FixtureWeb:
                calls = []

                async def read(self, url, *, destination, limit):
                    self.calls.append(url)
                    destination.write_bytes(fixture.read_bytes())

            web = FixtureWeb()

            async def vision(**kwargs):
                self.assertEqual(kwargs["chat_provider_id"], "existing-openai")
                self.assertGreater(len(kwargs["image_urls"]), 0)
                with Image.open(kwargs["image_urls"][0]) as frame:
                    self.assertEqual(frame.width, 1280)
                    red, green, blue = frame.convert("RGB").getpixel((10, 10))
                    self.assertGreater(red, green + 100)
                return types.SimpleNamespace(completion_text="紅色畫面")

            context = types.SimpleNamespace(llm_generate=vision)
            engine = media.Understanding(
                context, web, {"vision_provider_id": "existing-openai"}
            )
            page = fetch.Page(
                "https://example.com/post",
                images=["https://example.com/image.png"],
                has_video=True,
            )
            content = await engine.describe(page, "group", work)
            self.assertEqual(web.calls, ["https://example.com/image.png"])
            self.assertIn("紅色畫面", content)
            self.assertIn("未讀取任何影片畫面", content)
        finally:
            for path in work.iterdir():
                path.unlink()
            work.rmdir()

    async def test_external_error_does_not_leak_secret(self):
        self.assertNotIn("api-key", media.safe_failure(RuntimeError("api-key=secret")))

    async def test_plugin_silent_background_injection_and_group_isolation(self):
        import logging

        work = Path(tempfile.mkdtemp(prefix="check-", dir=ROOT))
        names = [
            "astrbot",
            "astrbot.api",
            "astrbot.api.event",
            "astrbot.api.message_components",
            "astrbot.api.provider",
            "astrbot.api.star",
            "astrbot.core",
            "astrbot.core.agent",
            "astrbot.core.agent.message",
        ]
        modules = {name: types.ModuleType(name) for name in names}
        modules["astrbot.api"].AstrBotConfig = dict
        modules["astrbot.api"].logger = logging.getLogger("link_context_tests")

        handler_priorities = {}

        def decorator(*args, **kwargs):
            def register(function):
                handler_priorities[function.__name__] = kwargs.get("priority", 0)
                return function

            return register

        modules["astrbot.api.event"].filter = types.SimpleNamespace(
            command=decorator,
            event_message_type=decorator,
            on_llm_request=decorator,
            llm_tool=decorator,
            EventMessageType=types.SimpleNamespace(GROUP_MESSAGE="group"),
        )
        modules["astrbot.api.event"].AstrMessageEvent = object
        modules["astrbot.api.provider"].ProviderRequest = object

        class At:
            def __init__(self, qq):
                self.qq = qq

        modules["astrbot.api.message_components"].At = At

        class Star:
            def __init__(self, context):
                self.context = context

        class Part:
            def __init__(self, text):
                self.text = text

            def mark_as_temp(self):
                self.temporary = True
                return self

        modules["astrbot.api.star"].Star = Star
        modules["astrbot.api.star"].Context = object
        modules["astrbot.api.star"].StarTools = types.SimpleNamespace(
            get_data_dir=lambda _: work
        )
        modules["astrbot.core.agent.message"].TextPart = Part
        plugin = None
        try:
            with patch.dict(sys.modules, modules):
                main = importlib.import_module(PACKAGE + ".main")
                config = {
                    key: value["default"]
                    for key, value in json.loads(
                        (ROOT / "_conf_schema.json").read_text(encoding="utf-8")
                    ).items()
                }
                plugin = main.LinkContextPlugin(object(), config)
                await plugin.initialize()
                plugin.reader.read = AsyncMock(
                    return_value=fetch.Page("https://example.com/a", text="正文")
                )
                event = types.SimpleNamespace(
                    unified_msg_origin="discord-main:GroupMessage:111",
                    message_str="https://example.com/a",
                    is_at_or_wake_command=False,
                    _has_send_oper=False,
                    get_sender_id=lambda: "user",
                    get_self_id=lambda: "bot",
                    get_sender_name=lambda: "Alice",
                    get_messages=lambda: [],
                )

                async def builtin_group_chat(incoming):
                    request = types.SimpleNamespace(
                        system_prompt="persona", extra_user_content_parts=[]
                    )
                    await plugin.inject(incoming, request)
                    self.assertTrue(
                        request.extra_user_content_parts,
                        "Group chat started before link reading was queued",
                    )
                    self.assertIn(
                        '"state": "pending"', request.extra_user_content_parts[0].text
                    )

                # AstrBot 4.29.4 runs handlers sequentially, highest priority first;
                # its built-in group-chat handler uses sys.maxsize - 2.
                handlers = [
                    (sys.maxsize - 2, builtin_group_chat),
                    (handler_priorities["observe"], plugin.observe),
                ]
                # No send/yield/plain_result methods exist: accidental forwarding fails.
                for _, handler in sorted(handlers, key=lambda item: -item[0]):
                    self.assertIsNone(await handler(event))
                self.assertFalse(event.is_at_or_wake_command)
                self.assertFalse(event._has_send_oper)
                await asyncio.wait_for(plugin.queue.join(), 3)
                await plugin.observe(event)
                self.assertEqual(plugin.reader.read.call_count, 1)
                req = types.SimpleNamespace(
                    system_prompt="persona", extra_user_content_parts=[]
                )
                await plugin.inject(event, req)
                self.assertIn("正文", req.extra_user_content_parts[0].text)
                self.assertTrue(req.extra_user_content_parts[0].temporary)

                # Only an explicit mention of this bot waits for this message's URLs.
                mention = types.SimpleNamespace(**vars(event))
                mention.message_str = "https://example.com/mentioned"
                mention.get_messages = lambda: [At("bot")]
                started, release = asyncio.Event(), asyncio.Event()

                async def delayed_read(url):
                    started.set()
                    await release.wait()
                    return fetch.Page(url, text="等到的新內容")

                with patch.object(plugin.reader, "read", side_effect=delayed_read):
                    await plugin.observe(mention)
                    await asyncio.wait_for(started.wait(), 3)
                    other_mention = types.SimpleNamespace(**vars(mention))
                    other_mention.get_messages = lambda: [At("another-user")]
                    immediate_req = types.SimpleNamespace(
                        system_prompt="", extra_user_content_parts=[]
                    )
                    await asyncio.wait_for(
                        plugin.inject(other_mention, immediate_req), 1
                    )
                    self.assertIn(
                        '"state": "pending"',
                        immediate_req.extra_user_content_parts[0].text,
                    )
                    waited_req = types.SimpleNamespace(
                        system_prompt="persona", extra_user_content_parts=[]
                    )
                    waiting = asyncio.create_task(plugin.inject(mention, waited_req))
                    await asyncio.sleep(0.02)
                    self.assertFalse(
                        waiting.done(),
                        "Mentioned link returned before reading finished",
                    )
                    release.set()
                    await asyncio.wait_for(waiting, 3)
                    self.assertIn(
                        "等到的新內容", waited_req.extra_user_content_parts[0].text
                    )
                    await asyncio.wait_for(plugin.queue.join(), 3)

                # Timeout stops waiting, but leaves the background job running.
                started.clear()
                release.clear()
                mention.message_str = "https://example.com/slow"
                with patch.object(plugin.reader, "read", side_effect=delayed_read):
                    await plugin.observe(mention)
                    await asyncio.wait_for(started.wait(), 3)
                    timeout_req = types.SimpleNamespace(
                        system_prompt="", extra_user_content_parts=[]
                    )
                    with patch.object(main, "LINK_WAIT_SECONDS", 0.03):
                        await asyncio.wait_for(plugin.inject(mention, timeout_req), 1)
                    self.assertIn(
                        '"state": "pending"',
                        timeout_req.extra_user_content_parts[0].text,
                    )
                    self.assertFalse(plugin.worker.done())
                    release.set()
                    await asyncio.wait_for(plugin.queue.join(), 3)
                    self.assertEqual(
                        plugin.store.state(
                            mention.unified_msg_origin, mention.message_str
                        ),
                        "ready",
                    )

                # Dispatch the real command before observe()/chat, as AstrBot does.
                command_event = types.SimpleNamespace(
                    **vars(event),
                    get_group_id=lambda: "111",
                    stopped=False,
                    plain_result=lambda text: text,
                )
                command_event.stop_event = lambda: setattr(
                    command_event, "stopped", True
                )

                async def dispatch_reread(url):
                    command_event.stopped = False
                    command_event.message_str = f"/link_reread {url}"
                    replies = []
                    for _, handler in sorted(
                        [
                            (handler_priorities["reread"], plugin.reread),
                            (handler_priorities["observe"], plugin.observe),
                            (sys.maxsize - 2, builtin_group_chat),
                        ],
                        key=lambda item: -item[0],
                    ):
                        if command_event.stopped:
                            break
                        if handler == plugin.reread:
                            replies.extend(
                                [reply async for reply in handler(command_event, url)]
                            )
                        else:
                            await handler(command_event)
                    self.assertTrue(command_event.stopped)
                    self.assertEqual(len(replies), 1)
                    return replies[0]

                url = event.message_str
                # A record outside the recent-20 list must still be refreshable.
                for i in range(21):
                    plugin.store.put(
                        event.unified_msg_origin,
                        f"https://example.com/{i}",
                        "Alice",
                        "ready",
                        "old",
                    )
                self.assertNotIn(
                    url,
                    [row[0] for row in plugin.store.recent(event.unified_msg_origin)],
                )
                for invalid in ("", "http://127.0.0.1/a", "not-a-url"):
                    self.assertIn("用法", await dispatch_reread(invalid))
                    self.assertTrue(plugin.queue.empty())

                # Queue capacity failure must not discard a completed record.
                with patch.object(plugin.queue, "full", return_value=True):
                    self.assertIn("舊記錄仍保留", await dispatch_reread(url))
                self.assertEqual(
                    plugin.store.state(event.unified_msg_origin, url), "ready"
                )

                # Block the fetch boundary to exercise duplicate requests in flight.
                started, release = asyncio.Event(), asyncio.Event()

                async def refreshed(_):
                    started.set()
                    await release.wait()
                    return fetch.Page(url, text="重新分析的新內容")

                with patch.object(
                    plugin.reader, "read", side_effect=refreshed
                ) as reader:
                    self.assertIn("已排入", await dispatch_reread(f"<{url}>"))
                    self.assertEqual(plugin.queue.qsize(), 1)
                    self.assertEqual(
                        plugin.store.state(event.unified_msg_origin, url), "pending"
                    )
                    await asyncio.wait_for(started.wait(), 3)
                    self.assertIn("沒有重複", await dispatch_reread(url))
                    self.assertTrue(plugin.queue.empty())
                    release.set()
                    await asyncio.wait_for(plugin.queue.join(), 3)
                    reader.assert_awaited_once()
                self.assertIn(
                    "重新分析的新內容",
                    plugin.store.context(event.unified_msg_origin, 24, 18000),
                )

                command_event.unified_msg_origin = "discord-main:GroupMessage:other"
                self.assertIn("沒有", await dispatch_reread(url))
                self.assertTrue(plugin.queue.empty())
                self.assertIsNone(
                    plugin.store.state(command_event.unified_msg_origin, url)
                )
                command_event.unified_msg_origin = event.unified_msg_origin
                with patch.object(
                    plugin.store, "put", side_effect=sqlite3.OperationalError("busy")
                ):
                    self.assertIn("沒有排入", await dispatch_reread(url))
                self.assertTrue(plugin.queue.empty())
                self.assertEqual(
                    plugin.store.state(event.unified_msg_origin, url), "ready"
                )
                command_event.get_group_id = lambda: ""
                self.assertIn("群組", await dispatch_reread(url))

                plugin.store.finish(
                    event.unified_msg_origin, event.message_str, "ready", "x" * 15000
                )
                integer_page = await plugin.read_link_context(
                    event, event.message_str, 12000
                )
                self.assertEqual(
                    integer_page,
                    await plugin.read_link_context(event, event.message_str, 12000.0),
                )
                self.assertEqual(len(json.loads(integer_page)["content"]), 3000)
                self.assertIsNone(json.loads(integer_page)["next_offset"])
                for invalid in (-1, 0.5, True, float("nan"), float("inf"), "0"):
                    self.assertIn(
                        "非負整數",
                        await plugin.read_link_context(
                            event, event.message_str, invalid
                        ),
                    )

                with patch.object(
                    plugin.store, "prune", side_effect=sqlite3.OperationalError("busy")
                ):
                    await plugin.observe(event)
                unchanged = types.SimpleNamespace(
                    system_prompt="persona", extra_user_content_parts=[]
                )
                with patch.object(
                    plugin.store,
                    "context",
                    side_effect=sqlite3.OperationalError("busy"),
                ):
                    await plugin.inject(event, unchanged)
                self.assertEqual(unchanged.system_prompt, "persona")
                self.assertEqual(unchanged.extra_user_content_parts, [])
                with patch.object(
                    plugin.store, "recent", side_effect=sqlite3.OperationalError("busy")
                ):
                    self.assertIn(
                        "暫時不可用",
                        await plugin.read_link_context(event, event.message_str),
                    )

                # Distinct channel, thread and bot-instance UMO values must not share context.
                for scope in (
                    "discord-main:GroupMessage:222",
                    "discord-main:GroupMessage:333",
                    "discord-other:GroupMessage:111",
                ):
                    event.unified_msg_origin = scope
                    other = types.SimpleNamespace(
                        system_prompt="persona", extra_user_content_parts=[]
                    )
                    await plugin.inject(event, other)
                    self.assertEqual(other.extra_user_content_parts, [])
                    self.assertIn(
                        "沒有",
                        await plugin.read_link_context(event, "https://example.com/a"),
                    )

                faults = [
                    patch.object(
                        main.tempfile,
                        "mkdtemp",
                        side_effect=PermissionError("work directory unavailable"),
                    ),
                    patch.object(
                        Path,
                        "rmdir",
                        side_effect=PermissionError("cleanup unavailable"),
                    ),
                    patch.object(
                        plugin.store,
                        "finish",
                        side_effect=sqlite3.OperationalError("disk unavailable"),
                    ),
                ]
                for index, fault in enumerate(faults):
                    with self.subTest(background_failure=index):
                        event.message_str = f"https://example.com/failure-{index}"
                        with fault:
                            await plugin.observe(event)
                            await asyncio.wait_for(plugin.queue.join(), 3)
                        self.assertFalse(plugin.worker.done())
                        if index == 0:
                            self.assertEqual(
                                plugin.store.recent(event.unified_msg_origin)[0][3],
                                "failed",
                            )
                        event.message_str = f"https://example.com/recovery-{index}"
                        await plugin.observe(event)
                        await asyncio.wait_for(plugin.queue.join(), 3)
                        self.assertEqual(
                            plugin.store.recent(event.unified_msg_origin)[0][3], "ready"
                        )
        finally:
            if plugin:
                await plugin.terminate()
            for path in work.iterdir():
                if path.is_dir():
                    path.rmdir()  # Empty work directory left by the simulated cleanup failure.
                else:
                    path.unlink()
            work.rmdir()


if __name__ == "__main__":
    unittest.main()
