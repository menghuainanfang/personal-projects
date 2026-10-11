import { useEffect, useRef, useState } from "react";
import {
  api,
  statuses,
  actionStatuses,
  today,
  type Row,
  type Snapshot,
} from "./domain";
import { Editor } from "./Editor";
export type Dialog = {
  kind: string;
  row?: Partial<Row>;
  bookId?: string;
  annotationId?: string;
  journalId?: string;
  insightId?: string;
};
export function RecordDialog({
  dialog,
  data,
  close,
  done,
  notify,
}: {
  dialog: Dialog;
  data: Snapshot;
  close: () => void;
  done: () => Promise<void>;
  notify: (s: string) => void;
}) {
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    form.current?.querySelector<HTMLInputElement>("input,textarea")?.focus();
    return () => previous?.focus();
  }, []);
  const [row, setRow] = useState<Partial<Row>>({ ...dialog.row }),
    [busy, setBusy] = useState(false),
    [journalId, setJournalId] = useState(dialog.row?.id || crypto.randomUUID()),
    [selectedBooks, setSelectedBooks] = useState<string[]>(
      dialog.row?.id
        ? data.insight_links
            .filter((l) => l.insight_id === dialog.row!.id && l.book_id)
            .map((l) => l.book_id)
        : dialog.bookId
          ? [dialog.bookId]
          : [],
    );
  const set = (k: string, v: any) => setRow((r) => ({ ...r, [k]: v }));
  const kind = dialog.kind;
  const titles: Record<string, string> = {
    book: "书籍资料",
    journal: "阅读日志",
    insight: "洞见卡片",
    action: "实践行动",
    feedback: "实践反馈",
  };
  const field = (k: string, label: string, type = "text", required = false) => (
    <label>
      {label}
      <input
        aria-label={label}
        type={type}
        value={row[k] || ""}
        onChange={(e) => set(k, e.target.value)}
        required={required}
      />
    </label>
  );
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (kind === "book") await api.save("books", row);
      if (kind === "journal")
        await api.save("journals", {
          ...row,
          id: journalId || undefined,
          title: row.title || "阅读随记",
          source: row.source || "",
          content: row.content || "",
        });
      if (kind === "insight") {
        const id = await api.save("insights", {
          ...row,
          content: row.content || "",
        });
        const links = data.insight_links.filter((l) => l.insight_id === id);
        for (const l of links)
          if (l.book_id && !selectedBooks.includes(l.book_id))
            await api.remove("insight_links", l.id);
        for (const b of selectedBooks)
          if (!links.some((l) => l.book_id === b))
            await api.save("insight_links", {
              insight_id: id,
              book_id: b,
              annotation_id: dialog.annotationId || null,
              journal_id: dialog.journalId || null,
            });
      }
      if (kind === "action")
        await api.save("actions", {
          ...row,
          insight_id: row.insight_id || dialog.insightId || null,
          book_id: row.book_id || dialog.bookId || null,
          planned: row.planned || "",
          status: row.status || "planned",
        });
      if (kind === "feedback") await api.save("feedback", row);
      await done();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <form
        ref={form}
        role="dialog"
        aria-modal="true"
        aria-label={titles[kind]}
        className={"modal " + (kind === "journal" ? "wide" : "")}
        onSubmit={save}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.preventDefault();
            close();
          }
          if (e.key === "Tab") {
            const elements = Array.from(
              e.currentTarget.querySelectorAll<HTMLElement>(
                'button:not(:disabled),input,select,textarea,[contenteditable="true"]',
              ),
            );
            const first = elements[0],
              last = elements[elements.length - 1];
            if (e.shiftKey && document.activeElement === first) {
              e.preventDefault();
              last?.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
              e.preventDefault();
              first?.focus();
            }
          }
        }}
      >
        <div className="section-heading">
          <h2>{titles[kind]}</h2>
          <button type="button" aria-label="关闭对话框" onClick={close}>
            ×
          </button>
        </div>
        {kind === "book" && (
          <>
            {field("title", "书名", "text", true)}
            {field("author", "作者")}
            <div className="row">
              {field("tags", "标签（逗号分隔）")}
              {field("category", "分类")}
            </div>
            <label>
              阅读状态
              <select
                value={row.status || "want"}
                onChange={(e) => set("status", e.target.value)}
              >
                {Object.entries(statuses).map(([v, l]) => (
                  <option value={v} key={v}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <div className="row">
              {field("started", "开始日期", "date")}
              {field("completed", "完成日期", "date")}
            </div>
            <div className="row">
              <button
                type="button"
                onClick={async () => {
                  const c = await api.cover();
                  if (c) set("cover", c);
                }}
              >
                选择本地封面
              </button>
              {row.cover && (
                <>
                  <img
                    className="cover-preview"
                    src={row.cover}
                    alt="封面预览"
                  />
                  <button type="button" onClick={() => set("cover", "")}>
                    移除封面
                  </button>
                </>
              )}
            </div>
          </>
        )}
        {kind === "journal" && (
          <>
            {field("title", "日志标题")}
            {field("date", "日志日期", "date", true)}
            <label>
              关联章节或批注
              <select
                value={row.source || ""}
                onChange={(e) => set("source", e.target.value)}
              >
                <option value="">不关联</option>
                {data.annotations
                  .filter((a) =>
                    data.assets.some(
                      (f) => f.id === a.asset_id && f.book_id === row.book_id,
                    ),
                  )
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.text?.slice(0, 60) || "绘图批注"}
                    </option>
                  ))}
              </select>
              <input
                aria-label="章节说明"
                placeholder="也可输入章节说明"
                value={row.source || ""}
                onChange={(e) => set("source", e.target.value)}
              />
            </label>
            <Editor
              label="日志正文"
              value={row.content || ""}
              onSave={async (html) => {
                set("content", html);
                const id = await api.save("journals", {
                  ...row,
                  id: journalId || undefined,
                  content: html,
                  title: row.title || "阅读随记",
                  date: row.date || today(),
                  source: row.source || "",
                });
                setJournalId(id);
              }}
            />
            <small className="muted">正文自动保存，关闭后仍会保留。</small>
          </>
        )}
        {kind === "insight" && (
          <>
            {field("title", "洞见标题", "text", true)}
            <label>
              内容
              <textarea
                aria-label="洞见内容"
                rows={8}
                value={row.content || ""}
                onChange={(e) => set("content", e.target.value)}
              />
            </label>
            <fieldset>
              <legend>关联书籍</legend>
              {data.books.map((b) => (
                <label className="checkbox-label" key={b.id}>
                  <input
                    type="checkbox"
                    checked={selectedBooks.includes(b.id)}
                    onChange={(e) =>
                      setSelectedBooks(
                        e.target.checked
                          ? [...selectedBooks, b.id]
                          : selectedBooks.filter((v) => v !== b.id),
                      )
                    }
                  />
                  {b.title}
                </label>
              ))}
            </fieldset>
          </>
        )}
        {kind === "action" && (
          <>
            {field("description", "行动描述", "text", true)}
            {field("planned", "计划日期", "date")}
            <label>
              源洞见
              <select
                value={row.insight_id || dialog.insightId || ""}
                onChange={(e) => set("insight_id", e.target.value)}
              >
                <option value="">独立行动</option>
                {data.insights.map((i) => (
                  <option value={i.id} key={i.id}>
                    {i.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              状态
              <select
                value={row.status || "planned"}
                onChange={(e) => set("status", e.target.value)}
              >
                {Object.entries(actionStatuses).map(([v, l]) => (
                  <option value={v} key={v}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
        {kind === "feedback" && (
          <>
            {field("date", "反馈日期", "date", true)}
            <label>
              实践结果与反思
              <textarea
                aria-label="实践反馈"
                rows={8}
                value={row.content || ""}
                onChange={(e) => set("content", e.target.value)}
                required
              />
            </label>
          </>
        )}
        <div className="modal-footer">
          <button type="button" onClick={close}>
            关闭
          </button>
          <button className="primary" disabled={busy}>
            {busy ? "保存中…" : "保存"}
          </button>
        </div>
      </form>
    </div>
  );
}
