"""Read-only collection using a manually authenticated local browser."""
import time
from urllib.parse import urlencode
from analysis import decode_json, normalize, number, parse_date

BASE = "https://user.qzone.qq.com/proxy/domain/"
LIST = BASE + "taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6"
LIKES = BASE + "users.qzone.qq.com/cgi-bin/likes/get_like_list_app"
VIEWS = BASE + "g.qzone.qq.com/cgi-bin/friendshow/cgi_get_visitor_single"
DETAIL = BASE + "taotao.qq.com/cgi-bin/emotion_cgi_msgdetail_v6"

def gtk(key):
    h = 5381
    for c in key:
        h += (h << 5) + ord(c)
    return h & 0x7fffffff

def collect(options, status, cancel, save):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("采集需要 Playwright。请双击安装采集依赖.cmd，再重试。")
    with sync_playwright() as pw:
        # A fresh session keeps the user's regular browser profile untouched.
        browser = pw.chromium.launch(channel="msedge", headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://qzone.qq.com", wait_until="domcontentloaded")
        status.update(phase="login", message="请在打开的 Edge 窗口扫码登录自己的 QQ 空间，登录后自动开始。")
        cookies = {}
        while not cancel.is_set():
            if page.is_closed():
                raise RuntimeError("登录窗口已关闭。可以重新开始采集。")
            cookies = {c["name"]: c["value"] for c in context.cookies("https://user.qzone.qq.com")}
            if cookies.get("p_skey") and cookies.get("uin"):
                break
            page.wait_for_timeout(1000)
        if cancel.is_set():
            browser.close()
            return
        uin = cookies["uin"].lstrip("o0")
        if not uin.isdigit():
            raise RuntimeError("未识别到登录账号，请重新登录。")
        token = ""
        try:
            token = page.evaluate("() => typeof g_qzonetoken === 'string' ? g_qzonetoken : ''")
        except Exception:
            pass
        common = {"g_tk": gtk(cookies["p_skey"]), "qzonetoken": token, "format": "jsonp", "callback": "_Callback", "inCharset": "utf-8", "outCharset": "utf-8"}
        def request(url, params):
            response = context.request.get(url + "?" + urlencode({**common, **params}),
                                           headers={"Referer": f"https://user.qzone.qq.com/{uin}"}, timeout=30000)
            if not response.ok:
                raise RuntimeError(f"空间接口返回 HTTP {response.status}")
            data = decode_json(response.text())
            if data.get("code", 0) != 0:
                raise RuntimeError(f"空间接口未成功：{data.get('message') or data.get('msg') or data.get('code')}")
            return data
        start, end = options.get("start", ""), options.get("end", "")
        pos, seen, warnings = 0, set(), 0
        while not cancel.is_set():
            status.update(phase="collecting", message=f"读取动态列表，第 {pos // 20 + 1} 页…")
            data = request(LIST, {"uin": uin, "ftype": 0, "sort": 0, "pos": pos, "num": 20,
                                  "replynum": 0, "code_version": 1, "need_private_comment": 1})
            if "msglist" not in data:
                raise RuntimeError("接口没有返回动态列表；已采集内容保留，可稍后重新登录重试。")
            items = data["msglist"] or []
            if not items:
                if pos == 0:
                    status.update(message="接口返回空列表，未采集到动态。请确认账号内有可见说说。")
                break
            reached_start, new_on_page = False, 0
            for row in items:
                if cancel.is_set():
                    break
                tid = str(row.get("tid", ""))
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                new_on_page += 1
                day = parse_date(row.get("created_time"))[:10]
                if start and day < start:
                    reached_start = True
                    continue
                if end and day > end:
                    continue
                if row.get("has_more_con"):
                    try:
                        detail = request(DETAIL, {"uin": uin, "hostuin": uin, "tid": tid, "not_trunc_con": 1, "code_version": 1})
                        if detail.get("content"):
                            row["content"] = detail["content"]
                        else:
                            warnings += 1
                    except Exception:
                        warnings += 1
                    page.wait_for_timeout(650)
                post = normalize(row, "QQ 空间采集")
                post["id"] = tid
                post["likes"] = None
                post["views"] = None
                for field, url, params, count_key in [
                    ("likes", LIKES, {"uin": uin, "unikey": f"http://user.qzone.qq.com/{uin}/mood/{tid}", "begin_uin": 0, "query_count": 1, "if_first_page": 1}, "total_number"),
                    ("views", VIEWS, {"uin": uin, "appid": 311, "param": tid, "beginNum": 1, "num": 1, "needFriend": 0}, "viewCount"),
                ]:
                    if cancel.is_set():
                        break
                    try:
                        counts = request(url, params).get("data", {})
                        post[field] = number(counts.get(count_key))
                        if post[field] is None:
                            warnings += 1
                    except Exception:
                        warnings += 1
                    page.wait_for_timeout(650)
                save([post])
                status.update(count=status.get("count", 0) + 1, warnings=warnings,
                              message=f"已采集 {status.get('count', 0) + 1} 条；缺失统计或正文请求 {warnings} 项。")
            pos += len(items)
            total = number(data.get("total"))
            if reached_start or (total is not None and pos >= total):
                break
            if new_on_page == 0:
                raise RuntimeError("接口重复返回同一页，采集已停止。已采集内容保留，当前范围可能不完整。")
            page.wait_for_timeout(1200)
        browser.close()
        if not cancel.is_set():
            status.update(message=f"采集完成：{status.get('count', 0)} 条；缺失统计或正文请求 {warnings} 项。")
