"""Local Qzone analysis workspace. Python standard library server."""
import argparse
import csv
import io
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from analysis import DEFAULT_SETTINGS, analyze, demo_posts, import_text, merge_posts

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOCK = threading.RLock()
CANCEL = threading.Event()
STATUS = {"phase": "idle", "message": "尚未开始采集", "count": 0}

def read_state():
    path = DATA / "workspace.json"
    return json.loads(path.read_text("utf-8")) if path.exists() else {"posts": [], "settings": dict(DEFAULT_SETTINGS)}

def write_state(state):
    DATA.mkdir(exist_ok=True)
    temp = DATA / "workspace.tmp"
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")
    temp.replace(DATA / "workspace.json")

def save_posts(posts):
    with LOCK:
        state = read_state()
        state["posts"] = merge_posts(state["posts"], posts)
        write_state(state)

def run_collect(options):
    from collector import collect
    try:
        collect(options, STATUS, CANCEL, save_posts)
        STATUS["phase"] = "cancelled" if CANCEL.is_set() else "done"
        if CANCEL.is_set():
            STATUS["message"] = "采集已停止，已取得的动态保存在本地。"
    except Exception as e:
        STATUS.update(phase="error", message=str(e))

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, value, content_type="application/json; charset=utf-8", code=200, attachment=None):
        data = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False).encode("utf-8") if content_type.startswith("application/json") else value.encode("utf-8"))
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(path.query).items()}
        try:
            with LOCK:
                state = read_state()
            if path.path == "/":
                return self.send((ROOT / "index.html").read_text("utf-8"), "text/html; charset=utf-8")
            if path.path == "/api/state":
                return self.send({"settings": state["settings"], "total": len(state["posts"]), "status": STATUS})
            if path.path == "/api/analysis":
                posts = demo_posts() if query.get("demo") == "1" else state["posts"]
                return self.send(analyze(posts, state["settings"], query))
            if path.path == "/api/export":
                posts = analyze(demo_posts() if query.get("demo") == "1" else state["posts"], state["settings"], query)["posts"]
                if query.get("format") == "json":
                    return self.send({"posts": posts, "settings": state["settings"]}, attachment="qzone-posts.json")
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=["id", "published_at", "text", "likes", "views", "image_count", "topic", "rate", "source", "captured_at"], extrasaction="ignore")
                writer.writeheader()
                writer.writerows(posts)
                return self.send(("\ufeff" + buf.getvalue()).encode("utf-8"), "text/csv; charset=utf-8", attachment="qzone-posts.csv")
            if path.path == "/api/template":
                return self.send("\ufeffid,发布时间,内容,点赞数,浏览数,图片数,主题\r\nexample-1,2020-07-15 20:30:00,今天过生日,30,200,2,生日与纪念\r\n", "text/csv; charset=utf-8", attachment="qzone-template.csv")
            return self.send({"error": "页面不存在"}, code=404)
        except Exception as e:
            return self.send({"error": str(e)}, code=400)

    def do_POST(self):
        # Browser mutations originate from this local workspace.
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{self.headers.get('Host')}":
            return self.send({"error": "请在本地分析页面操作"}, code=403)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            path = urlparse(self.path).path
            if path == "/api/import":
                posts, errors = import_text(body["text"], body["name"])
                with LOCK:
                    before = len(read_state()["posts"])
                    save_posts(posts)
                    after = len(read_state()["posts"])
                return self.send({"imported": len(posts), "added": after - before, "errors": errors[:20], "error_count": len(errors)})
            if path == "/api/settings":
                settings = {**DEFAULT_SETTINGS, **body}
                if settings["start"] and settings["end"] and settings["start"] > settings["end"]:
                    raise ValueError("起始日期应早于结束日期")
                settings["min_views"] = max(1, int(settings.get("min_views", 1)))
                from datetime import datetime
                if settings.get("birthday"):
                    datetime.strptime("2000-" + settings["birthday"], "%Y-%m-%d")
                for e in settings["events"]:
                    datetime.strptime(e["date"] if len(e["date"]) == 10 else "2000-" + e["date"], "%Y-%m-%d")
                    if not e.get("name"):
                        raise ValueError("纪念日需填写名称")
                with LOCK:
                    state = read_state()
                    state["settings"] = settings
                    write_state(state)
                return self.send({"ok": True})
            if path == "/api/topic":
                if not str(body["topic"]).strip():
                    raise ValueError("请输入主题")
                with LOCK:
                    state = read_state()
                    for p in state["posts"]:
                        if p["id"] == body["id"]:
                            p.update(topic=body["topic"].strip(), topic_manual=True)
                            write_state(state)
                            return self.send({"ok": True})
                raise ValueError("没有找到这条动态")
            if path == "/api/collect/start":
                if STATUS["phase"] in ("starting", "login", "collecting"):
                    raise ValueError("采集正在进行")
                if body.get("start") and body.get("end") and body["start"] > body["end"]:
                    raise ValueError("起始日期应早于结束日期")
                CANCEL.clear()
                STATUS.clear()
                STATUS.update(phase="starting", message="正在打开登录窗口…", count=0)
                threading.Thread(target=run_collect, args=(body,), daemon=True).start()
                return self.send({"ok": True})
            if path == "/api/collect/stop":
                CANCEL.set()
                return self.send({"ok": True})
            return self.send({"error": "接口不存在"}, code=404)
        except Exception as e:
            return self.send({"error": str(e)}, code=400)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        print(f"端口 {args.port} 已被占用。可用 python app.py --port 8766 启动。")
        return
    url = f"http://127.0.0.1:{args.port}"
    print(f"QQ 空间研究室：{url}\n关闭本窗口即可停止服务。")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        CANCEL.set()
        server.server_close()

if __name__ == "__main__":
    main()
