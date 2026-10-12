import { zhCN } from "./locales/zh-CN";
export type Row = { id: string; [key: string]: any };
export type Book = Row & {
  title: string;
  author: string;
  tags: string;
  category: string;
  cover: string;
  status: string;
  started: string;
  completed: string;
};
export type Asset = Row & {
  book_id: string;
  format: "pdf" | "epub";
  name: string;
};
export type Annotation = Row & {
  asset_id: string;
  kind: string;
  anchor: string;
  color: string;
  width: number;
  text: string;
  comment: string;
};
export type Snapshot = {
  books: Book[];
  assets: Asset[];
  annotations: Annotation[];
  progress: Row[];
  summaries: Row[];
  summary_revisions: Row[];
  journals: Row[];
  insights: Row[];
  insight_links: Row[];
  actions: Row[];
  feedback: Row[];
  goals: Row[];
  plans: Row[];
  bookmarks: Row[];
};
export interface DesktopAPI {
  snapshot(): Promise<Snapshot>;
  save(table: string, data: Partial<Row>): Promise<string>;
  remove(table: string, id: string): Promise<void>;
  summary(bookId: string, content: string): Promise<void>;
  progress(id: string, location: string): Promise<void>;
  annotations(assetId: string, rows: Annotation[]): Promise<void>;
  goal(period: string, target: number): Promise<void>;
  plan(bookId: string, month: string, enabled: boolean): Promise<void>;
  importBook(
    bookId?: string,
  ): Promise<{ bookId?: string; duplicate?: boolean; error?: string }[]>;
  readAsset(id: string): Promise<Uint8Array>;
  cover(): Promise<string | null>;
  backup(): Promise<string | null>;
  restore(): Promise<string | null>;
  exportMarkdown(id: string): Promise<string | null>;
  info(): Promise<{ version: string; dataPath: string; packaged: boolean }>;
}
declare global {
  interface Window {
    readingos: DesktopAPI;
  }
}
export const api = window.readingos;
export const statuses: Record<string, string> = zhCN.bookStatus;
export const actionStatuses: Record<string, string> = zhCN.actionStatus;
export const today = () => new Date().toLocaleDateString("sv-SE");
export const empty: Snapshot = {
  books: [],
  assets: [],
  annotations: [],
  progress: [],
  summaries: [],
  summary_revisions: [],
  journals: [],
  insights: [],
  insight_links: [],
  actions: [],
  feedback: [],
  goals: [],
  plans: [],
  bookmarks: [],
};
