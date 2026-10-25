import Papa from 'papaparse';

export const MAX_BYTES = 2 * 1024 * 1024;
export const MAX_ROWS = 500;
export function normalize(value) {
  return String(value).normalize('NFKC').trim().replace(/\s+/g, ' ').toLowerCase();
}
export function bookKey(row) {
  return normalize(row.title) + '\0' + normalize(row.author || '');
}
export function validMonth(value) {
  return typeof value === 'string' && /^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(value);
}
export function rowError(row) {
  if (typeof row.title !== 'string' || !row.title.trim()) return '书名不能为空';
  if (row.title.length > 500) return '书名不能超过 500 字符';
  if (typeof row.author !== 'string' || row.author.length > 200) return '作者不能超过 200 字符';
  if (/[\u0000]/.test(row.title + row.author)) return '书名或作者含有无效字符';
  return '';
}
function checkText(text) {
  if (new TextEncoder().encode(text).byteLength > MAX_BYTES) throw Error('书单不能超过 2 MiB');
  if (text.includes('\0')) throw Error('文件编码无效，请另存为 UTF-8');
}
export function parseText(text) {
  checkText(text);
  const rows = text.replace(/^\uFEFF/, '').split(/\r\n|\n|\r/).filter(line => line.trim()).map(line => {
    const parts = line.split('\t');
    const row = { title: parts[0].trim(), author: (parts[1] || '').trim(), sourceMonth: '', error: '' };
    row.error = parts.length > 2 ? '纯文本每行最多两列：书名、作者' : rowError(row);
    return row;
  });
  if (rows.length > MAX_ROWS) throw Error('每批最多 500 条书目，请分批导入');
  return rows;
}
export function parseDelimited(text, delimiter = '') {
  checkText(text);
  const table = { records: [], errors: [], delimiter: '', warning: '' };
  Papa.parse(text, {
    delimiter, delimitersToGuess: [',', '\t', ';', '|'], header: false,
    dynamicTyping: false, skipEmptyLines: 'greedy',
    step(result, parser) {
      table.records.push(result.data);
      table.errors.push(result.errors.filter(e => e.code !== 'UndetectableDelimiter').map(e => e.code + '：' + e.message).join('；'));
      table.delimiter = result.meta.delimiter;
      if (result.errors.some(e => e.code === 'UndetectableDelimiter')) table.warning = '未检测到多列分隔符；可手动选择分隔符，或按单列书名导入。';
      if (table.records.length > MAX_ROWS + 1) parser.abort();
    },
  });
  return table;
}
export function guessMapping(headers) {
  const find = names => headers.findIndex(h => names.includes(normalize(h).replace(/[\s_]/g, '')));
  return {
    title: find(['书名', '标题', '名称', 'title', 'booktitle', 'name']),
    author: find(['作者', '著者', 'author', 'authors']),
    month: find(['月份', '计划月份', 'month', 'plannedmonth']),
  };
}
export function mapColumns(table, mapping, hasHeader = true) {
  if (mapping.title < 0) throw Error('请选择书名所在的列');
  if (hasHeader && table.errors[0]) throw Error('表头解析失败：' + table.errors[0]);
  const records = table.records.slice(hasHeader ? 1 : 0);
  if (records.length > MAX_ROWS) throw Error('每批最多 500 条书目，请分批导入');
  const width = table.records[0]?.length || 0;
  return records.map((record, i) => {
    const rawMonth = (record[mapping.month] || '').trim();
    const match = rawMonth.match(/^(\d{4})(?:[-/]|年)(\d{1,2})月?$/);
    const sourceMonth = match ? match[1] + '-' + match[2].padStart(2, '0') : rawMonth;
    const row = { title: (record[mapping.title] || '').trim(), author: (record[mapping.author] || '').trim(), sourceMonth, error: '' };
    row.error = table.errors[i + (hasHeader ? 1 : 0)] || (record.length !== width ? '列数与首行不一致，请检查分隔符或引号' : '') || rowError(row) || (sourceMonth && !validMonth(sourceMonth) ? '月份无效，请使用 YYYY-MM' : '');
    return row;
  });
}
export function identifyBook(row, books) {
  const candidates = books.filter(book => normalize(book.title) === normalize(row.title));
  const exact = candidates.filter(book => bookKey(book) === bookKey(row));
  if (exact.length === 1) return { status: 'existing', bookId: exact[0].id, candidates };
  return { status: candidates.length ? 'possible' : 'new', candidates };
}
export function monthRange(start, end) {
  if (!validMonth(start) || !validMonth(end) || start > end) throw Error('请填写有效的起止月份，结束月份不能早于开始月份');
  const index = month => Number(month.slice(0, 4)) * 12 + Number(month.slice(5)) - 1;
  const from = index(start), to = index(end);
  if (to - from >= 120) throw Error('一次最多安排 120 个月');
  return Array.from({ length: to - from + 1 }, (_, i) => String(Math.floor((from + i) / 12)).padStart(4, '0') + '-' + String((from + i) % 12 + 1).padStart(2, '0'));
}

// First compute balanced monthly quotas, then fill them in input order.
export function arrangeBooks(rows, plans, { start, end, limit }) {
  const months = monthRange(start, end);
  if (limit !== undefined && (!Number.isInteger(limit) || limit < 1 || limit > MAX_ROWS)) throw Error('每月新增上限应为 1–500，或留空');
  const existing = new Set(plans.map(p => p.book_id + '\0' + p.month));
  const load = Object.fromEntries(months.map(m => [m, plans.filter(p => p.month === m).length]));
  const added = {}, seen = new Set(), assigned = rows.map(() => ''), pending = [], first = new Map(), aliases = [];
  rows.forEach((row, index) => {
    if (!row.active) return;
    if (!row.month && first.has(row.key)) { aliases.push([index, first.get(row.key)]); return; }
    if (!first.has(row.key)) first.set(row.key, index);
    let month = row.month || (row.bookId ? months.find(m => existing.has(row.bookId + '\0' + m)) : '');
    if (!month) { pending.push(index); return; }
    if (!validMonth(month)) throw Error('目标月份无效');
    assigned[index] = month;
    const key = row.key + '\0' + month;
    if (!seen.has(key) && !(row.bookId && existing.has(row.bookId + '\0' + month))) added[month] = (added[month] || 0) + 1;
    seen.add(key);
  });
  const quota = Object.fromEntries(months.map(m => [m, 0]));
  for (const index of pending) {
    const eligible = months.filter(m => limit === undefined || (added[m] || 0) + quota[m] < limit);
    if (!eligible.length) break;
    const month = eligible.reduce((best, m) => load[m] + (added[m] || 0) + quota[m] < load[best] + (added[best] || 0) + quota[best] ? m : best);
    quota[month]++;
  }
  let next = 0;
  for (const month of months) for (let n = 0; n < quota[month]; n++) assigned[pending[next++]] = month;
  for (const [index, original] of aliases) assigned[index] = assigned[original];
  return { months, assigned, overCapacity: Object.keys(added).filter(m => limit !== undefined && added[m] > limit) };
}
