import { useEffect, useId, useRef, useState } from 'react';
import { DayPicker } from '@daypicker/react';
import { zhCN } from '@daypicker/react/locale';
import { localDate, parseDate } from '../../../shared/dates.mjs';
import { CalendarPopover } from './CalendarPopover';
export function ReadingDatePicker({ label, value, onChange, required=false, disabled=false }: {label:string;value:string;onChange:(value:string)=>void;required?:boolean;disabled?:boolean}) {
  const id=useId(), input=useRef<HTMLInputElement>(null);
  const [draft,setDraft]=useState(value),[opened,setOpened]=useState(false),[month,setMonth]=useState(parseDate(value)||new Date());
  useEffect(()=>{setDraft(value);const date=parseDate(value);if(date)setMonth(date);},[value]);
  const error=draft&&!parseDate(draft)?'请输入有效日期 YYYY-MM-DD':required&&!draft?'请选择或填写日期':'';
  useEffect(()=>{input.current?.setCustomValidity(error);},[error]);
  const change=(text:string)=>{setDraft(text);const date=parseDate(text);if(date){setMonth(date);onChange(text);}else if(!text&&!required)onChange('');};
  return <div className="calendar-field"><label htmlFor={id}>{label}</label><div className="calendar-input-row"><input id={id} ref={input} aria-label={label} type="text" placeholder="YYYY-MM-DD" value={draft} required={required} disabled={disabled} aria-invalid={!!error} aria-describedby={error?id+'-error':undefined} onChange={event=>change(event.target.value)}/>{!disabled&&<CalendarPopover label={'打开'+label+'日历'} opened={opened} setOpened={setOpened}>{close=><>
    <DayPicker mode="single" locale={zhCN} weekStartsOn={1} captionLayout="dropdown" navLayout="after" month={month} onMonthChange={setMonth} startMonth={new Date(Math.min(1900,month.getFullYear()),0,1)} endMonth={new Date(Math.max(2100,month.getFullYear()),11,31)} selected={parseDate(draft)} onSelect={date=>{if(date){change(localDate(date));close();}}} autoFocus showOutsideDays labels={{labelDayButton:date=>'选择 '+localDate(date),labelNext:()=> '下个月',labelPrevious:()=> '上个月',labelMonthDropdown:()=> '选择月份',labelYearDropdown:()=> '选择年份'}} />
    <div className="calendar-shortcuts"><button type="button" onClick={()=>{change(localDate(new Date()));close();}}>今天</button>{!required&&<button type="button" onClick={()=>{change('');close();}}>清空</button>}</div>
  </>}</CalendarPopover>}</div>{error&&<small id={id+'-error'} className="date-error" role="alert">{error}</small>}</div>;
}
