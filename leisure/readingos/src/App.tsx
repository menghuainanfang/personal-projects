import { useEffect, useState } from "react";
import {
  BookOpen,
  Library,
  Lightbulb,
  Target,
  Settings,
  Plus,
  Search,
  LayoutGrid,
  List,
  Sun,
  Moon,
  ArrowUpRight,
  ArrowLeft,
  Download,
} from "lucide-react";
import {
  api,
  empty,
  statuses,
  actionStatuses,
  today,
  type Book,
  type Row,
  type Snapshot,
  type Asset,
  type Annotation,
  annotationLocation,
} from "./domain";
import { RecordDialog, type Dialog } from "./RecordDialog";
import { Editor } from "./Editor";
import { Reader } from "./reader/Reader";
import { ReadingAppShell } from './components/shell/ReadingAppShell';
import { useReadingTheme } from './components/shell/ReadingThemeProvider';

import { BooklistDialog } from './BooklistDialog';
import DOMPurify from "dompurify";
function Plain({ html }: { html: string }) {
  return (
    <div
      className="prose"
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }}
    />
  );
}
function Cover({ book, small = false }: { book: Book; small?: boolean }) {
  const colors = ["#506453", "#675343", "#52616d", "#685864", "#626147"];
  let n = 0;
  for (const c of book.id) n += c.charCodeAt(0);
  return (
    <div
      className={"cover " + (small ? "small" : "")}
      style={{ background: colors[n % colors.length] }}
    >
      {book.cover ? (
        <img src={book.cover} alt={book.title + " 封面"} />
      ) : (
        <>
          <span className="cover-line">{book.category || '读书档案'}</span>
          <strong>{book.title}</strong>
          <span>{book.author || "未署名"}</span>
        </>
      )}
    </div>
  );
}
export function App() {
  const [data, setData] = useState<Snapshot>(empty),
    [loaded, setLoaded] = useState(false),
    [view, setView] = useState("library"),
    [bookId, setBookId] = useState<string | null>(null),
    [asset, setAsset] = useState<Asset | null>(null),
    [readerLocation, setReaderLocation] = useState<{value:string} | undefined>(),
    [dialog, setDialog] = useState<Dialog | null>(null),
    [toast, setToast] = useState("");
  const {theme,setTheme}=useReadingTheme();
  const [query, setQuery] = useState(""),
    [filter, setFilter] = useState("all"),
    [sort, setSort] = useState("updated"),
    [layout, setLayout] = useState("grid"),
    [info, setInfo] = useState<{
      version: string;
      dataPath: string;
      packaged: boolean;
    } | null>(null),
    [month, setMonth] = useState(today().slice(0, 7)),
    [logQuery, setLogQuery] = useState(""),
    [revision, setRevision] = useState(false);
  const [booklistOpen, setBooklistOpen] = useState(false);
  const notify = (s: string) => setToast(s);
  const reload = async () => {
    setData(await api.snapshot());
    setLoaded(true);
  };
  useEffect(() => {
    if (!api) {
      setToast("请从 ReadingOS 桌面应用启动。");
      return;
    }
    reload().catch((e) => notify(e.message));
    api.info().then(setInfo);
  }, []);

  const run = async (fn: () => Promise<unknown>, message?: string) => {
    try {
      await fn();
      await reload();
      if (message) notify(message);
    } catch (e) {
      notify((e as Error).message);
    }
  };
  const importBooks = async (id?: string) => {
    try {
      const result = await api.importBook(id);
      await reload();
      if (result.length)
        notify(
          result
            .map(
              (r) => r.error || (r.duplicate ? "该文件已在书库中" : "导入成功"),
            )
            .join("\n"),
        );
    } catch (e) {
      notify((e as Error).message);
    }
  };
  const openBook = async (id: string) => {
    try {
      await reload();
      setBookId(id);
      setRevision(false);
      setLogQuery("");
      setView("book");
    } catch (e) {
      notify((e as Error).message);
    }
  };
  const book = data.books.find((b) => b.id === bookId);
  const startReading = (file:Asset, location?:string) => {
    setBookId(file.book_id); setView('book'); setReaderLocation(location ? {value:location} : undefined); setAsset(file);
  };
  const openSource = (id:string) => {
    const a=data.annotations.find(a=>a.id===id);
    const file=a && data.assets.find(f=>f.id===a.asset_id);
    if(!a || !file) {notify('关联批注或原书已删除，无法定位原文。');return;}
    try {setDialog(null);startReading(file,annotationLocation(file,a));}catch{notify('这条批注的位置已不可用。');}
  };
  const quoteAnnotation = async (annotation:Annotation) => {
    await reload();
    const block=document.createElement('blockquote'); block.textContent=annotation.text || 'PDF 绘图批注';
    const comment=document.createElement('p');comment.textContent=annotation.comment;
    setDialog({kind:'journal',row:{book_id:asset!.book_id,date:today(),title:'原文与我的理解',source:annotation.id,content:block.outerHTML+comment.outerHTML}});
  };
  const linkedInsights = (id?: string) =>
    id
      ? data.insights.filter((i) =>
          data.insight_links.some(
            (l) => l.insight_id === i.id && l.book_id === id,
          ),
        )
      : data.insights;
  const remove = (table: string, id: string) => {
    if (window.confirm("确定删除？此操作无法撤销。"))
      void run(() => api.remove(table, id), "已删除");
  };
  const promote = (
    content: string,
    annotationId?: string,
    journalId?: string,
  ) =>
    setDialog({
      kind: "insight",
      row: { content },
      bookId: bookId || undefined,
      annotationId,
      journalId,
    });
  const renderActions = (actions: Row[]) =>
    actions.map((a) => (
      <article className="action-card" key={a.id}>
        <div className="row">
          <span className={"status " + (a.status === "done" ? "done" : "")}>
            {actionStatuses[a.status]}
          </span>
          <span className="muted">{a.planned || "未安排日期"}</span>
          <div className="grow" />
          <button
            aria-label="编辑行动"
            onClick={() => setDialog({ kind: "action", row: a })}
          >
            编辑
          </button>
          <button onClick={() => remove("actions", a.id)}>删除</button>
        </div>
        <h3>{a.description}</h3>
        {a.insight_id && (
          <p className="muted">
            源于：{data.insights.find((i) => i.id === a.insight_id)?.title}
          </p>
        )}
        <select
          aria-label="行动状态"
          value={a.status}
          onChange={(e) =>
            void run(() =>
              api.save("actions", { ...a, status: e.target.value }),
            )
          }
        >
          {Object.entries(actionStatuses).map(([v, label]) => (
            <option value={v} key={v}>
              {label}
            </option>
          ))}
        </select>
        <button
          onClick={() =>
            setDialog({
              kind: "feedback",
              row: { action_id: a.id, date: today() },
            })
          }
        >
          记录实践反馈
        </button>
        {data.feedback
          .filter((f) => f.action_id === a.id)
          .map((f) => (
            <div className="feedback" key={f.id}>
              <small>{f.date}</small>
              <p>{f.content}</p>
              <button onClick={() => setDialog({ kind: "feedback", row: f })}>
                编辑
              </button>
              <button onClick={() => remove("feedback", f.id)}>删除</button>
            </div>
          ))}
      </article>
    ));
  const renderInsights = (items: Row[]) =>
    items.map((i) => (
      <article className="insight-card" key={i.id}>
        <div className="row">
          <Lightbulb size={18} />
          <span className="eyebrow">洞见</span>
          <div className="grow" />
          <button
            onClick={() =>
              setDialog({
                kind: "insight",
                row: i,
                bookId: bookId || undefined,
              })
            }
          >
            编辑
          </button>
          <button onClick={() => remove("insights", i.id)}>删除</button>
        </div>
        <h3>{i.title}</h3>
        <p className="prewrap">{i.content}</p>
        <div className="row wrap">
          {data.insight_links
            .filter((l) => l.insight_id === i.id)
            .map((l) => (
              <button
                key={l.id}
                className="source"
                onClick={() => {
                  if(l.annotation_id) openSource(l.annotation_id);
                  else if(l.journal_id) {
                    const journal=data.journals.find(j=>j.id===l.journal_id);
                    if(journal) setDialog({kind:'journal',row:journal}); else notify('来源日志已删除。');
                  } else if (l.book_id) void openBook(l.book_id);
                }}
              >
                {data.books.find((b) => b.id === l.book_id)?.title ||
                  "独立洞见"}
                {l.annotation_id ? " · 批注" : l.journal_id ? " · 日志" : ""}
              </button>
            ))}
        </div>
        <button
          className="text-button"
          onClick={() =>
            setDialog({
              kind: "action",
              row: { status: "planned", book_id: bookId },
              insightId: i.id,
            })
          }
        >
          化为行动 <ArrowUpRight size={14} />
        </button>
      </article>
    ));
  if (asset)
    return (
      <>
        <Reader
          key={asset.id}
          asset={asset}
          data={data}
          theme={theme}
          onClose={() => setAsset(null)}
          reload={reload}
          promote={promote}
          notify={notify}
          quote={a=>void quoteAnnotation(a)}
          initialLocation={readerLocation}
        />
        {dialog && (
          <RecordDialog
            key={dialog.row?.id || dialog.kind}
            dialog={dialog}
            data={data}
            close={() => {
              setDialog(null);
              void reload();
            }}
            done={async () => {
              await reload();
              setDialog(null);
              notify("已保存");
            }}
            notify={notify}
            openSource={openSource}
          />
        )}
        <Toast message={toast} close={() => setToast("")} />
      </>
    );
  const visible = data.books
    .filter(
      (b) =>
        (filter === "all" || b.status === filter) &&
        [b.title, b.author, b.tags, b.category]
          .join(" ")
          .toLowerCase()
          .includes(query.toLowerCase()),
    )
    .sort((a, b) =>
      sort === "title"
        ? a.title.localeCompare(b.title, "zh-CN")
        : String(b[sort]).localeCompare(String(a[sort])),
    );
  const completed = data.books.filter(
    (b) =>
      b.status === "completed" && b.completed.startsWith(month.slice(0, 4)),
  ).length;
  const yearTarget =
    data.goals.find((g) => g.period === month.slice(0, 4))?.target || 0;
  return (
    <><ReadingAppShell view={view} data={data} book={view==='book'?book:undefined} theme={theme} setTheme={setTheme}
      navigate={value=>{setView(value);setBookId(null);}} openBook={id=>void openBook(id)}
      resume={()=>{const files=book?data.assets.filter(a=>a.book_id===book.id):data.assets;const latest=[...files].sort((a,b)=>(data.progress.find(p=>p.asset_id===b.id)?.updated||'').localeCompare(data.progress.find(p=>p.asset_id===a.id)?.updated||''))[0];if(latest)startReading(latest);}}
      journal={id=>{const row=data.journals.find(j=>j.id===id);if(row)setDialog({kind:'journal',row});}} source={openSource}>
        {view === "library" && (
          <>
            <header className="page-heading">
              <div>
                <p className="eyebrow">书房 · 阅读与思考</p>
                <h1>
                  我的书库<span>{data.books.length} 本</span>
                </h1>
                <p className="muted">从一本书开始，积累自己的理解。</p>
              </div>
              <div className="row">
                <button
                  onClick={() =>
                    setDialog({ kind: "book", row: { status: "want" } })
                  }
                >
                  <Plus size={17} />
                  添加纸质书
                </button>
                <button className="primary" onClick={() => void importBooks()}>
                  <Download size={17} />
                  导入电子书
                </button>
              </div>
            </header>
            <div className="library-toolbar">
              <div className="search-field">
                <Search size={17} />
                <input
                  aria-label="搜索书库"
                  placeholder="搜索书名、作者、标签…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <select
                aria-label="书籍排序"
                value={sort}
                onChange={(e) => setSort(e.target.value)}
              >
                <option value="updated">最近更新</option>
                <option value="created">最近添加</option>
                <option value="title">书名排序</option>
              </select>
              <div className="view-toggle">
                <button
                  aria-label="封面网格"
                  title="封面网格"
                  className={layout === "grid" ? "active" : ""}
                  onClick={() => setLayout("grid")}
                >
                  <LayoutGrid size={17} />
                </button>
                <button
                  aria-label="书籍列表"
                  title="书籍列表"
                  className={layout === "list" ? "active" : ""}
                  onClick={() => setLayout("list")}
                >
                  <List size={17} />
                </button>
              </div>
            </div>
            <div className="tabs">
              {Object.entries({ all: "全部", ...statuses }).map(
                ([v, label]) => (
                  <button
                    className={filter === v ? "active" : ""}
                    key={v}
                    onClick={() => setFilter(v)}
                  >
                    {label}
                    <small>
                      {v === "all"
                        ? data.books.length
                        : data.books.filter((b) => b.status === v).length}
                    </small>
                  </button>
                ),
              )}
            </div>
            {!loaded ? (
              <div className="empty">正在打开书库…</div>
            ) : visible.length === 0 ? (
              <div className="empty">
                <BookOpen size={48} />
                <h2>
                  {data.books.length
                    ? "没有匹配的书籍"
                    : "你的第一本书，等你打开"}
                </h2>
                <p>导入 PDF、EPUB，或为手边的纸质书建档。</p>
                <button className="primary" onClick={() => void importBooks()}>
                  导入电子书
                </button>
                <button
                  onClick={() =>
                    setDialog({ kind: "book", row: { status: "want" } })
                  }
                >
                  添加纸质书
                </button>
              </div>
            ) : (
              <div className={layout === "grid" ? "book-grid" : "book-list"}>
                {visible.map((b) => (
                  <article className="book-entry" key={b.id}>
                  <button
                    className="book-card"
                    key={b.id}
                    onClick={() => openBook(b.id)}
                  >
                    <Cover book={b} small={layout === "list"} />
                    <div className="book-card-info">
                      <div className="row">
                        <span className={"status " + b.status}>
                          {statuses[b.status]}
                        </span>
                        <small className="muted">
                          {data.assets
                            .filter((a) => a.book_id === b.id)
                            .map((a) => a.format.toUpperCase())
                            .join(" / ") || "纸质书"}
                        </small>
                      </div>
                      <h3>{b.title}</h3>
                      <p>{b.author || "作者未填写"}</p>
                      {b.tags && <small className="tags">{b.tags}</small>}
                    </div>
                  </button>
                  {data.assets.some(a=>a.book_id===b.id) && <button className="resume-book" aria-label={'继续阅读《'+b.title+'》'} onClick={()=>{
                    const files=data.assets.filter(a=>a.book_id===b.id);
                    const last=[...files].sort((a,b)=>(data.progress.find(p=>p.asset_id===b.id)?.updated || '').localeCompare(data.progress.find(p=>p.asset_id===a.id)?.updated || ''))[0];
                    startReading(last);
                  }}>继续阅读 <ArrowUpRight size={14}/></button>}
                  </article>
                ))}
              </div>
            )}
          </>
        )}
        {view === "book" && book && (
          <>
            <button className="back" onClick={() => setView("library")}>
              <ArrowLeft size={16} />
              返回书库
            </button>
            <header className="book-heading">
              <Cover book={book} small />
              <div>
                <p className="eyebrow">书籍 · 我的阅读档案</p>
                <h1>{book.title}</h1>
                <p>
                  {book.author || "作者未填写"}{" "}
                  {book.category && " · " + book.category}
                </p>
                <div className="row wrap">
                  <span className="status">{statuses[book.status]}</span>
                  <span className="tags">{book.tags}</span>
                  <button
                    onClick={() => setDialog({ kind: "book", row: book })}
                  >
                    编辑资料
                  </button>
                  <button onClick={() => void importBooks(book.id)}>
                    关联电子版本
                  </button>
                  <button
                    onClick={() =>
                      void run(
                        () => api.exportMarkdown(book.id),
                        "已导出读书笔记",
                      )
                    }
                  >
                    导出 Markdown
                  </button>
                </div>
                <small className="muted">
                  {book.started && "开始：" + book.started + "　"}
                  {book.completed && "完成：" + book.completed}
                </small>
              </div>
            </header>
            <div className="asset-row">
              {data.assets
                .filter((a) => a.book_id === book.id)
                .map((a) => (
                  <button
                    className="primary"
                    key={a.id}
                    onClick={() => startReading(a)}
                  >
                    <BookOpen size={16} />
                    继续阅读 · {a.format.toUpperCase()}
                    <small>{a.name}</small>
                  </button>
                ))}
            </div>
            <section className="reflection-section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">置顶 · 随时续写</span>
                  <h2>我的主读后感</h2>
                </div>
                <button
                  onClick={() =>
                    void reload().then(() => setRevision(!revision))
                  }
                >
                  版本记录 (
                  {
                    data.summary_revisions.filter((r) => r.book_id === book.id)
                      .length
                  }
                  )
                </button>
              </div>
              <p className="muted">
                这本书改变了什么？用自己的话留下最重要的理解。
              </p>
              <Editor
                key={book.id}
                label="主读后感"
                version={
                  data.summaries.find((s) => s.book_id === book.id)?.updated
                }
                value={
                  data.summaries.find((s) => s.book_id === book.id)?.content ||
                  ""
                }
                onSave={(html) => api.summary(book.id, html)}
              />
              {revision && (
                <div className="revision-list">
                  {data.summary_revisions
                    .filter((r) => r.book_id === book.id)
                    .reverse()
                    .map((r) => (
                      <details key={r.id}>
                        <summary>
                          {new Date(r.created).toLocaleString("zh-CN")}
                        </summary>
                        <Plain html={r.content} />
                        <button
                          onClick={() =>
                            void run(
                              () => api.summary(book.id, r.content),
                              "已恢复此版本",
                            )
                          }
                        >
                          恢复此版本
                        </button>
                      </details>
                    ))}
                </div>
              )}
            </section>
            <section>
              <div className="section-heading">
                <h2>关键洞见</h2>
                <button
                  onClick={() =>
                    setDialog({ kind: "insight", bookId: book.id })
                  }
                >
                  <Plus size={15} />
                  新建洞见
                </button>
              </div>
              <div className="insights-grid">
                {renderInsights(linkedInsights(book.id))}
              </div>
              {!linkedInsights(book.id).length && (
                <p className="muted">
                  值得反复使用的想法，可以独立写下，也可以从批注和日志提炼。
                </p>
              )}
            </section>
            <section>
              <div className="section-heading">
                <h2>实践行动</h2>
                <button
                  onClick={() =>
                    setDialog({
                      kind: "action",
                      row: { book_id: book.id, status: "planned" },
                    })
                  }
                >
                  <Plus size={15} />
                  添加行动
                </button>
              </div>
              {renderActions(
                data.actions.filter(
                  (a) =>
                    a.book_id === book.id ||
                    linkedInsights(book.id).some((i) => i.id === a.insight_id),
                ),
              )}
            </section>
            <section>
              <div className="section-heading">
                <h2>阅读日志</h2>
                <button
                  onClick={() =>
                    setDialog({
                      kind: "journal",
                      row: { book_id: book.id, date: today(), content: "" },
                    })
                  }
                >
                  <Plus size={15} />
                  写一篇日志
                </button>
              </div>
              <input
                className="log-search"
                aria-label="搜索阅读日志"
                placeholder="搜索日志标题与内容…"
                value={logQuery}
                onChange={(e) => setLogQuery(e.target.value)}
              />
              {data.journals
                .filter(
                  (j) =>
                    j.book_id === book.id &&
                    (j.title + j.content)
                      .toLowerCase()
                      .includes(logQuery.toLowerCase()),
                )
                .sort((a, b) => b.date.localeCompare(a.date))
                .map((j) => (
                  <article className="journal-card" key={j.id}>
                    <div className="row">
                      <span className="eyebrow">{j.date}</span>
                      <div className="grow" />
                      <button
                        onClick={() =>
                          promote(
                            j.content.replace(/<[^>]*>/g, ""),
                            undefined,
                            j.id,
                          )
                        }
                      >
                        提炼洞见
                      </button>
                      <button
                        onClick={() => setDialog({ kind: "journal", row: j })}
                      >
                        编辑
                      </button>
                      <button onClick={() => remove("journals", j.id)}>
                        删除
                      </button>
                    </div>
                    <h3>{j.title}</h3>
                    <Plain html={j.content} />
                    {j.source && (data.annotations.some(a=>a.id===j.source) ? (
                      <button
                        className="source"
                        disabled={!data.annotations.some(a=>a.id===j.source)}
                        onClick={() => openSource(j.source)}
                      >
                        {data.annotations.some((a) => a.id === j.source)
                          ? "返回引用原文"
                          : "来源：" + j.source}
                      </button>
                    ) : <small className="source-note">{/^[0-9a-f]{8}-/.test(j.source) ? '关联批注已删除' : '章节：'+j.source}</small>)}
                  </article>
                ))}
            </section>
            <section>
              <h2>批注概览</h2>
              {data.annotations
                .filter((a) =>
                  data.assets.some(
                    (f) => f.book_id === book.id && f.id === a.asset_id,
                  ),
                )
                .map((a) => (
                  <button
                    className="annotation-overview"
                    key={a.id}
                    onClick={() => {
                      openSource(a.id);
                    }}
                  >
                    <span style={{ background: a.color }} />
                    {a.text || "绘图批注"}
                    {a.comment && " · " + a.comment}
                  </button>
                ))}
            </section>
            <button
              className="danger"
              onClick={() => {
                if (confirm("删除本书及其文件、批注、读后感和日志？"))
                  void run(async () => {
                    await api.remove("books", book.id);
                    setBookId(null);
                    setView("library");
                  });
              }}
            >
              删除此书
            </button>
          </>
        )}
        {view === "insights" && (
          <>
            <header className="page-heading">
              <div>
                <p className="eyebrow">THINK → DO → REFLECT</p>
                <h1>洞见与实践</h1>
                <p className="muted">让读过的文字，成为用得上的理解。</p>
              </div>
              <button
                className="primary"
                onClick={() => setDialog({ kind: "insight" })}
              >
                <Plus size={17} />
                新建洞见
              </button>
            </header>
            <div className="insights-grid">{renderInsights(data.insights)}</div>
            {!data.insights.length && (
              <div className="empty">
                <Lightbulb size={40} />
                <h2>给一个想法留下位置</h2>
                <p>从书中提炼，也可以记录自己的独立思考。</p>
              </div>
            )}
            <div className="section-heading">
              <h2>实践行动</h2>
              <button
                onClick={() =>
                  setDialog({ kind: "action", row: { status: "planned" } })
                }
              >
                新建行动
              </button>
            </div>
            {renderActions(data.actions)}
          </>
        )}
        {view === "goals" && (
          <>
            <header className="page-heading">
              <div>
                <p className="eyebrow">A LITTLE, OFTEN</p>
                <h1>阅读计划</h1>
                <p className="muted">计划提供方向，完成日期记录事实。</p>
              </div>
              <div className="row wrap"><button className="primary" onClick={() => setBooklistOpen(true)}>导入与安排书单</button><input aria-label="计划月份" type="month" value={month} onChange={e=>setMonth(e.target.value)}/></div>
            </header>
            {booklistOpen && <BooklistDialog data={data} month={month} close={() => setBooklistOpen(false)} reload={reload} />}
            <div className="goal-grid">
              {[month.slice(0, 4), month].map((period) => {
                const count = data.books.filter(
                  (b) =>
                    b.status === "completed" && b.completed.startsWith(period),
                ).length;
                const goal =
                  data.goals.find((g) => g.period === period)?.target || 0;
                return (
                  <div className="goal-card" key={period}>
                    <span className="eyebrow">
                      {period.length === 4 ? "年度阅读" : "月度阅读"} · {period}
                    </span>
                    <h2>
                      {count}
                      <small> / {goal || "—"} 本</small>
                    </h2>
                    <progress max={goal || 1} value={count} />
                    <label>
                      目标本数{" "}
                      <input
                        aria-label={period + " 目标"}
                        type="number"
                        min="0"
                        defaultValue={goal}
                        onBlur={(e) =>
                          void run(() =>
                            api.goal(
                              period,
                              Math.max(0, Math.floor(Number(e.target.value))),
                            ),
                          )
                        }
                      />
                    </label>
                  </div>
                );
              })}
            </div>
            <h2>{month} 的计划书单</h2>
            <p className="muted">
              勾选书籍安排到本月。每本书按实际完成日期统计一次。
            </p>
            <div className="plan-list">
              {data.books.map((b) => (
                <label key={b.id}>
                  <input
                    type="checkbox"
                    checked={data.plans.some(
                      (p) => p.book_id === b.id && p.month === month,
                    )}
                    onChange={(e) =>
                      void run(() => api.plan(b.id, month, e.target.checked))
                    }
                  />
                  <strong>{b.title}</strong>
                  <span>{statuses[b.status]}</span>
                  {b.completed && <small>完成于 {b.completed}</small>}
                </label>
              ))}
            </div>
            <h2>年度记录</h2>
            <p>
              {month.slice(0, 4)} 年完成 {completed} 本
              {yearTarget ? "，目标 " + yearTarget + " 本" : ""}。
            </p>
            <div className="month-chart">
              {Array.from({ length: 12 }, (_, n) => {
                const m =
                  month.slice(0, 4) + "-" + String(n + 1).padStart(2, "0");
                const nBooks = data.books.filter(
                  (b) => b.status === "completed" && b.completed.startsWith(m),
                ).length;
                return (
                  <div key={m}>
                    <strong>{nBooks}</strong>
                    <div style={{ height: Math.max(4, nBooks * 14) + "px" }} />
                    <small>{n + 1} 月</small>
                  </div>
                );
              })}
            </div>
          </>
        )}
        {view === "settings" && (
          <>
            <header className="page-heading">
              <div>
                <p className="eyebrow">YOUR DATA, YOURS</p>
                <h1>资料与设置</h1>
                <p className="muted">书籍和想法，只保存在这台电脑上。</p>
              </div>
            </header>
            <section className="settings-card">
              <h2>备份与恢复</h2>
              <p>完整备份包括图书文件、批注、读后感、日志、洞见和行动。</p>
              <div className="row">
                <button
                  className="primary"
                  onClick={() => void run(() => api.backup(), "备份已完成")}
                >
                  创建完整备份
                </button>
                <button
                  onClick={() =>
                    void run(() => api.restore(), "恢复操作已结束")
                  }
                >
                  从备份恢复
                </button>
              </div>
              <p className="muted">
                恢复前会自动保存当前书库。备份包含私人资料，请妥善保管。
              </p>
            </section>
            <section className="settings-card">
              <h2>ReadingOS {info?.version || "0.2.0"}</h2>
              <p>数据位置</p>
              <code>{info?.dataPath || "正在读取…"}</code>
              <p>
                运行方式：{info?.packaged ? "已打包桌面应用" : "开发桌面应用"}
              </p>
              <p>阅读格式：无 DRM PDF / EPUB；纸质书可独立建档。</p>
            </section>
          </>
        )}
      </ReadingAppShell>
      {dialog && (
        <RecordDialog
          key={dialog.row?.id || dialog.kind}
          dialog={dialog}
          data={data}
          close={() => {
            setDialog(null);
            void reload();
          }}
          done={async () => {
            await reload();
            setDialog(null);
            notify("已保存");
          }}
          notify={notify}
          openSource={openSource}
        />
      )}
      <Toast message={toast} close={() => setToast("")} />
    </>
  );
}
function Toast({ message, close }: { message: string; close: () => void }) {
  return message ? (
    <div className="toast" role="status">
      <span>{message}</span>
      <button aria-label="关闭提示" onClick={close}>
        ×
      </button>
    </div>
  ) : null;
}
