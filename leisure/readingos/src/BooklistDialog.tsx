import { useMemo, useRef, useState } from 'react';
import { Modal } from './Modal';
import { api, type Snapshot, type BatchPlanRow, type BatchPlanResult } from './domain';
import { MAX_BYTES, MAX_ROWS, normalize, parseText, parseDelimited, mapColumns, guessMapping, bookKey, identifyBook, arrangeBooks, type InputBook, type ParsedTable, type Mapping } from '../shared/booklist.mjs';

export function BooklistDialog({ data, month, close, reload }: {
  data: Snapshot; month: string; close: () => void; reload: () => Promise<void>;
}) {
  const [source, setSource] = useState('text');
  const [text, setText] = useState('');
  const [fileText, setFileText] = useState('');
  const [table, setTable] = useState<ParsedTable | null>(null);
  const [delimiter, setDelimiter] = useState('');
  const [hasHeader, setHasHeader] = useState(true);
  const [mapping, setMapping] = useState<Mapping>({ title: -1, author: -1, month: -1 });
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState('');
  const [rows, setRows] = useState<InputBook[] | null>(null);
  const [excluded, setExcluded] = useState<Set<number>>(new Set());
  const [choices, setChoices] = useState<Record<number, string>>({});
  const [manual, setManual] = useState<Record<number, string>>({});
  const [start, setStart] = useState(month);
  const [end, setEnd] = useState(() => {
    const n = Number(month.slice(0, 4)) * 12 + Number(month.slice(5)) + 1;
    return String(Math.floor(n / 12)).padStart(4, '0') + '-' + String(n % 12 + 1).padStart(2, '0');
  });
  const [capacity, setCapacity] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BatchPlanResult | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const previewRef = useRef<HTMLHeadingElement>(null);
  const fail = (message: string) => { setError(message); requestAnimationFrame(() => errorRef.current?.focus()); };
  const clearPreview = () => { setRows(null); setResult(null); setError(''); };
  const changeSchedule = () => { setResult(null); setError(''); };

  const resolved = useMemo(() => (rows || []).map((row, index) => {
    const match = identifyBook(row, data.books);
    if (match.status === 'new' && rows!.slice(0, index).some(previous => !previous.error && normalize(previous.title) === normalize(row.title) && bookKey(previous) !== bookKey(row))) match.status = 'possible';
    const choice = choices[index] || '';
    let mode = row.bookId || match.status === 'existing' ? 'link' : match.status === 'possible' ? 'review' : 'auto';
    let bookId = row.bookId || match.bookId;
    if (choice.startsWith('link:')) { mode = 'link'; bookId = choice.slice(5); }
    if (choice === 'create') { mode = 'create'; bookId = undefined; }
    const active = !row.error && !excluded.has(index) && mode !== 'review';
    return { ...row, match, mode, bookId, active, key: bookId || bookKey(row), month: manual[index] ?? row.sourceMonth };
  }), [rows, choices, data.books, excluded, manual]);
  const duplicateOf = useMemo(() => {
    const seen = new Map<string, number>(), duplicates = new Map<number, number>();
    (rows || []).forEach((row, i) => { const key = row.bookId || bookKey(row); if (seen.has(key)) duplicates.set(i, seen.get(key)!); else seen.set(key, i); });
    return duplicates;
  }, [rows]);
  const schedule = useMemo(() => {
    try {
      return { ...arrangeBooks(resolved, data.plans, { start, end, limit: capacity ? Number(capacity) : undefined }), error: '' };
    } catch (e) { return { assigned: [] as string[], months: [] as string[], overCapacity: [] as string[], error: (e as Error).message }; }
  }, [resolved, data.plans, start, end, capacity]);
  const unresolved = resolved.filter((row, i) => !row.error && !excluded.has(i) && row.mode === 'review').length;
  const waiting = resolved.filter((row, i) => row.active && !schedule.assigned[i]).length;
  const ready = resolved.filter(row => row.active).length;
  const blocked = !!schedule.error || unresolved > 0 || waiting > 0 || schedule.overCapacity.length > 0 || !ready;

  const readTable = (content: string, separator: string, header = hasHeader) => {
    const parsed = parseDelimited(content, separator); setTable(parsed);
    setMapping(header ? guessMapping(parsed.records[0] || []) : { title: 0, author: -1, month: -1 });
  };
  const generatePreview = () => {
    setError('');
    try {
      let items: InputBook[];
      if (source === 'text') items = parseText(text);
      else if (source === 'file') {
        if (!table) throw Error('请先选择 CSV 或 TSV 文件');
        items = mapColumns(table, mapping, hasHeader);
      } else items = data.books.filter(b => selected.has(b.id)).map(b => ({ title: b.title, author: b.author, bookId: b.id, sourceMonth: '', error: '' }));
      if (!items.length) throw Error('书单为空，请输入或选择书目');
      if (items.length > MAX_ROWS) throw Error('每批最多 500 条书目');
      const seen = new Set<string>(), duplicates = new Set<number>();
      items.forEach((row, i) => { const key = row.bookId || bookKey(row); if (seen.has(key)) duplicates.add(i); seen.add(key); });
      setRows(items); setExcluded(duplicates); setChoices({}); setManual({}); setResult(null);
      requestAnimationFrame(() => previewRef.current?.focus());
    } catch (e) { fail((e as Error).message); }
  };
  const save = async () => {
    if (blocked) { fail(schedule.error || '请先确认可能重复的书目，并为全部参与条目安排月份，或暂时排除它们。'); return; }
    setBusy(true); setError('');
    const payload: BatchPlanRow[] = resolved.map((row, i) => ({
      title: row.error ? row.title.slice(0, 500) : row.title, author: row.error ? row.author.slice(0, 200) : row.author, bookId: row.bookId,
      mode: row.error ? 'invalid' : excluded.has(i) ? 'skip' : row.mode as BatchPlanRow['mode'],
      month: schedule.assigned[i] || '',
    }));
    try { const saved = await api.batchPlans({ rows: payload, limit: capacity ? Number(capacity) : undefined }); await reload(); setResult(saved); }
    catch (e) { fail(`整批保存失败：${ready} 条；已写入 0 条。` + (e as Error).message.replace(/^Error invoking remote method '[^']+': (?:Error: )?/, '')); await reload(); }
    finally { setBusy(false); }
  };
  return <Modal title="导入与安排书单" wide onClose={() => { if (!busy) close(); }} onSubmit={e => { e.preventDefault(); if (rows) void save(); else generatePreview(); }}>
    <p className="muted">先检查书目，再按输入顺序均匀安排。已有阅读记录和原计划保留。</p>
    {error && <p className="import-error" role="alert" tabIndex={-1} ref={errorRef}>{error}</p>}
    <details className="import-input" open={!rows}><summary>{rows ? `书单输入 · 已解析 ${rows.length} 条，展开修改` : '输入书单'}</summary>
    <div className="import-sources" role="group" aria-label="书单来源">
      {[['text', '粘贴书单'], ['file', 'CSV / TSV 文件'], ['library', '从书库选择']].map(([value, label]) => <button type="button" key={value} aria-pressed={source === value} className={source === value ? 'active' : ''} onClick={() => { setSource(value); clearPreview(); }}>{label}</button>)}
    </div>
    {source === 'text' && <label>每行一本书；可用 Tab 分隔书名和作者<textarea aria-label="粘贴书单" rows={6} value={text} onChange={e => { setText(e.target.value); clearPreview(); }} placeholder={'慢读的练习\n时间,与理解\n关于“停顿”的笔记'} /></label>}
    {source === 'file' && <>
      <label>选择 UTF-8 CSV / TSV，最多 2 MiB、500 条<input aria-label="书单文件" type="file" accept=".csv,.tsv,text/csv,text/tab-separated-values" onChange={async e => {
        clearPreview(); setTable(null); const file = e.target.files?.[0]; if (!file) return;
        try {
          if (file.size > MAX_BYTES) throw Error('文件不能超过 2 MiB');
          let content: string;
          try { content = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()); } catch { throw Error('文件编码无效，请另存为 UTF-8'); }
          const separator = file.name.toLowerCase().endsWith('.tsv') ? '\t' : '';
          setFileText(content); setDelimiter(separator); readTable(content, separator);
        } catch (e) { fail((e as Error).message); }
      }} /></label>
      <div className="import-mapping">
        <label>分隔符<select aria-label="书单分隔符" value={delimiter} onChange={e => { clearPreview(); setDelimiter(e.target.value); try { readTable(fileText, e.target.value); } catch (e) { fail((e as Error).message); } }}><option value="">自动识别</option><option value=",">逗号</option><option value={'\t'}>Tab</option><option value=";">分号</option><option value="|">竖线</option></select></label>
        <label className="checkbox-label"><input type="checkbox" checked={hasHeader} onChange={e => { clearPreview(); setHasHeader(e.target.checked); if (table) setMapping(e.target.checked ? guessMapping(table.records[0] || []) : { title: 0, author: -1, month: -1 }); }} />首行为表头</label>
      </div>
      {table && <div className="import-mapping">{(['title', 'author', 'month'] as const).map((key, i) => <label key={key}>{['书名列', '作者列', '月份列'][i]}<select aria-label={['书名列', '作者列', '月份列'][i]} value={mapping[key]} onChange={e => { clearPreview(); setMapping({ ...mapping, [key]: Number(e.target.value) }); }}><option value={-1}>{key === 'title' ? '请选择' : '不使用'}</option>{(table.records[0] || []).map((column, index) => <option key={index} value={index}>{index + 1} · {hasHeader ? column || '空表头' : '第 ' + (index + 1) + ' 列'}</option>)}</select></label>)}</div>}
      {table?.warning && <p className="muted">{table.warning}</p>}
    </>}
    {source === 'library' && <>
      <label>搜索书库<input aria-label="筛选可选书目" value={query} onChange={e => setQuery(e.target.value)} /></label>
      <div className="import-library">{data.books.filter(b => (b.title + b.author).toLowerCase().includes(query.toLowerCase())).map(b => <label className="checkbox-label" key={b.id}><input type="checkbox" checked={selected.has(b.id)} onChange={e => { clearPreview(); setSelected(current => { const next = new Set(current); if (e.target.checked) next.add(b.id); else next.delete(b.id); return next; }); }} /><span>{b.title}<small className="muted"> · {b.author || '未署名'}</small></span></label>)}</div>
      <p className="muted">已选 {selected.size} 本，按书库顺序预览。</p>
    </>}
    </details>
    <div className="import-schedule">
      <label>开始月份<input aria-label="排期开始月份" type="month" value={start} onChange={e => { setStart(e.target.value); changeSchedule(); }} /></label>
      <label>结束月份<input aria-label="排期结束月份" type="month" value={end} onChange={e => { setEnd(e.target.value); changeSchedule(); }} /></label>
      <label>每月最多新安排<input aria-label="每月新增上限" type="number" min="1" max="500" placeholder="不限" value={capacity} onChange={e => { setCapacity(e.target.value); changeSchedule(); }} /></label>
    </div>
    <p className="import-hint">顺序均匀安排：已有计划计入均衡权重；上限只限制本次新增。文件月份与手动月份优先，已安排书目默认沿用范围内的原月份。</p>
    {rows && <section className="import-preview">
      <div className="section-heading"><h3 tabIndex={-1} ref={previewRef}>书单预览 · {rows.length} 条</h3><button type="button" onClick={generatePreview}>重新生成预览</button></div>
      <p className="import-hint">参与有效条目 {ready} 条 · 待确认 {unresolved} 条 · 无效 {resolved.filter(row => row.error).length} 条 · 暂时排除 {excluded.size} 条</p>
      {!ready && !unresolved && <p className="import-error" role="status">没有可保存的有效条目，请修改输入或重新选择书目。</p>}
      {(schedule.error || unresolved > 0 || waiting > 0 || schedule.overCapacity.length > 0) && <p className="import-error" role="status">{schedule.error || `待确认 ${unresolved} 条，待安排 ${waiting} 条。`}{schedule.overCapacity.length > 0 && ` ${schedule.overCapacity.join('、')} 超过本次新增上限。`} 可增加月份、调整上限或暂时排除条目。</p>}
      <ol className="import-list">{resolved.map((row, i) => {
        const included = !excluded.has(i);
        const label = row.error ? '无效' : duplicateOf.has(i) || row.mode === 'review' ? '可能重复' : row.mode === 'link' ? '已存在' : '待创建';
        const exists = row.bookId && data.plans.some(p => p.book_id === row.bookId && p.month === schedule.assigned[i]);
        return <li key={i} className="import-row">
          <div className="import-row-heading"><label className="checkbox-label"><input aria-label={`参与第${i + 1}条`} type="checkbox" disabled={!!row.error} checked={included && !row.error} onChange={e => { changeSchedule(); setExcluded(current => { const next = new Set(current); if (e.target.checked) next.delete(i); else next.add(i); return next; }); }} /><span className="import-title">{i + 1}. {row.title || '（空书名）'}</span></label><span className="status">{label}</span></div>
          <p className="muted">{row.author || '未提供作者'}{duplicateOf.has(i) && ` · 与第${duplicateOf.get(i)! + 1}条相同，默认排除`}{row.sourceMonth && ` · 文件月份 ${row.sourceMonth}`}{!included && ' · 暂时排除'}{exists && ' · 此月已有计划，将跳过重复关系'}</p>
          {row.error ? <p className="import-error">{row.error}</p> : <div className="import-row-controls">
            {row.match.status === 'possible' && !rows[i].bookId && <label>确认书目<select aria-label={`第${i + 1}条匹配方式`} value={choices[i] || ''} onChange={e => { changeSchedule(); setChoices({ ...choices, [i]: e.target.value }); }}><option value="">请选择关联或新建</option>{row.match.candidates.map(b => <option key={b.id} value={'link:' + b.id}>关联：{b.title} · {b.author || '未署名'}</option>)}<option value="create">确认新建独立书目</option></select></label>}
            <label>目标月份<input aria-label={`第${i + 1}条目标月份`} type="month" disabled={!row.active} value={schedule.assigned[i] || ''} onChange={e => { changeSchedule(); setManual({ ...manual, [i]: e.target.value }); }} /></label>
            {manual[i] !== undefined && <button type="button" onClick={() => { changeSchedule(); setManual({ ...manual, [i]: '' }); }}>自动安排</button>}
          </div>}
        </li>;
      })}</ol>
    </section>}
    {result && <p className="import-result" role="status">已安排 {result.scheduled} 条；新建 {result.created} 本，关联已有 {result.linked} 条；跳过 {result.skipped} 条（其中重复 {result.duplicates} 条）；失败 {result.failed} 条。</p>}
    <div className="modal-footer"><button type="button" disabled={busy} onClick={close}>{result ? '完成' : '取消'}</button>{rows ? <button className="primary" disabled={busy || blocked || !!result}>{busy ? '保存中…' : result ? '已保存' : '确认保存'}</button> : <button className="primary">生成预览</button>}</div>
  </Modal>;
}
