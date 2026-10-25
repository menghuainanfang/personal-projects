import { Stack } from '@mantine/core';
import { type Book, type Snapshot } from '../../domain';
export function ReadingContextPanel({ book, data, journal, source }: { book: Book; data: Snapshot; journal: (id: string) => void; source: (id: string) => void }) {
  const journals = data.journals.filter(j => j.book_id === book.id);
  const assets = data.assets.filter(a => a.book_id === book.id);
  const annotations = data.annotations.filter(a => assets.some(f => f.id === a.asset_id));
  const insights = data.insights.filter(i => data.insight_links.some(l => l.insight_id === i.id && l.book_id === book.id));
  const actions = data.actions.filter(a => a.book_id === book.id);
  return <Stack gap="lg" className="book-context">
    <div><p className="eyebrow">当前阅读档案</p><h2>{book.title}</h2><p className="muted">{book.author || '未署名'}</p></div>
    <section><h3>关联日志 · {journals.length}</h3>{journals.length ? journals.slice(0,8).map(j => <button key={j.id} onClick={() => journal(j.id)}>{j.title}<small>{j.date}</small></button>) : <p className="muted">这本书还没有阅读日志。</p>}</section>
    <section><h3>原文批注 · {annotations.length}</h3>{annotations.slice(0,6).map(a => <button key={a.id} onClick={() => source(a.id)}>{a.text || '绘图批注'}</button>)}</section>
    <section><h3>洞见与实践</h3>{insights.map(i => <p key={i.id}>{i.title}</p>)}{actions.map(a => <p key={a.id}>{a.description}</p>)}{!insights.length && !actions.length && <p className="muted">从心得或日志中整理想法，再记录一次实践。</p>}</section>
  </Stack>;
}
