"""Run: python -m unittest discover -s . -p 'test_*.py' -v.

Network/model boundaries are replaced; browser execution and image decoding are real.
"""

import asyncio
import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent
PACKAGE = "link_context_under_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package
fetch = importlib.import_module(PACKAGE + ".fetch")
media = importlib.import_module(PACKAGE + ".media")
Store = importlib.import_module(PACKAGE + ".store").Store


class Files(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="check-", dir=ROOT))

    def tearDown(self):
        for path in self.work.iterdir():
            if path.is_file():
                path.unlink()
        self.work.rmdir()


class ParsingTests(Files):
    def test_url_boundary_and_deduplication(self):
        for url in ("http://127.0.0.1/", "http://[::1]/", "http://10.0.0.1/", "file:///etc/passwd", "https://user:secret@example.com/", "https://example.com:22/", "http://localhost/", "http://box.local/"):
            with self.subTest(url=url), self.assertRaises(fetch.ReadError):
                fetch.checked_url(url)
        self.assertEqual(fetch.links_in("看看 https://www.ptt.cc/bbs/Test/M.1.html。 https://www.ptt.cc/bbs/Test/M.1.html\n[文](https://example.com/a_(b))"),
                         ["https://www.ptt.cc/bbs/Test/M.1.html", "https://example.com/a_(b)"])
        self.assertFalse(fetch.host_is("https://bilibili.com.attacker.example", "bilibili.com"))

    def test_ptt_body_and_images(self):
        body = '<html><title>標題</title><nav>導覽</nav><div id="main-content">正文<img src="https://i.imgur.com/test.jpg"><div class="push">推文</div><script>evil()</script></div></html>'.encode()
        page = fetch.parse_html("https://www.ptt.cc/bbs/Test/M.1.html", body)
        self.assertIn("正文", page.text)
        self.assertIn("推文", page.text)
        self.assertNotIn("evil", page.text)
        self.assertNotIn("導覽", page.text)
        self.assertEqual(page.images, ["https://i.imgur.com/test.jpg"])

    def test_html_script_is_not_context_and_relative_media(self):
        page = fetch.parse_html("https://example.com/post/1", b'<html><body><article>hello<script>instructions</script><img src="/a.png"><video src="/v.mp4"></video></article></body></html>')
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
            with patch.object(fetch.DefaultResolver, "resolve", AsyncMock(return_value=[{"host": "192.168.1.2"}])):
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
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
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
            self.assertEqual(web.headers("https://api.bilibili.com/x")["Cookie"], "secret=1")
            for url in ("https://api.fxtwitter.com/status/1", "https://x.bilivideo.com/a", "https://bilibili.com.attacker.example"):
                self.assertNotIn("Cookie", web.headers(url))
        finally:
            await web.close()

    async def test_twitter_text_images_video_and_wrong_id(self):
        payload = {"tweet": {"id": "123", "text": "貼文", "author": {"screen_name": "alice"}, "quote": {"text": "引用"}, "media": {"photos": [{"url": "https://pbs.twimg.com/a.jpg"}], "videos": [{"url": "https://video.twimg.com/a.mp4"}]}}}
        web = types.SimpleNamespace(json=AsyncMock(return_value=payload))
        page = await fetch.Reader(web).twitter("https://x.com/alice/status/123")
        self.assertIn("引用", page.text)
        self.assertEqual(len(page.images), 1)
        self.assertTrue(page.has_video)
        with self.assertRaises(fetch.ReadError):
            await fetch.Reader(web).twitter("https://x.com/alice/status/456")

    async def test_bilibili_metadata_only_never_requests_stream(self):
        web = types.SimpleNamespace(json=AsyncMock(side_effect=[
            {"code": 0, "data": {"title": "test", "desc": "簡介", "pic": "https://i.hdslb.com/cover.jpg"}}
        ]))
        page = await fetch.Reader(web).bilibili("https://www.bilibili.com/video/BVtest?p=2")
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
                data = [{"code": "wrong", "user": {"username": "wrong"}, "caption": {"text": "不可混入"}},
                        {"code": "target", "user": {"username": "author"}, "caption": {"text": "目標正文"}, "image_versions2": {"candidates": [{"url": "https://example.com/p.jpg"}]}}]
                await page.set_content('<script type="application/json">' + json.dumps(data) + '</script>')
                result = await page.evaluate(fetch.THREADS_POST, "target")
                self.assertEqual(result["text"], "目標正文")
                self.assertEqual(result["images"], ["https://example.com/p.jpg"])
                self.assertIsNone(await page.evaluate(fetch.THREADS_POST, "missing"))
            finally:
                await browser.close()

    async def test_bilibili_post_text_images_and_quoted_post(self):
        item = {"id_str": "123", "modules": {"module_author": {"name": "作者"}, "module_dynamic": {"desc": {"text": "正文"}, "major": {"draw": {"items": [{"src": "//i.hdslb.com/image.jpg"}]}}}},
                "orig": {"modules": {"module_author": {"name": "原作者"}, "module_dynamic": {"desc": {"text": "引用內容"}}}}}
        web = types.SimpleNamespace(json=AsyncMock(return_value={"code": 0, "data": {"item": item}}))
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
            engine = media.Understanding(context, web, {"vision_provider_id": "existing-openai"})
            page = fetch.Page("https://example.com/post", images=["https://example.com/image.png"], has_video=True)
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
        names = ["astrbot", "astrbot.api", "astrbot.api.event", "astrbot.api.provider", "astrbot.api.star", "astrbot.core", "astrbot.core.agent", "astrbot.core.agent.message"]
        modules = {name: types.ModuleType(name) for name in names}
        modules["astrbot.api"].AstrBotConfig = dict
        modules["astrbot.api"].logger = logging.getLogger("link_context_tests")
        decorator = lambda *args, **kwargs: lambda function: function
        modules["astrbot.api.event"].filter = types.SimpleNamespace(
            event_message_type=decorator, on_llm_request=decorator, llm_tool=decorator,
            EventMessageType=types.SimpleNamespace(GROUP_MESSAGE="group"))
        modules["astrbot.api.event"].AstrMessageEvent = object
        modules["astrbot.api.provider"].ProviderRequest = object
        class Star:
            def __init__(self, context): self.context = context
        class Part:
            def __init__(self, text): self.text = text
            def mark_as_temp(self): self.temporary = True; return self
        modules["astrbot.api.star"].Star = Star
        modules["astrbot.api.star"].Context = object
        modules["astrbot.api.star"].StarTools = types.SimpleNamespace(get_data_dir=lambda _: work)
        modules["astrbot.core.agent.message"].TextPart = Part
        plugin = None
        try:
            with patch.dict(sys.modules, modules):
                main = importlib.import_module(PACKAGE + ".main")
                config = {key: value["default"] for key, value in json.loads((ROOT / "_conf_schema.json").read_text(encoding="utf-8")).items()}
                plugin = main.LinkContextPlugin(object(), config)
                await plugin.initialize()
                plugin.reader.read = AsyncMock(return_value=fetch.Page("https://example.com/a", text="正文"))
                event = types.SimpleNamespace(
                    unified_msg_origin="group-a", message_str="https://example.com/a",
                    get_sender_id=lambda: "user", get_self_id=lambda: "bot", get_sender_name=lambda: "Alice")
                # No send/yield/plain_result methods exist on this event: accidental forwarding fails.
                self.assertIsNone(await plugin.observe(event))
                await asyncio.wait_for(plugin.queue.join(), 3)
                await plugin.observe(event)
                self.assertEqual(plugin.reader.read.call_count, 1)
                req = types.SimpleNamespace(system_prompt="persona", extra_user_content_parts=[])
                await plugin.inject(event, req)
                self.assertIn("正文", req.extra_user_content_parts[0].text)
                self.assertTrue(req.extra_user_content_parts[0].temporary)
                event.unified_msg_origin = "group-b"
                other = types.SimpleNamespace(system_prompt="persona", extra_user_content_parts=[])
                await plugin.inject(event, other)
                self.assertEqual(other.extra_user_content_parts, [])
                self.assertIn("沒有", await plugin.read_link_context(event, "https://example.com/a"))
        finally:
            if plugin:
                await plugin.terminate()
            for path in work.iterdir():
                path.unlink()
            work.rmdir()


if __name__ == "__main__":
    unittest.main()
