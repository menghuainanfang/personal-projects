import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
import app

class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_data = app.DATA
        app.DATA = Path(self.temp.name)
        self.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        app.DATA = self.old_data
        self.temp.cleanup()

    def request(self, path, body=None):
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            return response.read().decode("utf-8-sig")

    def test_import_edit_reimport_export_and_settings(self):
        data = {"name": "posts.csv", "text": 'id,发布时间,内容,点赞数,浏览数,图片数\na,2021-09-18 20:00:00,生日,30,200,2\n'}
        self.assertEqual(json.loads(self.request("/api/import", data))["added"], 1)
        self.request("/api/topic", {"id": "a", "topic": "朋友与社交"})
        self.assertEqual(json.loads(self.request("/api/import", data))["added"], 0)
        saved = json.loads(self.request("/api/export?format=json"))
        self.assertEqual(saved["posts"][0]["topic"], "朋友与社交")
        self.assertEqual(saved["posts"][0]["rate"], 15)
        self.assertIn("30,200,2", self.request("/api/export?format=csv"))
        self.request("/api/settings", {**app.DEFAULT_SETTINGS, "min_views": 300, "events": [{"date": "06-07", "name": "高考"}]})
        report = json.loads(self.request("/api/analysis"))
        self.assertEqual(report["summary"]["valid"], 0)
        self.assertEqual(json.loads((app.DATA / "workspace.json").read_text("utf-8"))["settings"]["min_views"], 300)

    def test_demo_does_not_write_real_data(self):
        demo = json.loads(self.request("/api/analysis?demo=1"))
        self.assertEqual(demo["total"], 300)
        self.assertEqual(json.loads(self.request("/api/state"))["total"], 0)
        self.assertFalse((app.DATA / "workspace.json").exists())

    def test_public_defaults_have_no_personal_profile(self):
        settings = json.loads(self.request("/api/state"))["settings"]
        self.assertEqual((settings["start"], settings["end"], settings["birthday"]), ("", "", ""))
        self.assertEqual(settings["events"], [])

if __name__ == "__main__":
    unittest.main()
