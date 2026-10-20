import { useEffect, useRef, useState } from "react";
import { api, annotationLocation, type Asset, type Annotation, type Snapshot, type ReaderPreferences } from "../domain";
import { Modal } from '../Modal';
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
  quote: (a:Annotation)=>void;
  initialLocation?:{value:string};
};
export function Reader({
  asset,
  data,
  theme,
  onClose,
  reload,
  promote,
  notify,
  quote,
  initialLocation,
}: Props) {
  const [preferences,setPreferences]=useState<ReaderPreferences>(()=>JSON.parse(data.reader_preferences.find(p=>p.book_id===asset.book_id)?.settings || '{}'));
  const [bytes, setBytes] = useState<Uint8Array | null>(null),
    [error, setError] = useState("");
  const [annotations, setAnnotations] = useState(
    data.annotations.filter((a) => a.asset_id === asset.id),
  );
  const annRef = useRef(annotations);
  annRef.current = annotations;
  const [location, setLocation] = useState(
      initialLocation?.value || data.progress.find((p) => p.asset_id === asset.id)?.location || "",
    ),
    [tool, setTool] = useState("select"),
    [color, setColor] = useState(preferences.color || "#dcc776"),
    [width, setWidth] = useState(preferences.width || 2),
    [zoom, setZoom] = useState(preferences.zoom || 1),
    [focus, setFocus] = useState(false),
    [left, setLeft] = useState(true),
    [right, setRight] = useState(true),
    [fontSize, setFontSize] = useState(preferences.fontSize || 20),
    [lineHeight, setLineHeight] = useState(preferences.lineHeight || 1.8),
    [selection, setSelection] = useState<Selection | null>(null),
    [toc, setToc] = useState<{ label: string; location: string }[]>([]),
    [saveStatus, setSaveStatus] = useState("已保存");
  const [textBox, setTextBox] = useState(""),
    [pendingBox, setPendingBox] = useState<string | null>(null),
    [pendingComment,setPendingComment]=useState<Selection|null>(null),
    [comment,setComment]=useState('');
  const history = useRef<Annotation[][]>([]),
    future = useRef<Annotation[][]>([]),
    queue = useRef(Promise.resolve());
  const generation=useRef(0);
  const enqueue=(job:()=>Promise<void>)=>{
    const version=++generation.current;setSaveStatus('保存中…');
    queue.current=queue.current.catch(()=>{}).then(job).then(()=>{if(version===generation.current)setSaveStatus('已保存');}).catch(e=>{if(version===generation.current)setSaveStatus('保存失败');notify(e.message);});
  };
  const setting=(patch:ReaderPreferences)=>{
    setPreferences(current=>({...current,...patch}));
    if(patch.color!==undefined)setColor(patch.color);
    if(patch.width!==undefined)setWidth(patch.width);
    if(patch.zoom!==undefined)setZoom(patch.zoom);
    if(patch.fontSize!==undefined)setFontSize(patch.fontSize);
    if(patch.lineHeight!==undefined)setLineHeight(patch.lineHeight);
    enqueue(()=>api.preferences(asset.book_id,patch));
  };
  const readerTheme=preferences.readerTheme==='system' || !preferences.readerTheme ? theme : preferences.readerTheme;
  const background=readerTheme==='custom' ? preferences.background || '#f5f2ec' : readerTheme==='dark' ? '#222721' : '#fffdf6';
  const foreground=readerTheme==='custom' ? preferences.foreground || '#242925' : readerTheme==='dark' ? '#e8e5dc' : '#242925';
  useEffect(() => {
    api
      .readAsset(asset.id)
      .then((v) => setBytes(new Uint8Array(v)))
      .catch((e) => setError(e.message));
  }, [asset.id]);
  const persist = (next: Annotation[]) => {
    annRef.current = next;
    setAnnotations(next);
    enqueue(()=>api.annotations(asset.id,next));
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
    enqueue(()=>api.progress(asset.id,s));
  };
  useEffect(()=>{if(initialLocation)move(initialLocation.value);},[initialLocation]);
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
    try {move(annotationLocation(asset,a));}catch{notify('批注位置已不可用。');}
  };
  const bookmarks = data.bookmarks.filter((b) => b.asset_id === asset.id);
  return (
    <div className="reader-shell" style={{'--reading-background':background} as React.CSSProperties}>
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
        <strong title={data.books.find((b) => b.id === asset.book_id)?.title}>{data.books.find((b) => b.id === asset.book_id)?.title}</strong>
        <span>{asset.format.toUpperCase()}</span>
        <div className="grow" />
        <small role="status">{saveStatus}</small>
        <button aria-pressed={focus} title="收起侧栏，专心阅读" onClick={() => setFocus(!focus)}>
          {focus ? "研读模式" : "专注模式"}
        </button>
        <button aria-label="切换目录" aria-expanded={!focus && left} onClick={() => setLeft(!left)}>
          目录
        </button>
        <button aria-label="切换批注面板" aria-expanded={!focus && right} onClick={() => setRight(!right)}>
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
                aria-pressed={tool===v}
                title={label+(v==='select'?'（默认）':'')}
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
                aria-label="绘图线宽"
                onChange={(e) => setting({width:Number(e.target.value)})}
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
                onChange={(e) => setting({zoom:Number(e.target.value)})}
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
                  setting({fontSize:Math.min(40,Math.max(12,Number(e.target.value)))})
                }
              />
            </label>
            <label>
              行距{" "}
              <select
                value={lineHeight}
                aria-label="EPUB 行距"
                onChange={(e) => setting({lineHeight:Number(e.target.value)})}
              >
                {[1.4, 1.8, 2.2].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
          </>
        )}
        <div className="swatches">
          {["#dcc776", "#8ab49b", "#8da9c4", "#c7939d"].map((c) => (
            <button
              key={c}
              aria-label={"颜色 " + c}
              className={color === c ? "chosen" : ""}
              style={{ background: c }}
              title={'高亮颜色 '+c}
              aria-pressed={color===c}
              onClick={() => setting({color:c})}
            />
          ))}
        </div>
        <input aria-label="自定义高亮颜色" title="自定义高亮和绘图颜色" type="color" value={color} onChange={e=>setting({color:e.target.value})}/>
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
        <button disabled={!selection} onMouseDown={e=>e.preventDefault()} onClick={()=>{setPendingComment(selection);setComment('');}}>写批注</button>
        <button title="撤销（Ctrl+Z）" onClick={undo}>撤销</button>
        <button title="重做（Ctrl+Shift+Z）" onClick={redo}>重做</button>
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
        <details className="reader-preferences"><summary>阅读设置</summary><div className="preferences-panel">
          <p>仅应用于这本书，自动保存</p>
          <label>阅读配色<select aria-label="阅读配色" value={preferences.readerTheme || 'system'} onChange={e=>setting({readerTheme:e.target.value as ReaderPreferences['readerTheme']})}>
            <option value="system">跟随应用</option><option value="light">浅色纸张</option><option value="dark">深色夜读</option><option value="custom">自定义</option>
          </select></label>
          {readerTheme==='custom' && <div className="row"><label>背景<input aria-label="阅读背景颜色" type="color" value={background} onChange={e=>setting({background:e.target.value})}/></label><label>文字<input aria-label="阅读文字颜色" type="color" value={foreground} onChange={e=>setting({foreground:e.target.value})}/></label></div>}
          <small>PDF 保留原书页面颜色；背景用于页面周围。</small>
        </div></details>
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
                background={background}
                foreground={foreground}
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
                <small className="annotation-location">{asset.format==='pdf' ? 'PDF · 第 '+JSON.parse(a.anchor).page+' 页' : 'EPUB · 原文片段'}</small>
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
                  <button onClick={async()=>{await queue.current;quote(a);}}>引用到日志</button>
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
          <Modal title="添加文本框" onClose={()=>setPendingBox(null)} onSubmit={(e) => {
              e.preventDefault();
              if (textBox.trim()) add("textbox", pendingBox, textBox);
              setPendingBox(null);
            }}>
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
          </Modal>
      )}
      {pendingComment && <Modal title="写一条批注" onClose={()=>setPendingComment(null)} onSubmit={e=>{
        e.preventDefault();add('highlight',pendingComment.anchor,pendingComment.text,comment);setSelection(null);setPendingComment(null);window.getSelection()?.removeAllRanges();
      }}><blockquote className="selection-excerpt">{pendingComment.text}</blockquote><label>我的想法<textarea autoFocus aria-label="选文批注" value={comment} onChange={e=>setComment(e.target.value)} rows={5}/></label><div className="modal-footer"><button type="button" onClick={()=>setPendingComment(null)}>取消</button><button className="primary">保存批注</button></div></Modal>}
    </div>
  );
}
