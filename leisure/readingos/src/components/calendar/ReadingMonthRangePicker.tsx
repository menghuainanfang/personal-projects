import { useState } from 'react';
import { addMonths, localDate } from '../../../shared/dates.mjs';
import { CalendarPopover } from './CalendarPopover';
import { MonthGrid, MonthText } from './ReadingMonthPicker';
export function ReadingMonthRangePicker({start,end,onChange}: {start:string;end:string;onChange:(start:string,end:string)=>void}) {
  const [opened,setOpened]=useState(false),[from,setFrom]=useState(start),[to,setTo]=useState(end);
  const open=(value:boolean)=>{if(value){setFrom(start);setTo(end);}setOpened(value);};
  return <div className="month-range"><MonthText label="排期开始月份" value={start} onChange={value=>onChange(value,end)}/><MonthText label="排期结束月份" value={end} onChange={value=>onChange(start,value)}/><CalendarPopover label="选择排期月份范围" opened={opened} setOpened={open}>{close=><><div className="month-range-panels"><MonthGrid label="起始月份" value={from} onChange={setFrom} range={{start:from,end:to}}/><MonthGrid label="结束月份" value={to} onChange={setTo} range={{start:from,end:to}}/></div><p role={from>to?'alert':undefined}>{from>to?'结束月份不能早于开始月份':from+' 至 '+to}</p><div className="calendar-shortcuts"><button type="button" onClick={()=>{const now=localDate(new Date()).slice(0,7);setFrom(now);setTo(addMonths(now,2));}}>从本月起三个月</button><button type="button" disabled={from>to} className="primary" onClick={()=>{onChange(from,to);close();}}>应用月份范围</button></div></>}</CalendarPopover></div>;
}
