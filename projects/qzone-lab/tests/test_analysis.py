import json
import unittest
from analysis import DEFAULT_SETTINGS, adjusted_comparison, analyze, event_names, import_text, merge_posts, normalize, summarize

def post(identity, date, likes, views, topic="日常", images=0):
    return normalize({"id": identity, "published_at": date, "text": "example", "likes": likes, "views": views, "topic": topic, "image_count": images})

class AnalysisTests(unittest.TestCase):
    def test_qzone_export_fields_use_totals(self):
        rows, errors = import_text(json.dumps({"data": [{"tid": "a", "created_time": 1631937600,
            "custom_content": "生日", "likeTotal": 30, "likes": [{"uin": 1}],
            "custom_visitor": {"viewCount": 200, "totalNum": 1, "list": [{"uin": 1}]}, "custom_images": [{}, {}]}]}), "backup.json")
        self.assertFalse(errors)
        self.assertEqual((rows[0]["likes"], rows[0]["views"], rows[0]["image_count"]), (30, 200, 2))
        self.assertEqual(rows[0]["published_at"][:10], "2021-09-18")

    def test_missing_and_zero_are_distinct(self):
        p = normalize({"created_time": 1631937600, "likes": [{"uin": 1}], "visitor": [1, 2]})
        self.assertIsNone(p["likes"])
        self.assertIsNone(p["views"])
        self.assertIsNone(p["image_count"])
        summary = summarize([p, post("zero", "2021-09-18", 0, 0), post("valid", "2021-09-18", 0, 100)])
        self.assertEqual(summary["valid"], 1)
        self.assertEqual(summary["median_rate"], 0)
        self.assertEqual(summary["pooled_rate"], 0)

    def test_duplicate_import_preserves_manual_topics_and_existing_counts(self):
        old = post("a", "2021-09-18", 10, 100, "人工主题")
        new = normalize({"id": "a", "created_time": 1631937600, "content": "生日", "like_count": 15})
        merged = merge_posts([old], [new, new])
        self.assertEqual(len(merged), 1)
        self.assertEqual((merged[0]["likes"], merged[0]["views"], merged[0]["topic"]), (15, 100, "人工主题"))

    def test_csv_quotes_and_invalid_rows(self):
        rows, errors = import_text('id,发布时间,内容,点赞数,浏览数,图片数\na,2021-09-18 20:00:00,"生日,快乐",0,100,0\nb,错误,坏时间,1,2,0\n', "posts.csv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "生日,快乐")
        self.assertEqual(len(errors), 1)

    def test_filters_include_end_of_day_and_birthday(self):
        posts = [post("a", "2024-12-31 23:59:59", 10, 100), post("b", "2025-01-01", 10, 100)]
        result = analyze(posts, DEFAULT_SETTINGS, {"start": "2021-01-01", "end": "2024-12-31"})
        self.assertEqual(result["summary"]["n"], 1)
        self.assertIn("生日", event_names("2021-09-18", {**DEFAULT_SETTINGS, "birthday": "09-18"}))
        self.assertIn("中秋", event_names("2021-09-21", DEFAULT_SETTINGS))
        self.assertNotIn("国庆节", event_names("2021-10-02", DEFAULT_SETTINGS))

    def test_pooled_rate_uses_only_complete_pairs(self):
        rows = [post("a", "2021-09-18", 20, 100), post("b", "2021-09-18", 10, 1000), post("c", "2021-09-18", None, 100000)]
        s = summarize(rows)
        self.assertAlmostEqual(s["pooled_rate"], 100 * 30 / 1100)
        self.assertAlmostEqual(s["median_rate"], 10.5)
        self.assertEqual(summarize(rows, 200)["valid"], 1)

    def test_within_year_comparison_recovers_simpson_reversal(self):
        rows = []
        # Topic A has a lower rate in both years but appears better overall.
        for year, topic, n, likes in [(2021, "A", 30, 80), (2021, "B", 3, 90), (2022, "A", 3, 10), (2022, "B", 30, 20)]:
            rows.extend(post(f"{year}-{topic}-{i}", f"{year}-09-18", likes, 100, topic) for i in range(n))
        a = summarize([p for p in rows if p["topic"] == "A"])["pooled_rate"]
        b = summarize([p for p in rows if p["topic"] == "B"])["pooled_rate"]
        self.assertGreater(a, b)
        adjusted = adjusted_comparison(rows, lambda p: p["topic"], DEFAULT_SETTINGS)
        self.assertAlmostEqual(adjusted[0]["difference"], -10)
        self.assertEqual(adjusted[0]["years"], ["2021", "2022"])
        self.assertTrue(all(x < 0 for x in adjusted[0]["ci"]))

    def test_har_import_only_extracts_message_responses(self):
        obj = {"log": {"entries": [{"request": {"url": "https://user.qzone.qq.com/emotion_cgi_msglist_v6?g_tk=secret"},
            "response": {"content": {"text": '_preloadCallback({"msglist":[{"tid":"a","created_time":1631937600,"content":"hi"}]});'}}}]}}
        rows, errors = import_text(json.dumps(obj), "capture.har")
        self.assertFalse(errors)
        self.assertEqual(len(rows), 1)
        self.assertNotIn("secret", json.dumps(rows))

if __name__ == "__main__":
    unittest.main()
