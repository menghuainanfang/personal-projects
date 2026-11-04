import {parseDate,validMonth} from './dates.mjs';
export function subjectPath(categories,id){const parts=[];const seen=new Set();while(id&&!seen.has(id)){seen.add(id);const c=categories.find(c=>c.id===id);if(!c)break;parts.unshift(c.name);id=c.parent_id;}return parts.join(' → ');}
export function descendants(categories,id){const ids=new Set([id]);let changed=true;while(changed){changed=false;for(const c of categories)if(ids.has(c.parent_id)&&!ids.has(c.id)){ids.add(c.id);changed=true;}}return ids;}
export function subjectBooks(data,id,recursive=true){const ids=recursive?descendants(data.subject_categories,id):new Set([id]);return new Set(data.book_subjects.filter(l=>ids.has(l.category_id)).map(l=>l.book_id));}
export function timeMonths(book,basis,plans){
 if(basis==='planned')return [...new Set(plans.filter(p=>p.book_id===book.id&&validMonth(p.month)).map(p=>p.month))];
 const value=book[basis];if(!value)return [];
 if(basis!=='created')return parseDate(value)?[value.slice(0,7)]:[];
 const date=new Date(value);return Number.isNaN(date.valueOf())?[]:[date.getFullYear()+'-'+String(date.getMonth()+1).padStart(2,'0')];
}
export function timeline(books,basis,plans){const groups=new Map();for(const book of books){const months=timeMonths(book,basis,plans);for(const month of months.length?months:['undated']){if(!groups.has(month))groups.set(month,new Map());groups.get(month).set(book.id,book);}}return [...groups].map(([month,items])=>({month,books:[...items.values()]}));}
export function knowledgeGraph(data){
 const nodes=[...data.books.map(b=>({id:b.id,type:'book',label:b.title})),...data.subject_categories.map(c=>({id:c.id,type:'subject',label:c.name})),...data.insights.map(i=>({id:i.id,type:'insight',label:i.title}))];
 const edges=[...data.book_subjects.map(l=>({source:l.book_id,target:l.category_id,type:'categorized_as'})),...data.subject_categories.filter(c=>c.parent_id).map(c=>({source:c.id,target:c.parent_id,type:'parent_subject'})),...data.insight_links.filter(l=>l.book_id).map(l=>({source:l.insight_id,target:l.book_id,type:'derived_from',evidence:l.id}))];
 return {nodes,edges};
}
