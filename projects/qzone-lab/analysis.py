"""Normalization and descriptive analysis for personal Qzone posts."""
import csv
import io
import json
import math
import random
import re
import statistics
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
DEFAULT_SETTINGS = {"start": "", "end": "", "birthday": "", "events": [], "min_views": 1}
TOPICS = {
    "校园与学习": ["考试", "高考", "作业", "老师", "上课", "学校", "数学", "学习", "毕业", "宿舍"],
    "朋友与社交": ["朋友", "同学", "聚会", "合照", "兄弟", "姐妹", "一起", "友谊"],
    "情绪与感想": ["难过", "开心", "焦虑", "emo", "想念", "孤独", "心情", "人生", "遗憾", "希望"],
    "日常与美食": ["吃", "火锅", "奶茶", "早餐", "晚饭", "午饭", "日常", "猫", "狗"],
    "旅行与风景": ["旅行", "旅游", "风景", "日落", "海边", "爬山", "夕阳", "出游", "城市"],
    "兴趣与娱乐": ["游戏", "电影", "音乐", "动漫", "篮球", "足球", "演唱会", "追剧", "运动"],
    "生日与纪念": ["生日", "周年", "纪念", "快乐", "新年", "圣诞", "节日"],
}
# Calendar festivals, not statutory days off.
FIXED_EVENTS = {"01-01": "元旦", "02-14": "情人节", "05-01": "劳动节", "06-01": "儿童节", "09-10": "教师节", "10-01": "国庆节", "12-25": "圣诞节"}
LUNAR_EVENTS = {
    "2018": ["02-16", "06-18", "09-24"], "2019": ["02-05", "06-07", "09-13"],
    "2020": ["01-25", "06-25", "10-01"], "2021": ["02-12", "06-14", "09-21"],
    "2022": ["02-01", "06-03", "09-10"], "2023": ["01-22", "06-22", "09-29"],
    "2024": ["02-10", "06-10", "09-17"], "2025": ["01-29", "05-31", "10-06"],
    "2026": ["02-17", "06-19", "09-25"],
}

def first(row, *keys):
    for key in keys:
        if key in row and row[key] is not None and row[key] != "":
            return row[key]
    return None

def number(value):
    if value is None or value == "" or isinstance(value, (list, dict, bool)):
        return None
    try:
        n = float(str(value).replace(",", ""))
        return int(n) if math.isfinite(n) and n >= 0 and n.is_integer() else None
    except (ValueError, TypeError):
        return None

def parse_date(value):
    if value is None:
        raise ValueError("缺少发布时间")
    if isinstance(value, (int, float)) or re.fullmatch(r"\d{10,13}", str(value)):
        t = float(value)
        return datetime.fromtimestamp(t / 1000 if t > 1e11 else t, TZ).isoformat()
    s = str(value).strip().replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-")
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (d.replace(tzinfo=TZ) if d.tzinfo is None else d.astimezone(TZ)).isoformat()

