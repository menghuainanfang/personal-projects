export function subjectPath(categories:any[],id:string):string;
export function descendants(categories:any[],id:string):Set<string>;
export function subjectBooks(data:any,id:string,recursive?:boolean):Set<string>;
export function timeMonths(book:any,basis:string,plans:any[]):string[];
export function timeline(books:any[],basis:string,plans:any[]):{month:string;books:any[]}[];
export type KnowledgeNode={id:string;type:'book'|'subject'|'insight';label:string};
export type KnowledgeEdge={source:string;target:string;type:'categorized_as'|'parent_subject'|'related_to'|'derived_from';evidence?:string};
export function knowledgeGraph(data:any):{nodes:KnowledgeNode[];edges:KnowledgeEdge[]};
