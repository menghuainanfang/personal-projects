import { useEffect, useRef, useState } from "react";
import { api, type Asset, type Annotation, type Snapshot } from "../domain";
import { PdfReader, type Selection } from "./PdfReader";
import { EpubReader } from "./EpubReader";
type Props = {
  asset: Asset;
  data: Snapshot;
  theme: string;
  onClose: () => void;
  reload: () => Promise<void>;
  promote: (text: string, annotationId: string) => void;
  notify: (s: string) => void;
};
export function Reader({
  asset,
  data,
  theme,
  onClose,
  reload,
  promote,
  notify,
}: Props) {
  const [bytes, setBytes] = useState<Uint8Array | null>(null),
    [error, setError] = useState("");
  const [annotations, setAnnotations] = useState(
    data.annotations.filter((a) => a.asset_id === asset.id),
  );
  const annRef = useRef(annotations);
  annRef.current = annotations;
  const [location, setLocation] = useState(
      data.progress.find((p) => p.asset_id === asset.id)?.location || "",
    ),
    [tool, setTool] = useState("select"),
    [color, setColor] = useState("#e6b84e"),
    [width, setWidth] = useState(2),
    [zoom, setZoom] = useState(1),
    [focus, setFocus] = useState(false),
    [left, setLeft] = useState(true),
    [right, setRight] = useState(true),
    [fontSize, setFontSize] = useState(20),
    [lineHeight, setLineHeight] = useState(1.8),
    [selection, setSelection] = useState<Selection | null>(null),
    [toc, setToc] = useState<{ label: string; location: string }[]>([]),
    [saveStatus, setSaveStatus] = useState("已保存");
  const [textBox, setTextBox] = useState(""),
    [pendingBox, setPendingBox] = useState<string | null>(null);
  const history = useRef<Annotation[][]>([]),
    future = useRef<Annotation[][]>([]),
    queue = useRef(Promise.resolve());
  useEffect(() => {
    api
      .readAsset(asset.id)
      .then((v) => setBytes(new Uint8Array(v)))
      .catch((e) => setError(e.message));
  }, [asset.id]);
  const persist = (next: Annotation[]) => {
    const previous = annRef.current;
    annRef.current = next;
    setAnnotations(next);
    setSaveStatus("保存中…");
    queue.current = queue.current
      .catch(() => {})
      .then(async () => {
        await api.annotations(asset.id, next);
        setSaveStatus("已保存");
      })
      .catch((e) => {
        setSaveStatus("保存失败");
        notify(e.message);
      });
  };
  const change = (next: Annotation[]) => {
    history.current.push(annRef.current);
    future.current = [];
    persist(next);
  };
  const undo = () => {
    const prev = history.current.pop();
    if (prev) {
      future.current.push(annRef.current);
      persist(prev);
    }
  };
  const redo = () => {
    const next = future.current.pop();
    if (next) {
      history.current.push(annRef.current);
      persist(next);
    }
  };
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (
        (e.ctrlKey || e.metaKey) &&
        e.key === "z" &&
        !(e.target as HTMLElement)?.closest("input,textarea,[contenteditable]")
      ) {
        e.preventDefault();
        e.shiftKey ? redo() : undo();
      }
    };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, []);
  const move = (s: string) => {
    setLocation(s);
    void api.progress(asset.id, s).catch((e) => notify(e.message));
  };
  const add = (kind: string, anchor: string, text = "", comment = "") =>
    change([
      ...annRef.current,
      {
        id: crypto.randomUUID(),
        asset_id: asset.id,
        kind,
        anchor,
        color,
        width,
        text,
        comment,
      },
    ]);
  const draw = (kind: string, anchor: string) => {
    if (kind === "textbox") {
      setPendingBox(anchor);
      setTextBox("");
    } else add(kind, anchor);
  };
  const common = {
    bytes: bytes!,
    annotations,
    location,
    tool,
    color,
    width,
    zoom,
    onLocation: move,
    onSelection: setSelection,
    onDraw: draw,
    onErase: (id: string) => change(annRef.current.filter((a) => a.id !== id)),
    onToc: setToc,
    onError: setError,
  };
  const goAnnotation = (a: Annotation) => {
    const anchor = JSON.parse(a.anchor);
    move(
      asset.format === "pdf"
        ? JSON.stringify({ page: anchor.page })
        : anchor.cfi,
    );
  };
  const bookmarks = data.bookmarks.filter((b) => b.asset_id === asset.id);
  return (
    <div className="reader-shell">
      <header className="reader-header">
        <button
          onClick={async () => {
            await queue.current;
            await reload();
            onClose();
          }}
        >
          ← 书籍主页
        </button>
        <strong>{data.books.find((b) => b.id === asset.book_id)?.title}</strong>
        <span>{asset.format.toUpperCase()}</span>
        <div className="grow" />
        <small role="status">{saveStatus}</small>
        <button onClick={() => setFocus(!focus)}>
          {focus ? "研读模式" : "专注模式"}
        </button>
        <button aria-label="切换目录" onClick={() => setLeft(!left)}>
          目录
        </button>
        <button aria-label="切换批注面板" onClick={() => setRight(!right)}>
          批注
        </button>
      </header>
      <div className="reader-tools">
        {asset.format === "pdf" ? (
          <>
            {[
              ["select", "选择文字"],
              ["ink", "手绘"],
              ["line", "直线"],
              ["circle", "圆圈"],
              ["textbox", "文本框"],
              ["erase", "橡皮擦"],
            ].map(([v, label]) => (
              <button
                key={v}
                className={tool === v ? "active" : ""}
                onClick={() => {
                  setTool(v);
                  setSelection(null);
                }}
              >
                {label}
              </button>
            ))}
            <label>
              线宽{" "}
              <select
                value={width}
                onChange={(e) => setWidth(Number(e.target.value))}
              >
                {[1, 2, 4, 8].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              缩放{" "}
              <select
                aria-label="PDF 缩放"
                value={zoom}
                onChange={(e) => setZoom(Number(e.target.value))}
              >
                {[0.6, 0.8, 1, 1.25, 1.5, 2].map((v) => (
                  <option key={v} value={v}>
                    {Math.round(v * 100)}%
                  </option>
                ))}
              </select>
            </label>
          </>
        ) : (
          <>
            <label>
              字号{" "}
              <input
                aria-label="EPUB 字号"
                type="number"
                min="12"
                max="40"
                value={fontSize}
                onChange={(e) =>
                  setFontSize(
                    Math.min(40, Math.max(12, Number(e.target.value))),
                  )
                }
              />
            </label>
            <label>
              行距{" "}
              <select
                value={lineHeight}
                onChange={(e) => setLineHeight(Number(e.target.value))}
              >
                {[1.4, 1.8, 2.2].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
          </>
        )}
        <div className="swatches">
          {["#e6b84e", "#74ba93", "#6d9edc", "#d97b92"].map((c) => (
            <button
              key={c}
              aria-label={"颜色 " + c}
              className={color === c ? "chosen" : ""}
              style={{ background: c }}
              onClick={() => setColor(c)}
            />
          ))}
        </div>
        <button
          disabled={!selection}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => {
            if (selection) {
              add("highlight", selection.anchor, selection.text);
              setSelection(null);
              window.getSelection()?.removeAllRanges();
            }
          }}
        >
          高亮选文
        </button>
        <button onClick={undo}>撤销</button>
        <button onClick={redo}>重做</button>
        <button
          onClick={async () => {
            await api.save("bookmarks", {
              asset_id: asset.id,
              location,
              label: "书签 " + (bookmarks.length + 1),
            });
            await reload();
          }}
        >
          ＋ 书签
        </button>
      </div>
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <div className="reader-body">
        {!focus && left && (
          <aside className="reader-left">
            <h3>目录</h3>
            {toc.map((t, i) => (
              <button key={i} onClick={() => move(t.location)}>
                {t.label}
              </button>
            ))}
            <h3>书签</h3>
            {bookmarks.map((b) => (
              <div key={b.id}>
                <button onClick={() => move(b.location)}>{b.label}</button>
                <button
                  aria-label={"删除 " + b.label}
                  onClick={async () => {
                    await api.remove("bookmarks", b.id);
                    await reload();
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </aside>
        )}
        <main className="reader-content">
          {bytes ? (
            asset.format === "pdf" ? (
              <PdfReader {...common} />
            ) : (
              <EpubReader
                {...common}
                fontSize={fontSize}
                lineHeight={lineHeight}
                theme={theme}
              />
            )
          ) : (
            <div className="empty">正在打开本地图书…</div>
          )}
        </main>
        {!focus && right && (
          <aside className="reader-right">
            <h3>
              批注 <small>{annotations.length}</small>
            </h3>
            {annotations.length === 0 && (
              <p className="muted">
                选中文字后点击「高亮选文」。想法可以写在高亮的评论里。
              </p>
            )}
            {annotations.map((a) => (
              <article
                className="annotation-card"
                key={a.id}
                style={{ borderLeftColor: a.color }}
              >
                <button
                  className="annotation-jump"
                  onClick={() => goAnnotation(a)}
                >
                  {a.text ||
                    {
                      ink: "手绘笔迹",
                      line: "直线",
                      circle: "圆圈",
                      textbox: "文本框",
                    }[a.kind] ||
                    "批注"}
                </button>
                <textarea
                  aria-label="批注评论"
                  placeholder="写下想法…"
                  defaultValue={a.comment}
                  onBlur={(e) => {
                    if (e.target.value !== a.comment)
                      change(
                        annRef.current.map((v) =>
                          v.id === a.id ? { ...v, comment: e.target.value } : v,
                        ),
                      );
                  }}
                />
                {a.kind === "textbox" && (
                  <input
                    aria-label="文本框内容"
                    defaultValue={a.text}
                    onBlur={(e) =>
                      change(
                        annRef.current.map((v) =>
                          v.id === a.id ? { ...v, text: e.target.value } : v,
                        ),
                      )
                    }
                  />
                )}
                <div className="row">
                  <input
                    aria-label="批注颜色"
                    type="color"
                    value={a.color}
                    onChange={(e) =>
                      change(
                        annRef.current.map((v) =>
                          v.id === a.id ? { ...v, color: e.target.value } : v,
                        ),
                      )
                    }
                  />
                  <button
                    onClick={() => promote(a.text + "\n" + a.comment, a.id)}
                  >
                    提炼洞见
                  </button>
                  <button
                    onClick={() =>
                      change(annRef.current.filter((v) => v.id !== a.id))
                    }
                  >
                    删除
                  </button>
                </div>
              </article>
            ))}
          </aside>
        )}
      </div>
      {pendingBox && (
        <div className="modal-backdrop">
          <form
            className="modal"
            onSubmit={(e) => {
              e.preventDefault();
              if (textBox.trim()) add("textbox", pendingBox, textBox);
              setPendingBox(null);
            }}
          >
            <h2>添加文本框</h2>
            <input
              autoFocus
              aria-label="文本框文字"
              value={textBox}
              onChange={(e) => setTextBox(e.target.value)}
              required
            />
            <div className="row">
              <button type="button" onClick={() => setPendingBox(null)}>
                取消
              </button>
              <button className="primary">添加</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