def classify(text):
    scores = {topic: sum(word in text.lower() for word in words) for topic, words in TOPICS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "待分类"

def normalize(row, source="import"):
    published = parse_date(first(row, "published_at", "created_time", "timestamp", "createTime", "created_at", "时间", "发布时间"))
    text = str(first(row, "text", "custom_content", "content", "con", "内容", "正文") or "")
    images = first(row, "images", "custom_images", "pic", "pictures")
    image_count = number(first(row, "image_count", "pictotal", "imagetotal", "图片数"))
    if image_count is None and isinstance(images, list):
        image_count = len(images)
    if image_count is None:
        has = first(row, "has_image", "带图片")
        if has in (True, 1, "true", "1", "是", "有"):
            image_count = 1
        elif has in (False, 0, "false", "0", "否", "无"):
            image_count = 0
    likes = number(first(row, "like_count", "likeCount", "likeTotal", "赞数", "点赞数"))
    if likes is None:
        likes = number(row.get("likes"))
    if likes is None and isinstance(row.get("like"), dict):
        likes = number(first(row["like"], "total_number", "total", "count"))
    views = number(first(row, "views", "view_count", "readCount", "readcount", "浏览数", "观看数"))
    if views is None and isinstance(row.get("custom_visitor"), dict):
        views = number(row["custom_visitor"].get("viewCount"))
    topic = str(first(row, "topic", "主题", "题材") or classify(text))
    # Without a source ID, exact date and text identify a repeated import.
    identity = str(first(row, "id", "tid", "cur_key") or (published + "|" + text))
    return {"id": identity, "published_at": published, "text": text, "likes": likes, "views": views,
            "image_count": image_count, "topic": topic, "topic_manual": bool(row.get("topic_manual") or first(row, "topic", "主题", "题材")),
            "source": row.get("source", source), "captured_at": row.get("captured_at") or datetime.now(TZ).isoformat()}

def unwrap(value):
    if isinstance(value, list):
        for item in value:
            yield from unwrap(item)
    elif isinstance(value, dict):
        if first(value, "published_at", "created_time", "timestamp", "createTime", "created_at", "时间", "发布时间") is not None:
            yield value
        else:
            for key in ("posts", "msglist", "data", "messages", "list", "items"):
                if key in value:
                    yield from unwrap(value[key])

def decode_json(text):
    text = text.strip().lstrip("\ufeff")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.fullmatch(r"[\w.]+\s*\((.*)\)\s*;?", text, re.S)
        if match:
            return json.loads(match.group(1))
        raise ValueError("文件不是有效的 JSON / JSONP")

def import_text(text, name):
    if name.lower().endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))
    else:
        obj = decode_json(text)
        if isinstance(obj, dict) and "log" in obj:  # Browser HAR export
            rows = []
            for entry in obj["log"].get("entries", []):
                if "emotion_cgi_msglist" not in entry.get("request", {}).get("url", ""):
                    continue
                content = entry.get("response", {}).get("content", {})
                payload = content.get("text", "")
                if content.get("encoding") == "base64":
                    import base64
                    payload = base64.b64decode(payload).decode("utf-8")
                try:
                    rows.extend(unwrap(decode_json(payload)))
                except ValueError:
                    continue
        else:
            rows = list(unwrap(obj))
    posts, errors = [], []
    for index, row in enumerate(rows, 1):
        try:
            posts.append(normalize(row, name))
        except (ValueError, TypeError, OverflowError, OSError) as e:
            errors.append(f"第 {index} 条：{e}")
    if not rows:
        raise ValueError("没有识别到动态。请导入说说 JSON、浏览器 HAR 或模板 CSV；至少需要发布时间列。")
    return posts, errors

def merge_posts(old, new):
    result = {p["id"]: dict(p) for p in old}
    for p in new:
        previous = result.get(p["id"], {})
        merged = {**previous, **{k: v for k, v in p.items() if v is not None}}
        if previous.get("topic_manual"):
            merged.update(topic=previous["topic"], topic_manual=True)
        result[p["id"]] = merged
    return sorted(result.values(), key=lambda p: p["published_at"], reverse=True)

def event_names(day, settings):
    events = []
    md = day[5:10]
    if md == settings.get("birthday"):
        events.append("生日")
    if md in FIXED_EVENTS:
        events.append(FIXED_EVENTS[md])
    for date, name in zip(LUNAR_EVENTS.get(day[:4], []), ["春节", "端午", "中秋"]):
        if md == date:
            events.append(name)
    for e in settings.get("events", []):
        if e.get("date") in (day[:10], md):
            events.append(e["name"])
    return events

def rate(p, min_views=1):
    if p.get("likes") is None or p.get("views") is None or p["views"] < max(1, min_views):
        return None
    return 100 * p["likes"] / p["views"]

def summarize(posts, min_views=1):
    valid = [p for p in posts if rate(p, min_views) is not None]
    ls = [p["likes"] for p in posts if p.get("likes") is not None]
    vs = [p["views"] for p in posts if p.get("views") is not None]
    rates = [rate(p, min_views) for p in valid]
    return {"n": len(posts), "valid": len(valid), "median_likes": statistics.median(ls) if ls else None,
            "median_views": statistics.median(vs) if vs else None, "median_rate": statistics.median(rates) if rates else None,
            "pooled_rate": 100 * sum(p["likes"] for p in valid) / sum(p["views"] for p in valid) if valid else None}

def groups(posts, key, min_views):
    grouped = {}
    for p in posts:
        grouped.setdefault(str(key(p)), []).append(p)
    return [{"name": name, **summarize(ps, min_views)} for name, ps in sorted(grouped.items())]

