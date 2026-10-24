export const MAX_BYTES: number;
export const MAX_ROWS: number;
export interface InputBook { title: string; author: string; sourceMonth: string; error: string; bookId?: string }
export interface Candidate { id: string; title: string; author: string; status?: string }
export interface ParsedTable { records: string[][]; errors: string[]; delimiter: string; warning: string }
export interface Mapping { title: number; author: number; month: number }
export function normalize(value: string): string;
export function bookKey(row: {title: string; author?: string}): string;
export function validMonth(value: unknown): boolean;
export function rowError(row: {title: string; author: string}): string;
export function parseText(text: string): InputBook[];
export function parseDelimited(text: string, delimiter?: string): ParsedTable;
export function guessMapping(headers: string[]): Mapping;
export function mapColumns(table: ParsedTable, mapping: Mapping, hasHeader?: boolean): InputBook[];
export function identifyBook(row: {title: string; author: string}, books: Candidate[]): {status: 'existing'|'possible'|'new'; bookId?: string; candidates: Candidate[]};
export function monthRange(start: string, end: string): string[];
export function arrangeBooks(rows: {key: string; bookId?: string; month?: string; active: boolean}[], plans: {book_id: string; month: string}[], options: {start: string; end: string; limit?: number}): {months: string[]; assigned: string[]; overCapacity: string[]};
