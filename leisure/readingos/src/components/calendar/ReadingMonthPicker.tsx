import { useEffect, useId, useRef, useState } from 'react';
import { localDate, validMonth } from '../../../shared/dates.mjs';
import { CalendarPopover } from './CalendarPopover';
export function MonthGrid({value,onChange,label,range,counts}: {value:string;onChange:(month:string)=>void;label:string;range?:{start:string;end:string};counts?:Record<string,number>}) {
  const [year,setYear]=useState(Number(value.slice(0,4))||new Date().getFullYear());
  useEffect(()=>{if(validMonth(value))setYear(Number(value.slice(0,4)));},[value]);
  return <section className="month-panel" aria-label={label}><h3>{label}</h3><div className="month-year"><button type="button" aria-label={label+'上一年'} onClick={()=>setYear(y=>Math.max(1,y-1))}>‹</button><label>年份<input aria-label={label+'年份'} type="number" min={1} max={9999} value={year} onChange={e=>{const n=Number(e.target.value);if(n>=1&&n<=9999)setYear(n);}}/></label><button type="button" aria-label={label+'下一年'} onClick={()=>setYear(y=>Math.min(9999,y+1))}>›</button></div><div className="month-grid">{Array.from({length:12},(_,i)=>{const month=String(year).padStart(4,'0')+'-'+String(i+1).padStart(2,'0');return <button type="button" key={month} aria-label={label+' '+month} aria-pressed={value===month} data-in-range={range&&range.start<=month&&range.end>=month||undefined} onClick={()=>onChange(month)}>{i+1}月{counts?.[month]?<small>{counts[month]} 本</small>:null}</button>;})}</div></section>;
}
export function MonthText({label,value,onChange,disabled=false}: {label:string;value:string;onChange:(value:string)=>void;disabled?:boolean}) {
  const id=useId(),ref=useRef<HTMLInputElement>(null),[draft,setDraft]=useState(value);
  useEffect(()=>setDraft(value),[value]);
  const error=!validMonth(draft)?'请输入有效月份 YYYY-MM':'';
  useEffect(()=>{ref.current?.setCustomValidity(disabled?'':error);},[error,disabled]);
  return <div className="calendar-field"><label htmlFor={id}>{label}</label><input id={id} ref={ref} data-month-input aria-label={label} disabled={disabled} value={draft} placeholder="YYYY-MM" required aria-invalid={!!error&&!disabled} onChange={e=>{setDraft(e.target.value);if(validMonth(e.target.value))onChange(e.target.value);}}/>{error&&!disabled&&<small className="date-error" role="alert">{error}</small>}</div>;
}
export function ReadingMonthPicker({label,value,onChange,disabled=false,counts}: {label:string;value:string;onChange:(value:string)=>void;disabled?:boolean;counts?:Record<string,number>}) {
  const [opened,setOpened]=useState(false);
  return <div className="month-field"><MonthText label={label} value={value} onChange={onChange} disabled={disabled}/>{!disabled&&<CalendarPopover label={'打开'+label+'选择器'} opened={opened} setOpened={setOpened}>{close=><><MonthGrid label={label} value={value} counts={counts} onChange={month=>{onChange(month);close();}}/><button type="button" onClick={()=>{onChange(localDate(new Date()).slice(0,7));close();}}>本月</button></>}</CalendarPopover>}</div>;
}