def adjusted_comparison(posts, dimension, settings):
    """Within-year differences versus other posts, averaged over overlapping years."""
    threshold = settings.get("min_views", 1)
    labels = sorted(set(dimension(p) for p in posts))
    years = sorted(set(p["published_at"][:4] for p in posts))
    rows = []
    for label in labels:
        strata = []
        for year in years:
            ps = [p for p in posts if p["published_at"].startswith(year) and rate(p, threshold) is not None]
            a = [rate(p, threshold) for p in ps if dimension(p) == label]
            b = [rate(p, threshold) for p in ps if dimension(p) != label]
            if len(a) >= 3 and len(b) >= 3:
                strata.append((year, a, b))
        if not strata:
            rows.append({"name": label, "difference": None, "ci": None, "years": [], "n": 0})
            continue
        def difference(samples):
            weights = [min(len(a), len(b)) for _, a, b in samples]
            return sum(w * (statistics.mean(a) - statistics.mean(b)) for w, (_, a, b) in zip(weights, samples)) / sum(weights)
        rng = random.Random(42)
        estimates = sorted(difference([(y, rng.choices(a, k=len(a)), rng.choices(b, k=len(b))) for y, a, b in strata]) for _ in range(500))
        rows.append({"name": label, "difference": difference(strata), "ci": [estimates[12], estimates[487]],
                     "years": [y for y, _, _ in strata], "n": sum(len(a) for _, a, _ in strata)})
    return rows

def analyze(posts, settings, filters):
    start, end = filters.get("start", ""), filters.get("end", "")
    topic, search = filters.get("topic", ""), filters.get("search", "").lower()
    chosen = [p for p in posts if (not start or p["published_at"][:10] >= start)
              and (not end or p["published_at"][:10] <= end) and (not topic or p["topic"] == topic)
              and (not search or search in p["text"].lower())]
    threshold = settings.get("min_views", 1)
    image = lambda p: "图片未知" if p.get("image_count") is None else ("带图片" if p["image_count"] else "无图片")
    def events(p):
        return event_names(p["published_at"], settings)
    summary = summarize(chosen, threshold)
    summary.update(missing_likes=sum(p.get("likes") is None for p in chosen), missing_views=sum(p.get("views") is None for p in chosen),
                   anomalous=sum(p.get("likes") is not None and p.get("views") is not None and p["likes"] > p["views"] for p in chosen))
    return {"summary": summary, "topics": groups(chosen, lambda p: p["topic"], threshold),
            "years": groups(chosen, lambda p: p["published_at"][:4], threshold), "images": groups(chosen, image, threshold),
            "hours": groups(chosen, lambda p: datetime.fromisoformat(p["published_at"]).strftime("%H"), threshold),
            "weekdays": groups(chosen, lambda p: ["一", "二", "三", "四", "五", "六", "日"][datetime.fromisoformat(p["published_at"]).weekday()], threshold),
            "events": groups(chosen, lambda p: "生日" if "生日" in events(p) else ("节日 / 纪念日" if events(p) else "普通日"), threshold),
            "adjusted": adjusted_comparison(chosen, lambda p: p["topic"], settings),
            "adjusted_images": adjusted_comparison([p for p in chosen if p.get("image_count") is not None], image, settings),
            "posts": [{**p, "rate": rate(p, threshold), "events": events(p)} for p in chosen],
            "all_topics": sorted(set(p["topic"] for p in posts) | set(TOPICS) | {"待分类"}), "total": len(posts)}

def demo_posts():
    rng = random.Random(19)
    posts = []
    for i in range(300):
        date = datetime(2018, 1, 1, tzinfo=TZ) + timedelta(days=rng.randrange(3100), hours=rng.randrange(24))
        topic = rng.choice(list(TOPICS))
        views = rng.randrange(30, 800)
        likes = int(views * rng.uniform(.015, .16))
        posts.append(normalize({"id": f"demo-{i}", "published_at": date.isoformat(), "text": f"虚构样例 · {topic} · 第 {i + 1} 条", "likes": likes if i % 19 else None, "views": views if i % 17 else None, "image_count": rng.randrange(5), "topic": topic}, "demo"))
    return sorted(posts, key=lambda p: p["published_at"], reverse=True)
