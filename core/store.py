"""Small persistent, source-isolated link history using the Python standard library."""

import json
import sqlite3
import time


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS links (
            scope TEXT NOT NULL, url TEXT NOT NULL, sender TEXT NOT NULL,
            seen REAL NOT NULL, state TEXT NOT NULL, content TEXT NOT NULL,
            PRIMARY KEY(scope, url))""")
        self.db.execute(
            "UPDATE links SET state='interrupted', content='上次讀取因重啟中斷，尚未取得完整內容。' WHERE state='pending'"
        )
        self.db.commit()

    def put(self, scope, url, sender, state, content):
        self.db.execute(
            "INSERT OR REPLACE INTO links VALUES (?, ?, ?, ?, ?, ?)",
            (scope, url, sender, time.time(), state, content),
        )
        self.db.commit()

    def finish(self, scope, url, state, content):
        self.db.execute(
            "UPDATE links SET state=?, content=? WHERE scope=? AND url=?",
            (state, content, scope, url),
        )
        self.db.commit()

    def recent(self, scope, hours=24):
        return self.db.execute(
            "SELECT url, sender, seen, state, content FROM links WHERE scope=? AND seen>? ORDER BY seen DESC LIMIT 20",
            (scope, time.time() - hours * 3600),
        ).fetchall()

    def has(self, scope, url, hours):
        row = self.db.execute(
            "SELECT state FROM links WHERE scope=? AND url=? AND seen>?",
            (scope, url, time.time() - hours * 3600),
        ).fetchone()
        return bool(row and row[0] in ("pending", "ready"))

    def prune(self, hours):
        self.db.execute("DELETE FROM links WHERE seen<?", (time.time() - hours * 3600,))
        self.db.commit()

    def context(self, scope, hours, budget):
        entries, used = [], 0
        for url, sender, seen, state, content in self.recent(scope, hours):
            entry = {
                "url": url,
                "shared_by": sender,
                "shared_at_unix": seen,
                "state": state,
                "content": content,
            }
            if len(content) > 6000:
                entry["content"] = (
                    content[:6000]
                    + "\n[此連結的上下文記錄已截斷，後段未提供給本輪模型]"
                )
            encoded = json.dumps(entry, ensure_ascii=False)
            if used + len(encoded) > budget:
                break
            entries.append(encoded)
            used += len(encoded)
        return "[\n" + ",\n".join(entries) + "\n]" if entries else ""

    def close(self):
        self.db.close()
